import mysql.connector
import sys

def create_database():
    """Create the new database for blood tracking v2.1"""
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(
            host="localhost",
            port=3308,
            user="root",
            password="root"  # CHANGEZ CECI avec votre mot de passe root
        )
        
        cursor = conn.cursor()
        
        # Create database
        print("🗄️  Création de la base de données...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS blood_tracking_v2_1")
        print("✅ Base de données 'blood_tracking_v2_1' créée")
        
        # Drop user if exists and create fresh
        try:
            cursor.execute("DROP USER IF EXISTS 'blood_user_v2'@'localhost'")
            print("✅ Ancien utilisateur supprimé")
        except Exception as e:
            print(f"ℹ️  Pas d'ancien utilisateur: {e}")
        
        # Create user
        cursor.execute("CREATE USER 'blood_user_v2'@'localhost' IDENTIFIED BY 'blood_pass_2024'")
        print("✅ Utilisateur 'blood_user_v2' créé")
        
        # Grant privileges
        cursor.execute("GRANT ALL PRIVILEGES ON blood_tracking_v2_1.* TO 'blood_user_v2'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        print("✅ Privilèges accordés")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Configuration de la base de données terminée!")
        print("\n📋 INFORMATIONS DE CONNEXION:")
        print("   Database: blood_tracking_v2_1")
        print("   User: blood_user_v2")
        print("   Password: blood_pass_2024")
        print("   Port: 3308")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Erreur MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def print_manual_instructions():
    """Print manual setup instructions"""
    print("\n" + "="*60)
    print("📋 INSTRUCTIONS DE CONFIGURATION MANUELLE")
    print("="*60)
    print("""
Si la configuration automatique échoue, exécutez ces commandes dans MySQL:

1. Connectez-vous à MySQL:
   mysql -u root -p -P 3308

2. Exécutez ces commandes SQL:
   CREATE DATABASE IF NOT EXISTS blood_tracking_v2_1;
   DROP USER IF EXISTS 'blood_user_v2'@'localhost';
   CREATE USER 'blood_user_v2'@'localhost' IDENTIFIED BY 'blood_pass_2024';
   GRANT ALL PRIVILEGES ON blood_tracking_v2_1.* TO 'blood_user_v2'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;

3. Ensuite, lancez: python run_server.py
""")

if __name__ == "__main__":
    print("🚀 Configuration du Système de Suivi de Sang V2.1")
    print("="*60)
    
    success = create_database()
    
    if success:
        print("\n✅ Prêt à démarrer!")
        print("   Exécutez maintenant: python run_server.py")
    else:
        print_manual_instructions()
        sys.exit(1)