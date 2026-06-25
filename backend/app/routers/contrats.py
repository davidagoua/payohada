from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Contrat, Salarie, Etablissement, Dossier, JoursHebdomadaires, Horaires, DepartSalarie, MoisAExclure, Utilisateur
from app.schemas.contrat import ContratCreate, ContratUpdate, ContratOut
from app.services.security import get_current_user
from app.routers.etablissements import check_etablissement_ownership
from app.routers.salaries import check_salarie_ownership

router = APIRouter(tags=["Contrats"])


def check_contrat_ownership(contrat_id: int, user_id: int, db: Session) -> Contrat:
    contrat = db.query(Contrat).join(Dossier).filter(
        Contrat.id == contrat_id,
        Dossier.utilisateur_id == user_id
    ).first()
    if not contrat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrat introuvable ou accès refusé."
        )
    return contrat


@router.get("/salaries/{salarie_id}/contrats", response_model=List[ContratOut])
def get_salarie_contrats(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les contrats d'un salarié."""
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(Contrat).filter(Contrat.salarie_id == salarie_id).all()


@router.post("/contrats", response_model=ContratOut)
def create_contrat(
    contrat_in: ContratCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un contrat de travail."""
    # Validation du salarié et de l'établissement
    salarie = check_salarie_ownership(contrat_in.salarie_id, current_user.id, db)
    etab = check_etablissement_ownership(contrat_in.etablissement_id, current_user.id, db)

    # Vérification de l'unicité du numéro de contrat pour le dossier
    existing = db.query(Contrat).filter(
        Contrat.dossier_id == etab.dossier_id,
        Contrat.numero_contrat == contrat_in.numero_contrat
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un contrat avec ce numéro existe déjà dans ce dossier."
        )

    # Extraction des sous-modèles
    contrat_dict = contrat_in.model_dump(exclude={"jours_hebdomadaires", "horaires", "depart_salarie", "mois_a_exclure"})

    # Création contrat avec données dénormalisées DSN
    contrat = Contrat(
        **contrat_dict,
        dossier_id=etab.dossier_id,
        code_etablissement=etab.code,
        matricule_salarie=salarie.matricule
    )
    db.add(contrat)
    db.commit()
    db.refresh(contrat)

    # Jours Hebdo
    jours_data = contrat_in.jours_hebdomadaires.model_dump() if contrat_in.jours_hebdomadaires else {}
    jours = JoursHebdomadaires(**jours_data, contrat_id=contrat.id)
    db.add(jours)

    # Horaires
    horaires_data = contrat_in.horaires.model_dump() if contrat_in.horaires else {}
    horaires = Horaires(**horaires_data, contrat_id=contrat.id)
    db.add(horaires)

    # Depart Salarie (sortie)
    if contrat_in.depart_salarie:
        depart = DepartSalarie(**contrat_in.depart_salarie.model_dump(), contrat_id=contrat.id)
        db.add(depart)

    # Mois à exclure
    mois_exclure_data = contrat_in.mois_a_exclure.model_dump() if contrat_in.mois_a_exclure else {}
    mois_exclure = MoisAExclure(**mois_exclure_data, contrat_id=contrat.id)
    db.add(mois_exclure)

    db.commit()
    db.refresh(contrat)
    return contrat


@router.get("/dossiers/{dossier_id}/contrats", response_model=List[ContratOut])
def get_dossier_contrats(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les contrats d'un dossier client."""
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id, Dossier.utilisateur_id == current_user.id).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable ou accès refusé."
        )
    return db.query(Contrat).filter(Contrat.dossier_id == dossier_id).all()


@router.get("/contrats/{contrat_id}", response_model=ContratOut)
def get_contrat(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère les détails d'un contrat."""
    return check_contrat_ownership(contrat_id, current_user.id, db)


@router.put("/contrats/{contrat_id}", response_model=ContratOut)
def update_contrat(
    contrat_id: int,
    contrat_in: ContratUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour un contrat."""
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)

    for field, value in contrat_in.model_dump(exclude_unset=True).items():
        setattr(contrat, field, value)

    db.commit()
    db.refresh(contrat)
    return contrat


@router.delete("/contrats/{contrat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contrat(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un contrat."""
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    db.delete(contrat)
    db.commit()
    return None
