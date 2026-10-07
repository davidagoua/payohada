import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.schemas.utilisateur import (
    UtilisateurOut, LoginRequest, ChangePasswordRequest, CabinetSignupRequest
)
from app.services.security import (
    get_current_user, verify_password, get_password_hash, create_access_token,
    validate_password_strength,
)
from app.services.rate_limit import compte_rate_limiter, ip_rate_limiter, client_ip
from app.models.models import Utilisateur
from app.database import get_db
import uuid

router = APIRouter(prefix="/auth", tags=["Authentification"])

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Adresse email ou mot de passe incorrect."


def _find_user_by_email(db: Session, email: str) -> Utilisateur | None:
    """Recherche un compte par email, sans tenir compte de la casse.

    Les emails sont stockés tels qu'ils ont été saisis : comparer directement
    ferait échouer la connexion d'un compte enregistré en majuscules.
    """
    return (
        db.query(Utilisateur)
        .filter(func.lower(Utilisateur.email) == email.strip().lower())
        .first()
    )


def _build_user_payload(user: Utilisateur, nom_dossier: str | None = None) -> dict:
    return {
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
        "cabinet_ville": user.cabinet_ville,
        # Conservé pour la compatibilité du frontend : indique que l'utilisateur
        # doit définir son propre mot de passe.
        "is_default_password": bool(user.must_change_password),
    }


@router.get("/me", response_model=UtilisateurOut)
def read_current_user(current_user: Utilisateur = Depends(get_current_user)):
    """Récupère le profil de l'utilisateur actuellement connecté."""
    user_out = UtilisateurOut.model_validate(current_user)
    if current_user.dossier_id and current_user.dossier_client:
        user_out.nom_dossier = current_user.dossier_client.nom_dossier
    user_out.is_default_password = bool(current_user.must_change_password)
    return user_out


@router.post("/login")
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    """Connexion par email et mot de passe (cabinet, client ou salarié)."""
    email = (request.email or "").strip().lower()
    source = client_ip(http_request)
    # Double compteur : par compte ciblé (strict) et par adresse source (large).
    ip_rate_limiter.check(f"login:ip:{source}")
    compte_rate_limiter.check(f"login:email:{email}")

    user = _find_user_by_email(db, email)

    # Le message renvoyé est volontairement unique (pas d'énumération des
    # comptes), mais la cause exacte est journalisée côté serveur pour que
    # l'exploitant puisse diagnostiquer un 401 sans exposer d'information.
    if not user:
        logger.warning("Connexion refusée : aucun compte pour %s", email)
        motif = None
    elif not user.hashed_password:
        logger.warning(
            "Connexion refusée : le compte %s n'a aucun mot de passe défini "
            "(ancien compte créé avec la backdoor « Payohada@123 »). "
            "Définissez-en un : python set_password.py --email %s --password '<secret>'",
            email, user.email,
        )
        motif = None
    elif not verify_password(request.password, user.hashed_password):
        logger.warning("Connexion refusée : mot de passe incorrect pour %s", email)
        motif = None
    else:
        motif = user

    if motif is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé. Contactez votre administrateur.",
        )

    compte_rate_limiter.reset(f"login:email:{email}")

    access_token = create_access_token(
        data={"sub": user.supabase_uid, "email": user.email}
    )

    nom_dossier = None
    if user.dossier_id and user.dossier_client:
        nom_dossier = user.dossier_client.nom_dossier

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _build_user_payload(user, nom_dossier),
    }


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permet à l'utilisateur connecté de modifier son mot de passe."""
    if not current_user.hashed_password or not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ancien mot de passe est incorrect."
        )

    validate_password_strength(request.new_password, minimum=8)

    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit être différent de l'ancien."
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.must_change_password = False
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Mot de passe mis à jour avec succès.",
        "is_default_password": False
    }


@router.post("/signup-cabinet", status_code=status.HTTP_201_CREATED)
def signup_cabinet(
    request: CabinetSignupRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Inscription d'un nouveau cabinet de paie.

    Crée un compte `cabinet` et retourne un JWT pour une connexion immédiate.
    """
    ip_rate_limiter.check(f"signup:ip:{client_ip(http_request)}")

    email = (request.email or "").strip().lower()
    existing = _find_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse email est déjà associée à un compte."
        )

    validate_password_strength(request.password, minimum=8)

    new_user = Utilisateur(
        email=email,
        nom=request.nom,
        prenom=request.prenom,
        hashed_password=get_password_hash(request.password),
        supabase_uid=f"local-cabinet-{uuid.uuid4()}",
        is_active=True,
        is_admin=False,
        must_change_password=False,
        role="cabinet",
        cabinet_nom=request.cabinet_nom,
        cabinet_telephone=request.cabinet_telephone,
        cabinet_ville=request.cabinet_ville,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": new_user.supabase_uid, "email": new_user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _build_user_payload(new_user),
    }
