from fastapi import APIRouter, Depends
from app.schemas.utilisateur import UtilisateurOut
from app.services.security import get_current_user
from app.models.models import Utilisateur

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.get("/me", response_model=UtilisateurOut)
def read_current_user(current_user: Utilisateur = Depends(get_current_user)):
    """
    Récupère ou synchronise le profil de l'utilisateur actuellement connecté via Supabase.
    """
    return current_user
