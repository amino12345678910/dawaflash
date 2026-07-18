"""
Advanced Document Type Detection and Analysis for DawaFlash
Supports: Ordonnance, Bulletin de Soins, Vignettes, Receipts
"""

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""), transport="rest")


def clean_and_parse_json(text: str) -> dict:
    """Extract and parse JSON from Gemini response"""
    import re
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")
        print(f"Raw text: {text[:200]}")
        return {}


def detect_document_type(image_data: bytes) -> dict:
    """
    Detects what type of document is in the image.

    Returns:
    {
        "document_type": "ordonnance|bulletin_de_soins|receipt|vignette|unknown",
        "confidence": "high|medium|low",
        "description": "..."
    }
    """
    prompt = (
        "You are a medical document classifier for Tunisian CNAM healthcare system.\n\n"
        "Analyze the image and identify which type of document it is:\n\n"
        "1. **ORDONNANCE** (Medical Prescription):\n"
        "   - Written or printed document from doctor\n"
        "   - Contains: doctor name, medications list, dosage, patient name\n"
        "   - Has doctor's signature and stamp\n"
        "   - Usually on prescription pad (white/colored paper)\n\n"
        "2. **BULLETIN DE SOINS** (CNAM Green Form):\n"
        "   - Official GREEN form from CNAM\n"
        "   - Pre-printed CNAM header and logo\n"
        "   - Sections for: patient info, care details, doctor info\n"
        "   - Green color is signature feature\n"
        "   - Multiple stamps (doctor, CNAM, pharmacy)\n\n"
        "3. **RECEIPT** (Pharmacy Receipt/Facture):\n"
        "   - Cash register receipt from pharmacy\n"
        "   - Contains: pharmacy name, items purchased, prices, total\n"
        "   - Usually thermal paper or printed\n"
        "   - Itemized list with TND prices\n\n"
        "4. **VIGNETTE** (Medication Sticker):\n"
        "   - Small sticker/label from medicine box\n"
        "   - Contains: medicine name, barcode, price, dosage\n"
        "   - Usually attached to bulletin de soins\n"
        "   - Can be multiple vignettes on one paper\n\n"
        "5. **UNKNOWN**: Doesn't match any of the above\n\n"
        "Return JSON:\n"
        "{\n"
        "  \"document_type\": \"ordonnance|bulletin_de_soins|receipt|vignette|unknown\",\n"
        "  \"confidence\": \"high|medium|low\",\n"
        "  \"description\": \"Brief description of what you see\"\n"
        "}\n\n"
        "IMPORTANT: Return ONLY valid JSON, no other text."
    )

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            [prompt, {"mime_type": "image/jpeg", "data": image_data}],
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        data = clean_and_parse_json(response.text)
        print(f"📄 [DOCUMENT TYPE] Detected: {data.get('document_type', 'unknown')}")

        return {
            "document_type": data.get("document_type", "unknown"),
            "confidence": data.get("confidence", "low"),
            "description": data.get("description", "Unable to determine")
        }

    except Exception as e:
        print(f"💥 [DOCUMENT TYPE] Error: {str(e)}")
        return {"document_type": "unknown", "confidence": "low", "description": str(e)}


def analyze_ordonnance(image_data: bytes) -> dict:
    """
    Analyzes a medical prescription (ordonnance).

    Returns:
    {
        "valid": True/False,
        "doctor_name": "Dr. ...",
        "medications": ["Med1", "Med2"],
        "date": "YYYY-MM-DD",
        "has_signature": True/False,
        "has_stamp": True/False,
        "risk_score": 0-100
    }
    """
    prompt = (
        "Analyze this Tunisian medical prescription (ordonnance).\n\n"
        "Extract the following information:\n"
        "1. Doctor's name\n"
        "2. List of prescribed medications\n"
        "3. Prescription date\n"
        "4. Whether it has doctor's signature (check for handwritten signature)\n"
        "5. Whether it has doctor's stamp (official medical stamp)\n\n"
        "VALIDATION RULES:\n"
        "- Valid if: has doctor name, at least 1 medication, signature, stamp\n"
        "- Invalid if: missing critical elements, looks fake, too blurry\n\n"
        "Return JSON:\n"
        "{\n"
        "  \"valid\": true/false,\n"
        "  \"doctor_name\": \"Dr. Name or Unknown\",\n"
        "  \"medications\": [\"Med1\", \"Med2\"],\n"
        "  \"date\": \"YYYY-MM-DD or Unknown\",\n"
        "  \"has_signature\": true/false,\n"
        "  \"has_stamp\": true/false,\n"
        "  \"risk_score\": 0-100,\n"
        "  \"notes\": \"Any concerns or observations\"\n"
        "}\n\n"
        "risk_score: 0=high risk (fake/incomplete), 100=perfect (authentic, complete)"
    )

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            [prompt, {"mime_type": "image/jpeg", "data": image_data}],
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        data = clean_and_parse_json(response.text)
        print(f"💊 [ORDONNANCE] Valid: {data.get('valid', False)}, Score: {data.get('risk_score', 0)}")

        return data

    except Exception as e:
        print(f"💥 [ORDONNANCE] Error: {str(e)}")
        return {"valid": False, "risk_score": 0, "notes": str(e)}


def analyze_bulletin_de_soins(image_data: bytes) -> dict:
    """
    Analyzes a CNAM Bulletin de Soins (green form).

    Returns:
    {
        "valid": True/False,
        "cnam_number": "...",
        "patient_name": "...",
        "care_date": "YYYY-MM-DD",
        "has_cnam_stamp": True/False,
        "has_doctor_stamp": True/False,
        "has_vignettes": True/False,
        "risk_score": 0-100
    }
    """
    prompt = (
        "Analyze this Tunisian CNAM Bulletin de Soins (green healthcare form).\n\n"
        "Extract:\n"
        "1. CNAM beneficiary number (matricule)\n"
        "2. Patient name\n"
        "3. Date of care\n"
        "4. Whether it has CNAM stamp\n"
        "5. Whether it has doctor/pharmacy stamp\n"
        "6. Whether it has medication vignettes attached\n\n"
        "VALIDATION:\n"
        "- Must be predominantly GREEN\n"
        "- Must have CNAM logo/header\n"
        "- Must have official stamps\n"
        "- Should have vignettes or justification\n\n"
        "Return JSON:\n"
        "{\n"
        "  \"valid\": true/false,\n"
        "  \"cnam_number\": \"Number or Unknown\",\n"
        "  \"patient_name\": \"Name or Unknown\",\n"
        "  \"care_date\": \"YYYY-MM-DD or Unknown\",\n"
        "  \"has_cnam_stamp\": true/false,\n"
        "  \"has_doctor_stamp\": true/false,\n"
        "  \"has_vignettes\": true/false,\n"
        "  \"risk_score\": 0-100,\n"
        "  \"notes\": \"Observations\"\n"
        "}\n\n"
        "risk_score: 100=perfect authentic form, 0=fake/incomplete"
    )

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            [prompt, {"mime_type": "image/jpeg", "data": image_data}],
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        data = clean_and_parse_json(response.text)
        print(f"📗 [BULLETIN] Valid: {data.get('valid', False)}, Score: {data.get('risk_score', 0)}")

        return data

    except Exception as e:
        print(f"💥 [BULLETIN] Error: {str(e)}")
        return {"valid": False, "risk_score": 0, "notes": str(e)}


def analyze_vignettes(image_data: bytes) -> dict:
    """
    Analyzes medication vignettes (stickers).

    Returns:
    {
        "valid": True/False,
        "vignettes": [
            {"medicine": "...", "price": 0.0, "barcode_visible": True/False}
        ],
        "count": 0,
        "risk_score": 0-100
    }
    """
    prompt = (
        "Analyze this image for medication vignettes (stickers from medicine boxes).\n\n"
        "For EACH vignette found, extract:\n"
        "1. Medicine name\n"
        "2. Price (if visible)\n"
        "3. Whether barcode is visible\n\n"
        "Return JSON:\n"
        "{\n"
        "  \"valid\": true/false,\n"
        "  \"vignettes\": [\n"
        "    {\n"
        "      \"medicine\": \"Medicine name\",\n"
        "      \"price\": 0.0,\n"
        "      \"barcode_visible\": true/false\n"
        "    }\n"
        "  ],\n"
        "  \"count\": 0,\n"
        "  \"risk_score\": 0-100,\n"
        "  \"notes\": \"Observations\"\n"
        "}\n\n"
        "risk_score: 100=authentic vignettes, 0=fake/suspicious"
    )

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            [prompt, {"mime_type": "image/jpeg", "data": image_data}],
            generation_config={"response_mime_type": "application/json", "temperature": 0}
        )

        data = clean_and_parse_json(response.text)
        print(f"🏷️ [VIGNETTES] Count: {data.get('count', 0)}, Score: {data.get('risk_score', 0)}")

        return data

    except Exception as e:
        print(f"💥 [VIGNETTES] Error: {str(e)}")
        return {"valid": False, "count": 0, "risk_score": 0, "notes": str(e)}


def comprehensive_document_analysis(image_data: bytes) -> dict:
    """
    Complete document analysis pipeline.
    1. Detect document type
    2. Run specialized analysis based on type
    3. Calculate combined confidence score

    Returns complete analysis with risk scoring.
    """
    # Step 1: Detect type
    type_result = detect_document_type(image_data)
    doc_type = type_result["document_type"]

    # Step 2: Specialized analysis
    specialized_result = {}

    if doc_type == "ordonnance":
        specialized_result = analyze_ordonnance(image_data)
    elif doc_type == "bulletin_de_soins":
        specialized_result = analyze_bulletin_de_soins(image_data)
    elif doc_type == "vignette":
        specialized_result = analyze_vignettes(image_data)
    elif doc_type == "receipt":
        # Receipt analysis already handled by main OCR
        specialized_result = {"valid": True, "risk_score": 85}
    else:
        specialized_result = {"valid": False, "risk_score": 0}

    # Step 3: Combined scoring
    combined_score = specialized_result.get("risk_score", 0)

    return {
        "document_type": doc_type,
        "type_confidence": type_result["confidence"],
        "type_description": type_result["description"],
        "analysis": specialized_result,
        "overall_confidence": combined_score,
        "recommendation": "ACCEPT" if combined_score >= 70 else "MANUAL_REVIEW" if combined_score >= 40 else "REJECT"
    }
