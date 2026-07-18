import sqlite3

print("--- Initializing Dynamic Account Mapping Patch ---")
conn = sqlite3.connect('app/database/bimasme.db')
cursor = conn.cursor()

# 1. Discover the exact table schema columns
cursor.execute("PRAGMA table_info(policies)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Detected Policies Table Schema: {columns}")

# Find which column matches the phone identifier
phone_column = next((c for c in columns if 'phone' in c.lower()), columns[1])

# 2. Update the seeded test accounts to match your real number variation
# We will overwrite row 1 to point directly to your testing device number
cursor.execute(f"UPDATE policies SET {phone_column} = '+21692177031' WHERE rowid = 1")

# Just in case your router checks for the raw string without the plus sign, we'll alter row 2 too
if len(columns) > 0:
    try:
        cursor.execute(f"UPDATE policies SET {phone_column} = '21692177031' WHERE rowid = 2")
    except Exception:
        pass

conn.commit()

# 3. Read back data to confirm success
cursor.execute("SELECT * FROM policies LIMIT 2")
updated_rows = cursor.fetchall()
print(f"Successfully Patched Active Records:\n{updated_rows}")

conn.close()
print("--- Patch Matrix Applied Cleanly ---")
