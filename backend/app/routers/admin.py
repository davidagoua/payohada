"""Administration du cabinet : membres, rôles et accès.

Deux niveaux d'administration coexistent :

* l'**administrateur plateforme** (`is_admin`) voit tous les comptes du
  personnel (cabinet et gestionnaire de paie) ;
* le **cabinet** (rôle `cabinet`) administre ses propres membres : le
  propriétaire (gestionnaire référent, `cabinet_owner_id = NULL`) et les
  comptes qui lui sont rattachés.

Un membre promu au rôle `cabinet` devient co-administrateur : il accède aux
sociétés du propriétaire et à cette page, sans pouvoir modifier le propriétaire.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import AccesDossier, Dossier, Utilisateur
from app.schemas.utilisateur import (
    CabinetUtilisateurCreate,
    CabinetUtilisateurOut,
    CabinetUtilisateurUpdate,
)
from app.services.email import send_email
from app.services.email_templates import email_acces_cree, lien_connexion
from app.services.permissions import (
    ROLE_CABINET,
    ROLE_GESTIONNAIRE_PAIE,
    STAFF_ROLES,
    est_admin_cabinet,
    membres_du_cabinet,
    racine_cabinet,
)
from app.services.security import (
    generate_password,
    get_current_user,
    get_password_hash,
    validate_password_strength,
)

router = APIRouter(prefix="/admin", tags=["Administration du cabinet"])

ROLES_ADMINISTRABLES = (ROLE_CABINET, ROLE_GESTIONNAIRE_PAIE)


def _require_admin_cabinet(user: Utilisateur) -> None:
    if not est_admin_cabinet(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administration réservée au propriétaire du cabinet.",
        )


def _cible_du_cabinet(db: Session, user: Utilisateur, user_id: int) -> Utilisateur:
    """Charge un membre en le limitant à la portée de l'administrateur."""
    cible = membres_du_cabinet(db, user).filter(Utilisateur.id == user_id).first()
    if not cible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable dans ce cabinet.",
        )
    return cible


def _nombre_societes(db: Session, cible: Utilisateur) -> int:
    """Nombre de sociétés accessibles au membre (possédées ou affectées)."""
    if cible.role == ROLE_CABINET:
        racine = cible.cabinet_owner_id or cible.id
        return (
            db.query(func.count(Dossier.id))
            .filter(Dossier.utilisateur_id == racine)
            .scalar()
            or 0
        )
    return (
        db.query(func.count(AccesDossier.id))
        .filter(AccesDossier.utilisateur_id == cible.id)
        .scalar()
        or 0
    )


def _presenter(db: Session, cible: Utilisateur) -> CabinetUtilisateurOut:
    out = CabinetUtilisateurOut.model_validate(cible)
    out.cabinet_owner_id = cible.cabinet_owner_id
    out.est_proprietaire = cible.role == ROLE_CABINET and cible.cabinet_owner_id is None
    out.nombre_societes = _nombre_societes(db, cible)
    return out


@router.get("/utilisateurs", response_model=list[CabinetUtilisateurOut])
def lister_utilisateurs(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Liste les membres du cabinet visibles par l'administrateur connecté."""
    _require_admin_cabinet(current_user)
    return [_presenter(db, membre) for membre in membres_du_cabinet(db, current_user).all()]


@router.post(
    "/utilisateurs",
    response_model=CabinetUtilisateurOut,
    status_code=status.HTTP_201_CREATED,
)
def creer_utilisateur(
    payload: CabinetUtilisateurCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Crée un membre du cabinet (gestionnaire ou co-administrateur).

    Réservé au personnel de cabinet. Le mot de passe peut être saisi ou généré :
    dans ce second cas il est envoyé par email et renvoyé une seule fois à
    l'administrateur (le SMTP peut être indisponible).
    """
    _require_admin_cabinet(current_user)
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La création de comptes est réservée au personnel du cabinet.",
        )

    email = (payload.email or "").strip().lower()
    existant = (
        db.query(Utilisateur).filter(func.lower(Utilisateur.email) == email).first()
    )
    if existant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse email est déjà associée à un compte.",
        )

    racine = racine_cabinet(current_user)
    if racine is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte sans cabinet de rattachement : création impossible.",
        )

    mot_de_passe = None
    must_change = True
    if payload.password:
        validate_password_strength(payload.password, minimum=8)
        pwd = payload.password
        must_change = False
    else:
        pwd = generate_password()
        mot_de_passe = pwd

    proprietaire = db.query(Utilisateur).filter(Utilisateur.id == racine).first()
    compte = Utilisateur(
        email=email,
        nom=payload.nom,
        prenom=payload.prenom,
        hashed_password=get_password_hash(pwd),
        supabase_uid=f"local-membre-{uuid.uuid4()}",
        is_active=True,
        is_admin=False,
        must_change_password=must_change,
        role=payload.role,
        cabinet_owner_id=racine,
        cabinet_nom=proprietaire.cabinet_nom if proprietaire else current_user.cabinet_nom,
        cabinet_telephone=(
            proprietaire.cabinet_telephone if proprietaire else current_user.cabinet_telephone
        ),
        cabinet_ville=(
            proprietaire.cabinet_ville if proprietaire else current_user.cabinet_ville
        ),
    )
    db.add(compte)
    db.commit()
    db.refresh(compte)

    sujet, contenu = email_acces_cree(
        compte.prenom,
        compte.nom,
        compte.email,
        pwd,
        None,
        lien_connexion(),
        changement_requis=must_change,
        espace_libelle="Espace Cabinet",
        espace_usage=(
            "administrer la paie des sociétés du cabinet"
            if compte.role == ROLE_CABINET
            else "gérer la paie des sociétés qui vous sont confiées"
        ),
    )
    envoye, motif = send_email(compte.email, sujet, contenu)

    out = _presenter(db, compte)
    out.mot_de_passe_initial = mot_de_passe
    out.email_envoye = envoye
    out.email_message = None if envoye else motif
    out.is_default_password = bool(compte.must_change_password)
    return out


@router.put("/utilisateurs/{user_id}", response_model=CabinetUtilisateurOut)
def modifier_utilisateur(
    user_id: int,
    payload: CabinetUtilisateurUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Change le rôle et/ou l'état d'activation d'un membre du cabinet.

    Garde-fous : on ne modifie pas son propre compte, un administrateur
    plateforme n'est modifiable que par un autre administrateur plateforme, et
    le propriétaire du cabinet ne peut être ni rétrogradé ni désactivé.
    """
    _require_admin_cabinet(current_user)
    cible = _cible_du_cabinet(db, current_user, user_id)

    if cible.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas modifier votre propre compte.",
        )
    if cible.is_admin and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un administrateur plateforme ne peut pas être modifié ici.",
        )

    racine = racine_cabinet(current_user)
    est_proprietaire = cible.role == ROLE_CABINET and cible.cabinet_owner_id is None
    if est_proprietaire and payload.role is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le propriétaire du cabinet ne peut pas changer de rôle.",
        )
    if est_proprietaire and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le propriétaire du cabinet ne peut pas être désactivé.",
        )

    if payload.role is not None:
        if payload.role not in ROLES_ADMINISTRABLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rôle non autorisé pour un membre du cabinet.",
            )
        cible.role = payload.role
        # Un membre reste rattaché au cabinet ; la promotion à « cabinet » lui
        # ouvre simplement toutes les sociétés du propriétaire.
        if not current_user.is_admin and racine is not None:
            cible.cabinet_owner_id = racine

    if payload.is_active is not None:
        cible.is_active = payload.is_active

    db.commit()
    db.refresh(cible)
    return _presenter(db, cible)
