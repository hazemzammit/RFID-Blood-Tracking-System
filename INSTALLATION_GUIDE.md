# 📘 Guide d'Installation - Système de Suivi de Sang V2.1

## 🔧 Prérequis Système

### Logiciels Requis
- **Python 3.9+** (recommandé: Python 3.10 ou 3.11)
- **MySQL Server 8.0+** (configuré sur le port 3308)
- **Git** (pour cloner le projet)
- **Navigateur Web moderne** (Chrome, Firefox, Edge)

### Matériel (pour production complète)
- ESP32 (x2 recommandé pour dual RFID)
- MFRC522 RFID Readers (x2)
- LCD 16x2 I2C
- LEDs (vert, rouge)
- Buzzer
- Câbles de connexion

---

## 📦 Installation Étape par Étape

### Étape 1: Cloner/Copier le Projet
```bash
# Si vous utilisez Git
git clone <votre-repo-url>
cd blood-tracking-v2-1

# OU créez un nouveau dossier et copiez tous les fichiers
mkdir blood-tracking-v2-1
cd blood-tracking-v2-1
# Copiez tous les fichiers du projet ici
```

### Étape 2: Créer un Environnement Virtuel Python
```bash
# Sous Windows
python -m venv venv
venv\Scripts\activate

```

Vous devriez voir `(venv)` apparaître dans votre terminal.

### Étape 3: Installer les Dépendances Python
```bash
# Mise à jour de pip
python -m pip install --upgrade pip

# Installation de toutes les dépendances
pip install -r requirements.txt
```

**Temps estimé:** 2-5 minutes selon votre connexion internet.

### Étape 4: Vérifier MySQL
```bash
# Vérifiez que MySQL est en cours d'exécution
# Sous Windows (PowerShell)
Get-Service MySQL*


# Testez la connexion
mysql -u root -p -P 3308
# Entrez votre mot de passe root MySQL
# Si connexion réussie, tapez: EXIT;
```

### Étape 5: Configurer la Base de Données

**Important:** Modifiez d'abord le mot de passe root dans `setup_new_database.py`
```python
# Ligne 8 dans setup_new_database.py
password="VOTRE_MOT_DE_PASSE_ROOT_ICI"  # Changez ceci!
```

Puis exécutez:
```bash
python setup_new_database.py
```

**Sortie attendue:**
```
🗄️  Création de la base de données...
✅ Base de données 'blood_tracking_v2_1' créée
✅ Ancien utilisateur supprimé
✅ Utilisateur 'blood_user_v2' créé
✅ Privilèges accordés

🎉 Configuration de la base de données terminée!

📋 INFORMATIONS DE CONNEXION:
   Database: blood_tracking_v2_1
   User: blood_user_v2
   Password: blood_pass_2024
   Port: 3308
```

### Étape 6: Vérifier la Configuration
```bash
# Vérifiez que config.py contient la bonne URL de base de données
# Elle devrait être:
# DATABASE_URL = "mysql+pymysql://blood_user_v2:blood_pass_2024@localhost:3308/blood_tracking_v2_1?charset=utf8mb4"
```

### Étape 7: Créer la Structure des Dossiers
```bash
# Créer les dossiers nécessaires s'ils n'existent pas
mkdir -p templates
mkdir -p static/css
```

### Étape 8: Lancer le Serveur
```bash
python run_server.py
```

**Sortie attendue:**
```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🩸  SYSTÈME DE SUIVI DE SANG V2.1                         ║
║   📊  Blood Tracking Management System                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

🔍 Vérification des prérequis...
✅ Tous les prérequis sont satisfaits

📍 ROUTES DISPONIBLES:
...

🚀 Démarrage du serveur...
⏳ Veuillez patienter...

============================================================
✅ SERVEUR DÉMARRÉ AVEC SUCCÈS!
============================================================

💡 Conseil: Gardez cette fenêtre ouverte pendant l'utilisation
🛑 Pour arrêter: Appuyez sur Ctrl+C
```

Le navigateur devrait s'ouvrir automatiquement sur http://localhost:8080

---

## 🧪 Test de l'Installation

### Test 1: Accès au Tableau de Bord
1. Ouvrez: http://localhost:8080
2. Vous devriez voir le tableau de bord avec des statistiques à 0

### Test 2: Health Check API
```bash
# Dans un nouveau terminal
curl http://localhost:8080/health
```
**Réponse attendue:**
```json
{"status":"healthy","timestamp":"2024-..."}
```

### Test 3: System Mode API
```bash
curl http://localhost:8080/api/system-mode
```
**Réponse attendue:**
```json
{
  "current_mode":"IDLE",
  "current_workflow":"NONE",
  "workflow_step":"",
  "active_module":"NONE",
  "id":1,
  "workflow_data":null,
  "patient_id_temp":null,
  "updated_at":"..."
}
```

### Test 4: Pages du Workflow
- Don: http://localhost:8080/donation
- Réception: http://localhost:8080/reception
- Debug: http://localhost:8080/admin/debug

---

## 🔌 Configuration ESP32 (Optionnel)

### Prérequis Arduino IDE
1. Installez Arduino IDE 2.x
2. Installez le support ESP32:
   - File → Preferences → Additional Board Manager URLs
   - Ajoutez: `https://dl.espressif.com/dl/package_esp32_index.json`
   - Tools → Board → Boards Manager → Recherchez "ESP32" → Install

### Bibliothèques Requises
Dans Arduino IDE: Sketch → Include Library → Manage Libraries
```
- MFRC522 (by GithubCommunity)
- LiquidCrystal I2C (by Frank de Brabander)
- ArduinoJson (by Benoit Blanchon) v6.x
- WiFi (intégré avec ESP32)
- HTTPClient (intégré avec ESP32)
```

### Configuration WiFi dans le Code ESP32
Modifiez ces lignes dans votre code ESP32:
```cpp
const char* ssid = "VOTRE_WIFI_SSID";
const char* password = "VOTRE_WIFI_PASSWORD";
const char* serverUrl = "http://VOTRE_IP_SERVEUR:8080";
```

Pour trouver votre IP serveur:
```bash
# Windows
ipconfig
# Cherchez "IPv4 Address"

# Linux/Mac
ifconfig
# OU
ip addr show
```

---

## 🐛 Dépannage

### Problème: Port 8080 déjà utilisé
**Solution:**
```bash
# Windows - Trouver et tuer le processus
netstat -ano | findstr :8080
taskkill /PID <PID_NUMBER> /F

# Linux/Mac
lsof -i :8080
kill -9 <PID>
```

### Problème: Erreur de connexion MySQL
**Solutions:**
1. Vérifiez que MySQL est démarré
2. Vérifiez le port (3308 vs 3306)
3. Vérifiez les identifiants dans `config.py`
4. Testez manuellement:
```bash
mysql -u blood_user_v2 -pblood_pass_2024 -P 3308 blood_tracking_v2_1
```

### Problème: Module 'X' introuvable
**Solution:**
```bash
# Réinstallez les dépendances
pip install -r requirements.txt --force-reinstall
```

### Problème: Templates non trouvés
**Solution:**
```bash
# Vérifiez la structure des dossiers
ls -la templates/
# Tous les fichiers .html doivent être là
```

### Problème: CSS ne se charge pas
**Solution:**
```bash
# Vérifiez le dossier static
ls -la static/css/
# mobile.css doit être présent

# Videz le cache du navigateur: Ctrl+Shift+R
```

---

## 📱 Test sur Mobile/Tablette

1. Trouvez l'IP de votre serveur (voir section ESP32)
2. Sur votre appareil mobile, connectez-vous au même réseau WiFi
3. Ouvrez le navigateur et accédez à: `http://VOTRE_IP:8080`
4. L'interface devrait être responsive et adaptée au mobile

---

## 🎯 Prochaines Étapes

Maintenant que l'installation est terminée:

1. **Créer un utilisateur admin:**
```bash
   # Utilisez l'API ou créez-le manuellement via MySQL
```

2. **Tester le workflow de don:**
   - Allez sur /donation
   - Suivez les étapes sans RFID (mode simulation)

3. **Configurer les ESP32:**
   - Téléversez le code
   - Testez la connexion WiFi
   - Vérifiez les logs dans /admin/debug

4. **Former les utilisateurs:**
   - Montrez les workflows
   - Expliquez les différents modules
   - Pratiquez avec des scénarios réels

---

## 📞 Support

En cas de problème:
1. Consultez les logs du serveur (terminal)
2. Vérifiez /admin/debug pour les erreurs RFID
3. Consultez la documentation API
4. Vérifiez que tous les fichiers sont présents

---

## ✅ Checklist de Vérification Finale

- [ ] Python 3.9+ installé
- [ ] MySQL démarré sur port 3308
- [ ] Environnement virtuel créé et activé
- [ ] Dépendances installées (`pip list` pour vérifier)
- [ ] Base de données créée (blood_tracking_v2_1)
- [ ] Utilisateur MySQL créé (blood_user_v2)
- [ ] Fichiers config.py configuré
- [ ] Dossiers templates/ et static/ présents
- [ ] Serveur démarre sans erreur
- [ ] Page d'accueil accessible (http://localhost:8080)
- [ ] API Health Check fonctionne
- [ ] Pages donation et reception accessibles

Si tous les points sont cochés: **🎉 Installation réussie!**