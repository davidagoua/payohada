from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Contrat, Absence, HeureSupplementaire, Prime, Option, VariableRepriseDossier, Utilisateur
from app.schemas.variables import (
    AbsenceCreate, AbsenceOut,
    HeureSupplementaireCreate, HeureSupplementaireOut,
    PrimeCreate, PrimeOut,
    OptionCreate, OptionOut,
    VariableRepriseDossierCreate, VariableRepriseDossierOut
)
from app.services.security import get_current_user
from app.routers.contrats import check_contrat_ownership

router = APIRouter(prefix="/contrats", tags=["Variables de Paie"])


# ─────────────────────────────────────────
#  ABSENCES
# ─────────────────────────────────────────

@router.get("/{contrat_id}/absences", response_model=List[AbsenceOut])
def get_absences(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les absences pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    return db.query(Absence).filter(Absence.contrat_id == contrat_id).all()


@router.post("/{contrat_id}/absences", response_model=AbsenceOut)
def create_absence(
    contrat_id: int,
    absence_in: AbsenceCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Saisit une absence pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)

    absence = Absence(**absence_in.model_dump(), contrat_id=contrat_id)
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return absence


# ─────────────────────────────────────────
#  HEURES SUPPLÉMENTAIRES
# ─────────────────────────────────────────

@router.get("/{contrat_id}/heures-supplementaires", response_model=List[HeureSupplementaireOut])
def get_heures_supplementaires(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les heures supplémentaires saisies pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    return db.query(HeureSupplementaire).filter(HeureSupplementaire.contrat_id == contrat_id).all()


@router.post("/{contrat_id}/heures-supplementaires", response_model=HeureSupplementaireOut)
def create_heure_supplementaire(
    contrat_id: int,
    hs_in: HeureSupplementaireCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Saisit des heures supplémentaires pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)

    hs = HeureSupplementaire(**hs_in.model_dump(), contrat_id=contrat_id)
    db.add(hs)
    db.commit()
    db.refresh(hs)
    return hs


# ─────────────────────────────────────────
#  PRIMES
# ─────────────────────────────────────────

@router.get("/{contrat_id}/primes", response_model=List[PrimeOut])
def get_primes(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les primes pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    return db.query(Prime).filter(Prime.contrat_id == contrat_id).all()


@router.post("/{contrat_id}/primes", response_model=PrimeOut)
def create_prime(
    contrat_id: int,
    prime_in: PrimeCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Saisit une prime pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)

    prime = Prime(**prime_in.model_dump(), contrat_id=contrat_id)
    db.add(prime)
    db.commit()
    db.refresh(prime)
    return prime


# ─────────────────────────────────────────
#  OPTIONS BULLETIN
# ─────────────────────────────────────────

@router.get("/{contrat_id}/options", response_model=List[OptionOut])
def get_options(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les options du bulletin pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    return db.query(Option).filter(Option.contrat_id == contrat_id).all()


@router.post("/{contrat_id}/options", response_model=OptionOut)
def create_option(
    contrat_id: int,
    option_in: OptionCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Saisit une option de bulletin pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)

    option = Option(**option_in.model_dump(), contrat_id=contrat_id)
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


# ─────────────────────────────────────────
#  REPRISES DOSSIER
# ─────────────────────────────────────────

@router.get("/{contrat_id}/reprises", response_model=List[VariableRepriseDossierOut])
def get_reprises(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les cumuls de reprise pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    return db.query(VariableRepriseDossier).filter(VariableRepriseDossier.contrat_id == contrat_id).all()


@router.post("/{contrat_id}/reprises", response_model=VariableRepriseDossierOut)
def create_reprise(
    contrat_id: int,
    reprise_in: VariableRepriseDossierCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Saisit une variable de reprise historique pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)

    reprise = VariableRepriseDossier(**reprise_in.model_dump(), contrat_id=contrat_id)
    db.add(reprise)
    db.commit()
    db.refresh(reprise)
    return reprise


# ─────────────────────────────────────────
#  SUPPRESSION DES VARIABLES
# ─────────────────────────────────────────

@router.delete("/absences/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_absence(
    absence_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime une absence."""
    absence = db.query(Absence).filter(Absence.id == absence_id).first()
    if not absence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence introuvable.")
    check_contrat_ownership(absence.contrat_id, current_user.id, db)
    db.delete(absence)
    db.commit()
    return None


@router.delete("/heures-supplementaires/{hs_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_heure_supplementaire(
    hs_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime des heures supplémentaires."""
    hs = db.query(HeureSupplementaire).filter(HeureSupplementaire.id == hs_id).first()
    if not hs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heure supplémentaire introuvable.")
    check_contrat_ownership(hs.contrat_id, current_user.id, db)
    db.delete(hs)
    db.commit()
    return None


@router.delete("/primes/{prime_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prime(
    prime_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime une prime."""
    prime = db.query(Prime).filter(Prime.id == prime_id).first()
    if not prime:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prime introuvable.")
    check_contrat_ownership(prime.contrat_id, current_user.id, db)
    db.delete(prime)
    db.commit()
    return None


@router.delete("/options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_option(
    option_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime une option du bulletin."""
    option = db.query(Option).filter(Option.id == option_id).first()
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option introuvable.")
    check_contrat_ownership(option.contrat_id, current_user.id, db)
    db.delete(option)
    db.commit()
    return None

