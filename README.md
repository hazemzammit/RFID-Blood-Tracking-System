# 🩸 RFID Blood Tracking System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)](https://fastapi.tiangolo.com)

A complete blood donation and transfusion management system using RFID technology. Designed to improve blood bank safety and efficiency through automated tracking, compatibility verification, and real-time monitoring.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Hardware Requirements](#hardware-requirements)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Security](#security)
- [Roadmap](#roadmap)

---

## 🎯 Overview

The RFID Blood Tracking System is a comprehensive solution designed to:

- **Eliminate** blood compatibility errors during transfusions
- **Provide** complete traceability from donation to transfusion
- **Automate** verification processes with RFID technology
- **Reduce** processing time with streamlined workflows
- **Support** multi-platform access (Desktop, Tablet, Mobile)

### How It Works

1. **Donation Workflow**: Scan donor RFID card → Create blood pouch with RFID tag → Store with expiration date
2. **Reception Workflow**: Scan patient RFID card → Scan blood pouch → Automatic compatibility verification → Visual/audio result

---

## ⭐ Key Features

### 🔄 Intelligent Workflows

| Feature | Description |
|---------|------------|
| **Donation Process** | Patient identification via RFID, automatic blood pouch creation, 42-day expiration tracking |
| **Reception Process** | Patient verification, blood pouch scan, real-time compatibility checking with LED/sound feedback |
| **New Patient Registration** | Auto-generated patient codes (PT001, PT002...), RFID card creation |

### 📊 Real-Time Dashboard

- Global statistics overview
- Blood stock charts by group
- Recent activity log
- WebSocket live updates

### 📋 Complete Management

- **Patients**: Registration with auto-generated codes, full history
- **Blood Pouches**: Status tracking (available, used, expired), expiration management
- **Verifications**: Complete traceability with timestamps
- **Users**: Role-based access control (admin, medical_staff)

### 🔧 Admin Features

- **RFID Debug Center**: Test readers, check signal strength, manual read/write
- **Audit Logs**: Complete action history with user tracking
- **User Management**: Create, update, deactivate users

### 📱 Responsive Interface

- Bootstrap 5.3 design
- Touch-optimized (44px minimum buttons)
- Simplified mobile navigation
- Desktop, tablet, and mobile support

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    WEB INTERFACE                         │
│  (Dashboard, Donation, Reception, Admin, Management)     │
└───────────────────┬─────────────────────────────────────┘
                    │
                    │ HTTP/REST API + WebSocket
                    │
┌───────────────────▼─────────────────────────────────────┐
│              BACKEND SERVER (FastAPI)                     │
│  • Workflow management                                   │
│  • REST API endpoints                                    │
│  • Real-time WebSocket                                   │
│  • JWT authentication                                    │
└───────────────────┬─────────────────────────────────────┘
                    │
                    │ SQLAlchemy ORM
                    │
┌───────────────────▼─────────────────────────────────────┐
│              DATABASE (MySQL)                            │
│  • Patients, Pouches, Verifications                      │
│  • Users, Audit Logs                                     │
│  • System state, RFID Logs                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  ESP32 MODULES                           │
│                                                          │
│  ┌───────────────────┐      ┌───────────────────┐      │
│  │   MAIN Module     │      │ VERIFICATION Module│      │
│  │   • RFID Reader   │      │   • RFID Reader   │      │
│  │   • Read/Write    │      │   • Read only     │      │
│  └───────────────────┘      └───────────────────┘      │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │         LCD 16x2 Display                        │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  LEDs: Green (OK), Red (Error)                          │
│  Buzzer: Audio feedback                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.9+ | Runtime |
| FastAPI | 0.104.1 | Web framework |
| SQLAlchemy | 2.0.23 | ORM |
| PyJWT | 2.8.0 | Authentication |
| WebSockets | - | Real-time communication |
| Bcrypt | 4.0.1 | Password hashing |

### Frontend
| Technology | Purpose |
|------------|---------|
| HTML5 / CSS3 | Structure & styling |
| JavaScript (ES6+) | Client logic |
| Bootstrap 5.3 | UI framework |
| Font Awesome 6 | Icons |
| Chart.js | Dashboard charts |

### Hardware
| Component | Quantity | Purpose |
|-----------|----------|---------|
| ESP32 | 1-2 | Microcontroller |
| MFRC522 RFID | 2 | RFID readers |
| LCD 16x2 I2C | 1 | Status display |
| Green LED | 1 | Success indicator |
| Red LED | 1 | Error indicator |
| Buzzer | 1 | Audio feedback |

### Database
| Technology | Version |
|------------|---------|
| MySQL | 8.0+ |

---

## 📦 Hardware Setup

### ESP32 Pin Layout

#### Main Module
| Pin | GPIO |
|-----|------|
| SDA/SS | GPIO 5 |
| RST | GPIO 2 |
| SCK | GPIO 18 |
| MOSI | GPIO 23 |
| MISO | GPIO 19 |

#### Verification Module (shared SPI)
| Pin | GPIO |
|-----|------|
| SDA/SS | GPIO 15 |
| RST | GPIO 4 |
| SCK | GPIO 18 |
| MOSI | GPIO 23 |
| MISO | GPIO 19 |

#### Indicators
| Component | GPIO |
|-----------|------|
| LCD SDA | GPIO 21 |
| LCD SCL | GPIO 22 |
| Green LED | GPIO 25 |
| Red LED | GPIO 26 |
| Buzzer | GPIO 27 |

---

## 🚀 Quick Start

### Prerequisites

```bash
python --version  # >= 3.9
mysql --version   # >= 8.0
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/rfid-blood-system.git
cd rfid-blood-system

# 2. Set up environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your MySQL credentials

# 5. Set up database
python setup_new_database.py

# 6. Run the server
python run_server.py
```

The server will start at **http://localhost:8080**

---

## 💻 Usage Guide

### Web Interface

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Statistics and charts |
| Donation | `/donation` | Blood donation workflow |
| Reception | `/reception` | Blood reception workflow |
| Pouches | `/pouches` | Blood pouch management |
| Patients | `/patients` | Patient management |
| Verifications | `/verifications` | Verification history |
| Admin Debug | `/admin/debug` | RFID hardware testing |
| Audit Logs | `/audit` | System audit trail |
| Users | `/users` | User management (admin) |

### Donation Workflow

1. Navigate to **Donation** page
2. Click **Start Donation**
3. Choose existing patient or create new
4. Scan patient RFID card (MAIN module)
5. Scan blood bag RFID tag (MAIN module)
6. Donation automatically recorded

### Reception Workflow

1. Navigate to **Reception** page
2. Click **Start Reception**
3. Choose existing patient or create new
4. Scan patient RFID card (VERIFICATION module)
5. Scan blood bag (VERIFICATION module)
6. View compatibility result
   - ✅ **COMPATIBLE** - Green LED, transfusion authorized
   - ⚠️ **INCOMPATIBLE** - Red LED, danger alert

---

## 📡 API Documentation

### Authentication

```
POST /api/auth/register   - Create new user
POST /api/auth/login      - Login (returns JWT)
GET  /logout              - Logout
```

### Workflows

```
POST /api/workflow/start                    - Start workflow
POST /api/workflow/donation/patient-choice  - Choose patient type
POST /api/workflow/reception/patient-choice - Choose patient type
POST /api/workflow/patient/new              - Create new patient
POST /api/workflow/progress                 - Update workflow step
POST /api/workflow/cancel                   - Cancel workflow
POST /api/workflow/timeout                  - Handle timeout
```

### Data Management

```
GET  /api/patients          - List patients
POST /api/patients          - Create patient
GET  /api/pouches           - List blood pouches
POST /api/pouches           - Create blood pouch
POST /api/verify            - Verify compatibility
GET  /api/system-mode       - Get system state
PUT  /api/system-mode       - Update system state
```

### Administration

```
POST /api/admin/rfid-debug   - Send RFID debug command
GET  /api/admin/rfid-logs    - Get RFID debug logs
GET  /api/admin/system-metrics - Get system metrics
GET  /api/admin/users        - List all users
PUT  /api/admin/users/{id}   - Update user
DELETE /api/admin/users/{id} - Delete user
```

### Real-Time

```
WS   /ws                    - WebSocket connection
```

### Example

```python
import requests

# Login
response = requests.post(
    'http://localhost:8080/api/auth/login',
    json={'username': 'admin', 'password': 'password'}
)
token = response.json()['access_token']

# Start donation workflow
response = requests.post(
    'http://localhost:8080/api/workflow/start',
    json={'workflow_type': 'DONATION'},
    headers={'Authorization': f'Bearer {token}'}
)
```

---

## 🗄️ Database Schema

### Tables

**users** - System users
```sql
id, username, email, hashed_password, role, is_active, created_at, last_login
```

**patients** - Donors and recipients
```sql
id, uid (RFID), patient_code, patient_name, blood_group, created_at
```

**blood_pouches** - Blood bags
```sql
id, uid (RFID), donor_code, blood_group, status,
expiration_date, patient_id, created_at
```

**verifications** - Compatibility checks
```sql
id, pouch_id, patient_id, result, verified_at, operator_id
```

**system_mode** - Current workflow state
```sql
id, current_mode, current_workflow, workflow_step,
active_module, workflow_data, patient_id_temp, updated_at
```

**audit_log** - Action audit trail
```sql
id, user_id, action_type, details, timestamp
```

**rfid_debug_log** - RFID reader logs
```sql
id, module, action, tag_uid, data, success,
error_message, signal_strength, timestamp
```

---

## 🔒 Security

- ✅ **JWT Authentication** with HttpOnly cookies
- ✅ **Bcrypt password hashing**
- ✅ **Role-based access control** (admin, medical_staff)
- ✅ **Dual role verification** (token + database)
- ✅ **ESP32 API Key** for hardware endpoints
- ✅ **Complete audit logging**
- ✅ **Input validation** (Pydantic schemas)
- ✅ **Environment-based configuration**

---

## 📈 Performance

- Supports **100+ concurrent users**
- Response time **< 100ms** for most operations
- **WebSocket** real-time updates
- **Optimized database** with indexes

---

## 🎯 Roadmap

### Version 1.1 (Planned)
- [ ] Multi-language support (English, Arabic, French)
- [ ] PDF report export
- [ ] Email notifications
- [ ] Appointment scheduling
- [ ] Mobile native application

### Version 2.0 (Future)
- [ ] AI-powered demand prediction
- [ ] Hospital system integration
- [ ] NFC support in addition to RFID
- [ ] Advanced analytics dashboard

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the project
2. Create a branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push (`git push origin feature/improvement`)
5. Open a Pull Request

---

## 👥 Authors

- **Blood Tracking System** - Developed to improve blood bank safety

---

## 📞 Support

- Open an issue on GitHub
- Check the [Installation Guide](INSTALLATION_GUIDE.md)