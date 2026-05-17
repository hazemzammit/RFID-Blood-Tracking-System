"""
Database setup script for Blood Tracking System
Usage: python setup_new_database.py
"""

import mysql.connector
import sys
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3308")),
    "user": os.getenv("DB_ROOT_USER", "root"),
    "password": os.getenv("DB_ROOT_PASSWORD", "root"),
}

NEW_DB_NAME = os.getenv("NEW_DB_NAME", "blood_tracking_v2_1")
NEW_DB_USER = os.getenv("NEW_DB_USER", "blood_user_v2")
NEW_DB_PASS = os.getenv("NEW_DB_PASSWORD", "blood_pass_2024")


def create_database():
    """Create the new database for blood tracking"""
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Create database
        print(f"🗄️  Création de la base de données '{NEW_DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {NEW_DB_NAME}")
        print(f"✅ Base de données '{NEW_DB_NAME}' créée")

        # Drop user if exists and create fresh
        try:
            cursor.execute(f"DROP USER IF EXISTS '{NEW_DB_USER}'@'localhost'")
            print(f"✅ Ancien utilisateur '{NEW_DB_USER}' supprimé")
        except Exception as e:
            print(f"ℹ️  Pas d'ancien utilisateur: {e}")

        # Create user
        cursor.execute(
            f"CREATE USER '{NEW_DB_USER}'@'localhost' IDENTIFIED BY '{NEW_DB_PASS}'"
        )
        print(f"✅ Utilisateur '{NEW_DB_USER}' créé")

        # Grant privileges
        cursor.execute(
            f"GRANT ALL PRIVILEGES ON {NEW_DB_NAME}.* TO '{NEW_DB_USER}'@'localhost'"
        )
        cursor.execute("FLUSH PRIVILEGES")
        print("✅ Privilèges accordés")

        cursor.close()
        conn.close()

        print(f"\n🎉 Configuration de la base de données terminée!")
        print(f"\n📋 INFORMATIONS DE CONNEXION:")
        print(f"   Database: {NEW_DB_NAME}")
        print(f"   User: {NEW_DB_USER}")
        print(f"   Password: {NEW_DB_PASS}")
        print(f"   Port: {DB_CONFIG['port']}")

        return True

    except mysql.connector.Error as e:
        print(f"❌ Erreur MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def print_manual_instructions():
    """Print manual setup instructions"""
    print("\n" + "=" * 60)
    print("📋 INSTRUCTIONS DE CONFIGURATION MANUELLE")
    print("=" * 60)
    print(f"""
Si la configuration automatique échoue, exécutez ces commandes dans MySQL:

1. Connectez-vous à MySQL:
   mysql -u {DB_CONFIG['user']} -p -P {DB_CONFIG['port']}

2. Exécutez ces commandes SQL:
   CREATE DATABASE IF NOT EXISTS {NEW_DB_NAME};
   DROP USER IF EXISTS '{NEW_DB_USER}'@'localhost';
   CREATE USER '{NEW_DB_USER}'@'localhost' IDENTIFIED BY '{NEW_DB_PASS}';
   GRANT ALL PRIVILEGES ON {NEW_DB_NAME}.* TO '{NEW_DB_USER}'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;

3. Ensuite, lancez: python run_server.py
""")


if __name__ == "__main__":
    print("🚀 Configuration du Système de Suivi de Sang")
    print("=" * 60)

    success = create_database()

    if success:
        print("\n✅ Prêt à démarrer!")
        print("   Exécutez maintenant: python run_server.py")
    else:
        print_manual_instructions()
        sys.exit(1)