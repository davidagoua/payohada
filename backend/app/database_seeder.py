"""Peuplement initial (idempotent) des référentiels de paie.

Ce module insère les constantes et le plan de paie **uniquement s'ils sont
absents** : une valeur modifiée par un administrateur n'est jamais écrasée au
redémarrage de l'application.
"""
import logging

from sqlalchemy.orm import Session

from app.models.models import Constante, PlanPaie

logger = logging.getLogger(__name__)


#: Valeurs de référence Côte d'Ivoire (FCFA / %), modifiables via /constantes.
CONSTANTES_REFERENCE = [
    {"code": "SMIG", "description": "Salaire Minimum Interprofessionnel Garanti", "montant": 75000.0, "unite": "FCFA", "pays": "CI"},
    {"code": "CNPS_PF_PLAFOND", "description": "Plafond mensuel pour les Prestations Familiales", "montant": 70000.0, "unite": "FCFA", "pays": "CI"},
    {"code": "CNPS_PF_TAUX_P", "description": "Taux patronal Prestations Familiales", "montant": 5.0, "unite": "%", "pays": "CI"},
    {"code": "CNPS_RETRAITE_PLAFOND", "description": "Plafond mensuel pour la Retraite", "montant": 3375000.0, "unite": "FCFA", "pays": "CI"},
    {"code": "CNPS_RETRAITE_TAUX_S", "description": "Taux salarial Retraite", "montant": 6.3, "unite": "%", "pays": "CI"},
    {"code": "CNPS_RETRAITE_TAUX_P", "description": "Taux patronal Retraite", "montant": 7.7, "unite": "%", "pays": "CI"},
    {"code": "CNPS_AT_PLAFOND", "description": "Plafond mensuel Accident du Travail", "montant": 70000.0, "unite": "FCFA", "pays": "CI"},
    {"code": "CNPS_MATERNITE_PLAFOND", "description": "Plafond mensuel Assurance Maternité", "montant": 70000.0, "unite": "FCFA", "pays": "CI"},
    {"code": "CNPS_MATERNITE_TAUX_P", "description": "Taux patronal Assurance Maternité", "montant": 0.75, "unite": "%", "pays": "CI"},
    {"code": "CN_TAUX_P_LOC", "description": "Taux Contribution Nationale patronale locaux", "montant": 1.5, "unite": "%", "pays": "CI"},
    {"code": "CN_TAUX_P_EXP", "description": "Taux Contribution Nationale patronale expatriés", "montant": 8.0, "unite": "%", "pays": "CI"},
    {"code": "TA_TAUX_P", "description": "Taux Taxe Apprentissage patronale", "montant": 0.4, "unite": "%", "pays": "CI"},
    {"code": "TFC_TAUX_P", "description": "Taux Taxe Formation Continue patronale", "montant": 0.6, "unite": "%", "pays": "CI"},
    {"code": "CMU_MONTANT_S", "description": "Montant CMU part salariale", "montant": 500.0, "unite": "FCFA", "pays": "CI"},
    {"code": "CMU_MONTANT_P", "description": "Montant CMU part patronale", "montant": 500.0, "unite": "FCFA", "pays": "CI"},
    {"code": "RICF_MONTANT", "description": "Réduction d'impôt pour charge familiale, par part", "montant": -11000.0, "unite": "FCFA", "pays": "CI"},
]

PLAN_PAIE_REFERENCE = [
    {"code": "BASE", "type": "B", "libelle": "Salaire de base", "mode_calcul": "Manuel", "sens": "Gain", "pays": "CI"},
    {"code": "SURSALAIRE", "type": "B", "libelle": "Sursalaire", "mode_calcul": "Manuel", "sens": "Gain", "pays": "CI"},
    {"code": "ABS", "type": "B", "libelle": "Absence", "mode_calcul": "Sémi-auto", "sens": "Retenue", "pays": "CI"},
    {"code": "HS_15", "type": "B", "libelle": "Heures supplémentaires majorées à 15%", "mode_calcul": "Sémi-auto", "sens": "Gain", "pays": "CI"},
    {"code": "HS_25", "type": "B", "libelle": "Heures supplémentaires majorées à 25%", "mode_calcul": "Sémi-auto", "sens": "Gain", "pays": "CI"},
    {"code": "HS_50", "type": "B", "libelle": "Heures supplémentaires majorées à 50%", "mode_calcul": "Sémi-auto", "sens": "Gain", "pays": "CI"},
    {"code": "HS_75", "type": "B", "libelle": "Heures supplémentaires majorées à 75%", "mode_calcul": "Sémi-auto", "sens": "Gain", "pays": "CI"},
    {"code": "HS_100", "type": "B", "libelle": "Heures supplémentaires majorées à 100%", "mode_calcul": "Sémi-auto", "sens": "Gain", "pays": "CI"},
    {"code": "IBS", "type": "I", "libelle": "Impôt brut sur salaire", "mode_calcul": "Auto", "sens": "Retenue", "pays": "CI"},
    {"code": "RICF", "type": "I", "libelle": "Réduction d'impôt pour charge familiale", "mode_calcul": "Auto", "sens": "Gain", "pays": "CI"},
    {"code": "CNPS_PF", "type": "I", "libelle": "CNPS - Prestations Familiales", "mode_calcul": "Auto", "sens": "Retenue", "pays": "CI"},
    {"code": "CNPS_RETRAITE", "type": "I", "libelle": "CNPS - Retraite", "mode_calcul": "Auto", "sens": "Retenue", "pays": "CI"},
    {"code": "CNPS_AT", "type": "I", "libelle": "CNPS - Accidents du Travail et Maladies Pro.", "mode_calcul": "Auto", "sens": "Retenue", "pays": "CI"},
    {"code": "CNPS_MATERNITE", "type": "I", "libelle": "CNPS - Assurance Maternité", "mode_calcul": "Auto", "sens": "Retenue", "pays": "CI"},
    {"code": "CMU_S", "type": "I", "libelle": "Cotisation CMU part salariale", "mode_calcul": "Auto", "sens": "Retenue", "pays": "CI"},
    {"code": "CMU_P", "type": "C", "libelle": "Cotisation CMU part patronale", "mode_calcul": "Auto", "sens": "Charge", "pays": "CI"},
    {"code": "CN", "type": "C", "libelle": "Contribution nationale", "mode_calcul": "Auto", "sens": "Charge", "pays": "CI"},
    {"code": "TA", "type": "C", "libelle": "Taxe d'apprentissage", "mode_calcul": "Auto", "sens": "Charge", "pays": "CI"},
    {"code": "TFC", "type": "C", "libelle": "Taxe Formation continue", "mode_calcul": "Auto", "sens": "Charge", "pays": "CI"},
    {"code": "TRANSPORT", "type": "A", "libelle": "Indemnité de transport", "mode_calcul": "Sémi-auto", "sens": "Gain", "pays": "CI"},
    {"code": "TELEPHONE", "type": "A", "libelle": "Dotation téléphonique", "mode_calcul": "Sémi-auto", "sens": "Gain", "pays": "CI"},
]


def seed_database(db: Session) -> bool:
    """Insère les constantes et le plan de paie manquants.

    Retourne `True` si au moins une ligne a été créée.
    """
    created = False

    for item in CONSTANTES_REFERENCE:
        existing = db.query(Constante).filter(
            Constante.code == item["code"],
            Constante.pays == item["pays"],
        ).first()
        if not existing:
            db.add(Constante(**item))
            created = True

    for item in PLAN_PAIE_REFERENCE:
        existing = db.query(PlanPaie).filter(
            PlanPaie.code == item["code"],
            PlanPaie.pays == item["pays"],
        ).first()
        if not existing:
            db.add(PlanPaie(**item))
            created = True

    if created:
        db.commit()
        logger.info("Référentiels de paie initialisés (constantes + plan de paie).")

    return created
