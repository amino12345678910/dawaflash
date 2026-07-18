"""
Comprehensive Multi-Level Fraud Detection System for DawaFlash
Analyzes claims across multiple dimensions and returns detailed confidence scores
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from app.database.db import get_db_connection
import imagehash
from PIL import Image
import io


def calculate_fraud_score(
    policy_id: str,
    phone_number: str,
    extracted_items: List[Dict],
    image_data: bytes,
    analysis: Dict
) -> Dict[str, Any]:
    """
    Comprehensive fraud detection with multiple scoring dimensions.

    Returns:
    {
        "overall_score": 85,  # 0-100, higher = more confident/less fraud
        "risk_level": "LOW/MEDIUM/HIGH",
        "auto_approve": True/False,
        "breakdown": {
            "document_authenticity": 90,
            "tariff_compliance": 85,
            "duplicate_check": 95,
            "pattern_analysis": 80,
            "ceiling_validation": 90
        },
        "flags": ["flag1", "flag2"],
        "recommendation": "AUTO_APPROVE / MANUAL_REVIEW / REJECT"
    }
    """

    conn = get_db_connection()
    cursor = conn.cursor()

    scores = {}
    flags = []

    # ========================================
    # 1. DOCUMENT AUTHENTICITY (0-100)
    # ========================================
    doc_score = 100

    # Check if image looks like real receipt
    try:
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size

        # Too small images are suspicious
        if width < 200 or height < 200:
            doc_score -= 30
            flags.append("Image resolution too low")

        # Aspect ratio check (receipts are usually tall)
        aspect_ratio = height / width if width > 0 else 0
        if aspect_ratio < 0.5:  # Too wide
            doc_score -= 15
            flags.append("Unusual document aspect ratio")

    except Exception as e:
        doc_score -= 20
        flags.append(f"Image processing error: {str(e)}")

    scores["document_authenticity"] = max(0, doc_score)

    # ========================================
    # 2. TARIFF COMPLIANCE (0-100)
    # ========================================
    tariff_score = 100

    if analysis:
        total_requested = analysis.get("total_requested", 0)
        total_assessed = analysis.get("total_assessed", 0)

        # Check for items not in tariff
        not_found_count = len([item for item in analysis.get("breakdown", []) if item.get("status") == "not_in_tariff"])
        if not_found_count > 0:
            tariff_score -= not_found_count * 15
            flags.append(f"{not_found_count} items not in official tariff")

        # Check for excessive claims vs tariff
        if total_assessed > 0:
            excess_ratio = (total_requested - total_assessed) / total_assessed
            if excess_ratio > 0.5:  # Claiming >50% more than tariff
                tariff_score -= 30
                flags.append(f"Claiming {int(excess_ratio*100)}% above tariff limits")

        # Check if all items are high-value (suspicious)
        high_value_count = len([item for item in extracted_items if item.get("price", 0) > 50])
        if high_value_count == len(extracted_items) and len(extracted_items) >= 2:
            tariff_score -= 25
            flags.append(f"CRITICAL: All {len(extracted_items)} items have suspiciously high prices (>50 DT)")

        # Check for absurdly high individual prices
        absurd_prices = [item for item in extracted_items if item.get("price", 0) > 100]
        if absurd_prices:
            tariff_score -= len(absurd_prices) * 30
            flags.append(f"CRITICAL: {len(absurd_prices)} item(s) with absurd prices (>100 DT)")

        # Check if total requested is very large
        if total_requested > 300:
            tariff_score -= 20
            flags.append(f"High total claim: {total_requested:.0f} DT")

    scores["tariff_compliance"] = max(0, tariff_score)

    # ========================================
    # 3. DUPLICATE CHECK (0-100)
    # ========================================
    duplicate_score = 100

    try:
        # Perceptual hash for duplicate detection
        img = Image.open(io.BytesIO(image_data))
        current_hash = str(imagehash.phash(img))

        # Check against recent claims
        cursor.execute("""
            SELECT claim_id, receipt_hash, claim_date, status
            FROM claims
            WHERE policy_id = ?
            ORDER BY claim_date DESC
            LIMIT 50
        """, (policy_id,))

        recent_claims = cursor.fetchall()

        for claim in recent_claims:
            if claim["receipt_hash"] == current_hash:
                duplicate_score = 0
                flags.append(f"DUPLICATE: Exact same receipt as claim #{claim['claim_id']}")
                break

        # Check submission frequency (velocity check)
        recent_24h = [c for c in recent_claims if
                     (datetime.now() - datetime.fromisoformat(c["claim_date"])).days < 1]

        if len(recent_24h) >= 5:
            duplicate_score -= 30
            flags.append(f"High velocity: {len(recent_24h)} claims in 24h")

    except Exception as e:
        duplicate_score -= 10
        flags.append(f"Duplicate check warning: {str(e)}")

    scores["duplicate_check"] = max(0, duplicate_score)

    # ========================================
    # 4. PATTERN ANALYSIS (0-100)
    # ========================================
    pattern_score = 100

    # Check user history
    cursor.execute("""
        SELECT COUNT(*) as claim_count,
               AVG(amount) as avg_amount,
               SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count
        FROM claims
        WHERE policy_id = ?
    """, (policy_id,))

    history = cursor.fetchone()

    if history:
        # High rejection rate is suspicious
        if history["claim_count"] > 0:
            rejection_rate = history["rejected_count"] / history["claim_count"]
            if rejection_rate > 0.3:  # >30% rejected
                pattern_score -= 25
                flags.append(f"High rejection history: {int(rejection_rate*100)}%")

        # Check if current claim is unusually large
        if history["avg_amount"] and analysis:
            current_amount = analysis.get("total_assessed", 0)
            if current_amount > history["avg_amount"] * 3:
                pattern_score -= 20
                flags.append("Claim 3x larger than user's average")

    # Check time patterns (late night submissions are slightly suspicious)
    current_hour = datetime.now().hour
    if current_hour >= 23 or current_hour <= 5:
        pattern_score -= 5
        flags.append("Submitted during unusual hours (late night)")

    scores["pattern_analysis"] = max(0, pattern_score)

    # ========================================
    # 5. CEILING VALIDATION (0-100)
    # ========================================
    ceiling_score = 100

    if analysis:
        ceiling_status = analysis.get("ceiling_status", "unknown")

        if ceiling_status == "exceeded":
            ceiling_score = 0
            flags.append("CRITICAL: Annual ceiling exceeded")
        elif ceiling_status == "near_limit":
            ceiling_score -= 20
            flags.append("Warning: Approaching annual ceiling")

        # Check policy validity
        cursor.execute("SELECT status FROM policies WHERE policy_id = ?", (policy_id,))
        policy = cursor.fetchone()
        if policy and policy["status"] != "active":
            ceiling_score = 0
            flags.append(f"CRITICAL: Policy status is {policy['status']}")

    scores["ceiling_validation"] = max(0, ceiling_score)

    # ========================================
    # CALCULATE OVERALL SCORE
    # ========================================
    # Weighted average (some dimensions matter more)
    weights = {
        "document_authenticity": 0.20,  # 20%
        "tariff_compliance": 0.25,      # 25%
        "duplicate_check": 0.30,        # 30% - most important!
        "pattern_analysis": 0.15,       # 15%
        "ceiling_validation": 0.10      # 10%
    }

    overall_score = sum(scores[key] * weights[key] for key in scores.keys())
    overall_score = round(overall_score, 1)

    # Determine risk level
    if overall_score >= 80:
        risk_level = "LOW"
        recommendation = "AUTO_APPROVE"
        auto_approve = True
    elif overall_score >= 60:
        risk_level = "MEDIUM"
        recommendation = "MANUAL_REVIEW"
        auto_approve = False
    else:
        risk_level = "HIGH"
        recommendation = "MANUAL_REVIEW"  # Could also be REJECT for very low scores
        auto_approve = False

    # Critical flags override auto-approval
    critical_flags = [f for f in flags if "CRITICAL" in f or "DUPLICATE" in f]
    if critical_flags:
        auto_approve = False
        recommendation = "MANUAL_REVIEW"
        if "DUPLICATE" in str(critical_flags):
            recommendation = "REJECT"

    conn.close()

    return {
        "overall_score": overall_score,
        "risk_level": risk_level,
        "auto_approve": auto_approve,
        "recommendation": recommendation,
        "breakdown": scores,
        "flags": flags,
        "weights": weights,
        "analysis_timestamp": datetime.now().isoformat()
    }


def get_fraud_explanation_derja(fraud_result: Dict) -> str:
    """
    Converts fraud detection result to user-friendly Tunisian Derja explanation.
    """
    score = fraud_result["overall_score"]
    risk = fraud_result["risk_level"]
    flags = fraud_result["flags"]

    if fraud_result["auto_approve"]:
        return (
            f"✅ *Demande Approuvée!* (Score: {score}/100)\n\n"
            f"🎯 El demande mte3ek m9abbla automatiquement. "
            f"Kol chay yodhor s7i7 w conforme.\n\n"
            f"📊 Niveau de Risque: {risk}\n"
            f"💰 El flous bech yejiwek fi 3-5 iyem."
        )
    else:
        reason_text = ""
        if flags:
            reason_text = "\n\n⚠️ *Asbe asbeb:*\n"
            for i, flag in enumerate(flags[:3], 1):  # Show top 3 flags
                reason_text += f"{i}. {flag}\n"

        return (
            f"⏸️ *Demande Fi El Mura9aba* (Score: {score}/100)\n\n"
            f"📋 El demande mte3ek bech yraj3oha el mowadhfin mte3na bech yethabbtu minhaأ.\n"
            f"{reason_text}\n"
            f"📊 Niveau de Risque: {risk}\n\n"
            f"⏱️ *Enthadhir:* Bech nrejj3u jaweb fi 24-48 se3a."
        )
