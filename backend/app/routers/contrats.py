from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import (
    Contrat, Salarie, Etablissement, Dossier, JoursHebdomadaires,
    Horaires, DepartSalarie, MoisAExclure, Utilisateur, SoldeToutCompte, BulletinPaie
)
from app.schemas.contrat import (
    ContratCreate, ContratUpdate, ContratOut,
    DepartSalarieCreate, DepartSalarieOut
)
from app.schemas.bulletin import SoldeToutCompteOut, SoldeToutCompteBase
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


# Helper to calculate conges solde at exit date
def calculate_estimated_conges_solde(db: Session, contrat: Contrat, year: int, month: int) -> float:
    from datetime import date, datetime
    import calendar
    from app.models.models import SalarieAbsence
    
    start_date = None
    if contrat.date_debut_contrat:
        try:
            start_date = datetime.strptime(contrat.date_debut_contrat[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    if not start_date:
        start_date = date(year, 1, 1)
        
    months_seniority = (year - start_date.year) * 12 + (month - start_date.month) + 1
    months_seniority = max(1, months_seniority)
    conges_acquis_cumules = round(months_seniority * 2.5, 2)
    
    absences_cp = db.query(SalarieAbsence).filter(
        SalarieAbsence.salarie_id == contrat.salarie_id,
        SalarieAbsence.type_absence == "Congés payés"
    ).all()
    
    month_start = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    month_end = date(year, month, last_day)
    
    conges_pris_cumules = 0.0
    for a in absences_cp:
        a_start = a.date_debut_absence
        a_end = a.date_fin_absence
        if isinstance(a_start, datetime):
            a_start = a_start.date()
        if isinstance(a_end, datetime):
            a_end = a_end.date()
            
        if a_start <= month_end:
            actual_end = min(a_end, month_end)
            conges_pris_cumules += (actual_end - a_start).days + 1
            
    return round(conges_acquis_cumules - conges_pris_cumules, 2)


@router.get("/contrats/{contrat_id}/depart", response_model=Optional[DepartSalarieOut])
def get_depart_salarie(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère les détails du départ du salarié s'il a été déclaré."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    return db.query(DepartSalarie).filter(DepartSalarie.contrat_id == contrat_id).first()


@router.post("/contrats/{contrat_id}/depart", response_model=DepartSalarieOut)
def create_depart_salarie(
    contrat_id: int,
    depart_in: DepartSalarieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Enregistre le départ du salarié, met à jour le statut du contrat et initialise le STC."""
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    
    # Check if departure already declared
    existing_depart = db.query(DepartSalarie).filter(DepartSalarie.contrat_id == contrat_id).first()
    if existing_depart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le départ de ce salarié a déjà été déclaré pour ce contrat."
        )

    # 1. Mettre à jour le statut du contrat
    contrat.statut = "termine"
    if depart_in.date_sortie:
        contrat.date_fin_previsionnelle_contrat = depart_in.date_sortie

    # 2. Créer l'enregistrement DepartSalarie
    depart = DepartSalarie(**depart_in.model_dump(), contrat_id=contrat_id)
    db.add(depart)
    db.commit()
    db.refresh(depart)

    # 3. Calculer les indemnités compensatrices de congés payés par défaut
    # Trouver l'année/mois de sortie
    from datetime import datetime
    try:
        exit_date = datetime.strptime(depart_in.date_sortie[:10], "%Y-%m-%d")
        y, m = exit_date.year, exit_date.month
    except Exception:
        y, m = datetime.now().year, datetime.now().month

    conges_solde = calculate_estimated_conges_solde(db, contrat, y, m)
    daily_rate = (contrat.salaire_mensuel + (contrat.sursalaire or 0.0)) / 30.0
    icp_val = max(0.0, conges_solde) * daily_rate

    # 4. Créer l'enregistrement SoldeToutCompte
    stc = db.query(SoldeToutCompte).filter(SoldeToutCompte.contrat_id == contrat_id).first()
    if not stc:
        stc = SoldeToutCompte(
            contrat_id=contrat_id,
            indemnite_conges_payes=round(icp_val, 2),
            indemnite_licenciement=0.0,
            indemnite_preavis=0.0,
            indemnite_autre=0.0,
            total=round(icp_val, 2),
            statut="genere"
        )
        db.add(stc)
        db.commit()

    return depart


@router.delete("/contrats/{contrat_id}/depart", status_code=status.HTTP_204_NO_CONTENT)
def delete_depart_salarie(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Annule le départ du salarié en réactivant le contrat et supprimant le STC."""
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    
    depart = db.query(DepartSalarie).filter(DepartSalarie.contrat_id == contrat_id).first()
    if not depart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun départ n'est déclaré pour ce contrat."
        )

    # 1. Reset contrat statut
    contrat.statut = "actif"
    contrat.date_fin_previsionnelle_contrat = None

    # 2. Supprimer STC et DepartSalarie
    stc = db.query(SoldeToutCompte).filter(SoldeToutCompte.contrat_id == contrat_id).first()
    if stc:
        db.delete(stc)
    db.delete(depart)
    
    db.commit()
    return None


@router.get("/contrats/{contrat_id}/solde-tout-compte", response_model=Optional[SoldeToutCompteOut])
def get_solde_tout_compte(
    contrat_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère le Solde de Tout Compte (STC) lié au contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    return db.query(SoldeToutCompte).filter(SoldeToutCompte.contrat_id == contrat_id).first()


@router.put("/contrats/{contrat_id}/solde-tout-compte", response_model=SoldeToutCompteOut)
def update_solde_tout_compte(
    contrat_id: int,
    stc_in: SoldeToutCompteBase,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour les montants du Solde de Tout Compte (STC) et recalcule le total."""
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    stc = db.query(SoldeToutCompte).filter(SoldeToutCompte.contrat_id == contrat_id).first()
    if not stc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun Solde de Tout Compte n'a été généré pour ce contrat."
        )

    # Mettre à jour les champs
    for field, value in stc_in.model_dump(exclude={"total"}, exclude_unset=True).items():
        setattr(stc, field, value)

    # Recalculer le total
    stc.total = (
        (stc.indemnite_licenciement or 0.0) +
        (stc.indemnite_conges_payes or 0.0) +
        (stc.indemnite_preavis or 0.0) +
        (stc.indemnite_autre or 0.0)
    )

    db.commit()
    db.refresh(stc)
    
    # Recalculer automatiquement les bulletins brouillons pour appliquer le STC mis à jour!
    from app.routers.salaries_hr import auto_recalculate_payslips
    depart = db.query(DepartSalarie).filter(DepartSalarie.contrat_id == contrat_id).first()
    if depart and depart.date_sortie:
        try:
            from datetime import datetime
            exit_date = datetime.strptime(depart.date_sortie[:10], "%Y-%m-%d")
            auto_recalculate_payslips(db, contrat.salarie_id, exit_date.date(), exit_date.date())
        except Exception:
            pass

    return stc
