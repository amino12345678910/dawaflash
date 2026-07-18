import sqlite3
conn = sqlite3.connect('app/database/bimasme.db')
cursor = conn.cursor()

print("=========================================")
print("👥 ACTIVE USERS IN DATABASE:")
print("=========================================")
users = cursor.execute('SELECT * FROM users').fetchall()
for u in users:
    print(u)

print("\n=========================================")
print("📁 ALL SCHEMAS/TABLES FOUND:")
print("=========================================")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(t)

conn.close()
