import logging
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.models import (
    Contrat, BulletinPaie, LigneBulletinPaie, VariableBulletin,
    Absence, HeureSupplementaire, Prime, Option, CaisseCotisation, Etablissement, Constante, Salarie
)

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

    heures_sup = db.query(HeureSupplementaire).filter(
        HeureSupplementaire.contrat_id == contrat_id,
        HeureSupplementaire.annee == str(annee),
        HeureSupplementaire.mois == mois
    ).all()

    primes = db.query(Prime).filter(
        Prime.contrat_id == contrat_id,
        Prime.annee == str(annee),
        Prime.mois == mois
    ).all()

    options = db.query(Option).filter(
        Option.contrat_id == contrat_id,
        Option.annee == str(annee),
        Option.mois == mois
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
    options: list[Option] = []
) -> tuple[list[LigneBulletinPaie], float]:
    """Calcule le salaire de base, le sursalaire, applique les absences, heures supps, primes et calcule le Salaire Brut."""
    unite = contrat.unite_temps or "Heures"
    
    # 1. Base Salary
    if unite == "Jours":
        base_standard = 30.0
        salaire_base_brut = contrat.salaire_mensuel or 0.0
        taux_base = (salaire_base_brut / 30.0) if salaire_base_brut > 0 else 0.0
    else:
        base_standard = contrat.horaires.horaire_travail if (contrat.horaires and contrat.horaires.horaire_travail) else 173.33
        if contrat.type_salaire == "Mensuel":
            salaire_base_brut = contrat.salaire_mensuel or 0.0
            taux_base = (salaire_base_brut / base_standard) if base_standard > 0 else 0.0
        else:
            taux_base = contrat.salaire_horaire or 0.0
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

    # 1. IBS
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="IBS",
            libelle="Impôt brut sur salaire",
            base_s=round(salaire_brut, 2),
            taux_s=0.0,
            montant_cs=round(ibs_montant, 2)
        )
    )
    cotisations_salariales_totales += ibs_montant

    # 2. RICF
    lignes_cotisations.append(
        LigneBulletinPaie(
            bulletin_id=bulletin_id,
            code="RICF",
            libelle="Réduction d'impôt pour charge familiale",
            base_s=round(salaire_brut, 2),
            taux_s=0.0,
            montant_cs=round(ricf_montant, 2) # stored as negative in deductions
        )
    )
    cotisations_salariales_totales += ricf_montant

    # 3. CNPS Retraite Salariale & Patronale
    base_retraite = min(salaire_brut, cnps_retraite_plafond) if salaire_brut > 0 else 0.0
    montant_retraite_s = base_retraite * (cnps_retraite_taux_s / 100.0)
    montant_retraite_p = base_retraite * (cnps_retraite_taux_p / 100.0)
    cotisations_salariales_totales += montant_retraite_s
    cotisations_patronales_totales += montant_retraite_p
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


def calculate_payslip(db: Session, contrat_id: int, mois: int, annee: int, acompte: float = 0.0) -> BulletinPaie:
    """
    Calcule le bulletin de paie pour un contrat donné, un mois et une année.
    Si le bulletin existe déjà, il est recalculé et mis à jour.
    """
    # 1. Récupération des données d'entrée
    contrat, etab, salarie, absences, heures_sup, primes, options = _get_payroll_inputs(db, contrat_id, mois, annee)

    # 2. Récupération ou création du bulletin de paie
    bulletin = _get_or_create_bulletin(db, contrat_id, contrat.dossier_id, mois, annee)

    # 3. Calcul des lignes de salaire brut
    lignes_brut, salaire_brut = _calculate_gross_salary(bulletin.id, contrat, absences, heures_sup, primes, options)

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

    # 6. Calcul des totaux nets et imposables
    net_a_payer = (
        salaire_brut
        - cot_salariales
        - acompte
        + transport_montant
        + telephone_montant
        + options_gains_net
        - options_deductions_net
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
