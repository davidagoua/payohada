from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Dossier, NetEntreprise, Utilisateur
from app.schemas.dossier import DossierCreate, DossierUpdate, DossierOut, NetEntrepriseCreate, NetEntrepriseOut
from app.services.security import get_current_user

router = APIRouter(prefix="/dossiers", tags=["Dossiers"])


@router.get("", response_model=List[DossierOut])
def get_dossiers(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les dossiers appartenant au gestionnaire connecté."""
    return db.query(Dossier).filter(Dossier.utilisateur_id == current_user.id).all()


@router.post("", response_model=DossierOut)
def create_dossier(
    dossier_in: DossierCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un nouveau dossier d'entreprise."""
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
    dossier = db.query(Dossier).filter(
        Dossier.id == dossier_id,
        Dossier.utilisateur_id == current_user.id
    ).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable."
        )
    return dossier


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
