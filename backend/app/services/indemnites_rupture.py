"""Indemnités de rupture et de décès — réglementation ivoirienne.

Textes appliqués :

* **Décret n° 2017-210 du 30 mars 2017** (qui abroge le décret n° 96-201 du
  7 mars 1996) — indemnité de licenciement et de départ à la retraite :
  - art. 2 : au moins **un an de service effectif** et **absence de faute lourde** ;
  - art. 4 et 5 : barème **30 %** jusqu'à 5 ans, **35 %** de 6 à 10 ans,
    **40 %** au-delà, sur le **salaire global mensuel moyen des 12 mois** ;
    les fractions d'année sont retenues en **mois complets** (mois inférieur) ;
  - art. 5 : le départ à la retraite est indemnisé dans les conditions de
    l'article 4 ;
  - frais funéraires (décès) : **3 ×** le SMHC jusqu'à 5 ans, **4 ×** de 6 à
    10 ans, **6 ×** au-delà.

* **Code du travail (loi n° 2015-532), art. 15.8** — indemnité de fin de CDD :
  **3 %** du total des rémunérations brutes perçues pendant le contrat.

Toutes les fonctions de ce module sont **pures** : aucune dépendance à la base
de données ni à la session HTTP. Elles sont donc directement testables.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Sequence

# ─────────────────────────────────────────────
#  CONSTANTES RÉGLEMENTAIRES
# ─────────────────────────────────────────────

#: Barème de l'article 4 : (borne cumulée en mois, taux). La dernière tranche
#: n'a pas de borne.
BAREME_RUPTURE: tuple[tuple[Optional[int], float], ...] = (
    (60, 0.30),    # 1re à 5e année
    (120, 0.35),   # 6e à 10e année
    (None, 0.40),  # au-delà de 10 ans
)

#: Ancienneté minimale ouvrant droit à l'indemnité (art. 2), en mois.
ANCIENNETE_MINIMUM_MOIS = 12

#: Limites des tranches pour les frais funéraires, en mois.
LIMITE_FRAIS_FUNERAIRES_TRANCHE_1 = 60    # 5 ans
LIMITE_FRAIS_FUNERAIRES_TRANCHE_2 = 120   # 10 ans

#: Multiplicateurs des frais funéraires appliqués au SMHC mensuel.
MULTIPLICATEURS_FRAIS_FUNERAIRES = {
    "jusqu_a_5_ans": 3,
    "de_6_a_10_ans": 4,
    "au_dela_de_10_ans": 6,
}

#: Taux légal de l'indemnité de fin de CDD (art. 15.8).
TAUX_FIN_CDD = 0.03

#: Motifs pour lesquels l'indemnité de fin de CDD n'est pas due.
MOTIFS_EXCLUSION_FIN_CDD = {
    "refus_cdi_equivalent": (
        "Refus d'un CDI pour le même emploi ou un emploi similaire "
        "à rémunération au moins équivalente"
    ),
    "rupture_initiative_salarie": "Rupture anticipée à l'initiative du salarié",
    "faute_lourde": "Rupture consécutive à une faute lourde du salarié",
    "cdi_conclu": "Un CDI a été conclu à l'issue du CDD",
}

#: Motifs pour lesquels l'indemnité de fin de CDD est due sans réserve.
MOTIFS_FIN_CDD_DUE = {
    "terme_normal_sans_cdi": "Terme normal du contrat, sans conclusion d'un CDI",
}

#: Motifs nécessitant une vérification juridique manuelle.
MOTIFS_FIN_CDD_A_VERIFIER = {
    "autre": "Situation particulière à vérifier juridiquement",
}


# ─────────────────────────────────────────────
#  OUTILS DE DATE
# ─────────────────────────────────────────────

def _en_date(valeur) -> Optional[date]:
    """Convertit une date, un datetime ou une chaîne ISO en `date`."""
    if valeur is None or valeur == "":
        return None
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    if isinstance(valeur, str):
        try:
            return datetime.strptime(valeur[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def anciennete_en_mois(debut, fin) -> int:
    """Ancienneté en **mois complets**, arrondie au mois inférieur.

    Reproduit la sémantique de `DATEDIF(debut; fin; "m")`, retenue par le
    décret n° 2017-210 (art. 4) : un mois n'est compté que s'il est révolu.
    """
    d, f = _en_date(debut), _en_date(fin)
    if d is None or f is None or f < d:
        return 0
    mois = (f.year - d.year) * 12 + (f.month - d.month)
    if f.day < d.day:
        mois -= 1
    return max(0, mois)


def jours_service_360(debut, fin) -> int:
    """Jours de service en **année commerciale de 360 jours** (12 × 30).

    Utilisé pour le prorata de la gratification annuelle :
    `(années × 360) + (mois × 30) + (jours plafonnés à 30)`, bornes incluses.
    """
    d, f = _en_date(debut), _en_date(fin)
    if d is None or f is None or f < d:
        return 0
    jours = (
        (f.year - d.year) * 360
        + (f.month - d.month) * 30
        + (min(f.day, 30) - min(d.day, 30))
        + 1
    )
    return max(0, jours)


# ─────────────────────────────────────────────
#  INDEMNITÉ DE LICENCIEMENT / DÉPART À LA RETRAITE
# ─────────────────────────────────────────────

@dataclass
class TrancheIndemnite:
    """Détail d'une tranche du barème (pour affichage sur le bulletin de STC)."""
    libelle: str
    mois_retenus: float
    annees_equivalentes: float
    taux: float
    salaire_reference: float
    montant: float


@dataclass
class ResultatIndemniteRupture:
    """Résultat d'un calcul d'indemnité de licenciement ou de retraite."""
    anciennete_mois: int
    anciennete_annees: float
    salaire_global_moyen: float
    total_salaires_retenus: float
    nombre_salaires_retenus: int
    eligible: bool
    motif_ineligibilite: Optional[str]
    tranches: list[TrancheIndemnite] = field(default_factory=list)
    montant: float = 0.0


def salaire_global_moyen(salaires: Sequence[Optional[float]]) -> tuple[float, float, int]:
    """Moyenne des salaires renseignés.

    Retourne `(moyenne, total, nombre_de_mois_retenus)`. Les mois laissés à
    `None` ou vides sont ignorés — c'est le mécanisme des colonnes « À inclure ? »
    des classeurs, où l'utilisateur peut écarter un mois atypique.
    """
    retenus = [float(s) for s in salaires if s is not None and s != ""]
    if not retenus:
        return 0.0, 0.0, 0
    return sum(retenus) / len(retenus), sum(retenus), len(retenus)


def calculer_indemnite_rupture(
    salaires_12_mois: Sequence[Optional[float]],
    anciennete_mois: int,
    *,
    faute_lourde: bool = False,
    depart_retraite: bool = False,
    anciennete_minimum_requise: bool = True,
) -> ResultatIndemniteRupture:
    """Indemnité de licenciement (art. 4) ou de départ à la retraite (art. 5).

    Le barème est appliqué par tranches d'ancienneté sur le **salaire global
    mensuel moyen des 12 derniers mois** :

    * 1re à 5e année  : mois retenus / 12 × 30 %
    * 6e à 10e année  : idem × 35 %
    * au-delà de 10 ans : idem × 40 %

    Les fractions d'année sont converties en **années équivalentes**
    (`mois / 12`), ce qui autorise des tranches partielles.
    """
    moyenne, total, nombre = salaire_global_moyen(salaires_12_mois)
    mois = max(0, int(anciennete_mois or 0))

    resultat = ResultatIndemniteRupture(
        anciennete_mois=mois,
        anciennete_annees=round(mois / 12, 4),
        salaire_global_moyen=round(moyenne, 2),
        total_salaires_retenus=round(total, 2),
        nombre_salaires_retenus=nombre,
        eligible=False,
        motif_ineligibilite=None,
    )

    # Contrôles d'éligibilité (art. 2)
    if faute_lourde:
        resultat.motif_ineligibilite = (
            "Faute lourde retenue : aucune indemnité n'est due (art. 2)."
        )
        return resultat

    if anciennete_minimum_requise and mois < ANCIENNETE_MINIMUM_MOIS:
        resultat.motif_ineligibilite = (
            f"Ancienneté de {mois} mois inférieure au minimum d'un an (art. 2)."
        )
        return resultat

    if not anciennete_minimum_requise and mois <= 0:
        # Aucun droit calculable sans ancienneté, même si les conditions de
        # retraite sont remplies.
        resultat.motif_ineligibilite = "Aucune ancienneté acquise."
        return resultat

    # Calcul par tranches
    libelles = ("1re à 5e année", "6e à 10e année", "Au-delà de 10 ans")
    borne_precedente = 0
    montant_total = 0.0

    for index, (borne, taux) in enumerate(BAREME_RUPTURE):
        if borne is None:
            mois_tranche = max(0, mois - borne_precedente)
        else:
            mois_tranche = max(0, min(mois, borne) - borne_precedente)
        borne_precedente = borne if borne is not None else borne_precedente

        annees = mois_tranche / 12.0
        montant = annees * taux * moyenne
        montant_total += montant

        resultat.tranches.append(TrancheIndemnite(
            libelle=libelles[index],
            mois_retenus=mois_tranche,
            annees_equivalentes=round(annees, 4),
            taux=taux,
            salaire_reference=round(moyenne, 2),
            montant=round(montant, 2),
        ))

    resultat.eligible = True
    resultat.montant = round(montant_total, 2)
    if depart_retraite:
        # L'article 5 renvoie aux conditions de l'article 4 : le calcul est
        # identique, seul le motif diffère.
        pass
    return resultat


# ─────────────────────────────────────────────
#  INDEMNITÉ DE DÉCÈS
# ─────────────────────────────────────────────

@dataclass
class ResultatIndemniteDeces:
    """Indemnité de décès et participation aux frais funéraires."""
    anciennete_mois: int
    salaire_global_moyen: float
    eligible: bool
    motif_eligibilite: str
    indemnite_rupture: float
    tranches: list[TrancheIndemnite] = field(default_factory=list)
    multiplicateur_frais_funeraires: int = 0
    smhc_mensuel: float = 0.0
    frais_funeraires: float = 0.0
    total: float = 0.0


def multiplicateur_frais_funeraire(anciennete_mois: int) -> int:
    """3 × le SMHC jusqu'à 5 ans, 4 × de 6 à 10 ans, 6 × au-delà."""
    if anciennete_mois <= LIMITE_FRAIS_FUNERAIRES_TRANCHE_1:
        return MULTIPLICATEURS_FRAIS_FUNERAIRES["jusqu_a_5_ans"]
    if anciennete_mois <= LIMITE_FRAIS_FUNERAIRES_TRANCHE_2:
        return MULTIPLICATEURS_FRAIS_FUNERAIRES["de_6_a_10_ans"]
    return MULTIPLICATEURS_FRAIS_FUNERAIRES["au_dela_de_10_ans"]


def calculer_indemnite_deces(
    salaires_12_mois: Sequence[Optional[float]],
    anciennete_mois: int,
    smhc_mensuel: float,
    *,
    conditions_retraite_remplies: bool = False,
) -> ResultatIndemniteDeces:
    """Droits des ayants droit en cas de décès du salarié.

    L'indemnité due est **équivalente à l'indemnité de licenciement** dès lors
    que le salarié totalise au moins un an d'ancienneté **ou** remplissait les
    conditions d'un départ à la retraite. Les frais funéraires sont calculés
    séparément, même lorsque l'indemnité n'est pas due.
    """
    mois = max(0, int(anciennete_mois or 0))
    # Les conditions de retraite remplies ouvrent le droit quelle que soit
    # l'ancienneté : le seuil d'un an ne s'applique alors pas.
    rupture = calculer_indemnite_rupture(
        salaires_12_mois,
        mois,
        anciennete_minimum_requise=not conditions_retraite_remplies,
    )

    eligible = mois >= ANCIENNETE_MINIMUM_MOIS or (
        conditions_retraite_remplies and mois > 0
    )
    if eligible:
        motif = (
            "Conditions de départ à la retraite remplies"
            if conditions_retraite_remplies and mois < ANCIENNETE_MINIMUM_MOIS
            else f"Ancienneté de {mois} mois (≥ 12 mois)"
        )
    else:
        motif = f"Ancienneté de {mois} mois inférieure à 12 mois et conditions de retraite non remplies"

    multiplicateur = multiplicateur_frais_funeraire(mois)
    frais = max(0.0, float(smhc_mensuel or 0.0)) * multiplicateur
    indemnite = rupture.montant if eligible else 0.0

    return ResultatIndemniteDeces(
        anciennete_mois=mois,
        salaire_global_moyen=rupture.salaire_global_moyen,
        eligible=eligible,
        motif_eligibilite=motif,
        indemnite_rupture=indemnite,
        tranches=rupture.tranches if eligible else [],
        multiplicateur_frais_funeraires=multiplicateur,
        smhc_mensuel=round(float(smhc_mensuel or 0.0), 2),
        frais_funeraires=round(frais, 2),
        total=round(indemnite + frais, 2),
    )


# ─────────────────────────────────────────────
#  INDEMNITÉ DE FIN DE CDD (art. 15.8)
# ─────────────────────────────────────────────

@dataclass
class ResultatFinCdd:
    """Indemnité de fin de contrat à durée déterminée."""
    total_brut_cdd: float
    taux: float
    indemnite_theorique: float
    eligible: bool
    motif: str
    indemnite_due: float


def calculer_indemnite_fin_cdd(
    total_brut_cdd: float,
    motif_fin: str,
    *,
    total_brut_saisi: Optional[float] = None,
) -> ResultatFinCdd:
    """Indemnité de fin de CDD : 3 % du total des rémunérations brutes du contrat.

    `motif_fin` doit valoir l'une des clés de `MOTIFS_FIN_CDD_DUE`,
    `MOTIFS_EXCLUSION_FIN_CDD` ou `MOTIFS_FIN_CDD_A_VERIFIER`.
    """
    total = max(0.0, float(total_brut_cdd or 0.0))
    theorique = round(total * TAUX_FIN_CDD, 2)

    if motif_fin in MOTIFS_FIN_CDD_DUE:
        return ResultatFinCdd(
            total_brut_cdd=round(total, 2), taux=TAUX_FIN_CDD,
            indemnite_theorique=theorique, eligible=True,
            motif=MOTIFS_FIN_CDD_DUE[motif_fin], indemnite_due=theorique,
        )

    if motif_fin in MOTIFS_EXCLUSION_FIN_CDD:
        return ResultatFinCdd(
            total_brut_cdd=round(total, 2), taux=TAUX_FIN_CDD,
            indemnite_theorique=theorique, eligible=False,
            motif=MOTIFS_EXCLUSION_FIN_CDD[motif_fin], indemnite_due=0.0,
        )

    # Motif inconnu ou « autre » : on n'attribue rien automatiquement, mais le
    # montant théorique est retourné pour permettre une décision explicite.
    return ResultatFinCdd(
        total_brut_cdd=round(total, 2), taux=TAUX_FIN_CDD,
        indemnite_theorique=theorique, eligible=False,
        motif=MOTIFS_FIN_CDD_A_VERIFIER.get(
            motif_fin, f"Motif « {motif_fin} » non reconnu : vérification juridique requise"
        ),
        indemnite_due=0.0,
    )
