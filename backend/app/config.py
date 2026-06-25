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

    class Config:
        env_file = ".env"


settings = Settings()