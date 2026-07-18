import os
import json
import re
import io
import requests
from dotenv import load_dotenv
from PIL import Image
import imagehash
import google.generativeai as genai
from app.database.db import get_db_connection
from app.services.twilio_client import send_whatsapp_message

# Load environment variables
load_dotenv()

# Twilio Credentials needed to download secure media
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

# Configure Google Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""), transport="rest")

def process_tariffs_and_ceilings(policy_id: str, extracted_items: list):
    """
    Looks up each extracted item in the tariffs table (case-insensitive).
    Caps the reimbursement for each item at the tariff max limit.
    Flags items not found.
    Calculates total requested and total assessed.
    Compares against the policyholder's remaining annual ceiling limit.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch policy information
    cursor.execute("SELECT owner_name, coverage_limit, deductible, ceiling_total, ceiling_used FROM policies WHERE policy_id = ?", (policy_id,))
    policy = cursor.fetchone()
    
    if not policy:
        conn.close()
        return None
        
    owner_name = policy["owner_name"]
    deductible = policy["deductible"]
    ceiling_total = policy["ceiling_total"]
    ceiling_used = policy["ceiling_used"]
    remaining_ceiling = max(0.0, ceiling_total - ceiling_used)
    
    processed_items = []
    total_requested = 0.0
    total_assessed = 0.0
    flagged_items = []
    
    # 2. Iterate through receipt items and lookup their tariffs
    for item in extracted_items:
        name = item["name"]
        price = item["price"]
        total_requested += price
        
        # Look up in tariffs table (case-insensitive matching)
        cursor.execute("SELECT max_reimbursable FROM tariffs WHERE LOWER(item_name) = LOWER(?)", (name,))
        tariff_row = cursor.fetchone()
        
        if tariff_row:
            max_reimb = tariff_row["max_reimbursable"]
            assessed_price = min(price, max_reimb)
            processed_items.append({
                "name": name,
                "requested": price,
                "max_reimbursable": max_reimb,
                "assessed": assessed_price,
                "status": "APPROVED" if assessed_price == price else "CAPPED"
            })
            total_assessed += assessed_price
        else:
            # Item was not found in the official tariff table (Flagged!)
            processed_items.append({
                "name": name,
                "requested": price,
                "max_reimbursable": None,
                "assessed": 0.0,
                "status": "FLAGGED_UNKNOWN"
            })
            flagged_items.append(name)
            
    conn.close()
    
    # 3. Check ceiling limit thresholds
    is_over_ceiling = total_assessed > remaining_ceiling
    is_near_ceiling = False
    
    if not is_over_ceiling:
        # Near ceiling: remaining ceiling after payout is less than 10 TND, or total used exceeds 90% of total ceiling
        if (remaining_ceiling - total_assessed <= 10.0) or ((ceiling_used + total_assessed) / ceiling_total >= 0.9):
            is_near_ceiling = True
            
    # Payout is capped at the remaining ceiling
    payout_amount = min(total_assessed, remaining_ceiling)
    
    return {
        "owner_name": owner_name,
        "deductible": deductible,
        "processed_items": processed_items,
        "total_requested": total_requested,
        "total_assessed": total_assessed,
        "payout_amount": payout_amount,
        "flagged_items": flagged_items,
        "remaining_ceiling": remaining_ceiling,
        "ceiling_total": ceiling_total,
        "ceiling_used": ceiling_used,
        "is_over_ceiling": is_over_ceiling,
        "is_near_ceiling": is_near_ceiling
    }

def clean_and_parse_json(json_str: str) -> dict:
    """Tries to parse JSON, and if it fails due to missing closing braces/brackets, attempts to fix them."""
    json_str = json_str.strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Count open vs close braces and brackets
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        repaired_str = json_str
        if open_brackets > close_brackets:
            repaired_str += ']' * (open_brackets - close_brackets)
        if open_braces > close_braces:
            repaired_str += '}' * (open_braces - close_braces)
            
        try:
            return json.loads(repaired_str)
        except json.JSONDecodeError:
            # Raise original error if repair fails
            raise e

def run_ai_claim_agent(policy_id: str, phone_number: str, user_message: str, image_url: str = None) -> str:
    """
    Uses Gemini 3.5 Flash to perform OCR on pharmacy receipt images,
    extracts medicine line items, validates them against limits,
    performs duplicate checks, and writes results to the DB.
    """
    
    # 1. Fetch policy details
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies WHERE policy_id = ?", (policy_id,))
    policy = cursor.fetchone()
    conn.close()
    
    if not policy:
        return f"Error: Policy {policy_id} not found in our database."
        
    owner_name = policy["owner_name"]
    
    # 2. Perceptual hashing & Duplicate detection
    image_hash_str = None
    image_data = None
    if image_url:
        send_whatsapp_message(phone_number, "📸 *DawaFlash Agent:* Downloading receipt image from Twilio...")
        try:
            img_resp = requests.get(
                image_url, 
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None,
                timeout=15
            )
            if img_resp.status_code == 200:
                image_data = img_resp.content
                send_whatsapp_message(phone_number, "🧮 *DawaFlash Agent:* Calculating receipt image footprint (perceptual hash)...")
                
                # Compute perceptual hash of the image
                img = Image.open(io.BytesIO(image_data))
                image_hash_val = imagehash.phash(img)
                image_hash_str = str(image_hash_val)
                
                send_whatsapp_message(phone_number, "🔍 *DawaFlash Agent:* Checking for duplicate submissions...")
                # Fetch existing hashes from DB
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT claim_id, image_hash FROM claims WHERE image_hash IS NOT NULL")
                claims_rows = cursor.fetchall()
                conn.close()
                
                is_duplicate = False
                for row in claims_rows:
                    db_hash_str = row["image_hash"]
                    try:
                        db_hash = imagehash.hex_to_hash(db_hash_str)
                        distance = image_hash_val - db_hash
                        # Hamming distance <= 4 signifies a duplicate receipt
                        if distance <= 4:
                            is_duplicate = True
                            break
                    except Exception as hex_err:
                        print(f"Error parsing hash hex {db_hash_str}: {str(hex_err)}")
                
                if is_duplicate:
                    block_msg = "❌ *DawaFlash Agent:* Duplicate submission detected! This receipt matches a claim already filed in our system. Processing stopped."
                    return block_msg
                
                send_whatsapp_message(phone_number, "✅ *DawaFlash Agent:* Receipt footprint is unique. Proceeding with item extraction...")
            else:
                print(f"⚠️ [OCR] Download failed with status: {img_resp.status_code}")
                send_whatsapp_message(phone_number, "⚠️ *DawaFlash Agent:* Failed to download receipt image. Attempting text-based analysis.")
        except Exception as e:
            print(f"💥 [OCR] Error downloading or hashing image: {str(e)}")
            send_whatsapp_message(phone_number, "⚠️ *DawaFlash Agent:* Error reading image. Attempting text-based analysis.")

    # 3. Document Type Analysis (if image provided)
    document_analysis = None
    if image_data:
        send_whatsapp_message(phone_number, "📄 *DawaFlash Agent:* Analyzing document type...")
        from app.services.document_analyzer import comprehensive_document_analysis

        try:
            document_analysis = comprehensive_document_analysis(image_data)
            doc_type = document_analysis["document_type"]
            confidence = document_analysis["overall_confidence"]

            print(f"📄 [DOCUMENT] Type: {doc_type}, Confidence: {confidence}")

            # Update prompt based on document type
            if doc_type == "bulletin_de_soins":
                send_whatsapp_message(phone_number, "📗 *Bulletin de Soins détecté!* ✅")
            elif doc_type == "ordonnance":
                send_whatsapp_message(phone_number, "💊 *Ordonnance détectée!* ✅")
            elif doc_type == "vignette":
                send_whatsapp_message(phone_number, "🏷️ *Vignettes détectées!* ✅")

        except Exception as e:
            print(f"⚠️ [DOCUMENT] Analysis failed: {str(e)}")
            document_analysis = None

    # 4. AI Vision OCR and extraction
    send_whatsapp_message(phone_number, "📡 *DawaFlash Agent:* Processing items using AI Vision OCR...")

    prompt = (
        "You are an expert pharmacy receipt OCR and data extraction agent for DawaFlash, auditing a Tunisian CNAM package.\n"
        "Your goal is to extract a list of all line items (medicine names and their prices) from the pharmacy receipt / CNAM documents.\n"
        "Instructions:\n"
        "1. Identify and analyze the green 'Bulletin de Soin' paper and the medical 'Ordonnance' (prescription) in the attached documents.\n"
        "2. Specifically look at the green 'Bulletin de Soin' to find the physical 'Vignettes' (the small medicine box price stickers glued onto the page by the pharmacist).\n"
        "3. Extract the price and code from each vignette. Cross-match these vignettes with the handwritten medicine items on the doctor's prescription (ordonnance) to confirm consistency.\n"
        "4. If they match, extract the medicine name (from the ordonnance) and its price (from the vignette). Strip any currency symbols like TND, DT, DT., €, or $.\n"
        f"5. If no image is provided, extract the list of items from the user's message: '{user_message}'.\n"
        "6. You MUST return a valid JSON object with the key 'items' containing a list of objects. Each object must have:\n"
        "   - 'name': The name of the item/medicine (string)\n"
        "   - 'price': The cost of the item (float)\n"
        "7. Do NOT include totals, taxes, or service charges as line items.\n"
        "8. If you cannot find any items, return an empty list: {\"items\": []}.\n"
        "Example:\n"
        "{\n"
        "  \"items\": [\n"
        "    {\"name\": \"Doliprane\", \"price\": 4.200},\n"
        "    {\"name\": \"Clamoxyl\", \"price\": 18.500}\n"
        "  ]\n"
        "}\n\n"
        "IMPORTANT: Return ONLY valid JSON, no other text."
    )

    try:
        # Build Gemini contents
        gemini_contents = [prompt]
        if image_data:
            gemini_contents.append({"mime_type": "image/jpeg", "data": image_data})

        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            gemini_contents,
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        response_text = response.text
        print(f"🤖 [OCR] Raw Gemini response: {response_text}")

        # 4. Parse extracted items
        extracted_items = []
        try:
            data = clean_and_parse_json(response_text)
            items_list = data.get("items", [])
            if isinstance(items_list, list):
                for item in items_list:
                    name = item.get("name")
                    price = item.get("price")
                    if name and price is not None:
                        try:
                            extracted_items.append({
                                "name": str(name).strip(),
                                "price": float(price)
                            })
                        except ValueError:
                            pass
        except Exception as json_err:
            print(f"⚠️ [OCR] JSON Parsing failed: {str(json_err)}")

        # Check for extraction failure (No fallback amount!)
        if not extracted_items:
            return (
                "⚠️ *Mochkla fi el 9raya!*\n\n"
                "Ma njamnech na9raw el médicaments w el as3ar mel swar eli ab3aththom.\n\n"
                "💡 *El 7al:*\n"
                "1️⃣ Ab3ath tsawer afdhal (wadh7a, fi blassa madhya)\n"
                "2️⃣ Walla ektebhomli:\n"
                "   Mthalan: \"Chrit Doliprane b 8 DT w Spasfon b 7 DT\"\n\n"
                "📸 Lazem tsawer el *Bulletin de Soin* (el wara9a el khadhra) w el *Ordonnance* mte3 el docteur!"
            )

        # 5. Tariff + Ceiling validation
        send_whatsapp_message(phone_number, "📋 *DawaFlash Agent:* Checking medicines against TND tariffs...")
        analysis = process_tariffs_and_ceilings(policy_id, extracted_items)
        if not analysis:
            return "Error: Could not perform tariff analysis."

        send_whatsapp_message(phone_number, "🛡️ *DawaFlash Agent:* Running fraud detection analysis...")

        # 6. MULTI-LEVEL FRAUD DETECTION
        from app.services.fraud_detection import calculate_fraud_score, get_fraud_explanation_derja

        fraud_result = calculate_fraud_score(
            policy_id=policy_id,
            phone_number=phone_number,
            extracted_items=extracted_items,
            image_data=image_data,
            analysis=analysis
        )

        overall_score = fraud_result["overall_score"]
        auto_approve = fraud_result["auto_approve"]
        recommendation = fraud_result["recommendation"]

        # Determine claim status
        if recommendation == "REJECT":
            status = "REJECTED"
        elif auto_approve and overall_score >= 80:
            status = "AUTO_APPROVED"
        else:
            status = "MANUAL_REVIEW"

        # Update policy ceiling_used if auto approved
        if status == "AUTO_APPROVED":
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE policies SET ceiling_used = ceiling_used + ? WHERE policy_id = ?",
                (analysis["payout_amount"], policy_id)
            )
            conn.commit()
            conn.close()

        # 7. Record the Claim in Ledger (enhanced with fraud + document details)
        # Determine document types from analysis
        doc_types = []
        has_ordonnance = 0
        has_bulletin = 0
        has_vignette = 0

        if document_analysis:
            doc_type = document_analysis["document_type"]
            if doc_type == "ordonnance":
                has_ordonnance = 1
                doc_types.append("ordonnance")
            elif doc_type == "bulletin_de_soins":
                has_bulletin = 1
                doc_types.append("bulletin_de_soins")
            elif doc_type == "vignette":
                has_vignette = 1
                doc_types.append("vignette")
            elif doc_type == "receipt":
                doc_types.append("receipt")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO claims (
            policy_id, phone_number, extracted_amount, assessed_amount, status,
            fraud_score, risk_level, confidence_breakdown, risk_flags, receipt_hash,
            review_status, auto_approved, amount,
            document_types, has_ordonnance, has_bulletin, has_vignette
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            policy_id,
            phone_number,
            analysis["total_requested"],
            analysis["payout_amount"],
            status,
            overall_score,
            fraud_result["risk_level"],
            json.dumps(fraud_result["breakdown"]),
            json.dumps(fraud_result["flags"]),
            image_hash_str,
            "auto_approved" if auto_approve else "pending_review",
            1 if auto_approve else 0,
            analysis["payout_amount"],
            ",".join(doc_types),
            has_ordonnance,
            has_bulletin,
            has_vignette
        ))
        conn.commit()
        conn.close()
        
        # 8. Format detailed receipt response for the user
        items_detail_lines = []
        for it in analysis["processed_items"]:
            status_emoji = "✅"
            if it["status"] == "CAPPED":
                status_emoji = f"⚠️ (capped at {it['max_reimbursable']:.2f} DT)"
            elif it["status"] == "FLAGGED_UNKNOWN":
                status_emoji = "❌ (unlisted)"
            items_detail_lines.append(f"- {it['name']}: {it['requested']:.2f} DT {status_emoji}")
            
        details_text = "\n".join(items_detail_lines)
        
        # Check if the Matlab is over-ceiling to return the exact custom over-ceiling Derja notification
        if analysis["is_over_ceiling"]:
            return (
                f"Ahla *{owner_name}*! 🩺\n\n"
                f"⚠️ *Tanbih mohem:*\n"
                f"El matlab mte3ek fih overspend (fa9et el plafond).\n\n"
                f"💰 *El 7seb:*\n"
                f"• El fatora fiha: {analysis['total_requested']:.2f} DT\n"
                f"• El plafond el ba9i: {analysis['remaining_ceiling']:.2f} DT\n"
                f"• El far9: {analysis['total_requested'] - analysis['remaining_ceiling']:.2f} DT zayed\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🔍 *Chnowa 9a3ed ysir?*\n"
                f"7atina el matlab fi *Controle Yédawi* (Manual Review) m3a l'adjuster mte3na bech yetfassed el mawdhou3 afdhal.\n\n"
                f"⏰ El adjuster bech ychouf:\n"
                f"• El montant el sa7i7\n"
                f"• El plafond el mutba9\n"
                f"• Chnowa el possible nkhabrou bih\n\n"
                f"📲 Bech yji3lek el 9arar 9rib inchallah! Sabri chwaya. 🙏"
            )

        # 8. Format detailed response with fraud score
        items_detail_lines = []
        for it in analysis["processed_items"]:
            status_emoji = "✅"
            if it["status"] == "CAPPED":
                status_emoji = f"⚠️ (capped at {it['max_reimbursable']:.2f} DT)"
            elif it["status"] == "FLAGGED_UNKNOWN":
                status_emoji = "❌ (unlisted)"
            items_detail_lines.append(f"- {it['name']}: {it['requested']:.2f} DT {status_emoji}")

        details_text = "\n".join(items_detail_lines)

        # Build user message based on status
        if status == "AUTO_APPROVED":
            message_body = (
                f"✅ *Ahla {owner_name}!* 🩺\n\n"
                f"🎊 *Matlab M9abbla Automatiquement!*\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📋 *Détails el Médicaments:*\n{details_text}\n\n"
                f"💰 *El 7seb:*\n"
                f"• Total el matlab: {analysis['total_requested']:.2f} DT\n"
                f"• Montant mwafe9: {analysis['payout_amount']:.2f} DT\n"
                f"• Plafond ba9i: {max(0.0, analysis['ceiling_total'] - analysis['ceiling_used'] - analysis['payout_amount']):.2f} DT\n\n"
                f"📊 *Score Confiance:* {overall_score:.0f}/100 ({fraud_result['risk_level']})\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💸 *El Flous:* {analysis['payout_amount']:.2f} DT\n"
                f"🏦 *Fi tari9ou:* 3-5 iyem (virement bancaire)\n\n"
                f"✨ *Mabrouk! Bessahtek w rabi ichafik!* 🇹🇳"
            )
        elif status == "MANUAL_REVIEW":
            fraud_explanation = get_fraud_explanation_derja(fraud_result)
            message_body = (
                f"⏸️ *Ahla {owner_name}!* 🩺\n\n"
                f"{fraud_explanation}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📋 *Détails el Médicaments:*\n{details_text}\n\n"
                f"💰 *El 7seb:*\n"
                f"• Total el matlab: {analysis['total_requested']:.2f} DT\n"
                f"• Montant mwafe9: {analysis['payout_amount']:.2f} DT\n\n"
                f"📊 *Score Confiance:* {overall_score:.0f}/100 ({fraud_result['risk_level']})\n\n"
                f"⏱️ *Enthadhir jaweb:* 24-48 se3a"
            )
        else:  # REJECTED
            message_body = (
                f"❌ *Matlab Marfoudh* 🩺\n\n"
                f"Ma njamnech n9ablou el matlab mte3ek.\n\n"
                f"📊 *Score:* {overall_score:.0f}/100\n"
                f"⚠️ *Mochkla:* {', '.join(fraud_result['flags'][:3])}\n\n"
                f"💡 *Chnouwa ta3mel:*\n"
                f"• Verifi el tsawer w el wathi9et\n"
                f"• 3awed ab3athhom\n"
                f"• Walla ektebli bil détails\n\n"
                f"📞 Tnajem te9rab lel bureau CNAM pour plus d'info."
            )

        return message_body

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            "❌ *Mochkla techni9a!*\n\n"
            "Famma error wa9et fil système w ma njamnech nkammou el processing.\n\n"
            "💡 *Chnouwa ta3mel:*\n"
            "• 3awed ab3ath el swar ba3d chwaya\n"
            "• Walla ektebli el médicaments w el as3ar\n\n"
            "🛠️ E7na na7lou el mochkel! Sabri chwaya."
        )

def compare_face_with_cin(cin_image_data: bytes, face_image_data: bytes) -> dict:
    """
    Compares a selfie with the photo on a CIN card using Gemini Vision.
    Returns: {"match": True/False, "reason": "..."}
    """
    prompt = (
        "You are an EXTREMELY LENIENT facial recognition agent for Tunisian CNAM.\n\n"
        "🎯 **CRITICAL: APPROVE BY DEFAULT - REJECT ONLY IF IMPOSSIBLE**\n\n"
        "TWO photos:\n"
        "1. CIN (old ID photo)\n"
        "2. Selfie (current photo)\n\n"
        "⚠️ **IMPORTANT CONTEXT:**\n"
        "- CIN photos can be 10+ years old\n"
        "- Lighting is COMPLETELY different\n"
        "- Photo quality differs drastically\n"
        "- People look VERY different in ID vs selfie\n"
        "- Minor differences are NORMAL and EXPECTED\n\n"
        "✅ **APPROVE (match=true) IF:**\n"
        "- Same gender\n"
        "- Similar general face shape (oval, round, square)\n"
        "- Eyes are roughly in similar positions\n"
        "- Could POSSIBLY be same person\n"
        "- You have ANY doubt whatsoever\n"
        "- Features seem \"close enough\"\n"
        "- Not obviously fake/cartoon\n\n"
        "🚫 **COMPLETELY IGNORE:**\n"
        "- Different lighting, shadows, brightness\n"
        "- Photo quality differences\n"
        "- Aging (wrinkles, gray hair, fuller/thinner face)\n"
        "- Angle differences (slight tilt is normal)\n"
        "- Expression (smile vs neutral)\n"
        "- Makeup, glasses, hijab, facial hair, hairstyle\n"
        "- Weight changes (face gets fuller/thinner)\n"
        "- Skin tone variations (lighting/camera)\n"
        "- Blur, compression artifacts\n"
        "- Different eye/nose size (camera/lighting effect)\n\n"
        "❌ **REJECT ONLY IF:**\n"
        "- 100% ABSOLUTELY CERTAIN it's different people\n"
        "- Obviously different gender (male vs female)\n"
        "- One is a child, other is adult\n"
        "- One photo is clearly fake/cartoon/animal\n"
        "- Completely impossible to be same person under any circumstances\n\n"
        "🔑 **DECISION RULES:**\n"
        "1. If uncertain → APPROVE ✅\n"
        "2. If similar → APPROVE ✅\n"
        "3. If could be same person → APPROVE ✅\n"
        "4. If doubt → APPROVE ✅\n"
        "5. If low confidence but possible → APPROVE with confidence=\"low\" ✅\n"
        "6. If medium confidence → APPROVE with confidence=\"medium\" ✅\n"
        "7. ONLY reject if 100% impossible ❌\n\n"
        "Return JSON: {\"match\": true, \"confidence\": \"high/medium/low\", \"reason\": \"brief positive explanation\"}\n\n"
        "**DEFAULT RESPONSE: {\"match\": true, \"confidence\": \"medium\", \"reason\": \"Features appear compatible\"}**\n\n"
        "Remember: Real people's ID photos look NOTHING like their selfies. BE LENIENT."
    )

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            [
                prompt,
                {"mime_type": "image/jpeg", "data": cin_image_data},
                {"mime_type": "image/jpeg", "data": face_image_data}
            ],
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        response_text = response.text
        print(f"🤖 [FACE MATCH] Gemini response: {response_text}")
        data = clean_and_parse_json(response_text)

        match = data.get("match", False)
        confidence = data.get("confidence", "unknown")
        reason = data.get("reason", "No reason provided")

        if match:
            print(f"✅ [FACE MATCH] Faces MATCH ({confidence} confidence): {reason}")
        else:
            print(f"❌ [FACE MATCH] Faces DO NOT MATCH: {reason}")

        return {"match": bool(match), "confidence": confidence, "reason": reason}
    except Exception as e:
        print(f"💥 [FACE MATCH] Error during comparison: {str(e)}")
        return {"match": False, "confidence": "error", "reason": f"Comparison error: {str(e)}"}


def verify_cnam_carnet(carnet_image_data: bytes) -> dict:
    """
    Strictly verifies a Tunisian CNAM Carnet Vert and extracts key information.
    Returns: {"valid": True/False, "reason": "...", "cnam_id": "..." (if found)}
    """
    prompt = (
        "You are a STRICT document verification agent for Tunisian CNAM health insurance.\n\n"
        "Analyze the attached image and verify if it is an AUTHENTIC Tunisian CNAM Carnet de Soin (green health booklet).\n\n"
        "CRITICAL REQUIREMENTS:\n"
        "1. Must be predominantly GREEN in color (official CNAM green)\n"
        "2. Must show 'CNAM' branding or logo clearly visible\n"
        "3. Must contain a CNAM identification number or beneficiary number\n"
        "4. Must show official stamps, signatures, or authentication marks\n"
        "5. Must be a Tunisian document (French/Arabic text)\n"
        "6. Document must be clear enough to read text\n\n"
        "LOOK FOR:\n"
        "- CNAM logo or 'Caisse Nationale d'Assurance Maladie' text\n"
        "- Green color (signature CNAM identity)\n"
        "- Beneficiary information (name, ID number)\n"
        "- Official stamps or authentication marks\n"
        "- Tunisian government branding\n\n"
        "REJECT if:\n"
        "- Not green in color\n"
        "- No CNAM branding visible\n"
        "- Random green paper or card\n"
        "- Receipt, invoice, or other document\n"
        "- Too blurry to verify authenticity\n"
        "- Wrong country's health card\n"
        "- Clearly fake or doctored\n\n"
        "If you find a CNAM ID number, extract it.\n\n"
        "Return JSON: {\"valid\": true/false, \"reason\": \"detailed explanation\", \"cnam_id\": \"extracted ID or null\"}\n"
        "BE EXTREMELY STRICT - only approve genuine Tunisian CNAM cards with visible authentication."
    )

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            [prompt, {"mime_type": "image/jpeg", "data": carnet_image_data}],
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        response_text = response.text
        print(f"🤖 [CNAM VERIFY] Gemini response: {response_text}")
        data = clean_and_parse_json(response_text)

        valid = data.get("valid", False)
        reason = data.get("reason", "No reason provided")
        cnam_id = data.get("cnam_id", None)

        if valid:
            print(f"✅ [CNAM VERIFY] Carnet APPROVED: {reason}")
            if cnam_id:
                print(f"   📋 Extracted CNAM ID: {cnam_id}")
        else:
            print(f"❌ [CNAM VERIFY] Carnet REJECTED: {reason}")

        return {"valid": bool(valid), "reason": reason, "cnam_id": cnam_id}
    except Exception as e:
        print(f"💥 [CNAM VERIFY] Error during verification: {str(e)}")
        return {"valid": False, "reason": f"Verification error: {str(e)}", "cnam_id": None}


def analyze_onboarding_document_multi(step: str, image_data_list: list) -> dict:
    """
    Analyzes one or more images for onboarding verification.
    For CIN: can accept front + back images
    For Face/Carnet: expects single image
    Returns: {"valid": True/False, "reason": "...", "combined_image": bytes}
    """
    if not image_data_list:
        return {"valid": False, "reason": "No images provided", "combined_image": None}

    # Prepare contents for Gemini (can handle multiple images)
    contents = []

    if step == "NEED_CIN":
        if len(image_data_list) == 1:
            prompt = (
                "You are a STRICT identity verification agent for Tunisian CNAM insurance onboarding.\n\n"
                "Analyze the attached image and determine if it is a VALID Tunisian National Identity Card (CIN).\n\n"
                "REQUIRED ELEMENTS to mark as valid:\n"
                "1. Must show a Tunisian National ID card (Carte d'Identité Nationale)\n"
                "2. Must contain visible text fields: Name, CIN number (8 digits), Date of birth, Photo\n"
                "3. Must be clear and readable (not blurry)\n"
                "4. Shows at least the front with photo and CIN number visible\n"
                "5. Document must look authentic (not obviously fake or altered)\n\n"
                "REJECT if:\n"
                "- Random photos, screenshots, receipts, or other documents\n"
                "- Driver's license, passport, or any non-CIN document\n"
                "- Too blurry to read text\n"
                "- Missing critical fields (name, CIN number, photo)\n\n"
                "Return JSON: {\"valid\": true/false, \"reason\": \"brief explanation\"}\n"
                "BE STRICT: Only approve clear, authentic Tunisian CIN cards."
            )
        else:
            prompt = (
                "You are a STRICT identity verification agent for Tunisian CNAM insurance onboarding.\n\n"
                "You will receive MULTIPLE images showing the FRONT and BACK of a Tunisian National Identity Card (CIN).\n\n"
                "REQUIRED ELEMENTS across all images:\n"
                "1. Must show a Tunisian National ID card (Carte d'Identité Nationale)\n"
                "2. Must contain visible text: Name, CIN number (8 digits), Date of birth\n"
                "3. Must show the person's photo on the front\n"
                "4. Both sides must be clear and readable\n"
                "5. Document must look authentic\n\n"
                "REJECT if:\n"
                "- Not a CIN card\n"
                "- Missing critical information\n"
                "- Too blurry or unclear\n"
                "- Different documents mixed together\n\n"
                "Return JSON: {\"valid\": true/false, \"reason\": \"brief explanation\"}\n"
                "BE STRICT: Only approve complete, authentic Tunisian CIN cards."
            )
        contents.append(prompt)
        for img_data in image_data_list:
            contents.append({"mime_type": "image/jpeg", "data": img_data})

    elif step == "NEED_FACE":
        prompt = (
            "You are a facial verification agent for Tunisian CNAM insurance onboarding.\n\n"
            "Analyze the attached image and determine if it shows a human face suitable for identity verification.\n\n"
            "APPROVE (valid=true) if:\n"
            "1. Shows a clear view of a human face (front or slightly angled is OK)\n"
            "2. Eyes and major facial features are visible\n"
            "3. Face occupies reasonable portion of image\n"
            "4. Quality is good enough to see facial features\n"
            "5. Appears to be a real photo of a person\n\n"
            "REJECT (valid=false) ONLY if:\n"
            "- Clearly NOT a human face (animal, object, document, receipt)\n"
            "- Group photo with multiple people\n"
            "- Face completely obscured (full mask, back of head)\n"
            "- Too dark or blurry to see ANY features\n"
            "- Obviously fake (cartoon, drawing)\n\n"
            "BE LENIENT with:\n"
            "- Lighting variations (as long as face is visible)\n"
            "- Slight angle (doesn't need to be perfectly frontal)\n"
            "- Photo quality (as long as features are recognizable)\n"
            "- Glasses, hijab, or normal accessories (as long as face is visible)\n\n"
            "Return JSON: {\"valid\": true/false, \"reason\": \"brief explanation\"}\n"
            "When in doubt, APPROVE if it's a real human face photo."
        )
        contents.append(prompt)
        contents.append({"mime_type": "image/jpeg", "data": image_data_list[0]})

    elif step == "NEED_CARNET":
        prompt = (
            "You are a STRICT document verification agent for Tunisian CNAM insurance onboarding.\n\n"
            "Analyze the attached image and determine if it is a VALID Tunisian CNAM health card.\n\n"
            "REQUIRED ELEMENTS to mark as valid:\n"
            "1. Must show a Tunisian CNAM card (Carnet de Soin / Carnet Vert)\n"
            "2. Card should be GREEN in color (signature CNAM color)\n"
            "3. Must contain visible CNAM number or beneficiary information\n"
            "4. Must show CNAM logo or official branding\n"
            "5. Document must be clear and readable\n\n"
            "REJECT if:\n"
            "- Random photos, receipts, or other documents\n"
            "- ID cards, driver's license, or non-CNAM documents\n"
            "- Too blurry to read\n"
            "- Wrong country's health card\n"
            "- Missing CNAM branding or identification\n\n"
            "Return JSON: {\"valid\": true/false, \"reason\": \"brief explanation\"}\n"
            "BE STRICT: Only approve authentic Tunisian CNAM health cards."
        )
        contents.append(prompt)
        contents.append({"mime_type": "image/jpeg", "data": image_data_list[0]})
    else:
        return {"valid": False, "reason": "Unknown verification step", "combined_image": None}

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            contents,
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        response_text = response.text
        print(f"🤖 [ONBOARDING AGENT] Gemini Raw response: {response_text}")
        data = clean_and_parse_json(response_text)
        valid_val = data.get("valid", False)
        reason = data.get("reason", "No reason provided")

        if valid_val:
            print(f"✅ [ONBOARDING] Document APPROVED for {step}: {reason}")
        else:
            print(f"❌ [ONBOARDING] Document REJECTED for {step}: {reason}")

        # Return first image as the "primary" one to store
        return {"valid": bool(valid_val), "reason": reason, "combined_image": image_data_list[0]}
    except Exception as e:
        print(f"💥 [ONBOARDING AGENT] Error during Gemini verification: {str(e)}")
        return {"valid": False, "reason": f"Verification error: {str(e)}", "combined_image": None}


def analyze_onboarding_document(step: str, image_data: bytes) -> dict:
    """Uses Gemini 3.5 Flash to verify onboarding documents based on the step.
    Returns: {"valid": True, "reason": "..."} or {"valid": False, "reason": "..."}
    """
    if step == "NEED_CIN":
        prompt = (
            "You are a STRICT identity verification agent for Tunisian CNAM insurance onboarding.\n\n"
            "Analyze the attached image and determine if it is a VALID Tunisian National Identity Card (CIN).\n\n"
            "REQUIRED ELEMENTS to mark as valid:\n"
            "1. Must show a Tunisian National ID card (Carte d'Identité Nationale)\n"
            "2. Must contain visible text fields: Name, CIN number (8 digits), Date of birth, Photo\n"
            "3. Must be clear and readable (not blurry)\n"
            "4. Must show both front AND back sides, or at least the front with photo and CIN number\n"
            "5. Document must look authentic (not obviously fake or altered)\n\n"
            "REJECT if:\n"
            "- Random photos, screenshots, receipts, or other documents\n"
            "- Driver's license, passport, or any non-CIN document\n"
            "- Too blurry to read text\n"
            "- Missing critical fields (name, CIN number, photo)\n\n"
            "Return JSON: {\"valid\": true/false, \"reason\": \"brief explanation\"}\n"
            "BE STRICT: Only approve clear, authentic Tunisian CIN cards."
        )
    elif step == "NEED_FACE":
        prompt = (
            "You are a facial verification agent for Tunisian CNAM insurance onboarding.\n\n"
            "Analyze the attached image and determine if it shows a human face suitable for identity verification.\n\n"
            "APPROVE (valid=true) if:\n"
            "1. Shows a clear view of a human face (front or slightly angled is OK)\n"
            "2. Eyes and major facial features are visible\n"
            "3. Face occupies reasonable portion of image\n"
            "4. Quality is good enough to see facial features\n"
            "5. Appears to be a real photo of a person\n\n"
            "REJECT (valid=false) ONLY if:\n"
            "- Clearly NOT a human face (animal, object, document, receipt)\n"
            "- Group photo with multiple people\n"
            "- Face completely obscured (full mask, back of head)\n"
            "- Too dark or blurry to see ANY features\n"
            "- Obviously fake (cartoon, drawing)\n\n"
            "BE LENIENT with:\n"
            "- Lighting variations (as long as face is visible)\n"
            "- Slight angle (doesn't need to be perfectly frontal)\n"
            "- Photo quality (as long as features are recognizable)\n"
            "- Glasses, hijab, or normal accessories (as long as face is visible)\n\n"
            "Return JSON: {\"valid\": true/false, \"reason\": \"brief explanation\"}\n"
            "When in doubt, APPROVE if it's a real human face photo."
        )
    elif step == "NEED_CARNET":
        prompt = (
            "You are a STRICT document verification agent for Tunisian CNAM insurance onboarding.\n\n"
            "Analyze the attached image and determine if it is a VALID Tunisian CNAM health card.\n\n"
            "REQUIRED ELEMENTS to mark as valid:\n"
            "1. Must show a Tunisian CNAM card (Carnet de Soin / Carnet Vert)\n"
            "2. Card should be GREEN in color (signature CNAM color)\n"
            "3. Must contain visible CNAM number or beneficiary information\n"
            "4. Must show CNAM logo or official branding\n"
            "5. Document must be clear and readable\n\n"
            "REJECT if:\n"
            "- Random photos, receipts, or other documents\n"
            "- ID cards, driver's license, or non-CNAM documents\n"
            "- Too blurry to read\n"
            "- Wrong country's health card\n"
            "- Missing CNAM branding or identification\n\n"
            "Return JSON: {\"valid\": true/false, \"reason\": \"brief explanation\"}\n"
            "BE STRICT: Only approve authentic Tunisian CNAM health cards."
        )
    else:
        return {"valid": False}

    contents = [
        prompt,
        {
            "mime_type": "image/jpeg",
            "data": image_data
        }
    ]

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            contents,
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        response_text = response.text
        print(f"🤖 [ONBOARDING AGENT] Gemini Raw response: {response_text}")
        data = clean_and_parse_json(response_text)
        valid_val = data.get("valid", False)
        reason = data.get("reason", "No reason provided")

        if valid_val:
            print(f"✅ [ONBOARDING] Document APPROVED for {step}: {reason}")
        else:
            print(f"❌ [ONBOARDING] Document REJECTED for {step}: {reason}")

        return {"valid": bool(valid_val), "reason": reason}
    except Exception as e:
        print(f"💥 [ONBOARDING AGENT] Error during Gemini verification: {str(e)}")
        return {"valid": False, "reason": f"Verification error: {str(e)}"}