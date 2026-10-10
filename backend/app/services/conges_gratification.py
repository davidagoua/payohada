"""Congés payés et gratification annuelle — réglementation ivoirienne.

Textes appliqués :

* **Code du travail (loi n° 2015-532), art. 25.1 et 25.2** — acquisition de
  **2,2 jours ouvrables par mois** de service effectif, majorations
  d'ancienneté.
* **Convention collective interprofessionnelle, art. 71 et 72** — salaire
  journalier = salaire mensuel moyen / 30 ; indemnité calculée sur les jours
  **calendaires**.
* **Décret n° 98-39 du 28 janvier 1998, art. 12, 14 et 16** — allocation
  principale égale à **1/12** de la rémunération totale de la période de
  référence ; les jours restants sont valorisés au prorata.
* **Convention collective interprofessionnelle, art. 53** — gratification
  annuelle au moins égale aux **3/4 du salaire minimum conventionnel mensuel**
  de la catégorie, proratisée selon le temps de service (année de 360 jours).

Les fonctions sont pures et directement testables.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Sequence

from app.services.indemnites_rupture import _en_date, jours_service_360

# ─────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────

#: Jours ouvrables acquis par mois de service effectif.
#:
#: Le minimum légal est de 2,2 jours (Code du travail, art. 25.1). La
#: convention collective applicable en accorde 2,5 : une disposition plus
#: favorable au salarié, qui prévaut sur le minimum légal. C'est cette valeur
#: qui fait foi dans toute l'application ; elle est importée par le calcul du
#: bulletin et par l'estimation du solde de congés au départ, afin qu'une
#: modification ne puisse pas en laisser une copie divergente ailleurs.
JOURS_CONGES_PAR_MOIS = 2.5

#: Minimum légal, conservé pour référence et pour les contrôles.
JOURS_CONGES_PAR_MOIS_LEGAL = 2.2

#: Diviseur du salaire mensuel pour obtenir le salaire journalier (art. 71).
DIVISEUR_SALAIRE_JOURNALIER = 30

#: Coefficient de conversion jours ouvrables → jours calendaires.
#: 24 jours ouvrables correspondent à 30 jours calendaires (24 × 1,25 = 30).
COEFFICIENT_OUVRABLES_CALENDAIRES = 1.25

#: Fraction de la rémunération totale constituant l'allocation principale
#: (décret n° 98-39, art. 12).
FRACTION_ALLOCATION_PRINCIPALE = 1.0 / 12.0

#: Majorations d'ancienneté : (plafond d'années exclu, jours supplémentaires).
MAJORATIONS_ANCIENNETE: tuple[tuple[Optional[int], int], ...] = (
    (5, 0),
    (10, 1),
    (15, 2),
    (20, 3),
    (25, 5),
    (30, 7),
    (None, 8),
)

#: Méthodes de valorisation de l'indemnité de congés.
METHODE_CONVENTIONNELLE = "conventionnelle"
METHODE_DECRET = "decret"
METHODES_CONGEES = (METHODE_CONVENTIONNELLE, METHODE_DECRET)

#: Taux minimal de la gratification annuelle (art. 53).
TAUX_GRATIFICATION_MINIMUM = 0.75

#: Base annuelle conventionnelle pour le prorata.
BASE_ANNUELLE_JOURS = 360

#: Jours conventionnels par mois.
JOURS_CONVENTIONNELS_PAR_MOIS = 30


# ─────────────────────────────────────────────
#  CONGÉS PAYÉS
# ─────────────────────────────────────────────

def majoration_anciennete(annees_revolues: float) -> int:
    """Jours de congés supplémentaires acquis au titre de l'ancienneté.

    Barème : < 5 ans → 0 ; 5 à < 10 → 1 ; 10 à < 15 → 2 ; 15 à < 20 → 3 ;
    20 à < 25 → 5 ; 25 à < 30 → 7 ; ≥ 30 → 8.
    """
    annees = max(0.0, float(annees_revolues or 0))
    for plafond, jours in MAJORATIONS_ANCIENNETE:
        if plafond is None or annees < plafond:
            return jours
    return 0


@dataclass
class ResultatConges:
    """Droits acquis et valorisation de l'indemnité de congés payés."""
    remuneration_totale: float
    nombre_mois_remuneres: int
    salaire_mensuel_moyen: float
    salaire_journalier: float
    mois_service: float
    jours_principaux_acquis: float
    jours_supplementaires: float
    total_jours_acquis: float
    jours_pris: float
    solde_jours_ouvrables: float
    solde_jours_calendaires: float
    jours_anciennete_indicatifs: int
    #: Montant par la méthode conventionnelle (art. 71-72).
    montant_conventionnel: float
    #: Montant par la méthode du décret n° 98-39 (art. 12, 14, 16).
    montant_decret: float
    methode_retenue: str
    montant_retenu: float
    allocation_principale: float = 0.0
    comparaison: str = ""
    alertes: list[str] = field(default_factory=list)


def calculer_conges_payes(
    remunerations: Sequence[Optional[float]],
    mois_service: float,
    *,
    jours_supplementaires: float = 0.0,
    jours_pris: float = 0.0,
    anciennete_annees: float = 0.0,
    methode: str = METHODE_CONVENTIONNELLE,
    montant_manuel: Optional[float] = None,
) -> ResultatConges:
    """Calcule les droits à congés et l'indemnité correspondante.

    `remunerations` : les mois de la période de référence (les valeurs `None`
    sont ignorées). `mois_service` : mois de service effectif ouvrant droit.
    `methode` : `conventionnelle` (art. 71-72) ou `decret` (décret n° 98-39).
    `montant_manuel` : court-circuite le calcul lorsqu'un montant a déjà été
    validé par le gestionnaire.
    """
    retenues = [float(r) for r in remunerations if r is not None and r != ""]
    total = sum(retenues)
    nombre_mois = len(retenues)
    moyenne = total / nombre_mois if nombre_mois else 0.0
    journalier = moyenne / DIVISEUR_SALAIRE_JOURNALIER if moyenne else 0.0

    mois = max(0.0, float(mois_service or 0))
    principaux = mois * JOURS_CONGES_PAR_MOIS
    supplementaires = max(0.0, float(jours_supplementaires or 0))
    total_acquis = principaux + supplementaires
    pris = max(0.0, float(jours_pris or 0))
    solde_ouvrables = max(0.0, total_acquis - pris)
    solde_calendaires = solde_ouvrables * COEFFICIENT_OUVRABLES_CALENDAIRES

    # Méthode conventionnelle (art. 71-72) : journalier × jours calendaires.
    montant_conventionnel = journalier * solde_calendaires

    # Méthode du décret n° 98-39 : allocation principale = 1/12 de la
    # rémunération totale ; la part correspondant aux droits restants est
    # obtenue au prorata des jours principaux acquis.
    allocation_principale = total * FRACTION_ALLOCATION_PRINCIPALE
    montant_decret = (
        (allocation_principale / principaux) * solde_ouvrables if principaux > 0 else 0.0
    )

    if montant_conventionnel > montant_decret:
        comparaison = "Méthode conventionnelle supérieure dans cette saisie"
    elif montant_decret > montant_conventionnel:
        comparaison = "Méthode du décret supérieure dans cette saisie"
    else:
        comparaison = "Montants identiques"

    if methode not in METHODES_CONGEES:
        methode = METHODE_CONVENTIONNELLE
    montant_retenu = (
        montant_manuel if montant_manuel is not None
        else (montant_conventionnel if methode == METHODE_CONVENTIONNELLE else montant_decret)
    )

    alertes: list[str] = []
    if nombre_mois == 0:
        alertes.append("Aucune rémunération saisie sur la période de référence.")
    if mois <= 0:
        alertes.append("Le nombre de mois de service ouvrant droit au congé doit être renseigné.")
    if journalier <= 0:
        alertes.append("Le salaire journalier est nul : vérifiez les rémunérations saisies.")

    return ResultatConges(
        remuneration_totale=round(total, 2),
        nombre_mois_remuneres=nombre_mois,
        salaire_mensuel_moyen=round(moyenne, 2),
        salaire_journalier=round(journalier, 2),
        mois_service=round(mois, 2),
        jours_principaux_acquis=round(principaux, 2),
        jours_supplementaires=round(supplementaires, 2),
        total_jours_acquis=round(total_acquis, 2),
        jours_pris=round(pris, 2),
        solde_jours_ouvrables=round(solde_ouvrables, 2),
        solde_jours_calendaires=round(solde_calendaires, 2),
        jours_anciennete_indicatifs=majoration_anciennete(anciennete_annees),
        montant_conventionnel=round(montant_conventionnel, 2),
        montant_decret=round(montant_decret, 2),
        methode_retenue=methode,
        montant_retenu=round(montant_retenu, 2),
        allocation_principale=round(allocation_principale, 2),
        comparaison=comparaison,
        alertes=alertes,
    )


def droits_conges_acquis(
    mois_service: float,
    *,
    jours_supplementaires: float = 0.0,
    jours_pris: float = 0.0,
) -> dict:
    """Raccourci : droits acquis, solde ouvrable et solde calendaire."""
    principaux = max(0.0, float(mois_service or 0)) * JOURS_CONGES_PAR_MOIS
    total = principaux + max(0.0, float(jours_supplementaires or 0))
    solde = max(0.0, total - max(0.0, float(jours_pris or 0)))
    return {
        "jours_principaux_acquis": round(principaux, 2),
        "total_jours_acquis": round(total, 2),
        "solde_jours_ouvrables": round(solde, 2),
        "solde_jours_calendaires": round(solde * COEFFICIENT_OUVRABLES_CALENDAIRES, 2),
    }


# ─────────────────────────────────────────────
#  GRATIFICATION ANNUELLE (art. 53)
# ─────────────────────────────────────────────

@dataclass
class ResultatGratification:
    """Gratification annuelle (prime de fin d'année)."""
    smhc_mensuel: float
    jours_service: float
    prorata: float
    minimum_annuel_temps_plein: float
    minimum_conventionnel_proratise: float
    montant_par_taux_entreprise: float
    montant_fixe_entreprise_proratise: float
    meilleur_montant_entreprise: float
    gratification_retenue: float
    alertes: list[str] = field(default_factory=list)


def calculer_gratification(
    smhc_mensuel: float,
    jours_service: float,
    *,
    taux_entreprise: float = 0.0,
    montant_fixe_annuel_entreprise: float = 0.0,
    jours_a_deduire: float = 0.0,
) -> ResultatGratification:
    """Gratification annuelle minimale et avantages d'entreprise éventuels.

    Le minimum conventionnel ne se calcule **pas** sur le salaire réellement
    versé mais sur le **salaire minimum conventionnel mensuel de la catégorie**
    (SMHC) : `SMHC × 75 %`, proratisé au temps de service sur une base de
    360 jours. Une entreprise peut prévoir un taux supérieur ou un montant fixe ;
    le montant le plus favorable au salarié est retenu.
    """
    smhc = max(0.0, float(smhc_mensuel or 0.0))
    jours = max(0.0, float(jours_service or 0) - max(0.0, float(jours_a_deduire or 0)))
    jours = min(jours, float(BASE_ANNUELLE_JOURS))
    prorata = jours / BASE_ANNUELLE_JOURS if BASE_ANNUELLE_JOURS else 0.0

    minimum_plein = smhc * TAUX_GRATIFICATION_MINIMUM
    minimum_proratise = minimum_plein * prorata

    taux = max(0.0, float(taux_entreprise or 0.0))
    montant_taux = smhc * taux * prorata if taux > 0 else 0.0
    montant_fixe = max(0.0, float(montant_fixe_annuel_entreprise or 0.0)) * prorata
    meilleur_entreprise = max(montant_taux, montant_fixe)

    alertes: list[str] = []
    if smhc <= 0:
        alertes.append(
            "Renseignez le salaire minimum conventionnel mensuel (SMHC) de la "
            "catégorie : la gratification ne peut pas être calculée sans lui."
        )
    if jours <= 0:
        alertes.append("Aucun temps de service retenu sur l'année de référence.")

    return ResultatGratification(
        smhc_mensuel=round(smhc, 2),
        jours_service=round(jours, 2),
        prorata=round(prorata, 6),
        minimum_annuel_temps_plein=round(minimum_plein, 2),
        minimum_conventionnel_proratise=round(minimum_proratise, 2),
        montant_par_taux_entreprise=round(montant_taux, 2),
        montant_fixe_entreprise_proratise=round(montant_fixe, 2),
        meilleur_montant_entreprise=round(meilleur_entreprise, 2),
        gratification_retenue=round(max(minimum_proratise, meilleur_entreprise), 2),
        alertes=alertes,
    )


def jours_service_annuels(
    date_embauche,
    date_sortie,
    annee: int,
) -> int:
    """Jours de service retenus dans `annee`, bornés à 360.

    La période prise en compte va du 1er janvier (ou de l'embauche si elle est
    postérieure) au 31 décembre (ou à la sortie si elle est antérieure).
    """
    debut = _en_date(date_embauche)
    sortie = _en_date(date_sortie)
    premier = date(annee, 1, 1)
    dernier = date(annee, 12, 31)

    borne_debut = max(debut, premier) if debut else premier
    borne_fin = min(sortie, dernier) if sortie else dernier

    if borne_fin < borne_debut:
        return 0
    return min(jours_service_360(borne_debut, borne_fin), BASE_ANNUELLE_JOURS)


def jours_depuis_mois(mois: float) -> float:
    """Convertit un nombre de mois en jours conventionnels (30 jours/mois)."""
    return max(0.0, float(mois or 0.0)) * JOURS_CONVENTIONNELS_PAR_MOIS
