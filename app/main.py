import os
import sys
import io
import html
import time
from collections import defaultdict
from fastapi import FastAPI, Form, Response, BackgroundTasks
from app.database.db import get_db_connection, get_user_state, update_user_state
from app.services.agents import run_ai_claim_agent, analyze_onboarding_document, analyze_onboarding_document_multi, compare_face_with_cin, verify_cnam_carnet
from app.services.twilio_client import send_whatsapp_message
from dotenv import load_dotenv
from twilio.rest import Client

# Fix UTF-8 encoding for console output (Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DEV_MOCK_AI_AND_TWILIO = False  # Set to True to save API limits during phone practice, False for real live AI run

# Media batching: collect images sent within 2 seconds
MEDIA_BATCH_WINDOW = 2.0  # seconds
pending_media_batches = defaultdict(lambda: {"urls": [], "timestamp": None, "processed": False})

# Load environmental variables
load_dotenv()

# Initialize Twilio Client for out-of-band asynchronous messaging
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI(title="DawaFlash Webhook Gateway")

def translate_rejection_to_derja(step: str, english_reason: str) -> str:
    """Translates technical rejection reasons to user-friendly Tunisian Derja."""
    reason_lower = english_reason.lower()

    if step == 'NEED_CIN':
        if 'pharmacy' in reason_lower or 'receipt' in reason_lower:
            return "Tsawra eli ab3aththa fatora mel pharmacie mech CIN. 🧾"
        elif 'passport' in reason_lower:
            return "Tsawra eli ab3aththa passeport mech CIN. ✈️"
        elif 'blurry' in reason_lower or 'unclear' in reason_lower:
            return "Tsawra mech wadh7a barsha. Lazem tkoun clear bech na9raou el ma3loumet. 👓"
        elif 'missing' in reason_lower or 'not visible' in reason_lower:
            return "Famma ma3loumet me7lela: lazem el esem, rou9em el CIN (8 ara9em), w tsawra mte3ek. 📋"
        elif 'driver' in reason_lower or 'license' in reason_lower:
            return "Tsawra eli ab3aththa permis de conduire mech CIN. 🚗"
        else:
            return "El wathi9a eli ab3aththa mech CIN Tounsi sa7i7. 🪪"

    elif step == 'NEED_FACE':
        if 'receipt' in reason_lower or 'document' in reason_lower:
            return "Tsawra eli ab3aththa wathi9a mech swar wjeh. Lazem selfie wadh7a. 🤳"
        elif 'multiple' in reason_lower or 'group' in reason_lower:
            return "Famma barcha wjoueh fil swar. Lazem selfie fiha wjhek wa7dek barka. 👤"
        elif 'blurry' in reason_lower or 'dark' in reason_lower:
            return "Swar el wjeh mech wadh7a walla dhlam barsha. 3awed swar rou7ek fi blassa madhya. 💡"
        elif 'side' in reason_lower or 'profile' in reason_lower:
            return "Tsawra men el jneb. Lazem swar wjhek mel 9oddem mbecher. 📸"
        elif 'mask' in reason_lower or 'covered' in reason_lower:
            return "Wjhek mastour (masque, nudhdharet chams...). Lazem wjhek yedhher el kol. 😷"
        elif 'not match' in reason_lower or 'different' in reason_lower:
            return "Wjhek fil selfie ma yetsawwbch m3a tsawret el CIN. Bech t3addi lazem nafs el chakhes. 🆔"
        else:
            return "Tsawret el wjeh mech sa7i7a. Lazem selfie wadh7a fiha wjhek mel 9oddem. 🤳"

    elif step == 'NEED_CARNET':
        if 'receipt' in reason_lower or 'pharmacy' in reason_lower:
            return "Tsawra eli ab3aththa fatora mech el Carnet el Akhdar mte3 CNAM. 🧾"
        elif 'not green' in reason_lower or 'color' in reason_lower:
            return "El carnet lazem yekhdem akhdar (CNAM green). Eli ab3aththa mech akhdar. 🟢"
        elif 'no cnam' in reason_lower or 'branding' in reason_lower:
            return "Ma fammech logo CNAM walla authentication fil wathi9a. Lazem Carnet CNAM sa7i7. 🏥"
        elif 'blurry' in reason_lower:
            return "Tsawra mech wadh7a. Lazem tsawra clear bech na9raou el ma3loumet. 👓"
        elif 'id card' in reason_lower or 'cin' in reason_lower:
            return "Tsawra eli ab3aththa CIN mech Carnet CNAM. Lazem el carnet el akhdar. 🪪"
        else:
            return "El wathi9a mech Carnet Vert CNAM Tounsi sa7i7. Lazem el carnet mte3 CNAM bel logo w rou9em. 🟢"

    return "El wathi9a mech sa7i7a. 3awed ab3ath tsawer wadh7a bech nverifyouha. 📸"

def process_claim_in_background(policy_id: str, user_message: str, phone_number: str, image_url: str = None):
    """Runs the Gemini claim agent with OCR in the background and sends the final decision report."""
    print("🤖 [BG TASK] Triggering Gemini 3.5 Flash Agent with OCR...")
    ai_reply = run_ai_claim_agent(policy_id, phone_number, user_message, image_url)
    print("🤖 [BG TASK] Gemini finished processing.")
    send_whatsapp_message(phone_number, ai_reply)


def verify_onboarding_step_in_background(phone_number: str, step: str, media_urls: list):
    """Downloads documents (can be multiple), runs them through Gemini Vision, and updates user state."""
    # Standardize Twilio sender number format
    twilio_num = os.getenv("TWILIO_NUMBER", "+14155238886")
    twilio_sender = f"whatsapp:{twilio_num}" if not twilio_num.startswith("whatsapp:") else twilio_num
    user_recipient = f"whatsapp:{phone_number}" if not phone_number.startswith("whatsapp:") else phone_number

    if DEV_MOCK_AI_AND_TWILIO:
        import time
        time.sleep(1)
        is_valid = True
        print(f"🛠️ [DEV MOCK]: Bypassed Gemini Vision Document verification step {step} -> AUTO APPROVE")
    else:
        import requests
        print(f"📥 [ONBOARDING BG] Verification started for user {phone_number} on step {step}...")
        print(f"   Processing {len(media_urls)} image(s)...")

        try:
            # Download ALL images
            image_data_list = []
            for idx, media_url in enumerate(media_urls):
                print(f"   Downloading image {idx + 1}/{len(media_urls)}...")
                resp = requests.get(
                    media_url,
                    auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None,
                    timeout=15
                )
                if resp.status_code != 200:
                    print(f"❌ [ONBOARDING BG] Failed to download image {idx + 1}: {resp.status_code}")
                    twilio_client.messages.create(
                        body=f"⚠️ Fama mochkla fi download tsawra {idx + 1}. Brabbi 3awed ab3ath tsawer clear. 📸",
                        from_=twilio_sender,
                        to=user_recipient
                    )
                    return
                image_data_list.append(resp.content)

            print(f"✅ [ONBOARDING BG] Downloaded {len(image_data_list)} image(s) successfully")

            # Use multi-image analysis for better handling of CIN front+back
            analysis = analyze_onboarding_document_multi(step, image_data_list)
            is_valid = analysis.get("valid", False)
            rejection_reason = analysis.get("reason", "Document not recognized")
            primary_image = analysis.get("combined_image", image_data_list[0] if image_data_list else None)

            # Step-specific verification logic
            if step == 'NEED_CIN':
                if is_valid:
                    # Store CIN image for later face comparison
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE users SET cin_image_data = ? WHERE phone_number = ?",
                        (primary_image, phone_number.replace("whatsapp:", "").strip())
                    )
                    conn.commit()
                    conn.close()
                    print(f"💾 [ONBOARDING] Stored CIN image ({len(image_data_list)} photo(s)) for {phone_number}")

            elif step == 'NEED_FACE':
                if is_valid:
                    # Now compare face with CIN photo
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT cin_image_data FROM users WHERE phone_number = ? OR phone_number = ?",
                        (phone_number.replace("whatsapp:", "").strip(), phone_number)
                    )
                    row = cursor.fetchone()
                    conn.close()

                    if row and row["cin_image_data"]:
                        cin_image = row["cin_image_data"]
                        print(f"🔍 [ONBOARDING] Comparing face with CIN photo...")

                        face_match = compare_face_with_cin(cin_image, primary_image)

                        if not face_match.get("match", False):
                            is_valid = False
                            confidence = face_match.get("confidence", "unknown")
                            rejection_reason = f"Face does not match CIN photo ({confidence} confidence): {face_match.get('reason', 'No match')}"
                            print(f"❌ [ONBOARDING] Face match failed: {rejection_reason}")
                        else:
                            # Store face image
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE users SET face_image_data = ? WHERE phone_number = ?",
                                (primary_image, phone_number.replace("whatsapp:", "").strip())
                            )
                            conn.commit()
                            conn.close()
                            print(f"✅ [ONBOARDING] Face matches CIN! Confidence: {face_match.get('confidence', 'unknown')}")
                    else:
                        is_valid = False
                        rejection_reason = "CIN image not found in system. Please submit CIN first."
                        print(f"❌ [ONBOARDING] No CIN image found for comparison")

            elif step == 'NEED_CARNET':
                if is_valid:
                    # Use stricter CNAM verification
                    cnam_analysis = verify_cnam_carnet(primary_image)
                    is_valid = cnam_analysis.get("valid", False)
                    rejection_reason = cnam_analysis.get("reason", "Document not recognized")
                    cnam_id = cnam_analysis.get("cnam_id", None)

                    if is_valid:
                        # Store carnet image and CNAM ID
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE users SET carnet_image_data = ?, cnam_id = ? WHERE phone_number = ?",
                            (primary_image, cnam_id, phone_number.replace("whatsapp:", "").strip())
                        )
                        conn.commit()
                        conn.close()
                        print(f"💾 [ONBOARDING] Stored CNAM carnet, ID: {cnam_id}")

        except Exception as e:
            print(f"💥 [ONBOARDING BG] Error during download or Gemini: {str(e)}")
            twilio_client.messages.create(
                body="❌ Fama error fi verification. Brabbi 3awed ab3ath el fatora w dhar w wjeh clear. 🛠️",
                from_=twilio_sender,
                to=user_recipient
            )
            return

    # Database updates & Twilio message dispatch (runs for both Mock and Live flows!)
    try:
        if is_valid:
            if step == 'NEED_CIN':
                update_user_state(phone_number, 'NEED_FACE')
                reply_text = "✅ *Mabrouk!* El CIN mte3ek t9ablet! 🎉\n\n📋 *Esmek:* [يظهر في الـ CIN]\n📅 *Verification:* Sa7i7\n\n➡️ *El 5otwa ejjeya:*\nTawa ab3athli selfie (swar rou7ek) wadh7a mel 9oddem bech na9arnou wjhek m3a tsawret el CIN.\n\n💡 Lazem:\n• Wjhek mel 9oddem mbecher\n• Blassa madhya\n• Wadh7a w net9raw fiha\n\n📸 Yalla swar rou7ek!"
            elif step == 'NEED_FACE':
                update_user_state(phone_number, 'NEED_CARNET')
                reply_text = "✅ *Perfect!* Wjhek yetsaweb m3a el CIN! 🎉\n\n🔍 *Face Match:* Confirmed ✓\n👤 *El Hwya:* Verified\n\n➡️ *El 5otwa el a5ira:*\nTawa bech ncommletou el inscription, ab3athli tsawer clear mte3 el *Carnet el Akhdar* (Carnet Vert) mte3 el CNAM.\n\n💡 Lazem:\n• Akhdar el loun (CNAM green)\n• Fih logo CNAM\n• Wadh7 w net9raw fih\n\n🟢 Yalla 9rib nkammou!"
            elif step == 'NEED_CARNET':
                update_user_state(phone_number, 'VERIFIED')
                reply_text = "🎊 *MABROUK!* 🎊\n\n✅ El inscription kamlet bne7! El contrat mte3ek bel CNAM w DawaFlash bda rasmyan!\n\n📋 *Status:* VERIFIED ✓\n🏥 *CNAM:* Connected\n💳 *Plafond:* Active\n\n━━━━━━━━━━━━━━━\n\n🩺 *Tawa chnouwa?*\nFi ay wa9t t7ess rou7ek mridh w t7eb t3addi Matlab Mrayah (Remboursement), ab3athli:\n\n1️⃣ Tsawer el *Bulletin de Soin* (el wara9a el khadhra)\n2️⃣ Tsawer el *Ordonnance* (el wasef mte3 el docteur)\n\nW e7na na3mlou el reste! El flous traja3lek direct. 💰\n\n━━━━━━━━━━━━━━━\n\n✨ *DawaFlash* - El da3em mte3ek fi el se7a! 🇹🇳"
        else:
            # Translate rejection reason to Derja
            derja_reason = translate_rejection_to_derja(step, rejection_reason)

            if step == 'NEED_CIN':
                reply_text = f"❌ *Rafd:* {derja_reason}\n\n💡 *Chnouwa lazem:*\nAb3ath tsawer el CIN el Tunisiya (Carte d'Identité Nationale) mel wjeh w edhar. Lazem tkoun wadh7a w net9raw fiha:\n• Esmek el kemel\n• Rou9em el CIN (8 ara9em)\n• Tarikhet el milad\n• Tsawerek\n\n📸 *Conseil:* Swar fil blassa madhya, w rakkez 3al CIN bech tkoun wadh7a. 🪪"

            elif step == 'NEED_FACE':
                reply_text = f"❌ *Rafd:* {derja_reason}\n\n💡 *Chnouwa lazem:*\nAb3ath selfie (swar rou7ek) wadh7a:\n• Wjhek mel 9oddem mbecher\n• 3aynik, mankhrek, w fommek yedhrou el kol\n• Blassa madhya (mech dhlam)\n• Wa7dek fil swar (mech groupe)\n• Bla masque walla nudhdharet chams\n\n🔍 *Mohem:* Bech na9arnou wjhek m3a tsawret el CIN! 📸"

            elif step == 'NEED_CARNET':
                reply_text = f"❌ *Rafd:* {derja_reason}\n\n💡 *Chnouwa lazem:*\nAb3ath tsawer el Carnet el Akhdar (Carnet Vert) mte3 el CNAM:\n• Lazem yekhdem akhdar (CNAM green)\n• Lazem fih logo CNAM\n• Lazem fih rou9em el beneficiaire\n• Lazem fih tabe3 walla taw9i3 rasmi\n• Tsawra wadh7a w net9raw fiha\n\n📗 *Conseil:* Carnet CNAM sa7i7 fessel el welaya. 🟢"
                
        # Send out-of-band WhatsApp alert via Twilio REST API client
        twilio_client.messages.create(
            body=reply_text,
            from_=twilio_sender,
            to=user_recipient
        )
        print(f"✅ [ONBOARDING BG] Out-of-band message dispatched: '{reply_text}'")

        # CRITICAL: Clean up batch after processing (success or failure)
        batch_key = f"{phone_number.replace('whatsapp:', '').strip()}:{step}"
        if batch_key in pending_media_batches:
            del pending_media_batches[batch_key]
            print(f"🧹 [CLEANUP] Cleared batch: {batch_key}")

    except Exception as e:
        print(f"💥 [ONBOARDING BG] Error dispatching message or updating state: {str(e)}")
        # Clean up batch even on error
        batch_key = f"{phone_number.replace('whatsapp:', '').strip()}:{step}"
        if batch_key in pending_media_batches:
            del pending_media_batches[batch_key]
            print(f"🧹 [CLEANUP] Cleared batch after error: {batch_key}")


@app.get("/")
def home():
    return {"status": "online", "application": "DawaFlash"}


@app.post("/webhook")
def whatsapp_webhook(
    background_tasks: BackgroundTasks,
    from_number: str = Form(..., alias="From"),
    body_text: str = Form("", alias="Body"),
    num_media: int = Form(0, alias="NumMedia"),
    media_url_0: str = Form(None, alias="MediaUrl0"),
    media_url_1: str = Form(None, alias="MediaUrl1"),
    media_url_2: str = Form(None, alias="MediaUrl2"),
    media_url_3: str = Form(None, alias="MediaUrl3")
):
    phone_number = from_number.replace("whatsapp:", "").strip()
    user_message = body_text.strip()

    # Collect all media URLs that were sent
    media_urls = []
    if num_media > 0:
        for i in range(num_media):
            media_url = locals().get(f'media_url_{i}')
            if media_url:
                media_urls.append(media_url)

    print(f"\n📥 [WEBHOOK RECEIVED] From: {phone_number} | Message: '{user_message}' | Media Count: {num_media}")
    if media_urls:
        print(f"   Media URLs: {media_urls}")

    # Clean up old batches (older than 10 seconds)
    current_time = time.time()
    keys_to_delete = []
    for key, batch in pending_media_batches.items():
        if batch["timestamp"] and (current_time - batch["timestamp"]) > 10.0:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        print(f"🧹 [CLEANUP] Removing stale batch: {key}")
        del pending_media_batches[key]
    
    current_state = get_user_state(phone_number)
    
    if current_state == 'VERIFIED':
        # Check if this user exists in the policies table.
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM policies WHERE phone_number = ? OR phone_number = ?", (phone_number, f"whatsapp:{phone_number}"))
        policy = cursor.fetchone()
        
        # HACKATHON SAFEGUARD: If they are VERIFIED in the users table but missing from the policies table, 
        # automatically insert a default demo policy row
        if not policy:
            cursor.execute("""
            INSERT OR IGNORE INTO policies (policy_id, owner_name, phone_number, coverage_limit, deductible, ceiling_total, ceiling_used)
            VALUES ('POL-TUNIS-123', 'Amina Ben Ali', ?, 5000.0, 10.0, 500.0, 100.0)
            """, (phone_number,))
            conn.commit()
            
            cursor.execute("SELECT * FROM policies WHERE phone_number = ?", (phone_number,))
            policy = cursor.fetchone()
            
        if policy is None:
            policy = {
                "policy_id": "POL-TUNIS-123",
                "full_name": "Amina Ben Ali",
                "owner_name": "Amina Ben Ali",
                "remaining_ceiling": 500.0
            }
            
        policy_id = policy["policy_id"]
        
        # Everyday Claims Processing Logic w/ media extraction bypass
        if num_media > 0:
            reply = "Ya3tik essa7a, 5dhina el fatora mte3ek. Tawa 9a3din nanalysiw fiha... 🧪 Lahdha barka w yjik el chtar!"
            background_tasks.add_task(process_claim_in_background, policy_id, user_message, phone_number, media_url_0)
        else:
            reply = "3asslema! Fi ay wa9t t7eb t3addi Matlab Mrayah, ab3athli direct tsawer el Bulletin de Soin w l'ordonnance ensemble! 📸"
            
        conn.close()
        twilio_xml = f"<Response><Message>{html.escape(reply)}</Message></Response>"
        return Response(content=twilio_xml, media_type="text/xml")
        
    elif current_state == 'NEED_CIN':
        if num_media == 0:
            # Text message without media - clear any pending batch and respond normally
            batch_key = f"{phone_number}:NEED_CIN"
            if batch_key in pending_media_batches:
                del pending_media_batches[batch_key]
                print(f"🧹 [CLEANUP] Cleared batch on text message: {batch_key}")

            reply = "Brabbi ab3athli tsawer el CIN mte3ek mel wjeh w edhar bech nthabtu fil hwya! 🪪"
        else:
            # Batch media: WhatsApp sends each image in separate webhook
            batch_key = f"{phone_number}:NEED_CIN"
            current_time = time.time()

            batch = pending_media_batches[batch_key]

            # Add current media to batch
            batch["urls"].extend(media_urls)

            # If this is first image, set timestamp
            if batch["timestamp"] is None:
                batch["timestamp"] = current_time

            # Check if we should process now
            time_since_first = current_time - batch["timestamp"]

            if time_since_first < MEDIA_BATCH_WINDOW and not batch["processed"]:
                # Still collecting, acknowledge receipt
                reply = f"5dhina tsawra ({len(batch['urls'])} tsawer 7atta tawa)... Lahdha barka! 📸"

                # Schedule delayed processing
                def process_batch_after_delay():
                    time.sleep(MEDIA_BATCH_WINDOW - time_since_first + 0.5)
                    if not batch["processed"]:
                        batch["processed"] = True
                        all_urls = list(set(batch["urls"]))  # Remove duplicates
                        print(f"[BATCH] Processing {len(all_urls)} images for {phone_number}")
                        verify_onboarding_step_in_background(phone_number, 'NEED_CIN', all_urls)
                        # Clean up
                        del pending_media_batches[batch_key]

                background_tasks.add_task(process_batch_after_delay)
            else:
                # Time window passed or already processed, process immediately
                if not batch["processed"]:
                    batch["processed"] = True
                    all_urls = list(set(batch["urls"]))
                    reply = f"5dhina {len(all_urls)} tsawer mte3 el CIN, 9a3din nthabtu fihom bl AI... 🔍"
                    background_tasks.add_task(verify_onboarding_step_in_background, phone_number, 'NEED_CIN', all_urls)
                    del pending_media_batches[batch_key]
                else:
                    # Already processed, don't send duplicate
                    reply = ""

        twilio_xml = f"<Response><Message>{html.escape(reply)}</Message></Response>" if reply else "<Response></Response>"
        return Response(content=twilio_xml, media_type="text/xml")

    elif current_state == 'NEED_FACE':
        if num_media == 0:
            # Text message - respond normally
            reply = "Brabbi ab3athli swar rou7ek (selfie) bech ncommparouha m3a el CIN. 📸"
        else:
            # Process face immediately (usually single image)
            reply = "Mregla, 5dhina tsawret el wjeh. Tawa 9a3din nverifyiw fiha w ncommparouha m3a el CIN... Lahdha barka! 📸"
            background_tasks.add_task(verify_onboarding_step_in_background, phone_number, 'NEED_FACE', media_urls)

        twilio_xml = f"<Response><Message>{html.escape(reply)}</Message></Response>"
        return Response(content=twilio_xml, media_type="text/xml")

    elif current_state == 'NEED_CARNET':
        if num_media == 0:
            # Text message - respond normally
            reply = "Brabbi ab3athli tsawer clear mte3 el Carnet Vert mte3ek mta3 el CNAM. 🟢"
        else:
            # Process CNAM immediately (usually single image)
            reply = "5dhina tsawer el Carnet Vert. Sabri chwaya ncommpletou el inscription... 🟢"
            background_tasks.add_task(verify_onboarding_step_in_background, phone_number, 'NEED_CARNET', media_urls)
        
        twilio_xml = f"<Response><Message>{html.escape(reply)}</Message></Response>"
        return Response(content=twilio_xml, media_type="text/xml")