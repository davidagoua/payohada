"""Administration de la plateforme : cabinets et leurs administrateurs.

Espace réservé aux comptes `is_admin`. Un cabinet est représenté par son
propriétaire (`role = cabinet`, `cabinet_owner_id IS NULL`) ; les autres
administrateurs pointent vers lui. Suspendre un cabinet bloque la connexion et
les appels API de tous ses membres, sans supprimer leurs données.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Dossier, Utilisateur
from app.schemas.platform import (
    CabinetAdminCreate,
    CabinetAdminCreationOut,
    CabinetAdminOut,
    CabinetCreate,
    CabinetCreationOut,
    CabinetOut,
    CabinetStatutUpdate,
)
from app.services.email import send_email
from app.services.email_templates import email_acces_cree, lien_connexion
from app.services.security import (
    generate_password,
    get_current_user,
    get_password_hash,
    validate_password_strength,
)
from app.services.permissions import require_admin

router = APIRouter(prefix="/platform", tags=["Administration plateforme"])

ROLE_CABINET = "cabinet"


# ─────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────

def _proprietaire_ou_404(db: Session, cabinet_id: int) -> Utilisateur:
    proprietaire = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.id == cabinet_id,
            Utilisateur.role == ROLE_CABINET,
            Utilisateur.cabinet_owner_id.is_(None),
            Utilisateur.is_admin.is_(False),
        )
        .first()
    )
    if not proprietaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cabinet introuvable.",
        )
    return proprietaire


def _email_deja_pris(db: Session, email: str) -> bool:
    return (
        db.query(Utilisateur)
        .filter(func.lower(Utilisateur.email) == email.lower())
        .first()
        is not None
    )


def _administrateurs(db: Session, proprietaire: Utilisateur) -> list[Utilisateur]:
    membres = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.cabinet_owner_id == proprietaire.id,
            Utilisateur.role == ROLE_CABINET,
        )
        .order_by(Utilisateur.created_at, Utilisateur.id)
        .all()
    )
    return [proprietaire, *membres]


def _presenter_admin(utilisateur: Utilisateur, proprietaire_id: int) -> CabinetAdminOut:
    return CabinetAdminOut(
        id=utilisateur.id,
        email=utilisateur.email,
        prenom=utilisateur.prenom or "",
        nom=utilisateur.nom or "",
        role=utilisateur.role,
        is_active=utilisateur.is_active,
        must_change_password=bool(utilisateur.must_change_password),
        est_proprietaire=utilisateur.id == proprietaire_id,
    )


def _presenter_cabinet(db: Session, proprietaire: Utilisateur) -> CabinetOut:
    membres = (
        db.query(func.count(Utilisateur.id))
        .filter(
            Utilisateur.cabinet_owner_id == proprietaire.id,
        )
        .scalar()
        or 0
    )
    dossiers = (
        db.query(func.count(Dossier.id))
        .filter(Dossier.utilisateur_id == proprietaire.id)
        .scalar()
        or 0
    )
    return CabinetOut(
        id=proprietaire.id,
        cabinet_nom=proprietaire.cabinet_nom,
        email=proprietaire.email,
        prenom=proprietaire.prenom or "",
        nom=proprietaire.nom or "",
        telephone=proprietaire.cabinet_telephone,
        ville=proprietaire.cabinet_ville,
        suspendu=bool(proprietaire.cabinet_suspendu),
        is_active=bool(proprietaire.is_active),
        membres=membres + 1,
        dossiers=dossiers,
        administrateurs=[
            _presenter_admin(admin, proprietaire.id)
            for admin in _administrateurs(db, proprietaire)
        ],
        created_at=proprietaire.created_at,
    )


def _creer_admin(
    db: Session,
    donnees: CabinetAdminCreate,
    *,
    cabinet_owner_id: int | None,
    cabinet_nom: str | None,
    cabinet_telephone: str | None,
    cabinet_ville: str | None,
) -> tuple[Utilisateur, str | None, bool, str | None]:
    email = donnees.email.strip().lower()
    if _email_deja_pris(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"L'adresse {email} est déjà utilisée par un compte.",
        )

    mot_de_passe_initial = None
    must_change = True
    if donnees.password:
        validate_password_strength(donnees.password, minimum=8)
        pwd = donnees.password
        must_change = False
    else:
        pwd = generate_password()
        mot_de_passe_initial = pwd

    compte = Utilisateur(
        email=email,
        nom=donnees.nom.strip(),
        prenom=donnees.prenom.strip(),
        hashed_password=get_password_hash(pwd),
        supabase_uid=f"local-cabinet-{uuid.uuid4()}",
        is_active=True,
        is_admin=False,
        must_change_password=must_change,
        role=ROLE_CABINET,
        cabinet_owner_id=cabinet_owner_id,
        cabinet_nom=cabinet_nom,
        cabinet_telephone=cabinet_telephone,
        cabinet_ville=cabinet_ville,
        cabinet_suspendu=False,
    )
    db.add(compte)
    db.flush()

    sujet, contenu = email_acces_cree(
        compte.prenom,
        compte.nom,
        compte.email,
        pwd,
        None,
        lien_connexion(),
        changement_requis=must_change,
        espace_libelle="Espace Cabinet",
        espace_usage="administrer la paie des sociétés du cabinet",
    )
    envoye, motif = send_email(compte.email, sujet, contenu)
    return compte, mot_de_passe_initial, envoye, motif


# ─────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────

@router.get("/cabinets", response_model=list[CabinetOut])
def lister_cabinets(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Liste tous les cabinets de la plateforme, avec leurs administrateurs."""
    require_admin(current_user)
    proprietaires = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.role == ROLE_CABINET,
            Utilisateur.cabinet_owner_id.is_(None),
            Utilisateur.is_admin.is_(False),
        )
        .order_by(func.lower(Utilisateur.cabinet_nom), Utilisateur.id)
        .all()
    )
    return [_presenter_cabinet(db, proprietaire) for proprietaire in proprietaires]


@router.get("/cabinets/{cabinet_id}", response_model=CabinetOut)
def detail_cabinet(
    cabinet_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    require_admin(current_user)
    return _presenter_cabinet(db, _proprietaire_ou_404(db, cabinet_id))


@router.post("/cabinets", response_model=CabinetCreationOut, status_code=status.HTTP_201_CREATED)
def creer_cabinet(
    payload: CabinetCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Crée un cabinet et son administrateur propriétaire.

    Le compte est actif immédiatement ; un mot de passe peut être fourni ou
    généré et envoyé par email (affiché une seule fois à l'administrateur).
    """
    require_admin(current_user)
    nom_cabinet = payload.cabinet_nom.strip()
    if not nom_cabinet:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le nom du cabinet est obligatoire.")
    email = payload.administrateur.email.strip().lower()
    if _email_deja_pris(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cette adresse email est déjà utilisée.")

    proprietaire, mot_de_passe, envoye, motif = _creer_admin(
        db,
        payload.administrateur,
        cabinet_owner_id=None,
        cabinet_nom=nom_cabinet,
        cabinet_telephone=payload.cabinet_telephone,
        cabinet_ville=payload.cabinet_ville,
    )
    # Le compte vient d'être créé : il devient sa propre racine.
    proprietaire.cabinet_owner_id = None
    db.commit()
    db.refresh(proprietaire)

    cabinet = _presenter_cabinet(db, proprietaire)
    return CabinetCreationOut(
        **cabinet.model_dump(),
        mot_de_passe_initial=mot_de_passe,
        email_envoye=envoye,
        email_message=None if envoye else motif,
    )


@router.post(
    "/cabinets/{cabinet_id}/administrateurs",
    response_model=CabinetAdminCreationOut,
    status_code=status.HTTP_201_CREATED,
)
def ajouter_administrateur(
    cabinet_id: int,
    payload: CabinetAdminCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Ajoute un administrateur (co-administrateur) à un cabinet existant."""
    require_admin(current_user)
    proprietaire = _proprietaire_ou_404(db, cabinet_id)
    compte, mot_de_passe, envoye, motif = _creer_admin(
        db,
        payload,
        cabinet_owner_id=proprietaire.id,
        cabinet_nom=proprietaire.cabinet_nom,
        cabinet_telephone=proprietaire.cabinet_telephone,
        cabinet_ville=proprietaire.cabinet_ville,
    )
    db.commit()
    db.refresh(compte)

    admin = _presenter_admin(compte, proprietaire.id)
    return CabinetAdminCreationOut(
        **admin.model_dump(),
        mot_de_passe_initial=mot_de_passe,
        email_envoye=envoye,
        email_message=None if envoye else motif,
    )


@router.put("/cabinets/{cabinet_id}/statut", response_model=CabinetOut)
def changer_statut_cabinet(
    cabinet_id: int,
    payload: CabinetStatutUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Suspend ou réactive un cabinet.

    La suspension bloque la connexion et les appels API de tous les membres ;
    elle ne modifie ni les comptes ni les données.
    """
    require_admin(current_user)
    proprietaire = _proprietaire_ou_404(db, cabinet_id)
    proprietaire.cabinet_suspendu = payload.suspendu
    # Aligne aussi les membres rattachés : la vérification d'accès peut ainsi
    # s'appuyer sur le drapeau du membre, y compris pour les comptes historiques.
    db.query(Utilisateur).filter(
        Utilisateur.cabinet_owner_id == proprietaire.id,
    ).update({Utilisateur.cabinet_suspendu: payload.suspendu}, synchronize_session=False)
    db.commit()
    db.refresh(proprietaire)
    return _presenter_cabinet(db, proprietaire)
