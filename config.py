import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://blood_user_v2:blood_pass_2024@localhost:3308/blood_tracking_v2_1?charset=utf8mb4"
    )
    
    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "v2_1_blood_tracker_secret_key_2024_enhanced"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
    )
    
    # API Security
    API_KEY: str = os.getenv(
        "API_KEY",
        "blood-tracker-v2-1-api-key-2024"
    )
    
    # ESP32 Configuration
    ESP32_TIMEOUT: int = int(os.getenv("ESP32_TIMEOUT", "30"))
    RFID_READ_TIMEOUT: int = int(os.getenv("RFID_READ_TIMEOUT", "60"))
    
    # Blood bag expiration (days)
    BLOOD_BAG_EXPIRATION_DAYS: int = int(os.getenv("BLOOD_BAG_EXPIRATION_DAYS", "42"))
    
    # System settings
    AUTO_LOGOUT_MINUTES: int = int(os.getenv("AUTO_LOGOUT_MINUTES", "30"))
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))

settings = Settings()