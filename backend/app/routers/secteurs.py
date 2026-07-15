from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Secteur, PosteSalaire, Utilisateur
from app.schemas.secteur import SecteurOut, PosteSalaireOut
from app.services.security import get_current_user

router = APIRouter(tags=["Secteurs et Postes"])

@router.get("/secteurs", response_model=List[SecteurOut])
def get_secteurs(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les secteurs d'activité."""
    return db.query(Secteur).order_by(Secteur.nom).all()

@router.get("/secteurs/{secteur_id}/postes", response_model=List[PosteSalaireOut])
def get_secteur_postes(
    secteur_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les postes associés à un secteur d'activité."""
    return db.query(PosteSalaire).filter(PosteSalaire.secteur_id == secteur_id).order_by(
        PosteSalaire.categorie_professionnelle, 
        PosteSalaire.echelon_categorie
    ).all()

@router.get("/postes-salaires", response_model=List[PosteSalaireOut])
def get_all_postes(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les postes/grilles salariales."""
    return db.query(PosteSalaire).order_by(
        PosteSalaire.categorie_professionnelle, 
        PosteSalaire.echelon_categorie
    ).all()
