"""Configuration de l'application.

Les valeurs sensibles proviennent exclusivement de l'environnement : aucun
secret n'est écrit dans le code. Une validation refuse les valeurs publiques
connues, afin qu'un déploiement ne puisse pas partir avec une clé de signature
que tout le monde peut lire.
"""
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings

#: Valeurs de démonstration publiées dans des documentations ou des dépôts.
#: Les utiliser comme clé de signature HS256 permet à quiconque de forger un
#: jeton pour n'importe quel compte, administrateur compris.
SECRETS_PUBLICS = frozenset({
    "your-super-secret-jwt-token-with-at-least-32-characters-long",
    "super-secret-jwt-token-with-at-least-32-characters-long",
    "your-anon-key",
    "changeme",
    "change-me",
    "secret",
    "test",
})


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
    #: Étiquette d'environnement jointe aux événements (production, staging…).
    BUGSINK_ENVIRONMENT: str = "production"
    #: Échantillonnage des traces de performance.
    #: Bugsink ne collecte que les erreurs : il répond un en-tête
    #: `x-sentry-rate-limits` pour les transactions et les écarte. Les laisser
    #: activées consomme ce quota et retarde les erreurs, d'où la valeur par
    #: défaut à 0. Ne l'augmenter que face à un Sentry complet.
    BUGSINK_TRACES_SAMPLE_RATE: float = 0.0

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

    @field_validator("SUPABASE_JWT_SECRET", "SECRET_KEY")
    @classmethod
    def _refuser_secret_public(cls, valeur: Optional[str], info) -> Optional[str]:
        """Refuse une clé de signature publique ou triviale.

        Le contrôle porte sur la valeur exacte : il ne rejette pas les secrets
        courts utilisés par les tests, mais interdit ceux qui sont publiés dans
        la documentation Supabase ou dans des dépôts d'exemple.
        """
        if valeur and valeur.strip().lower() in SECRETS_PUBLICS:
            raise ValueError(
                f"{info.field_name} contient une valeur publique connue. "
                "Elle permet à n'importe qui de forger un jeton valide pour "
                "n'importe quel compte. Renseignez le secret réel (Supabase : "
                "Project Settings → API → JWT Secret)."
            )
        return valeur

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
