from app.database.db import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

my_phone = "+21692177031"
policy_id = "POL-TUNIS-123"

# نلوجو على الـ Policy ونربطوها بنمرتك
cursor.execute("SELECT * FROM policies WHERE policy_id = ?", (policy_id,))
row = cursor.fetchone()

if row:
    cursor.execute("UPDATE policies SET phone_number = ? WHERE policy_id = ?", (my_phone, policy_id))
    print(f"✅ Linked policy {policy_id} to your phone {my_phone}!")
else:
    # لو مش موجودة نصنعوها من جديد
    cursor.execute("""
    INSERT INTO policies (policy_id, owner_name, coverage_limit, deductible, phone_number)
    VALUES (?, ?, ?, ?, ?)
    """, (policy_id, "Amina Ben Ali", 5000.0, 150.0, my_phone))
    print(f"✅ Created new policy {policy_id} for Amina Ben Ali with phone {my_phone}!")

conn.commit()
conn.close()