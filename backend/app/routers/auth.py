from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.utilisateur import UtilisateurOut, LoginRequest, ChangePasswordRequest, CabinetSignupRequest
from app.services.security import get_current_user, verify_password, get_password_hash, create_access_token
from app.models.models import Utilisateur
from app.database import get_db
import uuid

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.get("/me", response_model=UtilisateurOut)
def read_current_user(current_user: Utilisateur = Depends(get_current_user)):
    """
    Récupère ou synchronise le profil de l'utilisateur actuellement connecté via Supabase.
    """
    user_out = UtilisateurOut.model_validate(current_user)
    if current_user.dossier_id and current_user.dossier_client:
        user_out.nom_dossier = current_user.dossier_client.nom_dossier
    return user_out


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Connexion pour les salariés, clients et gestionnaires via email et mot de passe.
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

    nom_dossier = None
    if user.dossier_id and user.dossier_client:
        nom_dossier = user.dossier_client.nom_dossier

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "nom": user.nom,
            "prenom": user.prenom,
            "is_admin": user.is_admin,
            "role": user.role or "cabinet",
            "dossier_id": user.dossier_id,
            "nom_dossier": nom_dossier,
            "salarie_id": user.salarie_id,
            "supabase_uid": user.supabase_uid,
            "cabinet_nom": user.cabinet_nom,
            "cabinet_telephone": user.cabinet_telephone,
            "cabinet_ville": user.cabinet_ville
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


@router.post("/signup-cabinet", status_code=status.HTTP_201_CREATED)
def signup_cabinet(
    request: CabinetSignupRequest,
    db: Session = Depends(get_db)
):
    """
    Inscription d'un nouveau cabinet de paie.
    Crée un compte utilisateur avec rôle 'cabinet' et retourne un JWT
    pour une connexion immédiate sans validation email.
    """
    # Vérifier que l'email n'est pas déjà utilisé
    existing = db.query(Utilisateur).filter(Utilisateur.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse email est déjà associée à un compte."
        )

    # Validation du mot de passe
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 8 caractères."
        )

    # Création du compte cabinet
    hashed = get_password_hash(request.password)
    uid = f"local-cabinet-{uuid.uuid4()}"

    new_user = Utilisateur(
        email=request.email,
        nom=request.nom,
        prenom=request.prenom,
        hashed_password=hashed,
        supabase_uid=uid,
        is_active=True,
        is_admin=False,
        role="cabinet",
        cabinet_nom=request.cabinet_nom,
        cabinet_telephone=request.cabinet_telephone,
        cabinet_ville=request.cabinet_ville,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Génération du JWT pour connexion immédiate
    access_token = create_access_token(
        data={"sub": new_user.supabase_uid, "email": new_user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "nom": new_user.nom,
            "prenom": new_user.prenom,
            "is_admin": new_user.is_admin,
            "role": new_user.role,
            "dossier_id": None,
            "nom_dossier": None,
            "salarie_id": None,
            "supabase_uid": new_user.supabase_uid,
            "cabinet_nom": new_user.cabinet_nom,
            "cabinet_telephone": new_user.cabinet_telephone,
            "cabinet_ville": new_user.cabinet_ville,
        }
    }

