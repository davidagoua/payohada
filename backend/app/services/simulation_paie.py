"""Simulation d'un bulletin de paie en mémoire (aucune donnée persistée)."""
from sqlalchemy.orm import Session

from app.models.models import Constante
from app.schemas.bulletin import BulletinCumuls, BulletinCumulRow, LigneSimulationOut, SimulationInput, SimulationOut
from app.services.payroll import calculer_its, resoudre_brut_et_sursalaire


def _simuler_noyau(
    sim_in: SimulationInput,
    base_val: float,
    db: Session
) -> tuple:
    unite = sim_in.unite_temps or "Heures"

    # 1. Montant saisi, puis décomposition du brut : le montant porté au contrat
    #    est déjà le salaire brut, le sursalaire en est une composante.
    if unite == "Jours":
        base_standard = 30.0
    else:
        base_standard = sim_in.horaire_mensuel_standard or 173.33

    salaire_brut_reference, salaire_base_brut, sursalaire_brut = resoudre_brut_et_sursalaire(
        unite=unite,
        type_salaire=sim_in.type_salaire,
        base_standard=base_standard,
        montant_saisi=base_val,
        sursalaire_contrat=sim_in.sursalaire or 0.0,
    )
    taux_base = (salaire_brut_reference / base_standard) if base_standard > 0 else 0.0
    taux_base_affiche = (salaire_base_brut / base_standard) if base_standard > 0 else 0.0

    lignes = []

    # Ligne 1 : Salaire de base
    lignes.append(
        LigneSimulationOut(
            code="BASE",
            libelle="Salaire de base",
            salaire_base=round(salaire_base_brut, 2),
            base_s=base_standard,
            taux_s=round(taux_base_affiche, 2),
            montant_pr=round(salaire_base_brut, 2)
        )
    )

    # 2. Sursalaire : complément déjà compris dans le brut ci-dessus
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
            # Le taux journalier est celui du brut contractuel, sursalaire inclus.
            taux_abs = salaire_brut_reference / 30.0 if base_standard else 0.0
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
                    libelle="Jours congés pris" if unite == "Jours" else "Heures congés pris",
                    salaire_base=round(deduction, 2),
                    base_s=heures_jours_abs,
                    taux_s=round(taux_abs, 2),
                    montant_pr=round(deduction, 2)
                )
            )
            lignes.append(
                LigneSimulationOut(
                    code=f"ABS_{absence.code.upper()}",
                    libelle="Absences congés pris",
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
                    libelle="Absence non rémunérée",
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
        has_base_rate = prime.base is not None and prime.taux is not None
        lignes.append(
            LigneSimulationOut(
                code=prime.code.upper(),
                libelle=prime.libelle or f"Prime {prime.code}",
                salaire_base=round(prime.base if has_base_rate else prime.montant, 2),
                base_s=round(prime.base, 2) if has_base_rate else None,
                taux_s=round(prime.taux, 4) if has_base_rate else None,
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

    # ITS : même règle que le moteur de paie — base = brut imposable (la part
    # salariale CNPS/CMU n'est plus déductible depuis la réforme de 2024),
    # barème progressif puis RICF selon la situation familiale.
    ricf_par_part = abs(get_val("RICF_MONTANT", -11000.0))
    net_imposable = max(0.0, salaire_brut)
    ibs_montant, parts_its, ricf_applicable = calculer_its(
        net_imposable,
        sim_in.situation_matrimoniale,
        sim_in.enfants_charge,
        ricf_par_part,
    )
    ricf_montant = -ricf_applicable
    parts_str = f"{parts_its:.1f}".rstrip('0').rstrip('.')

    cn_taux_p = get_val("CN_TAUX_P_EXP", 8.0) if sim_in.expatrie else get_val("CN_TAUX_P_LOC", 1.5)
    ta_taux_p = get_val("TA_TAUX_P", 0.4)
    tfc_taux_p = get_val("TFC_TAUX_P", 0.6)

    # 1. IBS
    lignes.append(
        LigneSimulationOut(
            code="IBS",
            libelle="Impôt brut sur salaire",
            base_s=round(net_imposable, 2),
            taux_s=0.0,
            montant_cs=round(ibs_montant, 2)
        )
    )
    cotisations_salariales_totales += ibs_montant

    # 2. RICF
    lignes.append(
        LigneSimulationOut(
            code="RICF",
            libelle=f"Réduction d'impôt charge familiale ({parts_str} part{'s' if parts_its > 1 else ''})",
            base_s=round(net_imposable, 2),
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

    net_a_payer = salaire_brut - cotisations_salariales_totales - acompte + transport_montant + telephone_montant
    return (
        lignes,
        salaire_brut,
        cotisations_salariales_totales,
        cotisations_patronales_totales,
        net_a_payer,
        ibs_montant,
        ricf_montant,
        cmu_salariale,
        montant_retraite_s
    )


def simuler_bulletin(sim_in: SimulationInput, db: Session) -> SimulationOut:
    """Simule en mémoire un bulletin (zone UEMOA) sans rien persister.

    En mode `net` ou `brut`, le montant de base est recherché par dichotomie
    jusqu'à atteindre la cible. Lève `ValueError` si la saisie est invalide.
    """
    unite = sim_in.unite_temps or "Heures"
    base_standard = sim_in.horaire_mensuel_standard or 173.33

    # Resolve gross value based on mode_calcul (brut or net)
    if sim_in.mode_calcul == "net":
        target_net = sim_in.salaire_mensuel if sim_in.type_salaire == "Mensuel" else sim_in.salaire_horaire
        if target_net <= 0:
            raise ValueError("Le salaire net cible doit être supérieur à 0.")

        # Dichotomic solver for base_val
        low = 0.0
        high = target_net * 5.0
        if high < 1000000.0:
            high = 5000000.0

        base_val = 0.0
        for _ in range(50):
            mid = (low + high) / 2.0
            _, _, _, _, net, _, _, _, _ = _simuler_noyau(sim_in, mid, db)
            if abs(net - target_net) < 0.1:
                base_val = mid
                break
            if net < target_net:
                low = mid
            else:
                high = mid
        else:
            base_val = (low + high) / 2.0
    elif sim_in.mode_calcul == "brut":
        target_gross = sim_in.salaire_mensuel if sim_in.type_salaire == "Mensuel" else sim_in.salaire_horaire
        if target_gross <= 0:
            raise ValueError("Le salaire brut cible doit être supérieur à 0.")

        # Dichotomic solver for base_val to match target_gross
        low = 0.0
        high = target_gross * 5.0
        if high < 1000000.0:
            high = 5000000.0

        base_val = 0.0
        for _ in range(50):
            mid = (low + high) / 2.0
            _, gross, _, _, _, _, _, _, _ = _simuler_noyau(sim_in, mid, db)
            if abs(gross - target_gross) < 0.1:
                base_val = mid
                break
            if gross < target_gross:
                low = mid
            else:
                high = mid
        else:
            base_val = (low + high) / 2.0
    else:
        base_val = sim_in.salaire_mensuel if sim_in.type_salaire == "Mensuel" else sim_in.salaire_horaire

    # Run core calculation with resolved base_val
    (
        lignes,
        salaire_brut,
        cotisations_salariales_totales,
        cotisations_patronales_totales,
        net_a_payer,
        ibs_montant,
        ricf_montant,
        cmu_salariale,
        montant_retraite_s
    ) = _simuler_noyau(sim_in, base_val, db)

    # Base de l'ITS exposée au client : le brut imposable (réforme 2024).
    net_imposable = salaire_brut

    # Calculer les cumuls pour la simulation
    jours_absences = sum(line.base_s for line in lignes if line.code and line.code.startswith("ABS_") and line.base_s is not None)
    heures_supp = sum(line.base_s for line in lignes if line.code and line.code.startswith("HS_") and line.base_s is not None)
    
    if unite == "Jours":
        heures_jours = 30.0 - jours_absences
    else:
        heures_jours = base_standard - jours_absences + heures_supp

    cnps_line = next((line for line in lignes if line.code == "CNPS_RETRAITE"), None)
    brut_cnps = cnps_line.base_s if (cnps_line and cnps_line.base_s is not None) else salaire_brut
    
    cumul_row_data = {
        "heures_jours": round(heures_jours, 2),
        "heures_supp": round(heures_supp, 2),
        "jours_absences": round(jours_absences, 2),
        "salaire_brut": round(salaire_brut, 2),
        "brut_imposable": round(net_imposable, 2),
        "brut_cnps": round(brut_cnps, 2),
        "brut_conges": round(salaire_brut, 2),
        "ibs": round(ibs_montant, 2),
        "ricf": round(abs(ricf_montant), 2),
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
