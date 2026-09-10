from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.models import (
    Contrat, Absence, HeureSupplementaire, Prime, Option, VariableRepriseDossier,
    Utilisateur, Dossier, Etablissement, Salarie, BulletinPaie, PeriodePaie
)
from app.schemas.variables import (
    AbsenceCreate, AbsenceOut,
    HeureSupplementaireCreate, HeureSupplementaireOut,
    PrimeCreate, PrimeOut,
    OptionCreate, OptionOut,
    VariableRepriseDossierCreate, VariableRepriseDossierOut,
    PeriodePaieOut, PeriodePaieTransmettre, SalarieVariableRowOut
)
from app.services.security import get_current_user
from app.routers.contrats import check_contrat_ownership
from app.routers.dossiers import check_dossier_ownership

router = APIRouter(prefix="/contrats", tags=["Variables de Paie"])
dossier_variables_router = APIRouter(prefix="/dossiers", tags=["Variables Collectives & Périodes"])


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


@router.put("/primes/{prime_id}", response_model=PrimeOut)
def update_prime(
    prime_id: int,
    prime_in: PrimeCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour une prime."""
    prime = db.query(Prime).filter(Prime.id == prime_id).first()
    if not prime:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prime introuvable.")
    check_contrat_ownership(prime.contrat_id, current_user.id, db)

    for field, value in prime_in.model_dump().items():
        setattr(prime, field, value)

    db.commit()
    db.refresh(prime)
    return prime


@router.put("/options/{option_id}", response_model=OptionOut)
def update_option(
    option_id: int,
    option_in: OptionCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour une option du bulletin."""
    option = db.query(Option).filter(Option.id == option_id).first()
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option introuvable.")
    check_contrat_ownership(option.contrat_id, current_user.id, db)

    for field, value in option_in.model_dump().items():
        setattr(option, field, value)

    db.commit()
    db.refresh(option)
    return option


# ──────────────────────────────────────────────────────────────
#  VARIABLES COLLECTIVES DU DOSSIER & TRANSMISSION AU CABINET
# ──────────────────────────────────────────────────────────────

@dossier_variables_router.get("/{dossier_id}/periodes/{annee}/{mois}/statut", response_model=PeriodePaieOut)
def get_periode_statut(
    dossier_id: int,
    annee: str,
    mois: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Consulte le statut d'avancement de la paie pour un dossier et un mois donné."""
    check_dossier_ownership(dossier_id, current_user, db)

    periode = db.query(PeriodePaie).filter(
        PeriodePaie.dossier_id == dossier_id,
        PeriodePaie.annee == str(annee),
        PeriodePaie.mois == mois
    ).first()

    if not periode:
        periode = PeriodePaie(
            dossier_id=dossier_id,
            annee=str(annee),
            mois=mois,
            statut="saisie_en_cours"
        )
        db.add(periode)
        db.commit()
        db.refresh(periode)

    return periode


@dossier_variables_router.post("/{dossier_id}/periodes/{annee}/{mois}/transmettre", response_model=PeriodePaieOut)
def transmettre_periode(
    dossier_id: int,
    annee: str,
    mois: int,
    payload: Optional[PeriodePaieTransmettre] = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """L'entreprise cliente transmet officiellement ses variables saisies au cabinet pour calcul."""
    check_dossier_ownership(dossier_id, current_user, db)

    periode = db.query(PeriodePaie).filter(
        PeriodePaie.dossier_id == dossier_id,
        PeriodePaie.annee == str(annee),
        PeriodePaie.mois == mois
    ).first()

    if not periode:
        periode = PeriodePaie(
            dossier_id=dossier_id,
            annee=str(annee),
            mois=mois
        )
        db.add(periode)

    periode.statut = "transmis"
    periode.date_transmission = datetime.now(timezone.utc)
    periode.transmis_par_id = current_user.id
    if payload and payload.notes:
        periode.notes_client = payload.notes

    db.commit()
    db.refresh(periode)
    return periode


@dossier_variables_router.put("/{dossier_id}/periodes/{annee}/{mois}/statut", response_model=PeriodePaieOut)
def update_periode_statut(
    dossier_id: int,
    annee: str,
    mois: int,
    nouveau_statut: str = Query(..., description="saisie_en_cours, transmis, calcule, valide"),
    notes_cabinet: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Permet au cabinet de mettre à jour le statut de la période (ex: calculée, clôturée)."""
    check_dossier_ownership(dossier_id, current_user, db)

    periode = db.query(PeriodePaie).filter(
        PeriodePaie.dossier_id == dossier_id,
        PeriodePaie.annee == str(annee),
        PeriodePaie.mois == mois
    ).first()

    if not periode:
        periode = PeriodePaie(
            dossier_id=dossier_id,
            annee=str(annee),
            mois=mois
        )
        db.add(periode)

    periode.statut = nouveau_statut
    if notes_cabinet is not None:
        periode.notes_cabinet = notes_cabinet

    db.commit()
    db.refresh(periode)
    return periode


@dossier_variables_router.get("/{dossier_id}/variables-mensuelles", response_model=List[SalarieVariableRowOut])
def get_variables_mensuelles(
    dossier_id: int,
    mois: int = Query(..., ge=1, le=12),
    annee: str = Query(..., min_length=4, max_length=4),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Retourne la grille consolidée de tous les salariés d'un dossier pour un mois donné,
    avec leurs heures supplémentaires, absences, primes et statut du bulletin.
    Idéal pour la saisie collective par le client.
    """
    check_dossier_ownership(dossier_id, current_user, db)

    # Récupérer tous les contrats actifs pour ce dossier
    contrats = (
        db.query(Contrat)
        .join(Salarie, Contrat.salarie_id == Salarie.id)
        .join(Etablissement, Contrat.etablissement_id == Etablissement.id)
        .filter(Etablissement.dossier_id == dossier_id)
        .all()
    )

    results = []
    for c in contrats:
        sal = c.salarie
        if not sal:
            continue

        # Heures supplémentaires
        hs_list = db.query(HeureSupplementaire).filter(
            HeureSupplementaire.contrat_id == c.id,
            HeureSupplementaire.annee == str(annee),
            HeureSupplementaire.mois == mois
        ).all()
        hs_data = [{"id": h.id, "code": h.code, "nombre": h.nombre} for h in hs_list]

        # Absences
        abs_list = db.query(Absence).filter(
            Absence.contrat_id == c.id,
            Absence.annee == str(annee),
            Absence.mois == mois
        ).all()
        abs_data = [
            {
                "id": a.id,
                "code": a.code,
                "date_debut": a.date_debut.isoformat() if a.date_debut else None,
                "date_fin": a.date_fin.isoformat() if a.date_fin else None,
                "nbr_heure_by_user": a.nbr_heure_by_user,
                "nbr_jour_by_user": a.nbr_jour_by_user
            }
            for a in abs_list
        ]

        # Primes
        primes_list = db.query(Prime).filter(
            Prime.contrat_id == c.id,
            Prime.annee == str(annee),
            Prime.mois == mois
        ).all()
        primes_data = [
            {"id": p.id, "code": p.code, "montant": p.montant, "libelle": p.libelle}
            for p in primes_list
        ]

        # Options
        options_list = db.query(Option).filter(
            Option.contrat_id == c.id,
            Option.annee == str(annee),
            Option.mois == mois
        ).all()
        options_data = [
            {"id": o.id, "code": o.code, "valeur": o.valeur, "valeur_numerique": o.valeur_numerique, "libelle": o.libelle}
            for o in options_list
        ]

        # Vérifier si un bulletin est calculé pour ce contrat
        bulletin = db.query(BulletinPaie).filter(
            BulletinPaie.contrat_id == c.id,
            BulletinPaie.annee == int(annee),
            BulletinPaie.mois == mois
        ).first()

        row = SalarieVariableRowOut(
            salarie_id=sal.id,
            matricule=sal.matricule or f"EMP-{sal.id}",
            nom=sal.nom,
            prenom=sal.prenom,
            contrat_id=c.id,
            intitule_poste=c.emploi or getattr(sal, 'profession', '') or "Poste non défini",
            salaire_base=float(c.salaire_mensuel or 0.0),
            heures_supplementaires=hs_data,
            absences=abs_data,
            primes=primes_data,
            options=options_data,
            has_bulletin=bulletin is not None,
            bulletin_id=bulletin.id if bulletin else None,
            bulletin_statut=bulletin.statut if bulletin else None,
            net_a_payer=float(bulletin.net_a_payer) if (bulletin and bulletin.net_a_payer) else None
        )
        results.append(row)

    return results

