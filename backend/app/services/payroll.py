import logging
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.models import (
    Contrat, BulletinPaie, LigneBulletinPaie, VariableBulletin,
    Absence, HeureSupplementaire, Prime, Option, CaisseCotisation, Etablissement, Constante, Salarie, PretSalarie,
    SalarieAbsence, DepartSalarie, SoldeToutCompte
)

from typing import Optional

logger = logging.getLogger(__name__)


def _get_payroll_inputs(db: Session, contrat_id: int, mois: int, annee: int):
    """Récupère l'ensemble des données nécessaires au calcul de la paie."""
    contrat = db.query(Contrat).filter(Contrat.id == contrat_id).first()
    if not contrat:
        raise ValueError("Contrat introuvable.")

    etab = db.query(Etablissement).filter(Etablissement.id == contrat.etablissement_id).first()
    salarie = db.query(Salarie).filter(Salarie.id == contrat.salarie_id).first()
    
    absences = db.query(Absence).filter(
        Absence.contrat_id == contrat_id,
        Absence.annee == str(annee),
        Absence.mois == mois
    ).all()

    # Intégrer les absences de la fiche salarié (salaries_absences)
    import calendar
    from datetime import date
    import unicodedata

    month_start = date(annee, mois, 1)
    _, last_day = calendar.monthrange(annee, mois)
    month_end = date(annee, mois, last_day)

    hr_absences = db.query(SalarieAbsence).filter(
        SalarieAbsence.salarie_id == contrat.salarie_id,
        SalarieAbsence.date_debut_absence <= month_end,
        SalarieAbsence.date_fin_absence >= month_start
    ).all()

    daily_hours = 7.0
    if contrat.horaires and contrat.horaires.horaire_hebdo:
        daily_hours = contrat.horaires.horaire_hebdo / 5.0

    for a_hr in hr_absences:
        overlap_start = max(a_hr.date_debut_absence, month_start)
        overlap_end = min(a_hr.date_fin_absence, month_end)
        overlap_days = (overlap_end - overlap_start).days + 1

        # Normaliser le motif d'absence pour construire un code d'absence (ex: CONGES, MALADIE, etc.)
        raw_type = a_hr.type_absence or "ABSENCE"
        type_code = "".join(
            c for c in unicodedata.normalize('NFD', raw_type)
            if unicodedata.category(c) != 'Mn'
        ).upper().replace(" ", "_").replace("'", "_").replace("-", "_")

        # Éviter les doublons si l'absence a déjà été saisie manuellement dans les variables du bulletin
        duplicate = False
        for db_abs in absences:
            if db_abs.code == type_code and db_abs.date_debut and db_abs.date_fin:
                db_start = db_abs.date_debut.date() if isinstance(db_abs.date_debut, datetime) else db_abs.date_debut
                db_end = db_abs.date_fin.date() if isinstance(db_abs.date_fin, datetime) else db_abs.date_fin
                if db_start == overlap_start and db_end == overlap_end:
                    duplicate = True
                    break

        if not duplicate:
            virtual_abs = Absence(
                contrat_id=contrat_id,
                code=type_code,
                date_debut=datetime.combine(overlap_start, datetime.min.time()),
                date_fin=datetime.combine(overlap_end, datetime.min.time()),
                nbr_heure_by_user=float(overlap_days * daily_hours),
                nbr_jour_by_user=float(overlap_days),
                mois=mois,
                annee=str(annee)
            )
            absences.append(virtual_abs)

    heures_sup = db.query(HeureSupplementaire).filter(
        HeureSupplementaire.contrat_id == contrat_id,
        HeureSupplementaire.annee == str(annee),
        HeureSupplementaire.mois == mois
    ).all()

    primes = db.query(Prime).filter(
        Prime.contrat_id == contrat_id
    ).filter(
        (
            (Prime.est_persistant == False) & 
            (Prime.annee == str(annee)) & 
            (Prime.mois == mois)
        ) | (
            (Prime.est_persistant == True) & 
            (
                (Prime.annee < str(annee)) |
                ((Prime.annee == str(annee)) & (Prime.mois <= mois))
            )
        )
    ).all()

    options = db.query(Option).filter(
        Option.contrat_id == contrat_id
    ).filter(
        (
            (Option.est_persistant == False) & 
            (Option.annee == str(annee)) & 
            (Option.mois == mois)
        ) | (
            (Option.est_persistant == True) & 
            (
                (Option.annee < str(annee)) |
                ((Option.annee == str(annee)) & (Option.mois <= mois))
            )
        )
    ).all()

    return contrat, etab, salarie, absences, heures_sup, primes, options


def _get_or_create_bulletin(db: Session, contrat_id: int, dossier_id: int, mois: int, annee: int) -> BulletinPaie:
    """Récupère le bulletin de paie existant ou en crée un nouveau, en réinitialisant ses lignes."""
    bulletin = db.query(BulletinPaie).filter(
        BulletinPaie.contrat_id == contrat_id,
        BulletinPaie.mois == mois,
        BulletinPaie.annee == annee
    ).first()

    if bulletin:
        # Si le bulletin existe, on supprime les anciennes lignes pour recalculer
        db.query(LigneBulletinPaie).filter(LigneBulletinPaie.bulletin_id == bulletin.id).delete()
        db.query(VariableBulletin).filter(VariableBulletin.bulletin_id == bulletin.id).delete()
    else:
        bulletin = BulletinPaie(
            contrat_id=contrat_id,
            dossier_id=dossier_id,
            mois=mois,
            annee=annee,
            statut="brouillon"
        )
        db.add(bulletin)
        db.commit()
        db.refresh(bulletin)

    return bulletin


def _calculate_gross_salary(
    bulletin_id: int,
    contrat: Contrat,
    absences: list[Absence],
    heures_sup: list[HeureSupplementaire],
    primes: list[Prime],
    options: list[Option] = [],
    override_salary_value: Optional[float] = None
) -> tuple[list[LigneBulletinPaie], float]:
    """Calcule le salaire de base, le sursalaire, applique les absences, heures supps, primes et calcule le Salaire Brut."""
    unite = contrat.unite_temps or "Heures"
    
    # 1. Base Salary
    if unite == "Jours":
        base_standard = 30.0
        salaire_base_brut = override_salary_value if override_salary_value is not None else (contrat.salaire_mensuel or 0.0)
        taux_base = (salaire_base_brut / 30.0) if salaire_base_brut > 0 else 0.0
    else:
        base_standard = contrat.horaires.horaire_travail if (contrat.horaires and contrat.horaires.horaire_travail) else 173.33
        if contrat.type_salaire == "Mensuel":
            salaire_base_brut = override_salary_value if override_salary_value is not None else (contrat.salaire_mensuel or 0.0)
            taux_base = (salaire_base_brut / base_standard) if base_standard > 0 else 0.0
        else:
            taux_base = override_salary_value if override_salary_value is not None else (contrat.salaire_horaire or 0.0)
            salaire_base_brut = taux_base * base_standard

    lignes_bulletin = []

    # Ligne 1 : Salaire de base
    ligne_base = LigneBulletinPaie(
        bulletin_id=bulletin_id,
        code="BASE",
        libelle="Salaire de base",
        salaire_base=round(salaire_base_brut, 2),
        base_s=base_standard,
        taux_s=round(taux_base, 2),
        montant_pr=round(salaire_base_brut, 2)
    )
    lignes_bulletin.append(ligne_base)

    # 2. Sursalaire
    sursalaire_brut = contrat.sursalaire or 0.0
    if sursalaire_brut > 0:
        if unite == "Jours":
            base_sur = 30.0
            taux_sur = sursalaire_brut / 30.0
        else:
            base_sur = 0.0  # Empty base and rate for hourly sursalaire as in image
            taux_sur = 0.0
            
        ligne_sur = LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="SURSALAIRE",
            libelle="Sursalaire",
            salaire_base=round(sursalaire_brut, 2),
            base_s=base_sur if base_sur > 0 else None,
            taux_s=round(taux_sur, 2) if taux_sur > 0 else None,
            montant_pr=round(sursalaire_brut, 2)
        )
        lignes_bulletin.append(ligne_sur)

    # 3. Déduction des absences
    montant_deductions_absences = 0.0
    for absence in absences:
        # Determine absence units and rate
        if unite == "Jours":
            heures_jours_abs = absence.nbr_jour_by_user if absence.nbr_jour_by_user > 0 else (absence.nbr_heure_by_user / 7.0 if absence.nbr_heure_by_user > 0 else 0.0)
            # Daily contract rate includes sursalaire
            taux_abs = (salaire_base_brut + sursalaire_brut) / 30.0
        else:
            heures_jours_abs = absence.nbr_heure_by_user if absence.nbr_heure_by_user > 0 else (absence.nbr_jour_by_user * 8.0 if absence.nbr_jour_by_user > 0 else 0.0)
            taux_abs = taux_base
            
        deduction = heures_jours_abs * taux_abs
        montant_deductions_absences += deduction

        # If it's a paid vacation ("CONGES" or similar), we add the payment line and deduct it as absence
        is_conges = "CONGE" in absence.code.upper()
        if is_conges:
            # Jours/Heures congés pris (positive)
            lignes_bulletin.append(
                LigneBulletinPaie(
                    bulletin_id=bulletin_id,
                    code="CONGES_PRIS",
                    libelle=f"Jours congés pris {absence.date_debut.strftime('%d/%m/%Y') if absence.date_debut else ''}-{absence.date_fin.strftime('%d/%m/%Y') if absence.date_fin else ''}" if unite == "Jours" else f"Heures congés pris {absence.date_debut.strftime('%d/%m/%Y') if absence.date_debut else ''}-{absence.date_fin.strftime('%d/%m/%Y') if absence.date_fin else ''}",
                    salaire_base=round(deduction, 2),
                    base_s=heures_jours_abs,
                    taux_s=round(taux_abs, 2),
                    montant_pr=round(deduction, 2)
                )
            )
            # Absences congés pris (negative deduction)
            lignes_bulletin.append(
                LigneBulletinPaie(
                    bulletin_id=bulletin_id,
                    code=f"ABS_{absence.code}",
                    libelle=f"Absences congés pris {absence.date_debut.strftime('%d/%m/%Y') if absence.date_debut else ''}-{absence.date_fin.strftime('%d/%m/%Y') if absence.date_fin else ''}",
                    salaire_base=-round(deduction, 2),
                    base_s=heures_jours_abs,
                    taux_s=round(taux_abs, 2),
                    montant_pr=-round(deduction, 2)
                )
            )
        else:
            # Standard unpaid absence
            lignes_bulletin.append(
                LigneBulletinPaie(
                    bulletin_id=bulletin_id,
                    code=f"ABS_{absence.code}",
                    libelle=f"Absence non rémunérée {absence.date_debut.strftime('%d/%m/%Y') if absence.date_debut else ''}-{absence.date_fin.strftime('%d/%m/%Y') if absence.date_fin else ''}",
                    salaire_base=-round(deduction, 2),
                    base_s=heures_jours_abs,
                    taux_s=round(taux_abs, 2),
                    montant_pr=-round(deduction, 2)
                )
            )

    # 4. Heures supplémentaires
    montant_heures_sup = 0.0
    for hs in heures_sup:
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

        lignes_bulletin.append(
            LigneBulletinPaie(
                bulletin_id=bulletin_id,
                code=hs.code,
                libelle=f"Heures supplémentaires à {int((majoration-1)*100)}%" if "15" in hs.code else f"Heures supplémentaires majorées à {int((majoration-1)*100)}%",
                salaire_base=round(gain_hs, 2),
                base_s=hs.nombre,
                taux_s=round(taux_hs, 2),
                montant_pr=round(gain_hs, 2)
            )
        )

    # 5. Primes
    montant_primes = 0.0
    for prime in primes:
        montant_primes += prime.montant
        has_base_rate = prime.base is not None and prime.taux is not None
        lignes_bulletin.append(
            LigneBulletinPaie(
                bulletin_id=bulletin_id,
                code=prime.code,
                libelle=prime.libelle or f"Prime {prime.code}",
                salaire_base=round(prime.base if has_base_rate else prime.montant, 2),
                base_s=round(prime.base, 2) if has_base_rate else None,
                taux_s=round(prime.taux, 4) if has_base_rate else None,
                montant_pr=round(prime.montant, 2)
            )
        )

    # 6. Options (gains et avantages en nature)
    for opt in options:
        is_gross_gain = opt.code.startswith("AVANTAGE_") or opt.code == "AUTRE_GAIN"
        if is_gross_gain:
            val = opt.valeur_numerique or 0.0
            lignes_bulletin.append(
                LigneBulletinPaie(
                    bulletin_id=bulletin_id,
                    code=opt.code,
                    libelle=opt.libelle or f"Option {opt.code}",
                    salaire_base=round(val, 2),
                    montant_pr=round(val, 2)
                )
            )

    # To be extremely precise and match standard payroll, we sum all lines that make up the gross salary:
    salaire_brut = sum(line.montant_pr for line in lignes_bulletin)
    return lignes_bulletin, salaire_brut


def _calculate_cnps_cotisations(
    db: Session,
    bulletin_id: int,
    etab: Etablissement,
    contrat: Contrat,
    salarie: Salarie,
    salaire_brut: float
) -> tuple[list[LigneBulletinPaie], float, float]:
    """Calcule les cotisations sociales patronales et salariales ainsi que les impôts (zone UEMOA)."""
    cotisations_salariales_totales = 0.0
    cotisations_patronales_totales = 0.0

    pays_code = "CI"
    if etab and etab.adresse and etab.adresse.pays:
        p_name = etab.adresse.pays.upper()
        if "IVOIRE" in p_name or "CI" in p_name:
            pays_code = "CI"

    # Récupération dynamique des constantes depuis la base de données
    def get_val(code: str, default: float) -> float:
        const = db.query(Constante).filter(
            Constante.code == code,
            Constante.pays == pays_code,
            Constante.est_actif == True
        ).first()
        return const.montant if const else default

    # Plafonds
    cnps_pf_plafond = get_val("CNPS_PF_PLAFOND", 75000.0)
    cnps_pf_taux_p = get_val("CNPS_PF_TAUX_P", 5.0)

    cnps_retraite_plafond = get_val("CNPS_RETRAITE_PLAFOND", 3375000.0)
    cnps_retraite_taux_s = get_val("CNPS_RETRAITE_TAUX_S", 6.3)
    cnps_retraite_taux_p = get_val("CNPS_RETRAITE_TAUX_P", 7.7)

    cnps_at_plafond = get_val("CNPS_AT_PLAFOND", 75000.0)
    taux_at_patronal = etab.taux_at if (etab and etab.taux_at and etab.taux_at > 0) else 2.0

    cnps_maternite_plafond = get_val("CNPS_MATERNITE_PLAFOND", 75000.0)
    cnps_maternite_taux_p = get_val("CNPS_MATERNITE_TAUX_P", 0.75)

    # CMU Constants
    cmu_salariale = get_val("CMU_MONTANT_S", 500.0)
    cmu_patronale = get_val("CMU_MONTANT_P", 500.0)

    # IBS & RICF Constants
    ibs_montant = get_val("IBS_MONTANT", 74577.0)
    ricf_montant = get_val("RICF_MONTANT", -11000.0)

    # CN, TA, TFC Taux
    is_expat = salarie.expatrie if salarie else False
    cn_taux_p = get_val("CN_TAUX_P_EXP", 8.0) if is_expat else get_val("CN_TAUX_P_LOC", 1.5)
    ta_taux_p = get_val("TA_TAUX_P", 0.4)
    tfc_taux_p = get_val("TFC_TAUX_P", 0.6)

    lignes_cotisations = []

    # 1. CNPS Retraite Salariale & Patronale (calculée en premier pour déduire du brut imposable)
    base_retraite = min(salaire_brut, cnps_retraite_plafond) if salaire_brut > 0 else 0.0
    montant_retraite_s = base_retraite * (cnps_retraite_taux_s / 100.0)
    montant_retraite_p = base_retraite * (cnps_retraite_taux_p / 100.0)
    cotisations_salariales_totales += montant_retraite_s
    cotisations_patronales_totales += montant_retraite_p

    # Net Imposable = Salaire Brut - Retraite Salariale
    net_imposable = max(0.0, salaire_brut - montant_retraite_s)

    # 2. Calcul dynamique de l'ITS (IBS et RICF) sur le Net Imposable
    tranches = [
        (0, 75000, 0.0),  
        (75000, 240000, 0.16),
        (240000, 800000, 0.21),
        (800000, 2400000, 0.24),
        (2400000, 8000000, 0.28),
        (8000000, float('inf'), 0.32)
    ]
    its_brut = 0.0

    for min_val, max_val, taux in tranches:
        if net_imposable > min_val:
            portion = min(net_imposable, max_val) - min_val
            if portion > 0:
                its_brut += portion * taux

    # Calcul des parts familiales
    sit = (salarie.situation_matrimoniale if salarie else "").strip().lower() if (salarie and salarie.situation_matrimoniale) else ""
    kids = max(0, int(salarie.enfants_charge or 0)) if salarie else 0
    
    if "mari" in sit:
        parts = 2.0 + (kids * 0.5)
    elif "veuf" in sit or "veuve" in sit:
        parts = 1.0 if kids == 0 else 2.0 + (kids * 0.5)
    else:  # Célibataire / Divorcé(e)
        if kids == 0:
            parts = 1.0
        elif kids == 1:
            parts = 2.0
        else:
            parts = 2.0 + ((kids - 1) * 0.5)
    parts = min(5.0, parts)

    # Réduction d'Impôt pour Charge Familiale (RICF)
    ricf_montant = max(0.0, (parts - 1.0) * 11000.0)
    ricf_applicable = min(ricf_montant, its_brut)

    # IBS Line
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="IBS",
            libelle="Impôt brut sur salaire",
            base_s=round(net_imposable, 2),
            taux_s=0.0,
            montant_cs=round(its_brut, 2)
        )
    )
    cotisations_salariales_totales += its_brut

    # RICF Line
    parts_str = f"{parts:.1f}".rstrip('0').rstrip('.')
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="RICF",
            libelle=f"Réduction d'impôt charge familiale ({parts_str} part{'s' if parts > 1 else ''})",
            base_s=round(net_imposable, 2),
            taux_s=0.0,
            montant_cs=round(-ricf_applicable, 2)
        )
    )
    cotisations_salariales_totales += -ricf_applicable

    # CNPS Retraite Line
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
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
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="CMU_S",
            libelle="Cotisation CMU part salariale",
            base_s=500.0,
            taux_s=100.0,
            montant_cs=round(cmu_salariale, 2)
        )
    )
    cotisations_salariales_totales += cmu_salariale

    # 5. CN (Contribution Nationale Patronale)
    montant_cn_p = salaire_brut * (cn_taux_p / 100.0)
    cotisations_patronales_totales += montant_cn_p
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="CN",
            libelle="Contribution nationale",
            base_p=round(salaire_brut, 2),
            taux_p=cn_taux_p,
            montant_cp=round(montant_cn_p, 2)
        )
    )

    # 6. TA (Taxe d'Apprentissage Patronale)
    montant_ta_p = salaire_brut * (ta_taux_p / 100.0)
    cotisations_patronales_totales += montant_ta_p
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="TA",
            libelle="Taxe d'apprentissage",
            base_p=round(salaire_brut, 2),
            taux_p=ta_taux_p,
            montant_cp=round(montant_ta_p, 2)
        )
    )

    # 7. TFC (Taxe Formation Continue Patronale)
    montant_tfc_p = salaire_brut * (tfc_taux_p / 100.0)
    cotisations_patronales_totales += montant_tfc_p
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="TFC",
            libelle="Taxe Formation continue",
            base_p=round(salaire_brut, 2),
            taux_p=tfc_taux_p,
            montant_cp=round(montant_tfc_p, 2)
        )
    )

    # 8. CNPS PF (Prestations Familiales Patronale)
    base_pf = min(salaire_brut, cnps_pf_plafond) if salaire_brut > 0 else 0.0
    montant_pf_p = base_pf * (cnps_pf_taux_p / 100.0)
    cotisations_patronales_totales += montant_pf_p
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="CNPS_PF",
            libelle="CNPS - Prestations Familiales",
            base_p=round(base_pf, 2),
            taux_p=cnps_pf_taux_p,
            montant_cp=round(montant_pf_p, 2)
        )
    )

    # 9. CNPS AT (Accidents du Travail Patronale)
    base_at = min(salaire_brut, cnps_at_plafond) if salaire_brut > 0 else 0.0
    montant_at_p = base_at * (taux_at_patronal / 100.0)
    cotisations_patronales_totales += montant_at_p
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
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
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="CNPS_MATERNITE",
            libelle="CNPS - Assurance Maternité",
            base_p=round(base_mat, 2),
            taux_p=cnps_maternite_taux_p,
            montant_cp=round(montant_mat_p, 2)
        )
    )

    # 11. CMU Patronale
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="CMU_P",
            libelle="Cotisation CMU part patronale",
            base_p=500.0,
            taux_p=100.0,
            montant_cp=round(cmu_patronale, 2)
        )
    )
    cotisations_patronales_totales += cmu_patronale

    return lignes_cotisations, cotisations_salariales_totales, cotisations_patronales_totales


def _save_bulletin(
    db: Session,
    bulletin: BulletinPaie,
    lines: list[LigneBulletinPaie],
    salaire_brut: float,
    cot_salariales: float,
    cot_patronales: float,
    net_a_payer: float,
    net_imposable: float
) -> None:
    """Persiste le bulletin, met à jour ses totaux et ajoute les lignes/variables associées."""
    # Ajout des lignes au bulletin
    for ligne in lines:
        db.add(ligne)

    # Mise à jour de l'en-tête du bulletin de paie
    bulletin.salaire_brut = round(salaire_brut, 2)
    bulletin.cotisations_salariales = round(cot_salariales, 2)
    bulletin.cotisations_patronales = round(cot_patronales, 2)
    bulletin.net_a_payer = round(net_a_payer, 2)
    bulletin.net_imposable = round(net_imposable, 2)
    bulletin.statut = "calcule"
    bulletin.date_paiement = datetime.now()

    # Variables de bulletin spécifiques
    var_brut = VariableBulletin(bulletin_id=bulletin.id, code="BRUT", libelle="Salaire Brut", valeur=round(salaire_brut, 2))
    var_net_payer = VariableBulletin(bulletin_id=bulletin.id, code="NET_PAYER", libelle="Net à payer", valeur=round(net_a_payer, 2))
    var_net_imp = VariableBulletin(bulletin_id=bulletin.id, code="NET_IMP", libelle="Net Imposable", valeur=round(net_imposable, 2))
    
    db.add(var_brut)
    db.add(var_net_payer)
    db.add(var_net_imp)

    db.commit()
    db.refresh(bulletin)


def _calculate_payslip_raw(
    db: Session,
    bulletin_id: int,
    contrat: Contrat,
    etab: Etablissement,
    salarie: Salarie,
    absences: list[Absence],
    heures_sup: list[HeureSupplementaire],
    primes: list[Prime],
    options: list[Option],
    acompte: float,
    temp_salaire_value: float
) -> float:
    """Calcul du salaire net pour une valeur brute temporaire, sans affecter le model."""
    # Calcul temporaire des lignes de salaire brut
    _, salaire_brut = _calculate_gross_salary(
        bulletin_id, contrat, absences, heures_sup, primes, options,
        override_salary_value=temp_salaire_value
    )

    # Calcul temporaire des cotisations sociales et taxes
    _, cot_salariales, _ = _calculate_cnps_cotisations(db, bulletin_id, etab, contrat, salarie, salaire_brut)

    # Calcul temporaire des lignes complémentaires
    transport_montant = contrat.indemnite_transport or 0.0
    telephone_montant = contrat.dotation_telephonique or 0.0

    options_gains_net = 0.0
    options_deductions_net = 0.0
    for opt in options:
        val = opt.valeur_numerique or 0.0
        if opt.code.startswith("AVANTAGE_"):
            options_deductions_net += val
        elif opt.code == "FRAIS_PROFESSIONNELS":
            options_gains_net += val
        elif opt.code == "AUTRE_RETENUE":
            options_deductions_net += val

    net_a_payer = (
        salaire_brut
        - cot_salariales
        - acompte
        + transport_montant
        + telephone_montant
        + options_gains_net
        - options_deductions_net
    )
    return net_a_payer


def calculate_payslip(db: Session, contrat_id: int, mois: int, annee: int, acompte: float = 0.0) -> BulletinPaie:
    """
    Calcule le bulletin de paie pour un contrat donné, un mois et une année.
    Si le bulletin existe déjà, il est recalculé et mis à jour.
    """
    # 1. Récupération des données d'entrée
    contrat, etab, salarie, absences, heures_sup, primes, options = _get_payroll_inputs(db, contrat_id, mois, annee)

    # 2. Récupération ou création du bulletin de paie
    bulletin = _get_or_create_bulletin(db, contrat_id, contrat.dossier_id, mois, annee)

    # Récupérer les informations de Solde Tout Compte
    stc = db.query(SoldeToutCompte).filter(SoldeToutCompte.contrat_id == contrat_id).first()
    depart = db.query(DepartSalarie).filter(DepartSalarie.contrat_id == contrat_id).first()
    
    stc_gross_conges = 0.0
    stc_net_gains = 0.0
    stc_lines_to_add = []
    
    if stc and depart and depart.date_sortie:
        try:
            exit_date = datetime.strptime(depart.date_sortie[:10], "%Y-%m-%d")
            if exit_date.year == annee and exit_date.month == mois:
                if stc.indemnite_conges_payes and stc.indemnite_conges_payes > 0:
                    stc_gross_conges = stc.indemnite_conges_payes
                    
                if stc.indemnite_licenciement and stc.indemnite_licenciement > 0:
                    stc_net_gains += stc.indemnite_licenciement
                    stc_lines_to_add.append(
                        LigneBulletinPaie(
                            bulletin_id=bulletin.id,
                            code="INDEMNITE_LICENCIEMENT",
                            libelle="Indemnité de licenciement / rupture",
                            montant_pr=round(stc.indemnite_licenciement, 2)
                        )
                    )
                if stc.indemnite_preavis and stc.indemnite_preavis > 0:
                    stc_net_gains += stc.indemnite_preavis
                    stc_lines_to_add.append(
                        LigneBulletinPaie(
                            bulletin_id=bulletin.id,
                            code="INDEMNITE_PREAVIS",
                            libelle="Indemnité compensatrice de préavis",
                            montant_pr=round(stc.indemnite_preavis, 2)
                        )
                    )
                if stc.indemnite_autre and stc.indemnite_autre > 0:
                    stc_net_gains += stc.indemnite_autre
                    stc_lines_to_add.append(
                        LigneBulletinPaie(
                            bulletin_id=bulletin.id,
                            code="INDEMNITE_AUTRE",
                            libelle="Autre indemnité de rupture / départ",
                            montant_pr=round(stc.indemnite_autre, 2)
                        )
                    )
        except Exception as e:
            logger.error(f"Error parsing date_sortie for STC calculation: {e}")

    # Résolution net -> brut si mode_calcul == "net"
    override_val = None
    target_net = contrat.salaire_mensuel if contrat.type_salaire == "Mensuel" else contrat.salaire_horaire
    if target_net > 0 and getattr(contrat, "mode_calcul", "brut") == "net":
        low = 0.0
        high = target_net * 5.0
        if high < 1000000.0:
            high = 5000000.0

        for _ in range(50):
            mid = (low + high) / 2.0
            net = _calculate_payslip_raw(
                db, bulletin.id, contrat, etab, salarie,
                absences, heures_sup, primes, options, acompte, mid
            )
            # Add conges payes to target comparison if it's there
            if stc_gross_conges > 0:
                net += stc_gross_conges * 0.8  # approximate net part of ICP
            if abs(net - target_net) < 0.1:
                override_val = mid
                break
            if net < target_net:
                low = mid
            else:
                high = mid
        else:
            override_val = (low + high) / 2.0

    # 3. Calcul des lignes de salaire brut
    lignes_brut, salaire_brut = _calculate_gross_salary(
        bulletin.id, contrat, absences, heures_sup, primes, options,
        override_salary_value=override_val
    )
    
    # Intégrer l'indemnité compensatrice de congés payés au brut (soumise à cotisations)
    if stc_gross_conges > 0:
        lignes_brut.append(
            LigneBulletinPaie(
                bulletin_id=bulletin.id,
                code="INDEMNITE_CONGES_PAYES",
                libelle="Indemnité compensatrice de congés payés",
                montant_pr=round(stc_gross_conges, 2)
            )
        )
        salaire_brut += stc_gross_conges

    # 4. Calcul des cotisations sociales et taxes
    lignes_cotisations, cot_salariales, cot_patronales = _calculate_cnps_cotisations(db, bulletin.id, etab, contrat, salarie, salaire_brut)

    # 5. Calcul des lignes complémentaires (non-salary / allowances / post-tax deductions)
    lignes_sup = []
    transport_montant = contrat.indemnite_transport or 0.0
    if transport_montant > 0:
        lignes_sup.append(
            LigneBulletinPaie(
                bulletin_id=bulletin.id,
                code="TRANSPORT",
                libelle="Indemnité de transport",
                base_s=26.0,
                taux_s=round(transport_montant / 26.0, 2),
                montant_pr=round(transport_montant, 2)
            )
        )
        
    telephone_montant = contrat.dotation_telephonique or 0.0
    if telephone_montant > 0:
        lignes_sup.append(
            LigneBulletinPaie(
                bulletin_id=bulletin.id,
                code="TELEPHONE",
                libelle="Dotation téléphonique",
                montant_pr=round(telephone_montant, 2)
            )
        )
        
    if acompte > 0:
        lignes_sup.append(
            LigneBulletinPaie(
                bulletin_id=bulletin.id,
                code="ACOMPTE",
                libelle="Retenues divers services ex : acomptes",
                montant_cs=round(acompte, 2)
            )
        )

    # Options affecting net
    options_gains_net = 0.0
    options_deductions_net = 0.0
    for opt in options:
        val = opt.valeur_numerique or 0.0
        if opt.code.startswith("AVANTAGE_"):
            # Deduct benefit in kind from net (it's non-cash, was added to gross for tax)
            options_deductions_net += val
            lignes_sup.append(
                LigneBulletinPaie(
                    bulletin_id=bulletin.id,
                    code=f"RET_{opt.code}",
                    libelle=f"Retenue {opt.libelle or opt.code}",
                    montant_cs=round(val, 2)
                )
            )
        elif opt.code == "FRAIS_PROFESSIONNELS":
            # Non-taxable professional expense reimbursement (adds to net)
            options_gains_net += val
            lignes_sup.append(
                LigneBulletinPaie(
                    bulletin_id=bulletin.id,
                    code=opt.code,
                    libelle=opt.libelle or "Remboursement de frais",
                    montant_pr=round(val, 2)
                )
            )
        elif opt.code == "AUTRE_RETENUE":
            # Direct deduction (decreases net)
            options_deductions_net += val
            lignes_sup.append(
                LigneBulletinPaie(
                    bulletin_id=bulletin.id,
                    code=opt.code,
                    libelle=opt.libelle or "Autre retenue",
                    montant_cs=round(val, 2)
                )
            )

    # 5.5 Retenue sur prêts
    loans = db.query(PretSalarie).filter(
        PretSalarie.salarie_id == contrat.salarie_id,
        PretSalarie.reste_a_rembourser > 0
    ).all()
    
    loans_deduction = 0.0
    for loan in loans:
        deblocage_period = loan.date_deblocage.year * 12 + loan.date_deblocage.month
        current_period = annee * 12 + mois
        if deblocage_period <= current_period:
            mensualite = min(loan.montant_mensualite, loan.reste_a_rembourser)
            if mensualite > 0:
                loans_deduction += mensualite
                lignes_sup.append(
                    LigneBulletinPaie(
                        bulletin_id=bulletin.id,
                        code=f"RET_PRET_{loan.id}",
                        libelle=f"Retenue sur prêt (Reste: {loan.reste_a_rembourser - mensualite:,.0f} F CFA)",
                        montant_cs=round(mensualite, 2),
                        pret_id=loan.id
                    )
                )

    # 5.6 Ajouter les indemnités de rupture exonérées du STC
    lignes_sup.extend(stc_lines_to_add)

    # 6. Calcul des totaux nets et imposables
    net_a_payer = (
        salaire_brut
        - cot_salariales
        - acompte
        - loans_deduction
        + transport_montant
        + telephone_montant
        + options_gains_net
        - options_deductions_net
        + stc_net_gains
    )
    net_imposable = salaire_brut - (min(salaire_brut, 3375000) * 0.063) # basic net imposable (brut - retraite)
    
    # 7. Sauvegarde et persistance
    all_lines = lignes_brut + lignes_cotisations + lignes_sup
    _save_bulletin(
        db=db,
        bulletin=bulletin,
        lines=all_lines,
        salaire_brut=salaire_brut,
        cot_salariales=cot_salariales,
        cot_patronales=cot_patronales,
        net_a_payer=net_a_payer,
        net_imposable=net_imposable
    )

    return bulletin
