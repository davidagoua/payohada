from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.utilisateur import UtilisateurOut, LoginRequest, ChangePasswordRequest
from app.services.security import get_current_user, verify_password, get_password_hash, create_access_token
from app.models.models import Utilisateur
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.get("/me", response_model=UtilisateurOut)
def read_current_user(current_user: Utilisateur = Depends(get_current_user)):
    """
    Récupère ou synchronise le profil de l'utilisateur actuellement connecté via Supabase.
    """
    return current_user


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Connexion pour les salariés et utilisateurs locaux via email et mot de passe.
    """
    user = db.query(Utilisateur).filter(Utilisateur.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adresse email ou mot de passe incorrect."
        )

    # Si le mot de passe n'est pas encore haché (par défaut à la création), on accepte "Payohada@123"
    is_valid = False
    if not user.hashed_password:
        if request.password == "Payohada@123":
            is_valid = True
    else:
        is_valid = verify_password(request.password, user.hashed_password)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse email ou mot de passe incorrect."
        )

    # Génération du token JWT
    access_token = create_access_token(
        data={"sub": user.supabase_uid, "email": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "nom": user.nom,
            "prenom": user.prenom,
            "is_admin": user.is_admin,
            "salarie_id": user.salarie_id,
            "supabase_uid": user.supabase_uid
        }
    }


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permet à l'utilisateur connecté de modifier son mot de passe.
    """
    is_valid = False
    if not current_user.hashed_password:
        if request.old_password == "Payohada@123":
            is_valid = True
    else:
        is_valid = verify_password(request.old_password, current_user.hashed_password)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ancien mot de passe est incorrect."
        )

    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit faire au moins 6 caractères."
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    db.refresh(current_user)

    return {"message": "Mot de passe mis à jour avec succès."}

