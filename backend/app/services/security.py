import logging
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
    token = credentials.credentials
    
    # Mode développement/mock si activé et token au format "mock-email-uuid"
    if settings.DEBUG and token.startswith("mock-"):
        parts = token.split("-")
        email = parts[1] if len(parts) > 1 else "test@example.com"
        supabase_uid = parts[2] if len(parts) > 2 else "mock-uuid-12345"
        
        # Récupération ou création de l'utilisateur de test local
        user = db.query(Utilisateur).filter(Utilisateur.supabase_uid == supabase_uid).first()
        if not user:
            user = Utilisateur(
                email=email,
                nom="Mock",
                prenom="User",
                supabase_uid=supabase_uid,
                is_active=True,
                is_admin=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    try:
        # Décodage du token Supabase (HS256 avec la clé secrète Supabase)
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}  # Supabase utilise son propre aud (ex: "authenticated")
        )
        
        # Extraction des identifiants Supabase
        supabase_uid = payload.get("sub")
        email = payload.get("email")
        
        if not supabase_uid or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token Supabase invalide (champs sub/email manquants)",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError as e:
        logger.error(f"Erreur de décodage JWT Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalide ou expiré: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Récupération ou création automatique de l'utilisateur local
    user = db.query(Utilisateur).filter(Utilisateur.supabase_uid == supabase_uid).first()
    if not user:
        # Première connexion de l'utilisateur, synchronisation avec la BDD locale
        user_metadata = payload.get("user_metadata", {})
        user = Utilisateur(
            email=email,
            nom=user_metadata.get("last_name") or user_metadata.get("nom") or "Nom",
            prenom=user_metadata.get("first_name") or user_metadata.get("prenom") or "Prenom",
            supabase_uid=supabase_uid,
            is_active=True,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user
