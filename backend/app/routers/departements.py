from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Dossier, Departement, Utilisateur
from app.schemas.departement import DepartementCreate, DepartementUpdate, DepartementOut
from app.services.security import get_current_user

router = APIRouter(tags=["Départements"])


def check_dossier_ownership(dossier_id: int, user_id: int, db: Session) -> Dossier:
    dossier = db.query(Dossier).filter(
        Dossier.id == dossier_id,
        Dossier.utilisateur_id == user_id
    ).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable ou accès refusé."
        )
    return dossier


@router.get("/dossiers/{dossier_id}/departements", response_model=List[DepartementOut])
def get_departements(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les départements d'un dossier client."""
    check_dossier_ownership(dossier_id, current_user.id, db)
    return db.query(Departement).filter(Departement.dossier_id == dossier_id).all()


@router.post("/dossiers/{dossier_id}/departements", response_model=DepartementOut)
def create_departement(
    dossier_id: int,
    departement_in: DepartementCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un nouveau département pour un dossier client."""
    check_dossier_ownership(dossier_id, current_user.id, db)
    db_item = Departement(**departement_in.model_dump(), dossier_id=dossier_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/departements/{id}", response_model=DepartementOut)
def update_departement(
    id: int,
    departement_in: DepartementUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour un département."""
    db_item = db.query(Departement).filter(Departement.id == id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département introuvable."
        )
    check_dossier_ownership(db_item.dossier_id, current_user.id, db)
    for field, value in departement_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/departements/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_departement(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un département."""
    db_item = db.query(Departement).filter(Departement.id == id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Département introuvable."
        )
    check_dossier_ownership(db_item.dossier_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None
