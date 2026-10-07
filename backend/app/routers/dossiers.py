from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Dossier, Etablissement, NetEntreprise, Salarie, Utilisateur
from app.schemas.dossier import DossierCreate, DossierUpdate, DossierOut, NetEntrepriseCreate, NetEntrepriseOut
from app.schemas.utilisateur import CompteClientCreate, UtilisateurOut
from app.services.security import (
    get_current_user, get_password_hash, generate_password, validate_password_strength,
)
from app.services.permissions import get_dossier_or_403, require_staff
import uuid

router = APIRouter(prefix="/dossiers", tags=["Dossiers"])


def check_dossier_ownership(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    """Vérifie que l'utilisateur a accès au dossier (cabinet propriétaire,
    client rattaché ou administrateur)."""
    return get_dossier_or_403(dossier_id, user, db)


def _get_owned_dossier_for_write(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    """Écriture d'un dossier : réservé au cabinet propriétaire (ou admin)."""
    require_staff(user)
    dossier = get_dossier_or_403(dossier_id, user, db)
    if not user.is_admin and dossier.utilisateur_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le cabinet propriétaire peut modifier ce dossier.",
        )
    return dossier


@router.get("", response_model=List[DossierOut])
def get_dossiers(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les dossiers accessibles par l'utilisateur connecté."""
    if current_user.is_admin:
        return db.query(Dossier).all()
    if current_user.role == "client":
        if not current_user.dossier_id:
            return []
        return db.query(Dossier).filter(Dossier.id == current_user.dossier_id).all()
    if current_user.role == "salarie":
        if not current_user.salarie_id:
            return []
        salarie = db.query(Salarie).filter(Salarie.id == current_user.salarie_id).first()
        if not salarie:
            return []
        etab = db.query(Etablissement).filter(Etablissement.id == salarie.etablissement_id).first()
        if not etab:
            return []
        return db.query(Dossier).filter(Dossier.id == etab.dossier_id).all()
    return db.query(Dossier).filter(Dossier.utilisateur_id == current_user.id).all()


@router.post("", response_model=DossierOut)
def create_dossier(
    dossier_in: DossierCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un nouveau dossier d'entreprise (réservé au cabinet)."""
    if current_user.role == "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le cabinet peut créer des dossiers d'entreprises."
        )

    # Vérifier si le code existe déjà
    existing = db.query(Dossier).filter(Dossier.code == dossier_in.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un dossier avec ce code existe déjà."
        )

    # Création du dossier
    dossier_dict = dossier_in.model_dump(exclude={"net_entreprise"})
    dossier = Dossier(**dossier_dict, utilisateur_id=current_user.id)
    db.add(dossier)
    db.commit()
    db.refresh(dossier)

    # Création de NetEntreprise si fourni
    if dossier_in.net_entreprise:
        net_ent = NetEntreprise(
            **dossier_in.net_entreprise.model_dump(),
            dossier_id=dossier.id
        )
        db.add(net_ent)
        db.commit()
        db.refresh(dossier)

    return dossier


@router.get("/{dossier_id}", response_model=DossierOut)
def get_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère les détails d'un dossier."""
    return check_dossier_ownership(dossier_id, current_user, db)


@router.put("/{dossier_id}", response_model=DossierOut)
def update_dossier(
    dossier_id: int,
    dossier_in: DossierUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour un dossier (cabinet propriétaire uniquement)."""
    dossier = _get_owned_dossier_for_write(dossier_id, current_user, db)

    for field, value in dossier_in.model_dump(exclude_unset=True).items():
        setattr(dossier, field, value)

    db.commit()
    db.refresh(dossier)
    return dossier


@router.delete("/{dossier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un dossier (cabinet propriétaire uniquement)."""
    dossier = _get_owned_dossier_for_write(dossier_id, current_user, db)

    db.delete(dossier)
    db.commit()
    return None


@router.post("/{dossier_id}/net-entreprise", response_model=NetEntrepriseOut)
def create_or_update_net_entreprise(
    dossier_id: int,
    net_ent_in: NetEntrepriseCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Configure ou met à jour NetEntreprise pour un dossier."""
    _get_owned_dossier_for_write(dossier_id, current_user, db)

    net_ent = db.query(NetEntreprise).filter(NetEntreprise.dossier_id == dossier_id).first()
    if net_ent:
        for field, value in net_ent_in.model_dump().items():
            setattr(net_ent, field, value)
    else:
        net_ent = NetEntreprise(**net_ent_in.model_dump(), dossier_id=dossier_id)
        db.add(net_ent)

    db.commit()
    db.refresh(net_ent)
    return net_ent


# ─────────────────────────────────────────
#  GESTION DES COMPTES D'ACCÈS CLIENTS
# ─────────────────────────────────────────

@router.get("/{dossier_id}/comptes-clients", response_model=List[UtilisateurOut])
def get_comptes_clients(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les comptes d'accès pour un dossier d'entreprise."""
    check_dossier_ownership(dossier_id, current_user, db)
    return db.query(Utilisateur).filter(
        Utilisateur.dossier_id == dossier_id,
        Utilisateur.role == "client"
    ).all()


@router.post("/{dossier_id}/comptes-clients", response_model=UtilisateurOut)
def create_compte_client(
    dossier_id: int,
    request: CompteClientCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Permet au cabinet de créer un compte d'accès pour son entreprise cliente.

    Si aucun mot de passe n'est fourni, un mot de passe aléatoire est généré et
    renvoyé une seule fois (`mot_de_passe_initial`) ; l'utilisateur devra le
    remplacer à sa première connexion.
    """
    check_dossier_ownership(dossier_id, current_user, db)
    if not current_user.is_admin and current_user.role != "cabinet":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le cabinet peut créer un compte client.",
        )

    email = (request.email or "").strip().lower()
    existing = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse email est déjà utilisée par un autre compte."
        )

    password_genere = None
    if request.password:
        validate_password_strength(request.password, minimum=8)
        pwd = request.password
        must_change = False
    else:
        pwd = generate_password()
        password_genere = pwd
        must_change = True

    new_user = Utilisateur(
        email=email,
        nom=request.nom,
        prenom=request.prenom,
        hashed_password=get_password_hash(pwd),
        supabase_uid=f"local-client-{uuid.uuid4()}",
        is_active=True,
        is_admin=False,
        must_change_password=must_change,
        role="client",
        dossier_id=dossier_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    out = UtilisateurOut.model_validate(new_user)
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
    if dossier:
        out.nom_dossier = dossier.nom_dossier
    out.is_default_password = bool(new_user.must_change_password)
    out.mot_de_passe_initial = password_genere
    return out

