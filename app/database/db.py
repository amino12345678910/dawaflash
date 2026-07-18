import sqlite3
import os

# This dynamically finds where this exact db.py file lives, 
# and prepares to place our database file (bimasme.db) right next to it!
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "bimasme.db")

def get_db_connection():
    """Establishes a connection to the SQLite database file."""
    # SQLite will automatically create the 'bimasme.db' file if it doesn't exist yet!
    conn = sqlite3.connect(DB_PATH)
    
    # Row factory allows us to read columns by their actual names (like row['owner_name'])
    # instead of index numbers (like row[1]). This makes coding much easier!
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the tables and populates them with starter data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop existing tables to ensure a clean schema pivot for DawaFlash
    cursor.execute("DROP TABLE IF EXISTS sessions")
    cursor.execute("DROP TABLE IF EXISTS policies")
    cursor.execute("DROP TABLE IF EXISTS claims")
    cursor.execute("DROP TABLE IF EXISTS tariffs")
    
    # 1. CREATE SESSIONS TABLE (State Tracking)
    # This acts as our bot's memory so it knows what step the user is on.
    cursor.execute("""
    CREATE TABLE sessions (
        phone_number TEXT PRIMARY KEY,
        policy_id TEXT,
        current_state TEXT DEFAULT 'IDLE',
        meta_json TEXT DEFAULT '{}'
    )
    """)
    
    # 2. CREATE POLICIES TABLE (Mock Customer Database)
    # This stores who is registered with our insurance branch.
    # Enhanced with full CNAM details and status tracking.
    cursor.execute("""
    CREATE TABLE policies (
        policy_id TEXT PRIMARY KEY,
        owner_name TEXT,
        phone_number TEXT,
        cin_number TEXT,
        cnam_number TEXT,
        date_of_birth TEXT,
        address TEXT,
        region TEXT,

        -- Coverage Details
        coverage_limit REAL,
        deductible REAL,
        ceiling_total REAL,
        ceiling_used REAL,

        -- Status
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 3. CREATE CLAIMS TABLE (Claims Ledger)
    # This stores details of every claim filed over WhatsApp.
    # Enhanced with fraud detection and manual review workflow fields.
    cursor.execute("""
    CREATE TABLE claims (
        claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_id TEXT,
        phone_number TEXT,
        extracted_amount REAL,
        assessed_amount REAL,
        status TEXT,

        -- Fraud Detection Fields
        fraud_score REAL,
        risk_level TEXT,
        confidence_breakdown TEXT,
        risk_flags TEXT,
        receipt_hash TEXT,

        -- Manual Review Workflow
        review_status TEXT DEFAULT 'pending',
        auto_approved INTEGER DEFAULT 0,
        reviewer_id TEXT,
        reviewer_notes TEXT,
        reviewed_at TIMESTAMP,

        -- Document Types
        document_types TEXT,
        has_ordonnance INTEGER DEFAULT 0,
        has_bulletin INTEGER DEFAULT 0,
        has_vignette INTEGER DEFAULT 0,

        -- Timestamps
        claim_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        amount REAL
    )
    """)

    # 4. CREATE TARIFFS TABLE (Approved Medicine Price Cap List)
    # This holds the maximum reimbursable TND amount for common pharmacy items.
    cursor.execute("""
    CREATE TABLE tariffs (
        item_name TEXT PRIMARY KEY,
        max_reimbursable REAL
    )
    """)

    # 5. CREATE USERS TABLE (CNAM Onboarding Lifecycle)
    # Tracks the user's progress through the CNAM onboarding process.
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("""
    CREATE TABLE users (
        phone_number TEXT PRIMARY KEY,
        full_name TEXT,
        cin_number TEXT,
        cnam_id TEXT,
        onboarding_state TEXT,
        cin_image_data BLOB,
        face_image_data BLOB,
        carnet_image_data BLOB
    )
    """)
    
    # 6. INSERT REALISTIC TUNISIAN INSURANCE CUSTOMERS (10 sample profiles)
    # Mix of regions, ages, and coverage levels - ready for demo testing
    policies_data = [
        # (policy_id, owner_name, phone, cin, cnam, dob, address, region, coverage, deductible, ceiling_total, ceiling_used, status)
        ('POL-TUNIS-001', 'Amina Ben Ali', '+21650123456', '12345678', 'CNAM-001', '1995-03-15', 'Rue Habib Bourguiba, Tunis', 'Tunis', 5000.0, 10.0, 500.0, 120.0, 'active'),
        ('POL-TUNIS-002', 'Mohamed Trabelsi', '+21698765432', '23456789', 'CNAM-002', '1988-07-22', 'Avenue de la Liberté, Sfax', 'Sfax', 8000.0, 15.0, 800.0, 250.0, 'active'),
        ('POL-TUNIS-003', 'Salma Hamdi', '+21654321098', '34567890', 'CNAM-003', '1992-11-30', 'Rue du Bardo, Tunis', 'Tunis', 6000.0, 10.0, 600.0, 50.0, 'active'),
        ('POL-TUNIS-004', 'Youssef Mansour', '+21699888777', '45678901', 'CNAM-004', '1980-05-18', 'Boulevard 7 Novembre, Bizerte', 'Bizerte', 10000.0, 20.0, 1000.0, 450.0, 'active'),
        ('POL-TUNIS-005', 'Nadia Karray', '+21652111222', '56789012', 'CNAM-005', '1975-09-03', 'Avenue Habib Thameur, Sousse', 'Sousse', 12000.0, 25.0, 1200.0, 800.0, 'active'),
        ('POL-TUNIS-006', 'Karim Bouzid', '+21697555666', '67890123', 'CNAM-006', '2000-01-25', 'Rue de la République, Kairouan', 'Kairouan', 4000.0, 8.0, 400.0, 30.0, 'active'),
        ('POL-TUNIS-007', 'Leila Zaouche', '+21653444555', '78901234', 'CNAM-007', '1985-12-10', 'Avenue Farhat Hached, Nabeul', 'Nabeul', 7000.0, 12.0, 700.0, 180.0, 'active'),
        ('POL-TUNIS-008', 'Riadh Jebali', '+21696222333', '89012345', 'CNAM-008', '1978-04-28', 'Rue Ali Bach Hamba, Gabès', 'Gabès', 9000.0, 18.0, 900.0, 600.0, 'active'),
        ('POL-TUNIS-009', 'Sonia Fehri', '+21655777888', '90123456', 'CNAM-009', '1998-08-14', 'Avenue Mohamed V, Monastir', 'Monastir', 5500.0, 10.0, 550.0, 90.0, 'active'),
        ('POL-TUNIS-010', 'Hichem Dridi', '+21694333444', '01234567', 'CNAM-010', '1970-06-20', 'Boulevard de l\'Environnement, Ariana', 'Ariana', 11000.0, 22.0, 1100.0, 950.0, 'active'),
    ]

    cursor.executemany("""
    INSERT INTO policies (
        policy_id, owner_name, phone_number, cin_number, cnam_number,
        date_of_birth, address, region, coverage_limit, deductible,
        ceiling_total, ceiling_used, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, policies_data)

    # 7. INSERT COMPREHENSIVE TARIFF LIMITS (50+ common Tunisian pharmacy items)
    tariffs_data = [
        # Pain Relief & Fever
        ('Doliprane', 10.0),
        ('Panadol', 12.0),
        ('Paracétamol', 8.0),
        ('Efferalgan', 11.0),
        ('Aspégic', 9.0),
        ('Aspirin', 7.0),

        # Antibiotics
        ('Clamoxyl', 25.0),
        ('Augmentin', 45.0),
        ('Amoxicilline', 22.0),
        ('Zinnat', 38.0),
        ('Ciprofloxacine', 35.0),
        ('Azithromycine', 40.0),
        ('Flagyl', 28.0),

        # Digestive
        ('Gaviscon', 15.0),
        ('Spasfon', 8.0),
        ('Smecta', 12.0),
        ('Motilium', 18.0),
        ('Imodium', 14.0),
        ('Debridat', 20.0),

        # Respiratory & Allergies
        ('Rhinadvil', 16.0),
        ('Claritine', 22.0),
        ('Aerius', 25.0),
        ('Ventolin', 30.0),
        ('Pulmicort', 45.0),
        ('Toplexil', 18.0),
        ('Mucomyst', 20.0),

        # Anti-inflammatory
        ('Profenid', 24.0),
        ('Voltaren', 28.0),
        ('Brufen', 19.0),
        ('Nurofen', 21.0),
        ('Advil', 17.0),

        # Vitamins & Supplements
        ('Vitamine C', 8.0),
        ('Vitamine D', 12.0),
        ('Calcium', 10.0),
        ('Fer', 15.0),
        ('Magnésium', 14.0),
        ('Zinc', 13.0),

        # Diabetes
        ('Metformine', 35.0),
        ('Glucophage', 40.0),
        ('Insuline', 80.0),

        # Cardiovascular
        ('Cardioaspirine', 25.0),
        ('Atenolol', 30.0),
        ('Amlodipine', 28.0),

        # Dermatology
        ('Bépanthène', 16.0),
        ('Biafine', 18.0),
        ('Diprosone', 22.0),

        # Gynecology
        ('Utrogestan', 32.0),
        ('Duphaston', 35.0),

        # Other Common
        ('Solupred', 20.0),
        ('Atarax', 18.0),
        ('Lexomil', 16.0),
        ('Seresta', 15.0)
    ]

    cursor.executemany("""
    INSERT INTO tariffs (item_name, max_reimbursable)
    VALUES (?, ?)
    """, tariffs_data)
    
    # Commit saves our changes permanently to the file, then we close the connection.
    conn.commit()
    conn.close()

def get_user_state(phone_number: str) -> str:
    """Fetches the current onboarding state of the user. Default: 'NEED_CIN'."""
    clean_phone = phone_number.replace("whatsapp:", "").strip()
    prefixed_phone = f"whatsapp:{clean_phone}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT onboarding_state FROM users WHERE phone_number = ? OR phone_number = ?", (clean_phone, prefixed_phone))
    row = cursor.fetchone()
    conn.close()
    if row and row["onboarding_state"]:
        return row["onboarding_state"]
    return "NEED_CIN"

def update_user_state(phone_number: str, next_state: str, **kwargs):
    """Updates the user's onboarding state and saves any provided details as they are provided."""
    clean_phone = phone_number.replace("whatsapp:", "").strip()
    prefixed_phone = f"whatsapp:{clean_phone}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure the user exists in the table first (check both formats)
    cursor.execute("SELECT phone_number FROM users WHERE phone_number = ? OR phone_number = ?", (clean_phone, prefixed_phone))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute(
            "INSERT INTO users (phone_number, onboarding_state) VALUES (?, ?)",
            (clean_phone, next_state)
        )
        target_phone = clean_phone
    else:
        target_phone = row["phone_number"]
        
    # Dynamically build UPDATE query for state and optional kwargs
    update_fields = ["onboarding_state = ?"]
    params = [next_state]
    
    for key, val in kwargs.items():
        if key in ["full_name", "cin_number", "cnam_id"]:
            update_fields.append(f"{key} = ?")
            params.append(val)
            
    params.append(target_phone)
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE phone_number = ?"
    cursor.execute(query, params)
    
    conn.commit()
    conn.close()

# If we run this file directly in the terminal, it will execute this block:
if __name__ == "__main__":
    init_db()
    print("[SUCCESS] Database created and initialized successfully!")
    print(f"Database file is located at: {DB_PATH}")