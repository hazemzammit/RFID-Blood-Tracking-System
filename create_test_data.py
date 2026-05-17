import mysql.connector
from datetime import datetime, timedelta
import random
import bcrypt
import json


# Database connection
conn = mysql.connector.connect(
    host="localhost",
    port=3308,
    user="blood_user_v2",
    password="blood_pass_2024",
    database="blood_tracking_v2_1"
)

cursor = conn.cursor()

print("🧪 Création de données de test...")

# 1. Create test users
print("\n👥 Création d'utilisateurs de test...")

users = [
    ("admin", "admin@test.com", "admin123", "admin"),
    ("medecin1", "medecin1@test.com", "medecin123", "medical_staff"),
    ("medecin2", "medecin2@test.com", "medecin123", "medical_staff"),
]

for username, email, password, role in users:
    # Check if exists
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        print(f"  ⏭️  {username} existe déjà")
        continue
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute("""
        INSERT INTO users (username, email, hashed_password, role, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (username, email, hashed, role, True, datetime.now()))
    print(f"  ✅ {username} créé")

conn.commit()

# 2. Create test patients
print("\n🏥 Création de patients de test...")

blood_groups = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
first_names = ["Ahmed", "Fatma", "Mohamed", "Aicha", "Youssef", "Leila", "Karim", "Samira"]
last_names = ["Ben Ali", "Ben Salem", "Trabelsi", "Gharbi", "Jebali", "Mansouri"]

for i in range(20):
    patient_code = f"PT{i+1:03d}"
    patient_name = f"{random.choice(first_names)} {random.choice(last_names)}"
    blood_group = random.choice(blood_groups)
    uid = f"TEST{random.randint(10000000, 99999999):08X}"
    
    cursor.execute("""
        INSERT INTO patients (uid, patient_code, patient_name, blood_group, created_at)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE patient_code=patient_code
    """, (uid, patient_code, patient_name, blood_group, datetime.now() - timedelta(days=random.randint(0, 90))))

print(f"  ✅ 20 patients créés")
conn.commit()

# 3. Create test blood pouches
print("\n🩸 Création de poches de sang de test...")

cursor.execute("SELECT id, patient_code, blood_group FROM patients LIMIT 15")
patients = cursor.fetchall()

for patient_id, patient_code, blood_group in patients:
    donor_code = f"DN{patient_code[2:]}"
    uid = f"BAG{random.randint(10000000, 99999999):08X}"
    status = random.choice(["available", "available", "available", "used"])  # 75% available
    created = datetime.now() - timedelta(days=random.randint(0, 35))
    expiration = created + timedelta(days=42)
    
    cursor.execute("""
        INSERT INTO blood_pouches (uid, donor_code, blood_group, status, created_at, expiration_date, patient_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE donor_code=donor_code
    """, (uid, donor_code, blood_group, status, created, expiration, patient_id))

print(f"  ✅ {len(patients)} poches créées")
conn.commit()

# 4. Create test verifications
print("\n✅ Création de vérifications de test...")

cursor.execute("SELECT id FROM patients ORDER BY RAND() LIMIT 10")
patient_ids = [row[0] for row in cursor.fetchall()]

cursor.execute("SELECT id, blood_group FROM blood_pouches WHERE status='used' LIMIT 10")
pouches = cursor.fetchall()

for pouch_id, pouch_blood_group in pouches:
    if not patient_ids:
        break
    
    patient_id = patient_ids.pop()
    
    # Get patient blood group
    cursor.execute("SELECT blood_group FROM patients WHERE id = %s", (patient_id,))
    patient_blood_group = cursor.fetchone()[0]
    
    # Check compatibility
    compatible = {
        "O-": ["O-"],
        "O+": ["O-", "O+"],
        "A-": ["O-", "A-"],
        "A+": ["O-", "O+", "A-", "A+"],
        "B-": ["O-", "B-"],
        "B+": ["O-", "O+", "B-", "B+"],
        "AB-": ["O-", "A-", "B-", "AB-"],
        "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    }
    
    result = "COMPATIBLE" if pouch_blood_group in compatible.get(patient_blood_group, []) else "DANGER"
    verified_at = datetime.now() - timedelta(days=random.randint(0, 30))
    
    cursor.execute("""
        INSERT INTO verifications (pouch_id, patient_id, result, verified_at)
        VALUES (%s, %s, %s, %s)
    """, (pouch_id, patient_id, result, verified_at))

print(f"  ✅ {len(pouches)} vérifications créées")
conn.commit()

# 5. Create audit logs
print("\n📝 Création de logs d'audit de test...")

actions = ["login", "workflow_start", "workflow_progress", "donation", "reception"]

for i in range(50):
    action = random.choice(actions)
    user_id = random.randint(1, 3) if random.random() > 0.3 else None  # 70% have user, 30% system
    details = {"action": action, "test_data": True}
    timestamp = datetime.now() - timedelta(hours=random.randint(0, 72))
    
    cursor.execute("""
        INSERT INTO audit_log (user_id, action_type, details, timestamp)
        VALUES (%s, %s, %s, %s)
    """, (user_id, action, json.dumps(details), timestamp))

print(f"  ✅ 50 logs d'audit créés")
conn.commit()

# Summary
print("\n" + "="*60)
print("✅ DONNÉES DE TEST CRÉÉES AVEC SUCCÈS!")
print("="*60)

cursor.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM patients")
patient_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM blood_pouches")
pouch_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM verifications")
verification_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM audit_log")
audit_count = cursor.fetchone()[0]

print(f"""
📊 RÉSUMÉ:
   • Utilisateurs: {user_count}
   • Patients: {patient_count}
   • Poches de sang: {pouch_count}
   • Vérifications: {verification_count}
   • Logs d'audit: {audit_count}

🔐 IDENTIFIANTS DE TEST:
   Admin:
      Username: admin
      Password: admin123
   
   Médecin:
      Username: medecin1
      Password: medecin123

🚀 Prêt à tester!
   Allez sur: http://localhost:8080/login
""")

cursor.close()
conn.close()