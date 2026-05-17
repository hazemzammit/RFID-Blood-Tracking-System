from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import asyncio
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt as PyJWT
import traceback

from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from database import get_db, engine
import models
import schemas
from config import settings
from fastapi import Header


from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="Système de Suivi de Sang", version="1.0.0")

# ESP32 API Key (from config.py)
ESP32_API_KEY = settings.API_KEY  # "blood-tracker-v2-1-api-key-2024"

# Dependency to verify ESP32 API key
def verify_esp32_api_key(x_api_key: str = Header(None)):
    if x_api_key != ESP32_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True



# Import auth middleware from the new auth.py module
from auth import AuthMiddleware, require_admin
import auth as auth_mod

# Add middleware to app
app.add_middleware(AuthMiddleware)


# Create tables
models.Base.metadata.create_all(bind=engine)


# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Security
security = HTTPBearer()

# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()












# Store active workflow states
workflow_states = {}

# Authentication
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = PyJWT.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except PyJWT.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

def get_current_user(db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    user = db.query(models.User).filter(models.User.id == token["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur non autorisé")
    return user

# Blood compatibility logic
def is_compatible(patient_group: str, donor_group: str) -> bool:
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
    return donor_group in compatible.get(patient_group, [])


# Authentication routes
@app.post("/api/auth/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(models.User).filter(
            (models.User.username == user.username) | (models.User.email == user.email)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Nom d'utilisateur ou email déjà existant")
        
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        db_user = models.User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {"message": "Utilisateur créé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in register: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
@app.post("/api/auth/login")
def login(response: Response, login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        print(f"\n[LOGIN] Attempting login for: {login_data.username}")
        
        # Try to find user by username OR email
        user = db.query(models.User).filter(
            (models.User.username == login_data.username) | 
            (models.User.email == login_data.username)
        ).first()
        
        if not user:
            print(f"[LOGIN] User not found: {login_data.username}")
            raise HTTPException(status_code=401, detail="Identifiants invalides")
        
        print(f"[LOGIN] User found: {user.username}, Role: {user.role}")
        
        # Check password
        password_bytes = login_data.password.encode('utf-8')
        hash_bytes = user.hashed_password.encode('utf-8')
        
        password_match = bcrypt.checkpw(password_bytes, hash_bytes)
        
        print(f"[LOGIN] Password match: {password_match}")
        
        if not password_match:
            print(f"[LOGIN] Password mismatch")
            raise HTTPException(status_code=401, detail="Identifiants invalides")
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Create token with COMPLETE user data
        token_data = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        token = PyJWT.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Set token as secure HttpOnly cookie
        try:
            secure_flag = False  # Set to True in production with HTTPS
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=secure_flag,
                samesite="lax",
                max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
                path="/"
            )
            print(f"[LOGIN] Cookie set successfully")
        except Exception as e:
            print(f"[LOGIN] WARNING: could not set cookie: {e}")
        
        # Log login
        audit_log = models.AuditLog(
            user_id=user.id,
            action_type="login",
            details={
                "ip": "127.0.0.1", 
                "user_agent": "FastAPI",
                "username": user.username,
                "role": user.role
            }
        )
        db.add(audit_log)
        db.commit()
        
        print(f"[LOGIN] Login successful for user: {user.username} (Role: {user.role})")
        
        # Return complete user data including role
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in login: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# Workflow Management
@app.post("/api/workflow/start")
async def start_workflow(workflow: schemas.WorkflowStart, db: Session = Depends(get_db)):
    try:
        print(f"\n[DEBUG] Starting workflow: {workflow.workflow_type}")
        
        mode = db.query(models.SystemMode).first()
        if not mode:
            print("[DEBUG] Creating new SystemMode")
            mode = models.SystemMode()
            db.add(mode)
        
        mode.current_workflow = workflow.workflow_type
        mode.workflow_step = "WAIT_SELECTION"
        mode.active_module = "NONE"
        mode.workflow_data = {}
        mode.updated_at = datetime.now()
        db.commit()
        db.refresh(mode)
        
        print(f"[DEBUG] SystemMode updated: {mode.current_workflow}, {mode.workflow_step}")
        
        await manager.broadcast(json.dumps({
            "type": "workflow_started",
            "data": {
                "workflow_type": workflow.workflow_type,
                "step": "WAIT_SELECTION",
                "message": "Workflow démarré. Veuillez faire votre sélection."
            }
        }))
        
        print("[DEBUG] Broadcast sent")
        
        audit_log = models.AuditLog(
            user_id=None,
            action_type="workflow_start",
            details={"workflow_type": workflow.workflow_type}
        )
        db.add(audit_log)
        db.commit()
        
        print("[DEBUG] Workflow started successfully")
        
        return {"status": "started", "workflow": workflow.workflow_type}
        
    except Exception as e:
        db.rollback()
        print(f"ERROR in start_workflow: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/api/workflow/donation/patient-choice")
async def donation_patient_choice(choice: schemas.DonationPatientChoice, db: Session = Depends(get_db)):
    try:
        print(f"\n[DEBUG] Donation patient choice: {choice.has_existing_card}")
        
        mode = db.query(models.SystemMode).first()
        if not mode or mode.current_workflow != "DONATION":
            raise HTTPException(status_code=400, detail="Aucun workflow de don en cours")
        
        if choice.has_existing_card:
            mode.workflow_step = "WAIT_PATIENT_CARD"
            mode.active_module = "MAIN"
            message = "Veuillez scanner la carte patient sur le module PRINCIPAL"
        else:
            mode.workflow_step = "NEW_PATIENT_FORM"
            mode.active_module = "NONE"
            message = "Veuillez remplir le formulaire nouveau patient"
        
        mode.updated_at = datetime.now()
        db.commit()
        
        await manager.broadcast(json.dumps({
            "type": "workflow_step_changed",
            "data": {
                "step": mode.workflow_step,
                "active_module": mode.active_module,
                "message": message
            }
        }))
        
        return {"status": "success", "next_step": mode.workflow_step, "active_module": mode.active_module}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in donation_patient_choice: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/api/workflow/reception/patient-choice")
async def reception_patient_choice(choice: schemas.ReceptionPatientChoice, db: Session = Depends(get_db)):
    try:
        print(f"\n[DEBUG] Reception patient choice: {choice.has_existing_card}")
        
        mode = db.query(models.SystemMode).first()
        if not mode or mode.current_workflow != "RECEPTION":
            raise HTTPException(status_code=400, detail="Aucun workflow de réception en cours")
        
        if choice.has_existing_card:
            mode.workflow_step = "WAIT_PATIENT_CARD_VERIFICATION"
            mode.active_module = "VERIFICATION"
            message = "Veuillez scanner la carte patient sur le module VÉRIFICATION"
        else:
            mode.workflow_step = "NEW_PATIENT_FORM"
            mode.active_module = "NONE"
            message = "Veuillez remplir le formulaire nouveau patient"
        
        mode.updated_at = datetime.now()
        db.commit()
        
        await manager.broadcast(json.dumps({
            "type": "workflow_step_changed",
            "data": {
                "step": mode.workflow_step,
                "active_module": mode.active_module,
                "message": message
            }
        }))
        
        return {"status": "success", "next_step": mode.workflow_step, "active_module": mode.active_module}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in reception_patient_choice: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/api/workflow/patient/new")
async def create_new_patient_workflow(patient_data: schemas.NewPatientData, db: Session = Depends(get_db)):
    try:
        print(f"\n[DEBUG] Creating new patient: {patient_data.patient_name}")
        
        mode = db.query(models.SystemMode).first()
        if not mode:
            raise HTTPException(status_code=400, detail="Aucun workflow en cours")
        
        last_patient = db.query(models.Patient).order_by(models.Patient.id.desc()).first()
        if last_patient and last_patient.patient_code:
            try:
                last_number = int(last_patient.patient_code[2:])
                new_number = last_number + 1
            except:
                new_number = 1
        else:
            new_number = 1
        
        patient_code = f"PT{new_number:03d}"
        
        workflow_id = str(uuid.uuid4())
        workflow_states[workflow_id] = {
            "patient_data": {
                **patient_data.dict(),
                "patient_code": patient_code
            },
            "workflow_type": mode.current_workflow,
            "created_at": datetime.now()
        }
        
        mode.workflow_step = "WAIT_PATIENT_CARD_WRITE"
        mode.active_module = "MAIN"
        mode.workflow_data = {
            "workflow_id": workflow_id,
            "patient_code": patient_code,
            "patient_name": patient_data.patient_name,
            "blood_group": patient_data.blood_group
        }
        mode.updated_at = datetime.now()
        db.commit()
        
        await manager.broadcast(json.dumps({
            "type": "patient_data_ready",
            "data": {
                "workflow_id": workflow_id,
                "step": mode.workflow_step,
                "active_module": mode.active_module,
                "patient_code": patient_code,
                "message": "Veuillez scanner une nouvelle carte RFID sur le module PRINCIPAL"
            }
        }))
        
        return {
            "status": "success", 
            "workflow_id": workflow_id, 
            "next_step": mode.workflow_step,
            "patient_code": patient_code
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in create_new_patient_workflow: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")




# Make sure this is called in workflow_progress endpoint
@app.post("/api/workflow/progress")
async def workflow_progress(progress: dict, db: Session = Depends(get_db)):
    try:
        print(f"\n[DEBUG] ðŸ”„ Workflow progress received: {progress.get('step')}")
        print(f"[DEBUG] ðŸ“Š Full progress data: {progress}")
        
        # Log the progress
        audit_log = models.AuditLog(
            user_id=None,
            action_type="workflow_progress",
            details=progress
        )
        db.add(audit_log)
        db.commit()
        
        step = progress.get("step", "")
        
        print(f"[DEBUG] ðŸŽ¯ Processing step: {step}")
        
        # Route to appropriate handler
        if step == "PATIENT_SCANNED":
            await handle_patient_scanned(progress, db)
        elif step == "BLOOD_TAG_WRITTEN":
            print("[DEBUG] ðŸ©¸ Routing to handle_blood_tag_written...")
            await handle_blood_tag_written(progress, db)
        elif step == "PATIENT_TAG_WRITTEN":
            await handle_patient_tag_written(progress, db)
        elif step == "PATIENT_VERIFIED":
            await handle_patient_verified(progress, db)
        elif step == "BLOOD_VERIFIED":
            await handle_blood_verified(progress, db)
        else:
            print(f"[DEBUG] âš ï¸  Unknown step: {step}")
        
        print(f"[DEBUG] âœ… Workflow progress processing completed for step: {step}")
        return {"status": "progress_logged"}
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] âŒ Error in workflow_progress: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")



async def handle_patient_scanned(progress: dict, db: Session):
    """Handle patient scanned during donation workflow"""
    mode = db.query(models.SystemMode).first()
    if mode and mode.current_workflow == "DONATION":
        tag_data = progress.get("data", "")
        uid = progress.get("uid", "")
        
        patient = db.query(models.Patient).filter(models.Patient.uid == uid).first()
        
        if patient:
            mode.patient_id_temp = patient.id
            mode.workflow_step = "WAIT_BLOOD_TAG"
            mode.active_module = "MAIN"
            mode.workflow_data = {
                "patient_id": patient.id,
                "patient_code": patient.patient_code,
                "patient_name": patient.patient_name,  # Include name
                "blood_group": patient.blood_group
            }
            db.commit()
            
            # Broadcast with detailed patient info
            await manager.broadcast(json.dumps({
                "type": "workflow_step_changed",
                "data": {
                    "step": "WAIT_BLOOD_TAG",
                    "active_module": "MAIN",
                    "patient": {
                        "code": patient.patient_code,
                        "name": patient.patient_name,
                        "blood_group": patient.blood_group
                    },
                    "message": f"✅ Patient {patient.patient_name} ({patient.blood_group}) scanné. Veuillez scanner une poche de sang.",
                    "notification": {
                        "type": "success",
                        "title": "Patient Identifié",
                        "message": f"{patient.patient_name} - Groupe {patient.blood_group}"
                    }
                }
            }))


async def handle_blood_tag_written(progress: dict, db: Session):
    """Handle blood tag written during donation workflow"""
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("║  [BACKEND] BLOOD_TAG_WRITTEN           ║")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    mode = db.query(models.SystemMode).first()
    if not mode:
        print("  ❌ No system mode found")
        return
    
    if mode.current_workflow != "DONATION":
        print(f"  ⚠️ Wrong workflow: {mode.current_workflow}")
        return
    
    uid = progress.get("uid", "")
    tag_data = progress.get("data", "")
    
    print(f"  📋 Processing blood tag:")
    print(f"    UID: {uid}")
    print(f"    Data: {tag_data}")
    print(f"    Patient ID: {mode.patient_id_temp}")
    
    # Parse tag data
    parts = tag_data.split(":")
    if len(parts) < 3:
        print(f"  ❌ Invalid tag data format: {tag_data}")
        return
    
    donor_code = parts[1]
    blood_group = parts[2]
    
    print(f"  ✅ Parsed:")
    print(f"    Donor Code: {donor_code}")
    print(f"    Blood Group: {blood_group}")
    
    # Calculate expiration date
    from datetime import datetime, timedelta
    from config import settings
    
    expiration_date = datetime.now() + timedelta(days=settings.BLOOD_BAG_EXPIRATION_DAYS)
    
    print(f"    Expiration: {expiration_date.strftime('%Y-%m-%d')}")
    
    try:
        # Check if UID already exists
        existing_pouch = db.query(models.BloodPouch).filter(
            models.BloodPouch.uid == uid
        ).first()
        
        if existing_pouch:
            print(f"  ⚠️ Blood pouch with UID {uid} already exists! Updating...")
            existing_pouch.donor_code = donor_code
            existing_pouch.blood_group = blood_group
            existing_pouch.status = "available"
            existing_pouch.expiration_date = expiration_date
            existing_pouch.patient_id = mode.patient_id_temp
            blood_pouch = existing_pouch
        else:
            blood_pouch = models.BloodPouch(
                uid=uid,
                donor_code=donor_code,
                blood_group=blood_group,
                status="available",
                expiration_date=expiration_date,
                patient_id=mode.patient_id_temp
            )
            db.add(blood_pouch)
            print("  ✅ Created new blood pouch record")
        
        # Get patient info for notification
        patient = None
        if mode.patient_id_temp:
            patient = db.query(models.Patient).filter(
                models.Patient.id == mode.patient_id_temp
            ).first()
        
        # Reset workflow state
        mode.current_workflow = "NONE"
        mode.workflow_step = ""
        mode.active_module = "NONE"
        mode.patient_id_temp = None
        mode.workflow_data = {}
        mode.updated_at = datetime.now()
        print("  ✅ Workflow state reset")
        
        # Commit to database
        db.commit()
        db.refresh(blood_pouch)
        print("  ✅ Database committed")
        
        # Broadcast donation complete with rich notification
        completion_data = {
            "donor_code": donor_code,
            "blood_group": blood_group,
            "expiration_date": expiration_date.isoformat(),
            "uid": uid,
            "pouch_id": blood_pouch.id,
            "message": "✅ Don enregistré avec succès!",
            "notification": {
                "type": "success",
                "title": "Don Complété",
                "message": f"Poche {donor_code} ({blood_group}) créée",
                "details": {
                    "patient": patient.patient_name if patient else "N/A",
                    "blood_group": blood_group,
                    "donor_code": donor_code,
                    "expiration": expiration_date.strftime('%d/%m/%Y')
                }
            }
        }
        
        print("  📢 Broadcasting donation_complete...")
        
        await manager.broadcast(json.dumps({
            "type": "donation_complete",
            "data": completion_data
        }))
        
        print("  ✅ Broadcast sent successfully!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("║  ✅ DONATION WORKFLOW COMPLETED!      ║")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
    except Exception as e:
        db.rollback()
        print(f"  ❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        await manager.broadcast(json.dumps({
            "type": "workflow_error",
            "data": {
                "message": f"Erreur base de données: {str(e)}",
                "step": "BLOOD_TAG_WRITTEN",
                "notification": {
                    "type": "error",
                    "title": "Erreur",
                    "message": "Échec de l'enregistrement de la poche"
                }
            }
        }))


@app.get("/api/debug/websocket-connections")
def debug_websocket_connections():
    """Debug endpoint to check active WebSocket connections"""
    return {
        "active_connections": len(manager.active_connections),
        "connections": [
            {
                "id": id(conn),
                "state": "open" if conn.client_state == 1 else "closed"
            } for conn in manager.active_connections
        ]
    }


# ============================================================
# NEW: WORKFLOW ACTIVITY TRACKING
# ============================================================

@app.post("/api/workflow/activity")
async def log_workflow_activity(activity_data: dict, db: Session = Depends(get_db)):
    """Log workflow activity for timeout tracking"""
    try:
        print(f"[ACTIVITY] Workflow activity: {activity_data.get('action')}")
        
        # This endpoint is called periodically to keep workflow alive
        # No database changes needed, just acknowledge
        
        return {"status": "activity_logged"}
        
    except Exception as e:
        print(f"ERROR in log_workflow_activity: {str(e)}")
        return {"status": "error", "message": str(e)}


# ============================================================
# ENHANCED: SYSTEM MODE WITH FASTER POLLING
# ============================================================

@app.get("/api/system-mode/fast", response_model=schemas.SystemMode)
def get_system_mode_fast(db: Session = Depends(get_db)):
    """Fast system mode endpoint for ESP32 (reduced payload)"""
    mode = db.query(models.SystemMode).first()
    if not mode:
        mode = models.SystemMode(current_mode="IDLE")
        db.add(mode)
        db.commit()
        db.refresh(mode)
    return mode


# ============================================================
# NEW: NOTIFICATION BROADCAST HELPER
# ============================================================

async def broadcast_notification(notification_type: str, title: str, message: str, details: dict = None):
    """Helper to broadcast notifications to frontend"""
    notification_data = {
        "type": "notification",
        "data": {
            "type": notification_type,  # success, error, warning, info
            "title": title,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await manager.broadcast(json.dumps(notification_data))
    print(f"[NOTIFICATION] Broadcasted: {notification_type} - {title}")




# ============================================================
# ENHANCED: PATIENT TAG WRITTEN WITH NOTIFICATION
# ============================================================

async def handle_patient_tag_written(progress: dict, db: Session):
    """Enhanced patient tag written with duplicate handling"""
    mode = db.query(models.SystemMode).first()
    if mode:
        uid = progress.get("uid", "")
        tag_data = progress.get("data", "")
        
        print(f"[DEBUG] 🏷️ Processing PATIENT_TAG_WRITTEN for UID: {uid}")
        print(f"[DEBUG] Tag data: {tag_data}")
        
        parts = tag_data.split(":")
        if len(parts) >= 3:
            patient_code = parts[1]
            blood_group = parts[2]
            patient_name = parts[3] if len(parts) >= 4 else "Unknown"
            
            try:
                # First, check if patient exists by UID
                existing_patient_by_uid = db.query(models.Patient).filter(
                    models.Patient.uid == uid
                ).first()
                
                if existing_patient_by_uid:
                    print(f"[DEBUG] 🔄 Updating existing patient with UID: {uid}")
                    
                    # Check if we're changing the patient_code to one that already exists
                    if existing_patient_by_uid.patient_code != patient_code:
                        # Verify the new patient_code doesn't exist for another patient
                        code_exists = db.query(models.Patient).filter(
                            models.Patient.patient_code == patient_code,
                            models.Patient.uid != uid  # Exclude current patient
                        ).first()
                        
                        if code_exists:
                            print(f"[ERROR] ❌ Patient code {patient_code} already exists for another patient")
                            # Keep the original patient_code but update other fields
                            existing_patient_by_uid.patient_name = patient_name
                            existing_patient_by_uid.blood_group = blood_group
                        else:
                            # Safe to update patient_code
                            existing_patient_by_uid.patient_code = patient_code
                            existing_patient_by_uid.patient_name = patient_name
                            existing_patient_by_uid.blood_group = blood_group
                    else:
                        # Same patient_code, just update other fields
                        existing_patient_by_uid.patient_name = patient_name
                        existing_patient_by_uid.blood_group = blood_group
                    
                    patient = existing_patient_by_uid
                    
                else:
                    # Check if patient exists by patient_code
                    existing_patient_by_code = db.query(models.Patient).filter(
                        models.Patient.patient_code == patient_code
                    ).first()
                    
                    if existing_patient_by_code:
                        print(f"[DEBUG] 🔄 Updating patient {patient_code} with new UID: {uid}")
                        existing_patient_by_code.uid = uid
                        existing_patient_by_code.patient_name = patient_name
                        existing_patient_by_code.blood_group = blood_group
                        patient = existing_patient_by_code
                    else:
                        print(f"[DEBUG] ➕ Creating new patient: {patient_code}")
                        patient = models.Patient(
                            uid=uid,
                            patient_code=patient_code,
                            patient_name=patient_name,
                            blood_group=blood_group
                        )
                        db.add(patient)
                
                # Commit the changes
                db.commit()
                print(f"[DEBUG] ✅ Patient record updated/created successfully")
                
                # Update workflow based on type
                if mode.current_workflow == "DONATION":
                    mode.patient_id_temp = patient.id
                    mode.workflow_step = "WAIT_BLOOD_TAG"
                    mode.active_module = "MAIN"
                    message = f"✅ Patient {patient_name} mis à jour. Veuillez scanner une poche de sang."
                    
                elif mode.current_workflow == "RECEPTION":
                    mode.patient_id_temp = patient.id
                    mode.workflow_step = "WAIT_PATIENT_CARD_VERIFICATION" 
                    mode.active_module = "VERIFICATION"
                    message = f"✅ Patient {patient_name} mis à jour. Veuillez scanner sa carte sur le module VÉRIFICATION."
                else:
                    message = f"✅ Patient {patient_name} mis à jour avec succès."
                
                mode.workflow_data = {
                    "patient_id": patient.id,
                    "patient_code": patient.patient_code,  # Use the actual code from DB
                    "patient_name": patient_name,
                    "blood_group": blood_group
                }
                
                db.commit()
                
                # Broadcast success
                await manager.broadcast(json.dumps({
                    "type": "workflow_step_changed",
                    "data": {
                        "step": mode.workflow_step,
                        "active_module": mode.active_module,
                        "patient": {
                            "code": patient.patient_code,
                            "name": patient_name,
                            "blood_group": blood_group
                        },
                        "message": message,
                        "workflow_type": mode.current_workflow,
                        "notification": {
                            "type": "success",
                            "title": "Patient Mis à Jour",
                            "message": f"{patient_name} - Groupe {blood_group}"
                        }
                    }
                }))
                
                await manager.broadcast(json.dumps({
                    "type": "patient_created",
                    "data": {
                        "patient_code": patient.patient_code,
                        "patient_name": patient_name,
                        "blood_group": blood_group,
                        "next_step": mode.workflow_step,
                        "active_module": mode.active_module,
                        "message": message,
                        "workflow_type": mode.current_workflow
                    }
                }))
                
                print(f"[DEBUG] ✅ PATIENT_TAG_WRITTEN processing completed")
                
            except Exception as e:
                db.rollback()
                print(f"[ERROR] ❌ Database error: {str(e)}")
                
                # Send specific error message
                error_message = "Erreur de base de données"
                if "Duplicate entry" in str(e):
                    error_message = f"Le code patient {patient_code} existe déjà pour un autre patient"
                
                await broadcast_notification(
                    "error",
                    "Erreur de Mise à Jour",
                    error_message
                )

                
async def handle_patient_verified(progress: dict, db: Session):
    mode = db.query(models.SystemMode).first()
    if mode and mode.current_workflow == "RECEPTION":
        uid = progress.get("uid", "")
        
        patient = db.query(models.Patient).filter(models.Patient.uid == uid).first()
        
        if patient:
            mode.patient_id_temp = patient.id
            mode.workflow_step = "WAIT_BLOOD_TAG"
            mode.active_module = "VERIFICATION"
            mode.workflow_data = {
                "patient_id": patient.id,
                "patient_code": patient.patient_code,
                "blood_group": patient.blood_group
            }
            db.commit()
            
            await manager.broadcast(json.dumps({
                "type": "workflow_step_changed",
                "data": {
                    "step": "WAIT_BLOOD_TAG",
                    "active_module": "VERIFICATION",
                    "patient": {
                        "code": patient.patient_code,
                        "name": patient.patient_name,
                        "blood_group": patient.blood_group
                    },
                    "message": f"Patient {patient.patient_code} vÃ©rifiÃ©. Veuillez scanner la poche de sang."
                }
            }))


# ============================================================
# NEW: TIMEOUT ENDPOINT
# ============================================================

@app.post("/api/workflow/timeout")
async def handle_workflow_timeout(timeout_data: dict, db: Session = Depends(get_db)):
    """Handle workflow timeout from ESP32"""
    try:
        print("\n[TIMEOUT] Workflow timeout received from ESP32")
        print(f"  Reason: {timeout_data.get('reason')}")
        print(f"  Last activity: {timeout_data.get('last_activity')}")
        
        # Reset system mode
        mode = db.query(models.SystemMode).first()
        if mode:
            mode.current_workflow = "NONE"
            mode.workflow_step = ""
            mode.active_module = "NONE"
            mode.patient_id_temp = None
            mode.workflow_data = {}
            mode.updated_at = datetime.now()
            db.commit()
        
        # Log timeout event
        audit_log = models.AuditLog(
            user_id=None,
            action_type="workflow_timeout",
            details=timeout_data
        )
        db.add(audit_log)
        db.commit()
        
        # Broadcast timeout to all connected clients
        await manager.broadcast(json.dumps({
            "type": "workflow_timeout",
            "data": {
                "message": "Workflow annulé par inactivité (30 secondes)",
                "reason": timeout_data.get('reason', 'inactivity'),
                "timestamp": datetime.now().isoformat()
            }
        }))
        
        print("[TIMEOUT] System reset to IDLE")
        return {"status": "timeout_processed", "message": "Workflow reset"}
        
    except Exception as e:
        db.rollback()
        print(f"ERROR in handle_workflow_timeout: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# ENHANCED: VERIFICATION RESULT WITH LED CONTROL
# ============================================================
# In main.py, enhance the verification result handling:

async def handle_blood_verified(progress: dict, db: Session):
    """Enhanced verification with LED feedback"""
    mode = db.query(models.SystemMode).first()
    if mode and mode.current_workflow == "RECEPTION" and mode.patient_id_temp:
        uid = progress.get("uid", "")
        
        pouch = db.query(models.BloodPouch).filter(models.BloodPouch.uid == uid).first()
        patient = db.query(models.Patient).filter(models.Patient.id == mode.patient_id_temp).first()
        
        if pouch and patient:
            # FIXED: Use the same compatibility logic as frontend
            result = "COMPATIBLE" if is_compatible(patient.blood_group, pouch.blood_group) else "INCOMPATIBLE"
            
            verification = models.Verification(
                pouch_id=pouch.id,
                patient_id=patient.id,
                result=result
            )
            db.add(verification)
            
            if result == "COMPATIBLE":
                pouch.status = "used"
            
            # Reset workflow state
            mode.current_workflow = "NONE"
            mode.workflow_step = ""
            mode.active_module = "NONE"
            mode.patient_id_temp = None
            mode.workflow_data = {}
            
            db.commit()
            
            # ENHANCED: Send result with clear LED control instructions
            verification_message = {
                "type": "verification_result",
                "data": {
                    "result": result,
                    "patient": {
                        "patient_code": patient.patient_code,
                        "patient_name": patient.patient_name,
                        "blood_group": patient.blood_group
                    },
                    "pouch": {
                        "uid": pouch.uid,
                        "donor_code": pouch.donor_code,
                        "blood_group": pouch.blood_group
                    },
                    "message": "✅ COMPATIBLE - Transfusion autorisée" if result == "COMPATIBLE" else "⚠️ DANGER - Groupes sanguins incompatibles!",
                    "led_status": "GREEN" if result == "COMPATIBLE" else "RED"  # Clear instruction
                }
            }
            
            # Broadcast to frontend
            await manager.broadcast(json.dumps(verification_message))
            
            # CRITICAL: Also send to ESP32 for LCD display and LED control
            await send_verification_result_to_esp32(
                result, 
                patient.blood_group, 
                pouch.blood_group
            )

async def send_verification_result_to_esp32(result: str, patient_blood: str, pouch_blood: str):
    """Send verification result to ESP32 with LED control"""
    try:
        message = {
            "type": "verification_display",
            "data": {
                "result": result,
                "patient_blood": patient_blood,
                "pouch_blood": pouch_blood,
                "led_status": result  # "COMPATIBLE" or "INCOMPATIBLE"
            }
        }
        
        await manager.broadcast(json.dumps(message))
        print(f"[VERIFICATION] Sent result to ESP32: {result} with LED control")
        
    except Exception as e:
        print(f"[ERROR] Failed to send verification to ESP32: {str(e)}")


@app.get("/api/debug/workflow-state")
def debug_workflow_state(db: Session = Depends(get_db)):
    """Debug endpoint to check current workflow state"""
    mode = db.query(models.SystemMode).first()
    if not mode:
        return {"status": "no_mode"}
    
    return {
        "current_workflow": mode.current_workflow,
        "workflow_step": mode.workflow_step,
        "active_module": mode.active_module,
        "patient_id_temp": mode.patient_id_temp,
        "workflow_data": mode.workflow_data,
        "updated_at": mode.updated_at.isoformat() if mode.updated_at else None
    }

# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("error_404.html", {"request": request}, status_code=404)
    elif exc.status_code == 403:
        return templates.TemplateResponse("error_403.html", {"request": request}, status_code=403)
    elif exc.status_code == 500:
        return templates.TemplateResponse("error_500.html", {"request": request}, status_code=500)
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"UNHANDLED EXCEPTION: {str(exc)}")
    traceback.print_exc()
    return templates.TemplateResponse("error_500.html", {"request": request}, status_code=500)


@app.get("/api/debug/workflow-data")
def debug_workflow_data(db: Session = Depends(get_db)):
    """Debug endpoint to check current workflow data"""
    mode = db.query(models.SystemMode).first()
    if not mode:
        return {"status": "no_mode"}
    
    # Get recent workflow progress logs
    recent_logs = db.query(models.AuditLog).filter(
        models.AuditLog.action_type.like("%workflow%")
    ).order_by(models.AuditLog.timestamp.desc()).limit(10).all()
    
    return {
        "system_mode": {
            "current_workflow": mode.current_workflow,
            "workflow_step": mode.workflow_step,
            "active_module": mode.active_module,
            "patient_id_temp": mode.patient_id_temp,
            "workflow_data": mode.workflow_data,
            "updated_at": mode.updated_at.isoformat() if mode.updated_at else None
        },
        "recent_logs": [
            {
                "id": log.id,
                "action": log.action_type,
                "details": log.details,
                "timestamp": log.timestamp.isoformat()
            } for log in recent_logs
        ]
    }

@app.post("/api/debug/reset-workflow")
async def debug_reset_workflow(db: Session = Depends(get_db)):
    """Debug endpoint to reset workflow state"""
    try:
        mode = db.query(models.SystemMode).first()
        if mode:
            mode.current_workflow = "NONE"
            mode.workflow_step = ""
            mode.active_module = "NONE"
            mode.patient_id_temp = None
            mode.workflow_data = {}
            db.commit()
        
        await manager.broadcast(json.dumps({
            "type": "workflow_reset",
            "data": {"message": "Workflow rÃ©initialisÃ© par debug"}
        }))
        
        return {"status": "reset", "message": "Workflow rÃ©initialisÃ©"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}


@app.post("/api/workflow/cancel")
async def cancel_workflow(db: Session = Depends(get_db)):
    try:
        mode = db.query(models.SystemMode).first()
        if mode:
            mode.current_workflow = "NONE"
            mode.workflow_step = ""
            mode.active_module = "NONE"
            mode.patient_id_temp = None
            mode.workflow_data = {}
            db.commit()
        
        await manager.broadcast(json.dumps({
            "type": "workflow_cancelled",
            "data": {"message": "Workflow annulÃ©"}
        }))
        
        return {"status": "cancelled"}
    except Exception as e:
        db.rollback()
        print(f"ERROR in cancel_workflow: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# API Routes
@app.post("/api/pouches", response_model=schemas.BloodPouch)
async def create_pouch(pouch: schemas.BloodPouchCreate, db: Session = Depends(get_db)):
    try:
        existing_pouch = db.query(models.BloodPouch).filter(models.BloodPouch.uid == pouch.uid).first()
        if existing_pouch:
            existing_pouch.donor_code = pouch.donor_code
            existing_pouch.blood_group = pouch.blood_group
            existing_pouch.status = pouch.status
            existing_pouch.patient_id = pouch.patient_id
            db.commit()
            db.refresh(existing_pouch)
            
            await manager.broadcast(json.dumps({
                "type": "pouch_updated", 
                "data": schemas.BloodPouch.from_orm(existing_pouch).dict()
            }))
            
            return existing_pouch
        
        db_pouch = models.BloodPouch(**pouch.dict())
        db.add(db_pouch)
        db.commit()
        db.refresh(db_pouch)
        
        await manager.broadcast(json.dumps({
            "type": "pouch_created", 
            "data": schemas.BloodPouch.from_orm(db_pouch).dict()
        }))
        
        return db_pouch
        
    except Exception as e:
        db.rollback()
        print(f"ERROR in create_pouch: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/pouches", response_model=List[schemas.BloodPouch])
def read_pouches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    pouches = db.query(models.BloodPouch).offset(skip).limit(limit).all()
    
    # Convert to dict format expected by Pydantic
    result = []
    for pouch in pouches:
        pouch_dict = {
            "id": pouch.id,
            "uid": pouch.uid,
            "donor_code": pouch.donor_code,
            "blood_group": pouch.blood_group,
            "status": pouch.status,
            "created_at": pouch.created_at,
            "expiration_date": pouch.expiration_date,
            "patient_id": pouch.patient_id,
            "patient": None  # Set to None or convert patient if needed
        }
        
        # Optionally include patient info if relationship is loaded
        if pouch.patient:
            pouch_dict["patient"] = {
                "id": pouch.patient.id,
                "patient_code": pouch.patient.patient_code,
                "patient_name": pouch.patient.patient_name,
                "blood_group": pouch.patient.blood_group
            }
        
        result.append(pouch_dict)
    
    return result


@app.post("/api/patients", response_model=schemas.Patient)
async def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    try:
        existing_patient = db.query(models.Patient).filter(models.Patient.uid == patient.uid).first()
        if existing_patient:
            existing_patient.patient_code = patient.patient_code
            existing_patient.patient_name = patient.patient_name
            existing_patient.blood_group = patient.blood_group
            db.commit()
            db.refresh(existing_patient)
            
            await manager.broadcast(json.dumps({
                "type": "patient_updated", 
                "data": schemas.Patient.from_orm(existing_patient).dict()
            }))
            
            return existing_patient
        
        db_patient = models.Patient(**patient.dict())
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        
        await manager.broadcast(json.dumps({
            "type": "patient_created", 
            "data": schemas.Patient.from_orm(db_patient).dict()
        }))
        
        return db_patient
        
    except Exception as e:
        db.rollback()
        print(f"ERROR in create_patient: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/patients", response_model=List[schemas.Patient])
def read_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    patients = db.query(models.Patient).offset(skip).limit(limit).all()
    return patients

@app.post("/api/verify")
async def verify_compatibility(verification: schemas.VerificationCreate, db: Session = Depends(get_db)):
    try:
        pouch = db.query(models.BloodPouch).filter(models.BloodPouch.id == verification.pouch_id).first()
        patient = db.query(models.Patient).filter(models.Patient.id == verification.patient_id).first()
        
        if not pouch or not patient:
            raise HTTPException(status_code=404, detail="Poche ou patient non trouvÃ©")
        
        result = "COMPATIBLE" if is_compatible(patient.blood_group, pouch.blood_group) else "DANGER"
        
        db_verification = models.Verification(
            pouch_id=verification.pouch_id,
            patient_id=verification.patient_id,
            result=result
        )
        db.add(db_verification)
        
        if result == "COMPATIBLE":
            pouch.status = "used"
        
        db.commit()
        db.refresh(db_verification)
        
        db_verification.pouch = pouch
        db_verification.patient = patient
        
        verification_data = {
            "id": db_verification.id,
            "pouch": {"uid": pouch.uid, "blood_group": pouch.blood_group, "donor_code": pouch.donor_code},
            "patient": {"patient_code": patient.patient_code, "blood_group": patient.blood_group},
            "result": result,
            "verified_at": db_verification.verified_at.isoformat()
        }
        
        await manager.broadcast(json.dumps({
            "type": "verification_result", 
            "data": verification_data
        }))
        
        return {"result": result, "verification_id": db_verification.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in verify_compatibility: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/system-mode", response_model=schemas.SystemMode)
def get_system_mode(db: Session = Depends(get_db)):
    mode = db.query(models.SystemMode).first()
    if not mode:
        mode = models.SystemMode(current_mode="IDLE")
        db.add(mode)
        db.commit()
        db.refresh(mode)
    return mode

@app.put("/api/system-mode", response_model=schemas.SystemMode)
async def update_system_mode(mode_update: schemas.SystemModeBase, db: Session = Depends(get_db)):
    try:
        mode = db.query(models.SystemMode).first()
        if not mode:
            mode = models.SystemMode(**mode_update.dict())
            db.add(mode)
        else:
            mode.current_mode = mode_update.current_mode
            mode.current_workflow = mode_update.current_workflow or "NONE"
            mode.workflow_step = mode_update.workflow_step or ""
            mode.active_module = mode_update.active_module or "NONE"
        
        db.commit()
        db.refresh(mode)
        
        await manager.broadcast(json.dumps({
            "type": "mode_changed", 
            "data": {
                "current_mode": mode.current_mode,
                "current_workflow": mode.current_workflow,
                "workflow_step": mode.workflow_step,
                "active_module": mode.active_module
            }
        }))
        
        return mode
    except Exception as e:
        db.rollback()
        print(f"ERROR in update_system_mode: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/api/admin/rfid-debug")
async def rfid_debug_command(command: schemas.RFIDDebugCommand, db: Session = Depends(get_db),
                             current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        debug_log = models.RFIDDebugLog(
            module=command.module,
            action=command.action,
            tag_uid="",
            data=command.data,
            success=True,
            timestamp=datetime.now()
        )
        db.add(debug_log)
        db.commit()
        
        await manager.broadcast(json.dumps({
            "type": "rfid_debug_command",
            "data": {
                "module": command.module,
                "action": command.action,
                "data": command.data
            }
        }))
        
        return {"status": "command_sent", "module": command.module, "action": command.action}
    except Exception as e:
        db.rollback()
        print(f"ERROR in rfid_debug_command: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    

def get_system_metrics(db: Session = Depends(get_db), 
                       current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        total_pouches = db.query(models.BloodPouch).count()
        total_patients = db.query(models.Patient).count()
        total_verifications = db.query(models.Verification).count()
        total_users = db.query(models.User).count()
        
        recent_logs = db.query(models.AuditLog).order_by(
            models.AuditLog.timestamp.desc()
        ).limit(10).all()
        
        recent_activity = []
        for log in recent_logs:
            user = db.query(models.User).filter(models.User.id == log.user_id).first() if log.user_id else None
            recent_activity.append({
                "user": user.username if user else "System",
                "action": log.action_type,
                "timestamp": log.timestamp.isoformat()
            })
        
        return {
            "total_pouches": total_pouches,
            "total_patients": total_patients,
            "total_verifications": total_verifications,
            "total_users": total_users,
            "recent_activity": recent_activity
        }
    except Exception as e:
        print(f"ERROR in get_system_metrics: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/admin/rfid-logs")
def get_rfid_logs(limit: int = 50, db: Session = Depends(get_db),
                 current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        logs = db.query(models.RFIDDebugLog).order_by(
            models.RFIDDebugLog.timestamp.desc()
        ).limit(limit).all()
        
        return [{
            "id": log.id,
            "module": log.module,
            "action": log.action,
            "tag_uid": log.tag_uid,
            "data": log.data,
            "success": log.success,
            "error_message": log.error_message,
            "signal_strength": log.signal_strength,
            "timestamp": log.timestamp.isoformat()
        } for log in logs]
    except Exception as e:
        print(f"ERROR in get_rfid_logs: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/debug/system-mode")
def debug_system_mode(db: Session = Depends(get_db),
                     current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        mode = db.query(models.SystemMode).first()
        if not mode:
            return {"status": "no_mode", "message": "Aucun enregistrement SystemMode trouvÃ©"}
        
        return {
            "status": "success",
            "data": {
                "id": mode.id,
                "current_mode": mode.current_mode,
                "current_workflow": mode.current_workflow,
                "workflow_step": mode.workflow_step,
                "active_module": mode.active_module,
                "patient_id_temp": mode.patient_id_temp,
                "workflow_data": mode.workflow_data,
                "updated_at": mode.updated_at.isoformat() if mode.updated_at else None
            }
        }
    except Exception as e:
        print(f"ERROR in debug_system_mode: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

# Frontend Routes
# Login and Register Pages
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/logout")
async def logout(response: Response):
    # Clear the HttpOnly auth cookie and redirect to login
    response.delete_cookie("access_token", path="/")
    return RedirectResponse(url="/login")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = get_dashboard_stats(db)
    verifications = db.query(models.Verification).order_by(models.Verification.verified_at.desc()).limit(5).all()
    for verification in verifications:
        verification.pouch = db.query(models.BloodPouch).filter(models.BloodPouch.id == verification.pouch_id).first()
        verification.patient = db.query(models.Patient).filter(models.Patient.id == verification.patient_id).first()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "stats": stats,
        "verifications": verifications
    })

@app.get("/donation", response_class=HTMLResponse)
async def donation_page(request: Request):
    return templates.TemplateResponse("donation.html", {"request": request})

@app.get("/reception", response_class=HTMLResponse)
async def reception_page(request: Request):
    return templates.TemplateResponse("reception.html", {"request": request})




# --- DEBUG CENTER ---
@app.get("/admin/debug", response_class=HTMLResponse, dependencies=[Depends(auth_mod.require_admin)])
async def admin_debug_page(request: Request):
    """Admin debug center - Protected by require_admin dependency from auth.py"""
    auth_mod.logger.debug("Access granted - loading admin debug page")
    return templates.TemplateResponse("admin_debug.html", {"request": request})

@app.get("/pouches", response_class=HTMLResponse)
async def pouches_page(request: Request, db: Session = Depends(get_db)):
    pouches = read_pouches(0, 100, db)
    return templates.TemplateResponse("pouches.html", {"request": request, "pouches": pouches})

@app.get("/patients", response_class=HTMLResponse)
async def patients_page(request: Request, db: Session = Depends(get_db)):
    patients = read_patients(0, 100, db)
    return templates.TemplateResponse("patients.html", {"request": request, "patients": patients})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "now": datetime.now().strftime('%d/%m/%Y %H:%M')
    })


@app.get("/api/debug/user-info")
def debug_user_info(current_user: models.User = Depends(get_current_user)):
    """Debug endpoint to check current user info"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active
    }

@app.get("/verifications", response_class=HTMLResponse)
async def verifications_page(request: Request, db: Session = Depends(get_db)):
    verifications = db.query(models.Verification).order_by(models.Verification.verified_at.desc()).limit(100).all()
    for verification in verifications:
        verification.pouch = db.query(models.BloodPouch).filter(models.BloodPouch.id == verification.pouch_id).first()
        verification.patient = db.query(models.Patient).filter(models.Patient.id == verification.patient_id).first()
    return templates.TemplateResponse("verifications.html", {"request": request, "verifications": verifications})

@app.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, current_user: models.User = Depends(auth_mod.require_admin), 
                     db: Session = Depends(get_db)):
    audit_logs = db.query(models.AuditLog).order_by(
        models.AuditLog.timestamp.desc()
    ).limit(100).all()
    
    for log in audit_logs:
        if log.user_id:
            log.user = db.query(models.User).filter(
                models.User.id == log.user_id
            ).first()
    
    return templates.TemplateResponse("audit.html", {
        "request": request,
        "audit_logs": audit_logs
    })

@app.get("/api/audit/logs")
def get_audit_logs(limit: int = 100, db: Session = Depends(get_db), 
                   current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        logs = db.query(models.AuditLog).order_by(
            models.AuditLog.timestamp.desc()
        ).limit(limit).all()
        
        result = []
        for log in logs:
            user = db.query(models.User).filter(models.User.id == log.user_id).first() if log.user_id else None
            result.append({
                "id": log.id,
                "user": user.username if user else "Système",
                "action": log.action_type,
                "details": log.details,
                "timestamp": log.timestamp.isoformat()
            })
        
        return result
    
    except Exception as e:
        print(f"ERROR in get_audit_logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des logs")


@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        users = db.query(models.User).all()
        return [{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        } for user in users]
    except Exception as e:
        print(f"ERROR in get_all_users: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.put("/api/admin/users/{user_id}")
def update_user(user_id: int, user_data: dict, db: Session = Depends(get_db), 
                current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvÃ©")
        
        if "email" in user_data:
            user.email = user_data["email"]
        if "role" in user_data:
            user.role = user_data["role"]
        if "is_active" in user_data:
            user.is_active = user_data["is_active"]
        
        db.commit()
        return {"message": "Utilisateur mis Ã  jour"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in update_user: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), 
                current_user: models.User = Depends(auth_mod.require_admin)):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvÃ©")
        
        # Prevent self-deletion
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")
        
        db.delete(user)
        db.commit()
        return {"message": "Utilisateur supprimÃ©"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR in delete_user: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")



@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, current_user: models.User = Depends(auth_mod.require_admin)):
    return templates.TemplateResponse("users.html", {"request": request})

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                if message_data.get("type") == "tag_scanned":
                    await manager.broadcast(json.dumps({
                        "type": "tag_scanned",
                        "data": message_data.get("data", {})
                    }))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def get_dashboard_stats(db: Session):
    total_pouches = db.query(models.BloodPouch).count()
    total_patients = db.query(models.Patient).count()
    total_verifications = db.query(models.Verification).count()
    available_pouches = db.query(models.BloodPouch).filter(models.BloodPouch.status == "available").count()
    
    blood_groups = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
    blood_group_stats = []
    
    for group in blood_groups:
        count = db.query(models.BloodPouch).filter(
            models.BloodPouch.blood_group == group,
            models.BloodPouch.status == "available"
        ).count()
        blood_group_stats.append({"group": group, "count": count})
    
    return {
        "total_pouches": total_pouches,
        "total_patients": total_patients,
        "total_verifications": total_verifications,
        "available_pouches": available_pouches,
        "blood_group_stats": blood_group_stats
    }




# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)