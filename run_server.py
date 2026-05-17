# run_server.py - Serveur V2.1
import uvicorn
import os
import webbrowser
import threading
import time
import sys

def print_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🩸  SYSTÈME DE SUIVI DE SANG V2.1                         ║
║   📊  Blood Tracking Management System                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def open_browser():
    """Open the browser after a short delay"""
    time.sleep(3)
    try:
        webbrowser.open("http://localhost:8080")
        print("🌐 Navigateur ouvert automatiquement")
    except:
        print("⚠️  Impossible d'ouvrir le navigateur automatiquement")
        print("   Veuillez ouvrir manuellement: http://localhost:8080")

def print_routes():
    """Print available routes"""
    routes = """
📍 ROUTES DISPONIBLES:
═══════════════════════════════════════════════════════════════

🏠 Interface Principale:
   • Tableau de Bord:        http://localhost:8080
   • Processus Don:          http://localhost:8080/donation
   • Processus Réception:    http://localhost:8080/reception
   
📊 Gestion des Données:
   • Poches de Sang:         http://localhost:8080/pouches
   • Patients:               http://localhost:8080/patients
   • Vérifications:          http://localhost:8080/verifications
   
🔧 Administration:
   • Centre Debug:           http://localhost:8080/admin/debug
   
🔌 API Endpoints:
   • Health Check:           http://localhost:8080/health
   • System Mode:            http://localhost:8080/api/system-mode
   • Debug System:           http://localhost:8080/api/debug/system-mode
   
═══════════════════════════════════════════════════════════════
    """
    print(routes)

def check_prerequisites():
    """Check if all prerequisites are met"""
    print("\n🔍 Vérification des prérequis...")
    
    # Check if database.py exists
    if not os.path.exists("database.py"):
        print("❌ Erreur: database.py introuvable")
        return False
    
    # Check if models.py exists
    if not os.path.exists("models.py"):
        print("❌ Erreur: models.py introuvable")
        return False
    
    # Check if templates directory exists
    if not os.path.exists("templates"):
        print("❌ Erreur: Dossier 'templates' introuvable")
        return False
    
    # Check if static directory exists
    if not os.path.exists("static"):
        print("⚠️  Avertissement: Dossier 'static' introuvable")
        print("   Création du dossier static...")
        os.makedirs("static/css", exist_ok=True)
    
    print("✅ Tous les prérequis sont satisfaits")
    return True

def print_instructions():
    """Print usage instructions"""
    instructions = """
📖 INSTRUCTIONS D'UTILISATION:
═══════════════════════════════════════════════════════════════

1️⃣  PREMIÈRE UTILISATION:
   • Assurez-vous que MySQL est démarré sur le port 3308
   • Exécutez: python setup_new_database.py
   • Puis lancez: python run_server.py

2️⃣  WORKFLOW DE DON:
   • Accédez à: http://localhost:8080/donation
   • Suivez les étapes à l'écran
   • Utilisez le module PRINCIPAL pour tous les scans

3️⃣  WORKFLOW DE RÉCEPTION:
   • Accédez à: http://localhost:8080/reception
   • Suivez les étapes à l'écran
   • Utilisez le module VÉRIFICATION pour les scans

4️⃣  DEBUG RFID (Admin):
   • Accédez à: http://localhost:8080/admin/debug
   • Testez les modules RFID
   • Consultez les logs en temps réel

═══════════════════════════════════════════════════════════════

⚠️  NOTES IMPORTANTES:
   • Le serveur utilise le port 8080
   • WebSocket actif pour les mises à jour temps réel
   • Les logs sont affichés dans cette console
   • Utilisez Ctrl+C pour arrêter le serveur

═══════════════════════════════════════════════════════════════
    """
    print(instructions)

def main():
    """Main entry point"""
    print_banner()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prérequis non satisfaits. Veuillez corriger les erreurs ci-dessus.")
        sys.exit(1)
    
    print_routes()
    print_instructions()
    
    print("\n🚀 Démarrage du serveur...")
    print("⏳ Veuillez patienter...")
    
    # Open browser automatically in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    print("\n" + "="*60)
    print("✅ SERVEUR DÉMARRÉ AVEC SUCCÈS!")
    print("="*60)
    print("\n💡 Conseil: Gardez cette fenêtre ouverte pendant l'utilisation")
    print("🛑 Pour arrêter: Appuyez sur Ctrl+C\n")
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 ARRÊT DU SERVEUR...")
        print("="*60)
        print("✅ Serveur arrêté proprement")
        print("👋 À bientôt!\n")
    except Exception as e:
        print("\n\n" + "="*60)
        print("❌ ERREUR CRITIQUE")
        print("="*60)
        print(f"Erreur: {str(e)}")
        print("\n💡 Solutions possibles:")
        print("   1. Vérifiez que le port 8080 n'est pas déjà utilisé")
        print("   2. Vérifiez que MySQL est démarré")
        print("   3. Vérifiez la configuration dans config.py")
        print("   4. Consultez les logs ci-dessus pour plus de détails\n")
        sys.exit(1)

if __name__ == "__main__":
    main()