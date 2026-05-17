from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    role = Column(String(20), default="medical_staff")  # admin, medical_staff
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(50), unique=True, index=True)
    patient_code = Column(String(50), unique=True, index=True)
    patient_name = Column(String(100))
    blood_group = Column(String(5))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    verifications = relationship("Verification", back_populates="patient")
    donations = relationship("BloodPouch", back_populates="patient")

class BloodPouch(Base):
    __tablename__ = "blood_pouches"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(50), unique=True, index=True)
    donor_code = Column(String(50))
    blood_group = Column(String(5))
    status = Column(String(20), default="available")  # available, used, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expiration_date = Column(DateTime(timezone=True))
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    
    verifications = relationship("Verification", back_populates="pouch")
    patient = relationship("Patient", back_populates="donations")

class Verification(Base):
    __tablename__ = "verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    pouch_id = Column(Integer, ForeignKey("blood_pouches.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    result = Column(String(20))
    verified_at = Column(DateTime(timezone=True), server_default=func.now())
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    pouch = relationship("BloodPouch", back_populates="verifications")
    patient = relationship("Patient", back_populates="verifications")
    operator = relationship("User")

class SystemMode(Base):
    __tablename__ = "system_mode"
    
    id = Column(Integer, primary_key=True)
    current_mode = Column(String(20), default="IDLE")
    current_workflow = Column(String(20), default="NONE")  # DONATION, RECEPTION, NONE
    workflow_step = Column(String(50), default="")
    active_module = Column(String(20), default="NONE")  # MAIN, VERIFICATION, NONE
    workflow_data = Column(JSON, nullable=True)  # Store temporary workflow data
    patient_id_temp = Column(Integer, nullable=True)  # Temporary patient ID during workflow
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String(50))  # login, donation, reception, debug, scan
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")

class RFIDDebugLog(Base):
    __tablename__ = "rfid_debug_log"
    
    id = Column(Integer, primary_key=True)
    module = Column(String(20))  # MAIN, VERIFICATION
    action = Column(String(50))  # read, write, auth, signal
    tag_uid = Column(String(50))
    data = Column(Text, nullable=True)
    success = Column(Boolean)
    error_message = Column(Text, nullable=True)
    signal_strength = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())