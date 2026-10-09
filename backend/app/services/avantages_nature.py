"""Avantages en nature — barème fiscal ivoirien.

Source : **note de service DGI du 08/07/2024** (n° 0053/0001), qui fixe les
évaluations forfaitaires des avantages en nature.

Principes retenus :

* le **logement** et ses charges (mobilier, électricité, eau) sont évalués selon
  un barème fonction du **nombre de pièces** ;
* la **climatisation**, la **piscine** et la **domesticité** (gardien, employé de
  maison, cuisinier) relèvent de forfaits ou de montants unitaires ;
* les **repas** sont retenus pour leur coût réel diminué de l'exonération
  éventuelle ;
* un **véhicule de fonction ou de service** ne constitue pas un avantage
  imposable ; le **transport collectif** est exonéré dans la limite d'un
  plafond mensuel par salarié ; tout autre véhicule est évalué à sa valeur
  réelle ;
* la **participation du salarié** est déduite de l'avantage imposable ;
* l'assiette **CNPS** retient la valeur réelle : elle est saisie séparément,
  pour ne pas assimiler la règle fiscale à la règle sociale.

Module pur, sans dépendance à la base ni à la session HTTP.
"""
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
#  BARÈME LOGEMENT (nombre de pièces → montants mensuels)
# ─────────────────────────────────────────────

#: `nb_pieces` (7 = 7 et plus) → (logement, mobilier, électricité, eau).
BAREME_LOGEMENT: dict[int, tuple[float, float, float, float]] = {
    1: (60_000, 10_000, 10_000, 10_000),
    2: (80_000, 20_000, 20_000, 15_000),
    3: (160_000, 40_000, 30_000, 20_000),
    4: (300_000, 60_000, 40_000, 30_000),
    5: (480_000, 80_000, 50_000, 40_000),
    6: (600_000, 100_000, 60_000, 50_000),
    7: (800_000, 150_000, 70_000, 60_000),
}

#: Nombre de pièces maximal représenté par le barème (au-delà, on retient la
#: dernière ligne : « 7 pièces et + »).
PIECES_MAXIMUM_BAREME = 7

#: Montants unitaires des autres avantages.
MONTANT_CLIMATISEUR = 20_000        # par climatiseur / pièce climatisée
MONTANT_PISCINE = 30_000            # forfait mensuel
MONTANT_GARDIEN = 50_000            # par personne
MONTANT_EMPLOYE_MAISON = 60_000     # par personne
MONTANT_CUISINIER = 90_000          # par personne

#: Plafond mensuel d'exonération des repas.
PLAFOND_EXONERATION_REPAS = 30_000

#: Plafond mensuel d'exonération du transport collectif, par salarié.
PLAFOND_EXONERATION_TRANSPORT_COLLECTIF = 30_000

# ─────────────────────────────────────────────
#  MODES DE MISE À DISPOSITION D'UN VÉHICULE
# ─────────────────────────────────────────────

VEHICULE_FONCTION_SERVICE = "fonction_service"
VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS = "transport_collectif_couts_reels"
VEHICULE_TRANSPORT_COLLECTIF_FORFAIT = "transport_collectif_forfait"
VEHICULE_AUTRE_TAXABLE = "autre_taxable"

VEHICULES_TRANSPORT_COLLECTIF = (
    VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS,
    VEHICULE_TRANSPORT_COLLECTIF_FORFAIT,
)

LIBELLES_VEHICULE = {
    VEHICULE_FONCTION_SERVICE: "Véhicule de fonction / service",
    VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS: "Transport collectif — coûts réels",
    VEHICULE_TRANSPORT_COLLECTIF_FORFAIT: "Transport collectif — forfait par salarié",
    VEHICULE_AUTRE_TAXABLE: "Autre véhicule taxable",
}


# ─────────────────────────────────────────────
#  COMPOSANTES D'UN AVANTAGE
# ─────────────────────────────────────────────

@dataclass
class ComposanteAvantage:
    """Une ligne d'avantage en nature, telle qu'affichée sur le bulletin."""
    code: str
    libelle: str
    base_calcul: str
    montant: float


@dataclass
class ResultatVehicule:
    """Évaluation de l'avantage véhicule."""
    type_mise_a_disposition: str
    libelle_type: str
    cout_total_mensuel: float
    nombre_beneficiaires: int
    valeur_brute_par_salarie: float
    exoneration_transport_collectif: float
    participation_salarie: float
    avantage_imposable: float
    traitement_fiscal: str
    valeur_reelle_cnps: float = 0.0


@dataclass
class ResultatAvantagesNature:
    """Synthèse des avantages en nature d'un salarié pour un mois."""
    composantes: list[ComposanteAvantage] = field(default_factory=list)
    total_avant_participation: float = 0.0
    participation_salarie: float = 0.0
    avantage_imposable: float = 0.0
    salaire_imposable: float = 0.0
    salaire_brut_imposable: float = 0.0
    base_cnps_indicative: Optional[float] = None
    ecart_fiscal_cnps: Optional[float] = None
    #: Valeur réelle des avantages retenue pour l'assiette CNPS (0 si non saisie).
    valeur_reelle_avantages: float = 0.0
    alertes: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────
#  LOGEMENT
# ─────────────────────────────────────────────

def bareme_logement(nb_pieces: int) -> tuple[float, float, float, float]:
    """Montants forfaitaires `(logement, mobilier, électricité, eau)`.

    Un nombre de pièces inférieur à 1 retombe sur la première ligne ; un nombre
    supérieur à 7 retombe sur la dernière (« 7 pièces et + »).
    """
    pieces = int(nb_pieces or 1)
    pieces = max(1, min(pieces, PIECES_MAXIMUM_BAREME))
    return BAREME_LOGEMENT[pieces]


# ─────────────────────────────────────────────
#  VÉHICULE
# ─────────────────────────────────────────────

def calculer_avantage_vehicule(
    type_mise_a_disposition: str,
    *,
    couts_mensuels: Optional[dict[str, float]] = None,
    nombre_beneficiaires: int = 1,
    forfait_mensuel_par_salarie: float = 0.0,
    valeur_reelle_mensuelle: float = 0.0,
    participation_salarie: float = 0.0,
    valeur_reelle_cnps: float = 0.0,
) -> ResultatVehicule:
    """Évalue l'avantage véhicule et son traitement fiscal.

    * véhicule de fonction ou de service → **non imposable** ;
    * transport collectif (coûts réels répartis entre bénéficiaires, ou forfait
      par salarié) → imposable après application du plafond d'exonération ;
    * autre véhicule → valeur réelle.
    """
    couts = couts_mensuels or {}
    cout_total = sum(float(v or 0.0) for v in couts.values())
    beneficiaires = max(1, int(nombre_beneficiaires or 1))
    participation = max(0.0, float(participation_salarie or 0.0))

    if type_mise_a_disposition == VEHICULE_FONCTION_SERVICE:
        brut = 0.0
        exoneration = 0.0
        traitement = "Non imposable fiscalement"
    elif type_mise_a_disposition == VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS:
        brut = cout_total / beneficiaires
        exoneration = PLAFOND_EXONERATION_TRANSPORT_COLLECTIF
        traitement = "Transport collectif : exonération plafonnée"
    elif type_mise_a_disposition == VEHICULE_TRANSPORT_COLLECTIF_FORFAIT:
        brut = max(0.0, float(forfait_mensuel_par_salarie or 0.0))
        exoneration = PLAFOND_EXONERATION_TRANSPORT_COLLECTIF
        traitement = "Transport collectif : exonération plafonnée"
    else:
        brut = max(0.0, float(valeur_reelle_mensuelle or 0.0))
        exoneration = 0.0
        traitement = "Évaluation à la valeur réelle"

    imposable = 0.0 if type_mise_a_disposition == VEHICULE_FONCTION_SERVICE else max(
        0.0, brut - exoneration - participation
    )

    return ResultatVehicule(
        type_mise_a_disposition=type_mise_a_disposition,
        libelle_type=LIBELLES_VEHICULE.get(type_mise_a_disposition, type_mise_a_disposition),
        cout_total_mensuel=round(cout_total, 2),
        nombre_beneficiaires=beneficiaires,
        valeur_brute_par_salarie=round(brut, 2),
        exoneration_transport_collectif=round(exoneration, 2),
        participation_salarie=round(participation, 2),
        avantage_imposable=round(imposable, 2),
        traitement_fiscal=traitement,
        valeur_reelle_cnps=round(max(0.0, float(valeur_reelle_cnps or 0.0)), 2),
    )


# ─────────────────────────────────────────────
#  SYNTHÈSE DES AVANTAGES
# ─────────────────────────────────────────────

def calculer_avantages_nature(
    *,
    salaire_et_primes_imposables: float = 0.0,
    # Logement et charges
    logement_fourni: bool = False,
    mobilier_fourni: bool = False,
    electricite_prise_en_charge: bool = False,
    eau_prise_en_charge: bool = False,
    nombre_pieces: int = 1,
    # Équipements et domesticité
    nombre_climatiseurs: float = 0.0,
    piscine: bool = False,
    nombre_gardiens: float = 0.0,
    nombre_employes_maison: float = 0.0,
    nombre_cuisiniers: float = 0.0,
    # Repas et autres
    cout_mensuel_repas: float = 0.0,
    exoneration_repas_applicable: bool = False,
    autres_avantages_cout_reel: float = 0.0,
    # Participations et véhicule
    participation_salarie_hors_vehicule: float = 0.0,
    vehicule: Optional[ResultatVehicule] = None,
    # Information CNPS
    valeur_reelle_avantages_hors_vehicule_cnps: Optional[float] = None,
) -> ResultatAvantagesNature:
    """Assemble toutes les composantes d'avantages en nature d'un mois.

    Retourne le détail ligne à ligne, le total, l'avantage imposable et le
    **salaire brut imposable** (`salaire et primes + avantage imposable`).
    """
    resultat = ResultatAvantagesNature()
    composantes = resultat.composantes

    logement, mobilier, electricite, eau = bareme_logement(nombre_pieces)

    if logement_fourni:
        composantes.append(ComposanteAvantage(
            code="AN_LOGEMENT", libelle="Avantage logement",
            base_calcul=f"Barème {max(1, int(nombre_pieces or 1))} pièce(s)",
            montant=logement,
        ))
    if mobilier_fourni:
        composantes.append(ComposanteAvantage(
            code="AN_MOBILIER", libelle="Avantage mobilier",
            base_calcul="Barème logement", montant=mobilier,
        ))
    if electricite_prise_en_charge:
        composantes.append(ComposanteAvantage(
            code="AN_ELECTRICITE", libelle="Avantage électricité",
            base_calcul="Barème logement", montant=electricite,
        ))
    if eau_prise_en_charge:
        composantes.append(ComposanteAvantage(
            code="AN_EAU", libelle="Avantage eau",
            base_calcul="Barème logement", montant=eau,
        ))

    nb_clim = max(0.0, float(nombre_climatiseurs or 0.0))
    if nb_clim > 0:
        composantes.append(ComposanteAvantage(
            code="AN_CLIMATISATION", libelle="Avantage climatisation",
            base_calcul=f"{nb_clim:g} × {MONTANT_CLIMATISEUR:,} F".replace(",", " "),
            montant=nb_clim * MONTANT_CLIMATISEUR,
        ))

    if piscine:
        composantes.append(ComposanteAvantage(
            code="AN_PISCINE", libelle="Avantage piscine",
            base_calcul="Forfait mensuel", montant=MONTANT_PISCINE,
        ))

    for nombre, montant, code, libelle in (
        (nombre_gardiens, MONTANT_GARDIEN, "AN_GARDIEN", "Gardien / jardinier"),
        (nombre_employes_maison, MONTANT_EMPLOYE_MAISON, "AN_EMPLOYE_MAISON", "Employé de maison"),
        (nombre_cuisiniers, MONTANT_CUISINIER, "AN_CUISINIER", "Cuisinier"),
    ):
        quantite = max(0.0, float(nombre or 0.0))
        if quantite > 0:
            composantes.append(ComposanteAvantage(
                code=code, libelle=f"Avantage {libelle.lower()}",
                base_calcul=f"{quantite:g} personne(s)",
                montant=quantite * montant,
            ))

    cout_repas = max(0.0, float(cout_mensuel_repas or 0.0))
    if cout_repas > 0:
        montant_repas = (
            max(0.0, cout_repas - PLAFOND_EXONERATION_REPAS)
            if exoneration_repas_applicable else cout_repas
        )
        composantes.append(ComposanteAvantage(
            code="AN_REPAS", libelle="Avantage repas",
            base_calcul=(
                f"Coût {cout_repas:,.0f} − exonération {PLAFOND_EXONERATION_REPAS:,} F".replace(",", " ")
                if exoneration_repas_applicable else "Coût réel"
            ),
            montant=montant_repas,
        ))

    autres = max(0.0, float(autres_avantages_cout_reel or 0.0))
    if autres > 0:
        composantes.append(ComposanteAvantage(
            code="AN_AUTRES", libelle="Autres avantages en nature",
            base_calcul="Coût réel supporté par l'employeur", montant=autres,
        ))

    if vehicule is not None:
        composantes.append(ComposanteAvantage(
            code="AN_VEHICULE", libelle=f"Avantage véhicule — {vehicule.libelle_type}",
            base_calcul=vehicule.traitement_fiscal, montant=vehicule.avantage_imposable,
        ))

    total = sum(c.montant for c in composantes)
    participation = max(0.0, float(participation_salarie_hors_vehicule or 0.0))
    imposable = max(0.0, total - participation)
    salaire = max(0.0, float(salaire_et_primes_imposables or 0.0))

    resultat.total_avant_participation = round(total, 2)
    resultat.participation_salarie = round(participation, 2)
    resultat.avantage_imposable = round(imposable, 2)
    resultat.salaire_imposable = round(salaire, 2)
    resultat.salaire_brut_imposable = round(salaire + imposable, 2)

    # Assiette CNPS : valeur réelle, saisie séparément de la règle fiscale.
    if valeur_reelle_avantages_hors_vehicule_cnps is not None or (
        vehicule is not None and vehicule.valeur_reelle_cnps
    ):
        reel_hors_vehicule = float(valeur_reelle_avantages_hors_vehicule_cnps or 0.0)
        reel_vehicule = vehicule.valeur_reelle_cnps if vehicule is not None else 0.0
        resultat.valeur_reelle_avantages = round(reel_hors_vehicule + reel_vehicule, 2)
        resultat.base_cnps_indicative = round(salaire + reel_hors_vehicule + reel_vehicule, 2)
        resultat.ecart_fiscal_cnps = round(
            reel_hors_vehicule + reel_vehicule - total, 2
        )

    for composante in composantes:
        if composante.montant < 0:
            resultat.alertes.append(
                f"Le montant de « {composante.libelle} » est négatif."
            )
    if logement_fourni and int(nombre_pieces or 0) > PIECES_MAXIMUM_BAREME:
        resultat.alertes.append(
            f"Nombre de pièces plafonné à {PIECES_MAXIMUM_BAREME} par le barème "
            "(ligne « 7 pièces et + »)."
        )

    return resultat
