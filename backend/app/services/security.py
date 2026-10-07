import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import Utilisateur

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Utilisateur:
    """Valide le jeton porteur et retourne l'utilisateur local correspondant.

    Aucun compte n'est créé implicitement : un jeton dont le `sub` est inconnu
    est rejeté. Cela évite qu'un jeton forgé (ou un compte Supabase orphelin)
    ouvre un accès applicatif.
    """
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration d'authentification incomplète (SUPABASE_JWT_SECRET absent).",
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}  # Supabase utilise son propre aud
        )
        supabase_uid = payload.get("sub")
        if not supabase_uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Jeton invalide (champ sub manquant).",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError as e:
        logger.warning("Jeton JWT refusé: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(Utilisateur).filter(Utilisateur.supabase_uid == supabase_uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Aucun compte local n'est associé à ce jeton.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé.",
        )

    return user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        parts = hashed_password.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        original_key = bytes.fromhex(parts[3])
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(key, original_key)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2_sha256$100000${salt.hex()}${key.hex()}"


def generate_password(length: int = 16) -> str:
    """Génère un mot de passe aléatoire robuste (remplace les mots de passe partagés)."""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd) and any(c in "!@#$%*-_" for c in pwd)):
            return pwd


def validate_password_strength(password: str, minimum: int = 8) -> None:
    """Lève une HTTPException 400 si le mot de passe est trop faible."""
    if not password or len(password) < minimum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le mot de passe doit contenir au moins {minimum} caractères.",
        )
    if password.isdigit() or password.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit mélanger lettres et chiffres.",
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration d'authentification incomplète (SUPABASE_JWT_SECRET absent).",
        )
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "aud": "authenticated",
        "role": "authenticated"
    })
    return jwt.encode(to_encode, settings.SUPABASE_JWT_SECRET, algorithm=settings.ALGORITHM)
