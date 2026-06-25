from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Salarie, Etablissement, Dossier, Utilisateur
from app.schemas.salarie import SalarieCreate, SalarieUpdate, SalarieOut
from app.services.security import get_current_user
from app.routers.etablissements import check_etablissement_ownership

router = APIRouter(tags=["Salariés"])


def check_salarie_ownership(salarie_id: int, user_id: int, db: Session) -> Salarie:
    salarie = db.query(Salarie).join(Etablissement).join(Dossier).filter(
        Salarie.id == salarie_id,
        Dossier.utilisateur_id == user_id
    ).first()
    if not salarie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salarié introuvable ou accès refusé."
        )
    return salarie


@router.get("/etablissements/{etablissement_id}/salaries", response_model=List[SalarieOut])
def get_salaries(
    etablissement_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les salariés d'un établissement."""
    check_etablissement_ownership(etablissement_id, current_user.id, db)
    return db.query(Salarie).filter(Salarie.etablissement_id == etablissement_id).all()


@router.post("/etablissements/{etablissement_id}/salaries", response_model=SalarieOut)
def create_salarie(
    etablissement_id: int,
    salarie_in: SalarieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un salarié pour un établissement."""
    check_etablissement_ownership(etablissement_id, current_user.id, db)

    # Génération dynamique et unique du matricule
    existing_count = db.query(Salarie).filter(Salarie.etablissement_id == etablissement_id).count()
    generated_matricule = f"EMP-{etablissement_id}-{(existing_count + 1):04d}"
    
    while db.query(Salarie).filter(
        Salarie.etablissement_id == etablissement_id,
        Salarie.matricule == generated_matricule
    ).first():
        existing_count += 1
        generated_matricule = f"EMP-{etablissement_id}-{(existing_count + 1):04d}"

    salarie_data = salarie_in.model_dump()
    salarie_data["matricule"] = generated_matricule

    salarie = Salarie(**salarie_data, etablissement_id=etablissement_id)
    db.add(salarie)
    db.commit()
    db.refresh(salarie)
    return salarie


@router.get("/salaries/{salarie_id}", response_model=SalarieOut)
def get_salarie(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère un salarié par son ID."""
    return check_salarie_ownership(salarie_id, current_user.id, db)


@router.put("/salaries/{salarie_id}", response_model=SalarieOut)
def update_salarie(
    salarie_id: int,
    salarie_in: SalarieUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour les informations d'un salarié."""
    salarie = check_salarie_ownership(salarie_id, current_user.id, db)

    for field, value in salarie_in.model_dump(exclude_unset=True).items():
        setattr(salarie, field, value)

    db.commit()
    db.refresh(salarie)
    return salarie


@router.delete("/salaries/{salarie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salarie(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un salarié de la base."""
    salarie = check_salarie_ownership(salarie_id, current_user.id, db)
    db.delete(salarie)
    db.commit()
    return None
