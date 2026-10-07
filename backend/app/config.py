from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Base de données (SQLite par défaut pour le développement)
    DATABASE_URL: str = "sqlite:///./paie.db"

    # JWT / Supabase — AUCUNE valeur par défaut : à fournir via l'environnement.
    # SUPABASE_JWT_SECRET est la clé de signature HS256 : sa fuite permet de
    # forger un jeton pour n'importe quel compte.
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 heures

    # App
    APP_NAME: str = "Logiciel de Paie"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Journalisation des erreurs (facultatif : aucun DSN en dur dans le code)
    BUGSINK_DSN: Optional[str] = None

    # CORS : origines séparées par des virgules. En production, renseigner
    # explicitement le domaine du frontend (jamais "*" avec credentials).
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Anti brute-force sur l'authentification
    LOGIN_MAX_ATTEMPTS: int = 10
    LOGIN_WINDOW_SECONDS: int = 300

    # Réinitialisation de mot de passe
    #: Durée de validité d'un lien de réinitialisation.
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    #: URL publique du frontend, utilisée pour construire le lien envoyé par
    #: email (ex. https://app.payohada.cloud).
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # Téléversement de documents
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 Mo
    ALLOWED_UPLOAD_EXTENSIONS: str = ".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.txt,.csv"

    # SMTP Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_SECURE: bool = False
    #: Délai maximal des opérations SMTP (l'envoi est synchrone dans la requête :
    #: sans timeout, un serveur muet immobiliserait un worker FastAPI).
    SMTP_TIMEOUT: int = 20
    EMAIL_FROM: str = "noreply@payohada.com"
    EMAIL_FROM_NAME: str = "payohada Paie"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_upload_extensions(self) -> set:
        return {
            ext.strip().lower()
            for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",")
            if ext.strip()
        }

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
