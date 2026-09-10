from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Dossier, NetEntreprise, Utilisateur
from app.schemas.dossier import DossierCreate, DossierUpdate, DossierOut, NetEntrepriseCreate, NetEntrepriseOut
from app.schemas.utilisateur import CompteClientCreate, UtilisateurOut
from app.services.security import get_current_user, get_password_hash
import uuid

router = APIRouter(prefix="/dossiers", tags=["Dossiers"])


def check_dossier_ownership(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable."
        )
    if user.is_admin:
        return dossier
    if user.role == "client":
        if user.dossier_id != dossier_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce dossier."
            )
        return dossier
    if user.role == "cabinet":
        if dossier.utilisateur_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce dossier."
            )
        return dossier
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès non autorisé."
    )


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
    """Met à jour un dossier."""
    dossier = db.query(Dossier).filter(
        Dossier.id == dossier_id,
        Dossier.utilisateur_id == current_user.id
    ).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable."
        )

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
    """Supprime un dossier."""
    dossier = db.query(Dossier).filter(
        Dossier.id == dossier_id,
        Dossier.utilisateur_id == current_user.id
    ).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable."
        )

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
    dossier = db.query(Dossier).filter(
        Dossier.id == dossier_id,
        Dossier.utilisateur_id == current_user.id
    ).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable."
        )

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
    """Permet au cabinet de créer un compte d'accès pour son entreprise cliente."""
    check_dossier_ownership(dossier_id, current_user, db)

    # Vérifier si l'email existe déjà
    existing = db.query(Utilisateur).filter(Utilisateur.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse email est déjà utilisée par un autre compte."
        )

    pwd = request.password or "Payohada@123"
    hashed = get_password_hash(pwd)
    uid = f"local-client-{uuid.uuid4()}"

    new_user = Utilisateur(
        email=request.email,
        nom=request.nom,
        prenom=request.prenom,
        hashed_password=hashed,
        supabase_uid=uid,
        is_active=True,
        is_admin=False,
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
    return out

