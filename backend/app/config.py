from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Base de données (SQLite par défaut pour le développement)
    DATABASE_URL: str = "sqlite:///./paie.db"

    # JWT / Supabase
    SUPABASE_URL: str = "http://supabasekong-n98vdrdsn60ex9heyr6hb27u.72.62.179.19.sslip.io"
    SUPABASE_ANON_KEY: str = "changez-ceci-en-production-avec-la-cle-anon"
    SUPABASE_JWT_SECRET: str = "changez-ceci-en-production-avec-la-cle-jwt-supabase"
    SECRET_KEY: str = "changez-cette-cle-secrete-en-production"
    ALGORITHM: str = "HS256"
 
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 heures

    # App
    APP_NAME: str = "Logiciel de Paie"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    BUGSINK_DSN: Optional[str] = "https://0d8e0afc57dc4284ba102e9071a2df74@bugsink-wotq24lgae4gr7gwz7ueyrni.songon.shop/1"

    # SMTP Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_SECURE: bool = False
    EMAIL_FROM: str = "noreply@payohada.com"
    EMAIL_FROM_NAME: str = "payohada Paie"

    class Config:
        env_file = ".env"


settings = Settings()