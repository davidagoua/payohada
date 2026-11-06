"""Cumuls mensuels et annuels d'un bulletin de paie, calculés à la volée."""
import re

from sqlalchemy.orm import Session

from app.models.models import BulletinPaie, VariableRepriseDossier
from app.schemas.bulletin import BulletinCumuls, BulletinCumulRow
from app.services.conges_gratification import JOURS_CONGES_PAR_MOIS

#: Motif des codes d'heures supplémentaires : HS15, HS_15, HS-15, HS_100…
_HS_CODE_RE = re.compile(r"^HS[_\-\s]?\d+", re.IGNORECASE)


def compute_bulletin_cumuls(db: Session, bulletin: BulletinPaie) -> BulletinCumuls:
    """Calcule dynamiquement les cumuls mensuels et annuels pour un bulletin donné."""
    contrat = bulletin.contrat
    unite = contrat.unite_temps or "Heures"
    
    def get_row_values(b: BulletinPaie) -> dict:
        lignes = b.lignes or []
        jours_absences = sum(line.base_s for line in lignes if line.code and line.code.startswith("ABS_") and line.base_s is not None)
        # Les codes d'heures supplémentaires varient selon l'écran de saisie
        # (HS15, HS_15, HS-15…) : on s'appuie sur un motif et non sur un
        # préfixe littéral, sinon les heures supp n'étaient jamais cumulées.
        heures_supp = sum(
            line.base_s for line in lignes
            if line.code and _HS_CODE_RE.match(line.code) and line.base_s is not None
        )
        
        if unite == "Jours":
            heures_jours = 30.0 - jours_absences
        else:
            base_standard = (contrat.horaires.horaire_travail if (contrat.horaires and contrat.horaires.horaire_travail) else 173.33)
            heures_jours = base_standard - jours_absences + heures_supp
        
        cnps_line = next((line for line in lignes if line.code == "CNPS_RETRAITE"), None)
        brut_cnps = cnps_line.base_s if (cnps_line and cnps_line.base_s is not None) else (b.salaire_brut or 0.0)
        brut_imposable = getattr(b, "net_imposable", b.salaire_brut) or (b.salaire_brut or 0.0)
        
        ibs = sum(line.montant_cs for line in lignes if line.code == "IBS" and line.montant_cs is not None)
        ricf = sum(abs(line.montant_cs) for line in lignes if line.code == "RICF" and line.montant_cs is not None)
        cmu = sum(line.montant_cs for line in lignes if line.code == "CMU_S" and line.montant_cs is not None)
        cot_retraite = sum(line.montant_cs for line in lignes if line.code == "CNPS_RETRAITE" and line.montant_cs is not None)
        
        return {
            "heures_jours": round(heures_jours, 2),
            "heures_supp": round(heures_supp, 2),
            "jours_absences": round(jours_absences, 2),
            "salaire_brut": round(b.salaire_brut or 0.0, 2),
            "brut_imposable": round(brut_imposable, 2),
            "brut_cnps": round(brut_cnps, 2),
            "brut_conges": round(b.salaire_brut or 0.0, 2),
            "ibs": round(ibs, 2),
            "ricf": round(ricf, 2),
            "cmu": round(cmu, 2),
            "cot_retraite": round(cot_retraite, 2)
        }

    mensuel_data = get_row_values(bulletin)

    # Congés payés : le calcul vit dans `services.conges`, partagé avec
    # l'estimation du départ et l'espace salarié.
    from app.services.conges import solde_conges

    conges = solde_conges(db, contrat, bulletin.annee, bulletin.mois)
    months_seniority = conges.mois_anciennete
    periode_avant_contrat = conges.periode_avant_contrat
    debut_anciennete = conges.debut_anciennete.isoformat()
    
    # Récupérer tous les bulletins calculés ou validés de la même année jusqu'au mois en cours
    prior_bulletins = db.query(BulletinPaie).filter(
        BulletinPaie.contrat_id == bulletin.contrat_id,
        BulletinPaie.annee == bulletin.annee,
        BulletinPaie.mois <= bulletin.mois,
        (BulletinPaie.statut.in_(["calcule", "valide"]) | (BulletinPaie.id == bulletin.id))
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

    # Prise en compte des cumuls de reprise (migration de dossier en cours d'année)
    reprises = db.query(VariableRepriseDossier).filter(
        VariableRepriseDossier.contrat_id == bulletin.contrat_id,
        VariableRepriseDossier.annee == str(bulletin.annee)
    ).all()

    reprise_map = {
        "CUMUL_BRUT": "salaire_brut",
        "CUMUL_BRUT_IMPOSABLE": "brut_imposable",
        "CUMUL_BRUT_CNPS": "brut_cnps",
        "CUMUL_BRUT_CONGES": "brut_conges",
        "CUMUL_IBS": "ibs",
        "CUMUL_RICF": "ricf",
        "CUMUL_CMU": "cmu",
        "CUMUL_RETRAITE": "cot_retraite",
        "CUMUL_CNPS_RETRAITE": "cot_retraite",
        "CUMUL_HEURES": "heures_jours",
        "CUMUL_JOURS": "heures_jours",
        "CUMUL_HEURES_SUPP": "heures_supp",
        "CUMUL_ABSENCES": "jours_absences"
    }

    for rep in reprises:
        target_key = reprise_map.get(rep.code.upper() if rep.code else "")
        if target_key and target_key in annuel_totals and rep.valeur:
            annuel_totals[target_key] += rep.valeur
            
    for k in annuel_totals.keys():
        annuel_totals[k] = round(annuel_totals[k], 2)
        
    annuel_totals["conges_acquis"] = conges.acquis
    annuel_totals["conges_pris"] = conges.pris
    annuel_totals["conges_solde"] = conges.solde

    mensuel_data["conges_acquis"] = JOURS_CONGES_PAR_MOIS
    mensuel_data["conges_pris"] = conges.pris_ce_mois
    mensuel_data["conges_solde"] = conges.solde
        
    return BulletinCumuls(
        mensuel=BulletinCumulRow(**mensuel_data),
        annuel=BulletinCumulRow(**annuel_totals),
        mois_anciennete=months_seniority,
        debut_anciennete=debut_anciennete,
        periode_avant_contrat=periode_avant_contrat,
    )
