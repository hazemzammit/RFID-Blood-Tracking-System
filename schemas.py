from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class BloodPouchBase(BaseModel):
    uid: str
    donor_code: str
    blood_group: str
    status: str = "available"
    patient_id: Optional[int] = None

class BloodPouchCreate(BloodPouchBase):
    expiration_date: Optional[datetime] = None

class BloodPouch(BloodPouchBase):
    id: int
    created_at: datetime
    expiration_date: Optional[datetime] = None
    patient: Optional[Dict] = None
    
    class Config:
        from_attributes = True

class PatientBase(BaseModel):
    uid: str
    patient_code: str
    patient_name: str
    blood_group: str

class PatientCreate(PatientBase):
    pass

class Patient(PatientBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class VerificationBase(BaseModel):
    pouch_id: int
    patient_id: int
    result: str

class VerificationCreate(VerificationBase):
    pass

class Verification(VerificationBase):
    id: int
    verified_at: datetime
    pouch: Optional[BloodPouch] = None
    patient: Optional[Patient] = None
    
    class Config:
        from_attributes = True

class SystemModeBase(BaseModel):
    current_mode: str
    current_workflow: Optional[str] = "NONE"
    workflow_step: Optional[str] = ""
    active_module: Optional[str] = "NONE"

class SystemMode(SystemModeBase):
    id: int
    workflow_data: Optional[Dict] = None
    patient_id_temp: Optional[int] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_pouches: int
    total_patients: int
    total_verifications: int
    available_pouches: int
    blood_group_stats: List[dict]

class WorkflowStart(BaseModel):
    workflow_type: str  # DONATION, RECEPTION

class DonationPatientChoice(BaseModel):
    has_existing_card: bool
    patient_data: Optional[Dict] = None

class ReceptionPatientChoice(BaseModel):
    has_existing_card: bool
    patient_data: Optional[Dict] = None

class NewPatientData(BaseModel):
    patient_name: str
    blood_group: str

class RFIDDebugCommand(BaseModel):
    module: str  # MAIN, VERIFICATION
    action: str  # read, write, auth, signal
    data: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "medical_staff"

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class RFIDScanData(BaseModel):
    module: str  # MAIN, VERIFICATION
    uid: str
    tag_data: str
    timestamp: Optional[datetime] = None

class WorkflowProgressData(BaseModel):
    workflow_type: str
    step: str
    uid: str
    data: str
    timestamp: int

class AdminMetrics(BaseModel):
    total_pouches: int
    total_patients: int
    total_verifications: int
    total_users: int
    recent_activity: List[Dict]