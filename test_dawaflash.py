import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.database.db import init_db, get_db_connection
from app.services.agents import run_ai_claim_agent, process_tariffs_and_ceilings

def test_pipeline():
    print("[TEST] Initializing clean database...")
    init_db()
    
    policy_id = "POL-TUNIS-123"  # Amina Ben Ali. Ceiling: 500 TND, used: 100 TND (Remaining: 400 TND)
    phone_number = "+21650123456"
    
    print("\n--- TEST CASE 1: Standard Claim (Auto-Approved) ---")
    # Doliprane (Tariff: 10 TND max, requested 8.5 TND -> approved 8.5)
    # Spasfon (Tariff: 8 TND max, requested 7.0 TND -> approved 7.0)
    # Total requested: 15.5 TND. Total payout: 15.5 TND. Total <= 100 TND. Remaining ceiling = 400 TND.
    # Expected outcome: AUTO_APPROVED.
    user_msg_1 = "I bought Doliprane for 8.5 TND and Spasfon for 7 TND"
    res_1 = run_ai_claim_agent(policy_id, phone_number, user_msg_1)
    # Convert to ascii representation for terminal printing without crashing on cp1252
    print(res_1.encode('ascii', errors='replace').decode('ascii'))
    
    # Let's inspect database values after the update
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ceiling_used FROM policies WHERE policy_id = ?", (policy_id,))
    ceiling_used = cursor.fetchone()["ceiling_used"]
    print(f"Database: Policy Ceiling Used after Case 1 (Expected 115.50 TND): {ceiling_used:.2f} TND")
    
    print("\n--- TEST CASE 2: Capped Item (Auto-Approved, but capped) ---")
    # Doliprane (requested 12 TND -> capped at 10 TND)
    # Total requested: 12 TND. Total assessed: 10 TND.
    # Expected outcome: AUTO_APPROVED with Doliprane capped.
    user_msg_2 = "I bought Doliprane for 12 TND"
    res_2 = run_ai_claim_agent(policy_id, phone_number, user_msg_2)
    print(res_2.encode('ascii', errors='replace').decode('ascii'))
    
    cursor.execute("SELECT ceiling_used FROM policies WHERE policy_id = ?", (policy_id,))
    ceiling_used = cursor.fetchone()["ceiling_used"]
    print(f"Database: Policy Ceiling Used after Case 2 (Expected 125.50 TND): {ceiling_used:.2f} TND")

    print("\n--- TEST CASE 3: Unlisted Item (Under Manual Review) ---")
    # XYZMedicine for 15 TND -> unlisted/flagged item.
    # Expected outcome: UNDER_MANUAL_REVIEW due to unknown item.
    user_msg_3 = "I bought XYZMedicine for 15 TND"
    res_3 = run_ai_claim_agent(policy_id, phone_number, user_msg_3)
    print(res_3.encode('ascii', errors='replace').decode('ascii'))
    
    cursor.execute("SELECT ceiling_used FROM policies WHERE policy_id = ?", (policy_id,))
    ceiling_used_after_3 = cursor.fetchone()["ceiling_used"]
    print(f"Database: Policy Ceiling Used after Case 3 (Expected unchanged 125.50 TND since it is under review): {ceiling_used_after_3:.2f} TND")

    print("\n--- TEST CASE 4: High Value Claim > 100 TND (Under Manual Review) ---")
    # Clamoxyl for 24 TND + Augmentin for 44 TND + Panadol for 10 TND + Doliprane for 9 TND + Gaviscon for 12 TND + Spasfon for 5 TND
    # Total requested: 104 TND (which is > 100 TND limit)
    # Expected outcome: UNDER_MANUAL_REVIEW due to high value.
    user_msg_4 = "I bought Clamoxyl for 24 TND and Augmentin for 44 TND and Panadol for 10 TND and Doliprane for 9 TND and Gaviscon for 12 TND and Spasfon for 5 TND"
    res_4 = run_ai_claim_agent(policy_id, phone_number, user_msg_4)
    print(res_4.encode('ascii', errors='replace').decode('ascii'))

    print("\n--- TEST CASE 5: Extraction Failure (Honest failure reply, no fallback) ---")
    # Empty message / incomprehensible text -> Should fail honestly.
    # Expected outcome: Honest failure reply.
    user_msg_5 = "hello testing bot"
    res_5 = run_ai_claim_agent(policy_id, phone_number, user_msg_5)
    print(res_5.encode('ascii', errors='replace').decode('ascii'))

    print("\n--- TEST CASE 6: Near/Over Ceiling (Under Manual Review) ---")
    # Let's artificially set ceiling_used to 495 TND (Remaining: 5 TND)
    cursor.execute("UPDATE policies SET ceiling_used = 495.0 WHERE policy_id = ?", (policy_id,))
    conn.commit()
    print("Database: Set policy's ceiling_used to 495.0 TND (Remaining: 5.0 TND)")
    
    # Doliprane (requested 8.0 TND -> approved 8.0 assessed, but remaining ceiling is 5.0, so payout capped at 5.0)
    # Expected outcome: UNDER_MANUAL_REVIEW (Near/Over ceiling)
    user_msg_6 = "I bought Doliprane for 8 TND"
    res_6 = run_ai_claim_agent(policy_id, phone_number, user_msg_6)
    print(res_6.encode('ascii', errors='replace').decode('ascii'))

    conn.close()

if __name__ == "__main__":
    test_pipeline()
