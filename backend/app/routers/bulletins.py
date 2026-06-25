from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.models import BulletinPaie, Contrat, Dossier, Utilisateur, Constante, Salarie
from app.schemas.bulletin import (
    BulletinPaieOut, BulletinPaieCreate, SimulationInput, SimulationOut, 
    LigneSimulationOut, BulletinCumuls, BulletinCumulRow
)
from app.services.security import get_current_user
from app.routers.contrats import check_contrat_ownership
from app.services.payroll import calculate_payslip

router = APIRouter(tags=["Bulletins de Paie"])


def check_bulletin_ownership(bulletin_id: int, user_id: int, db: Session) -> BulletinPaie:
    bulletin = db.query(BulletinPaie).join(Dossier).filter(
        BulletinPaie.id == bulletin_id,
        Dossier.utilisateur_id == user_id
    ).first()
    if not bulletin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulletin de paie introuvable ou accès refusé."
        )
    return bulletin


def compute_bulletin_cumuls(db: Session, bulletin: BulletinPaie) -> BulletinCumuls:
    """Calcule dynamiquement les cumuls mensuels et annuels pour un bulletin donné."""
    contrat = bulletin.contrat
    unite = contrat.unite_temps or "Heures"
    
    def get_row_values(b: BulletinPaie) -> dict:
        jours_absences = sum(line.base_s for line in b.lignes if line.code.startswith("ABS_") and line.base_s is not None)
        
        if unite == "Jours":
            heures_jours = 30.0 - jours_absences
        else:
            base_standard = contrat.horaires.horaire_travail if (contrat.horaires and contrat.horaires.horaire_travail) else 173.33
            heures_supp = sum(line.base_s for line in b.lignes if line.code in ["HS_15", "HS_25", "HS_50"] and line.base_s is not None)
            heures_jours = base_standard - (jours_absences * 8.0) + heures_supp
            jours_absences = jours_absences
            
        heures_supp = sum(line.base_s for line in b.lignes if line.code in ["HS_15", "HS_25", "HS_50"] and line.base_s is not None)
        
        ibs = sum(line.montant_cs for line in b.lignes if line.code == "IBS" and line.montant_cs is not None)
        ricf = sum(line.montant_cs for line in b.lignes if line.code == "RICF" and line.montant_cs is not None)
        cmu = sum(line.montant_cs for line in b.lignes if line.code == "CMU_S" and line.montant_cs is not None)
        cot_retraite = sum(line.montant_cs for line in b.lignes if line.code == "CNPS_RETRAITE" and line.montant_cs is not None)
        
        return {
            "heures_jours": round(heures_jours, 2),
            "heures_supp": round(heures_supp, 2),
            "jours_absences": round(jours_absences, 2),
            "salaire_brut": round(b.salaire_brut, 2),
            "brut_imposable": round(b.salaire_brut, 2),
            "brut_cnps": round(b.salaire_brut, 2),
            "brut_conges": round(b.salaire_brut, 2),
            "ibs": round(ibs, 2),
            "ricf": round(ricf, 2),
            "cmu": round(cmu, 2),
            "cot_retraite": round(cot_retraite, 2)
        }

    mensuel_data = get_row_values(bulletin)
    
    # Récupérer tous les bulletins de la même année jusqu'au mois en cours
    prior_bulletins = db.query(BulletinPaie).filter(
        BulletinPaie.contrat_id == bulletin.contrat_id,
        BulletinPaie.annee == bulletin.annee,
        BulletinPaie.mois <= bulletin.mois
    ).all()
    
    annuel_totals = {
        "heures_jours": 0.0,
        "heures_supp": 0.0,
        "jours_absences": 0.0,
        "salaire_brut": 0.0,
        "brut_imposable": 0.0,
        "brut_cnps": 0.0,
        "brut_conges": 0.0,
        "ibs": 0.0,
        "ricf": 0.0,
        "cmu": 0.0,
        "cot_retraite": 0.0
    }
    
    for b in prior_bulletins:
        row_vals = get_row_values(b)
        for k in annuel_totals.keys():
            annuel_totals[k] += row_vals[k]
            
    for k in annuel_totals.keys():
        annuel_totals[k] = round(annuel_totals[k], 2)
        
    return BulletinCumuls(
        mensuel=BulletinCumulRow(**mensuel_data),
        annuel=BulletinCumulRow(**annuel_totals)
    )


@router.get("/dossiers/{dossier_id}/bulletins", response_model=List[BulletinPaieOut])
def get_dossier_bulletins(
    dossier_id: int,
    mois: Optional[int] = None,
    annee: Optional[int] = None,
    contrat_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les bulletins de paie d'un dossier avec filtre de période ou de contrat."""
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id, Dossier.utilisateur_id == current_user.id).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable ou accès refusé."
        )

    query = db.query(BulletinPaie).filter(BulletinPaie.dossier_id == dossier_id)
    if mois:
        query = query.filter(BulletinPaie.mois == mois)
    if annee:
        query = query.filter(BulletinPaie.annee == annee)
    if contrat_id:
        query = query.filter(BulletinPaie.contrat_id == contrat_id)
        
    bulletins = query.all()
    
    # Injecter les cumuls dynamiquement pour chaque bulletin
    result = []
    for b in bulletins:
        bout = BulletinPaieOut.model_validate(b)
        bout.cumuls = compute_bulletin_cumuls(db, b)
        result.append(bout)
        
    return result


@router.post("/bulletins/calculer", response_model=BulletinPaieOut)
def calculate_bulletin_paie(
    bulletin_in: BulletinPaieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Calcule ou recalcul le bulletin de paie pour un contrat et une période donnée."""
    check_contrat_ownership(bulletin_in.contrat_id, current_user.id, db)

    try:
        bulletin = calculate_payslip(
            db=db,
            contrat_id=bulletin_in.contrat_id,
            mois=bulletin_in.mois,
            annee=bulletin_in.annee,
            acompte=bulletin_in.acompte or 0.0
        )
        if bulletin_in.commentaire:
            bulletin.commentaire = bulletin_in.commentaire
            db.commit()
            db.refresh(bulletin)
            
        bout = BulletinPaieOut.model_validate(bulletin)
        bout.cumuls = compute_bulletin_cumuls(db, bulletin)
        return bout
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de calcul de paie: {str(e)}"
        )


@router.get("/bulletins/{bulletin_id}", response_model=BulletinPaieOut)
def get_bulletin(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère les détails d'un bulletin de paie (avec ses lignes de calcul)."""
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    bout = BulletinPaieOut.model_validate(bulletin)
    bout.cumuls = compute_bulletin_cumuls(db, bulletin)
    return bout


@router.put("/bulletins/{bulletin_id}/valider", response_model=BulletinPaieOut)
def validate_bulletin(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Valide définitivement un bulletin de paie."""
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    bulletin.statut = "valide"
    db.commit()
    db.refresh(bulletin)
    
    bout = BulletinPaieOut.model_validate(bulletin)
    bout.cumuls = compute_bulletin_cumuls(db, bulletin)
    return bout


@router.delete("/bulletins/{bulletin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bulletin(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un bulletin de paie (si encore à l'état brouillon ou calculé)."""
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    if bulletin.statut == "valide":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer un bulletin de paie validé."
        )

    db.delete(bulletin)
    db.commit()
    return None


@router.post("/bulletins/simuler", response_model=SimulationOut)
def simulate_bulletin_paie(
    sim_in: SimulationInput,
    db: Session = Depends(get_db)
):
    """Simule en mémoire un bulletin de paie pour la zone UEMOA sans persister de données."""
    try:
        unite = sim_in.unite_temps or "Heures"
        
        # 1. Base Salary
        if unite == "Jours":
            base_standard = 30.0
            salaire_base_brut = sim_in.salaire_mensuel or 0.0
            taux_base = (salaire_base_brut / 30.0) if salaire_base_brut > 0 else 0.0
        else:
            base_standard = sim_in.horaire_mensuel_standard or 173.33
            if sim_in.type_salaire == "Mensuel":
                salaire_base_brut = sim_in.salaire_mensuel or 0.0
                taux_base = (salaire_base_brut / base_standard) if base_standard > 0 else 0.0
            else:
                taux_base = sim_in.salaire_horaire or 0.0
                salaire_base_brut = taux_base * base_standard

        lignes = []

        # Ligne 1 : Salaire de base
        lignes.append(
            LigneSimulationOut(
                code="BASE",
                libelle="Salaire de base",
                salaire_base=round(salaire_base_brut, 2),
                base_s=base_standard,
                taux_s=round(taux_base, 2),
                montant_pr=round(salaire_base_brut, 2)
            )
        )

        # 2. Sursalaire
        sursalaire_brut = sim_in.sursalaire or 0.0
        if sursalaire_brut > 0:
            if unite == "Jours":
                base_sur = 30.0
                taux_sur = sursalaire_brut / 30.0
            else:
                base_sur = 0.0
                taux_sur = 0.0
                
            lignes.append(
                LigneSimulationOut(
                    code="SURSALAIRE",
                    libelle="Sursalaire",
                    salaire_base=round(sursalaire_brut, 2),
                    base_s=base_sur if base_sur > 0 else None,
                    taux_s=round(taux_sur, 2) if taux_sur > 0 else None,
                    montant_pr=round(sursalaire_brut, 2)
                )
            )

        # 3. Déduction des absences
        montant_deductions_absences = 0.0
        for absence in sim_in.absences:
            if unite == "Jours":
                heures_jours_abs = absence.nbr_jours if absence.nbr_jours > 0 else (absence.nbr_heures / 7.0 if absence.nbr_heures > 0 else 0.0)
                taux_abs = (salaire_base_brut + sursalaire_brut) / 30.0
            else:
                heures_jours_abs = absence.nbr_heures if absence.nbr_heures > 0 else (absence.nbr_jours * 8.0 if absence.nbr_jours > 0 else 0.0)
                taux_abs = taux_base

            deduction = heures_jours_abs * taux_abs
            montant_deductions_absences += deduction

            is_conges = "CONGE" in absence.code.upper()
            if is_conges:
                lignes.append(
                    LigneSimulationOut(
                        code="CONGES_PRIS",
                        libelle=f"Jours congés pris" if unite == "Jours" else f"Heures congés pris",
                        salaire_base=round(deduction, 2),
                        base_s=heures_jours_abs,
                        taux_s=round(taux_abs, 2),
                        montant_pr=round(deduction, 2)
                    )
                )
                lignes.append(
                    LigneSimulationOut(
                        code=f"ABS_{absence.code.upper()}",
                        libelle=f"Absences congés pris",
                        salaire_base=-round(deduction, 2),
                        base_s=heures_jours_abs,
                        taux_s=round(taux_abs, 2),
                        montant_pr=-round(deduction, 2)
                    )
                )
            else:
                lignes.append(
                    LigneSimulationOut(
                        code=f"ABS_{absence.code.upper()}",
                        libelle=f"Absence non rémunérée",
                        salaire_base=-round(deduction, 2),
                        base_s=heures_jours_abs,
                        taux_s=round(taux_abs, 2),
                        montant_pr=-round(deduction, 2)
                    )
                )

        # 4. Heures supplémentaires
        montant_heures_sup = 0.0
        for hs in sim_in.heures_sup:
            majoration = 1.0
            if "15" in hs.code:
                majoration = 1.15
            elif "25" in hs.code:
                majoration = 1.25
            elif "50" in hs.code:
                majoration = 1.50
            
            taux_hs = taux_base * majoration
            gain_hs = hs.nombre * taux_hs
            montant_heures_sup += gain_hs

            lignes.append(
                LigneSimulationOut(
                    code=hs.code.upper(),
                    libelle=f"Heures supplémentaires à {int(round((majoration-1)*100))}%" if "15" in hs.code else f"Heures supplémentaires majorées à {int(round((majoration-1)*100))}%",
                    salaire_base=round(gain_hs, 2),
                    base_s=hs.nombre,
                    taux_s=round(taux_hs, 2),
                    montant_pr=round(gain_hs, 2)
                )
            )

        # 5. Primes
        montant_primes = 0.0
        for prime in sim_in.primes:
            montant_primes += prime.montant
            lignes.append(
                LigneSimulationOut(
                    code=prime.code.upper(),
                    libelle=prime.libelle or f"Prime {prime.code}",
                    salaire_base=round(prime.montant, 2),
                    montant_pr=round(prime.montant, 2)
                )
            )

        # Calcul du Salaire Brut
        salaire_brut = sum(line.montant_pr for line in lignes)

        # 6. Cotisations sociales et Taxes (CNPS zone UEMOA)
        cotisations_salariales_totales = 0.0
        cotisations_patronales_totales = 0.0
        taux_at_patronal = sim_in.taux_at if (sim_in.taux_at and sim_in.taux_at > 0) else 2.0

        pays_code = "CI"

        # Récupération dynamique des constantes depuis la base de données
        def get_val(code: str, default: float) -> float:
            const = db.query(Constante).filter(
                Constante.code == code,
                Constante.pays == pays_code,
                Constante.est_actif == True
            ).first()
            return const.montant if const else default

        cnps_pf_plafond = get_val("CNPS_PF_PLAFOND", 75000.0)
        cnps_pf_taux_p = get_val("CNPS_PF_TAUX_P", 5.0)

        cnps_retraite_plafond = get_val("CNPS_RETRAITE_PLAFOND", 3375000.0)
        cnps_retraite_taux_s = get_val("CNPS_RETRAITE_TAUX_S", 6.3)
        cnps_retraite_taux_p = get_val("CNPS_RETRAITE_TAUX_P", 7.7)

        cnps_at_plafond = get_val("CNPS_AT_PLAFOND", 75000.0)
        cnps_maternite_plafond = get_val("CNPS_MATERNITE_PLAFOND", 75000.0)
        cnps_maternite_taux_p = get_val("CNPS_MATERNITE_TAUX_P", 0.75)

        cmu_salariale = get_val("CMU_MONTANT_S", 500.0)
        cmu_patronale = get_val("CMU_MONTANT_P", 500.0)
        ibs_montant = get_val("IBS_MONTANT", 74577.0)
        ricf_montant = get_val("RICF_MONTANT", -11000.0)

        cn_taux_p = get_val("CN_TAUX_P_EXP", 8.0) if sim_in.expatrie else get_val("CN_TAUX_P_LOC", 1.5)
        ta_taux_p = get_val("TA_TAUX_P", 0.4)
        tfc_taux_p = get_val("TFC_TAUX_P", 0.6)

        # 1. IBS
        lignes.append(
            LigneSimulationOut(
                code="IBS",
                libelle="Impôt brut sur salaire",
                base_s=round(salaire_brut, 2),
                taux_s=0.0,
                montant_cs=round(ibs_montant, 2)
            )
        )
        cotisations_salariales_totales += ibs_montant

        # 2. RICF
        lignes.append(
            LigneSimulationOut(
                code="RICF",
                libelle="Réduction d'impôt pour charge familiale",
                base_s=round(salaire_brut, 2),
                taux_s=0.0,
                montant_cs=round(ricf_montant, 2)
            )
        )
        cotisations_salariales_totales += ricf_montant

        # 3. CNPS Retraite
        base_retraite = min(salaire_brut, cnps_retraite_plafond) if salaire_brut > 0 else 0.0
        montant_retraite_s = base_retraite * (cnps_retraite_taux_s / 100.0)
        montant_retraite_p = base_retraite * (cnps_retraite_taux_p / 100.0)
        cotisations_salariales_totales += montant_retraite_s
        cotisations_patronales_totales += montant_retraite_p
        lignes.append(
            LigneSimulationOut(
                code="CNPS_RETRAITE",
                libelle="CNPS - Retraite",
                base_s=round(base_retraite, 2),
                base_p=round(base_retraite, 2),
                taux_s=cnps_retraite_taux_s,
                taux_p=cnps_retraite_taux_p,
                montant_cs=round(montant_retraite_s, 2),
                montant_cp=round(montant_retraite_p, 2)
            )
        )

        # 4. CMU Salariale
        lignes.append(
            LigneSimulationOut(
                code="CMU_S",
                libelle="Cotisation CMU part salariale",
                base_s=500.0,
                taux_s=100.0,
                montant_cs=round(cmu_salariale, 2)
            )
        )
        cotisations_salariales_totales += cmu_salariale

        # 5. CN Patronale
        montant_cn_p = salaire_brut * (cn_taux_p / 100.0)
        cotisations_patronales_totales += montant_cn_p
        lignes.append(
            LigneSimulationOut(
                code="CN",
                libelle="Contribution nationale",
                base_p=round(salaire_brut, 2),
                taux_p=cn_taux_p,
                montant_cp=round(montant_cn_p, 2)
            )
        )

        # 6. TA Patronale
        montant_ta_p = salaire_brut * (ta_taux_p / 100.0)
        cotisations_patronales_totales += montant_ta_p
        lignes.append(
            LigneSimulationOut(
                code="TA",
                libelle="Taxe d'apprentissage",
                base_p=round(salaire_brut, 2),
                taux_p=ta_taux_p,
                montant_cp=round(montant_ta_p, 2)
            )
        )

        # 7. TFC Patronale
        montant_tfc_p = salaire_brut * (tfc_taux_p / 100.0)
        cotisations_patronales_totales += montant_tfc_p
        lignes.append(
            LigneSimulationOut(
                code="TFC",
                libelle="Taxe Formation continue",
                base_p=round(salaire_brut, 2),
                taux_p=tfc_taux_p,
                montant_cp=round(montant_tfc_p, 2)
            )
        )

        # 8. CNPS PF Patronale
        base_pf = min(salaire_brut, cnps_pf_plafond) if salaire_brut > 0 else 0.0
        montant_pf_p = base_pf * (cnps_pf_taux_p / 100.0)
        cotisations_patronales_totales += montant_pf_p
        lignes.append(
            LigneSimulationOut(
                code="CNPS_PF",
                libelle="CNPS - Prestations Familiales",
                base_p=round(base_pf, 2),
                taux_p=cnps_pf_taux_p,
                montant_cp=round(montant_pf_p, 2)
            )
        )

        # 9. CNPS AT Patronale
        base_at = min(salaire_brut, cnps_at_plafond) if salaire_brut > 0 else 0.0
        montant_at_p = base_at * (taux_at_patronal / 100.0)
        cotisations_patronales_totales += montant_at_p
        lignes.append(
            LigneSimulationOut(
                code="CNPS_AT",
                libelle="CNPS - Accidents du Travail et Maladies Pro.",
                base_p=round(base_at, 2),
                taux_p=taux_at_patronal,
                montant_cp=round(montant_at_p, 2)
            )
        )

        # 10. CNPS Maternité Patronale
        base_mat = min(salaire_brut, cnps_maternite_plafond) if salaire_brut > 0 else 0.0
        montant_mat_p = base_mat * (cnps_maternite_taux_p / 100.0)
        cotisations_patronales_totales += montant_mat_p
        lignes.append(
            LigneSimulationOut(
                code="CNPS_MATERNITE",
                libelle="CNPS - Assurance Maternité",
                base_p=round(base_mat, 2),
                taux_p=cnps_maternite_taux_p,
                montant_cp=round(montant_mat_p, 2)
            )
        )

        # 11. CMU Patronale
        lignes.append(
            LigneSimulationOut(
                code="CMU_P",
                libelle="Cotisation CMU part patronale",
                base_p=500.0,
                taux_p=100.0,
                montant_cp=round(cmu_patronale, 2)
            )
        )
        cotisations_patronales_totales += cmu_patronale

        # Allowances / Deductions
        transport_montant = sim_in.indemnite_transport or 0.0
        if transport_montant > 0:
            lignes.append(
                LigneSimulationOut(
                    code="TRANSPORT",
                    libelle="Indemnité de transport",
                    base_s=26.0,
                    taux_s=round(transport_montant / 26.0, 2),
                    montant_pr=round(transport_montant, 2)
                )
            )
            
        telephone_montant = sim_in.dotation_telephonique or 0.0
        if telephone_montant > 0:
            lignes.append(
                LigneSimulationOut(
                    code="TELEPHONE",
                    libelle="Dotation téléphonique",
                    montant_pr=round(telephone_montant, 2)
                )
            )
            
        acompte = sim_in.acompte or 0.0
        if acompte > 0:
            lignes.append(
                LigneSimulationOut(
                    code="ACOMPTE",
                    libelle="Retenues divers services ex : acomptes",
                    montant_cs=round(acompte, 2)
                )
            )

        # 6. Calcul des totaux nets et imposables
        net_a_payer = salaire_brut - cotisations_salariales_totales - acompte + transport_montant + telephone_montant
        net_imposable = salaire_brut - (min(salaire_brut, 3375000) * 0.063)

        # Calculer les cumuls pour la simulation (mensuel et annuel sont identiques pour un one-shot)
        jours_absences = sum(line.base_s for line in lignes if line.code.startswith("ABS_") and line.base_s is not None)
        if unite == "Jours":
            heures_jours = 30.0 - jours_absences
        else:
            heures_supp = sum(line.base_s for line in lignes if line.code in ["HS_15", "HS_25", "HS_50"] and line.base_s is not None)
            heures_jours = base_standard - (jours_absences * 8.0) + heures_supp
            jours_absences = jours_absences
            
        heures_supp = sum(line.base_s for line in lignes if line.code in ["HS_15", "HS_25", "HS_50"] and line.base_s is not None)
        
        cumul_row_data = {
            "heures_jours": round(heures_jours, 2),
            "heures_supp": round(heures_supp, 2),
            "jours_absences": round(jours_absences, 2),
            "salaire_brut": round(salaire_brut, 2),
            "brut_imposable": round(salaire_brut, 2),
            "brut_cnps": round(salaire_brut, 2),
            "brut_conges": round(salaire_brut, 2),
            "ibs": round(ibs_montant, 2),
            "ricf": round(ricf_montant, 2),
            "cmu": round(cmu_salariale, 2),
            "cot_retraite": round(montant_retraite_s, 2)
        }
        
        sim_cumuls = BulletinCumuls(
            mensuel=BulletinCumulRow(**cumul_row_data),
            annuel=BulletinCumulRow(**cumul_row_data)
        )

        return SimulationOut(
            salaire_brut=round(salaire_brut, 2),
            cotisations_salariales=round(cotisations_salariales_totales, 2),
            cotisations_patronales=round(cotisations_patronales_totales, 2),
            net_a_payer=round(net_a_payer, 2),
            net_imposable=round(net_imposable, 2),
            lignes=lignes,
            cumuls=sim_cumuls
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de simulation de paie: {str(e)}"
        )
