"""Schémas des calculateurs réglementaires ivoiriens."""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.services.avantages_nature import (
    VEHICULE_AUTRE_TAXABLE,
    VEHICULE_FONCTION_SERVICE,
    VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS,
    VEHICULE_TRANSPORT_COLLECTIF_FORFAIT,
)
from app.services.conges_gratification import METHODE_CONVENTIONNELLE
from app.services.indemnites_rupture import MOTIFS_FIN_CDD_DUE

MOTIFS_FIN_CONTRAT = (
    "licenciement", "retraite", "deces", "fin_cdd", "demission", "rupture",
)
SOUS_MOTIFS_FIN_CDD = (
    "terme_normal_sans_cdi", "refus_cdi_equivalent",
    "rupture_initiative_salarie", "faute_lourde", "cdi_conclu", "autre",
)
TYPES_VEHICULE = (
    VEHICULE_FONCTION_SERVICE,
    VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS,
    VEHICULE_TRANSPORT_COLLECTIF_FORFAIT,
    VEHICULE_AUTRE_TAXABLE,
)


# ─────────────────────────────────────────────
#  INDEMNITÉS DE RUPTURE
# ─────────────────────────────────────────────

class RuptureRequest(BaseModel):
    """Indemnité de licenciement ou de départ à la retraite (décret n° 2017-210).

    Si `salaires_12_mois` n'est pas fourni, les 12 derniers bulletins du contrat
    sont utilisés.
    """
    date_embauche: Optional[date] = None
    date_fin: Optional[date] = None
    anciennete_mois: Optional[int] = Field(default=None, ge=0)
    faute_lourde: bool = False
    depart_retraite: bool = False
    salaires_12_mois: Optional[List[Optional[float]]] = None
    #: Conserve les montants calculés dans le solde de tout compte.
    enregistrer: bool = False


class DecesRequest(RuptureRequest):
    """Indemnité de décès et frais funéraires."""
    smhc_mensuel: Optional[float] = Field(default=None, ge=0)
    conditions_retraite_remplies: bool = False
    #: Salaire de présence, congés acquis et autres droits dus aux ayants droit.
    salaire_presence: float = Field(default=0.0, ge=0)
    conges_acquis: float = Field(default=0.0, ge=0)
    autres_droits: float = Field(default=0.0, ge=0)


class FinCddRequest(BaseModel):
    """Indemnité de fin de CDD (art. 15.8) : 3 % du brut du contrat."""
    total_brut_cdd: Optional[float] = Field(default=None, ge=0)
    sous_motif_fin_cdd: str = "terme_normal_sans_cdi"
    #: Ajoute les congés payés non pris au solde estimatif.
    conges_mois_service: float = Field(default=0.0, ge=0)
    conges_jours_pris: float = Field(default=0.0, ge=0)
    salaire_mensuel_moyen: Optional[float] = Field(default=None, ge=0)


# ─────────────────────────────────────────────
#  GRATIFICATION ET CONGÉS
# ─────────────────────────────────────────────

class GratificationRequest(BaseModel):
    """Gratification annuelle (art. 53 de la convention interprofessionnelle)."""
    annee: int = Field(ge=2000, le=2100)
    smhc_mensuel: Optional[float] = Field(default=None, ge=0)
    jours_service: Optional[float] = Field(default=None, ge=0)
    taux_entreprise: float = Field(default=0.0, ge=0, le=5)
    montant_fixe_annuel_entreprise: float = Field(default=0.0, ge=0)
    jours_a_deduire: float = Field(default=0.0, ge=0)


class CongesRequest(BaseModel):
    """Congés payés : droits acquis et indemnité."""
    remunerations: Optional[List[Optional[float]]] = None
    mois_service: float = Field(ge=0)
    jours_supplementaires: float = Field(default=0.0, ge=0)
    jours_pris: float = Field(default=0.0, ge=0)
    anciennete_annees: float = Field(default=0.0, ge=0)
    methode: str = METHODE_CONVENTIONNELLE
    montant_manuel: Optional[float] = Field(default=None, ge=0)


class AvantageNatureIn(BaseModel):
    """Avantages en nature d'un mois (barème DGI du 08/07/2024)."""
    mois: int = Field(ge=1, le=12)
    annee: str = Field(min_length=4, max_length=4)

    logement_fourni: bool = False
    mobilier_fourni: bool = False
    electricite_prise_en_charge: bool = False
    eau_prise_en_charge: bool = False
    nombre_pieces: int = Field(default=1, ge=1, le=50)

    nombre_climatiseurs: float = Field(default=0.0, ge=0)
    piscine: bool = False
    nombre_gardiens: float = Field(default=0.0, ge=0)
    nombre_employes_maison: float = Field(default=0.0, ge=0)
    nombre_cuisiniers: float = Field(default=0.0, ge=0)

    cout_mensuel_repas: float = Field(default=0.0, ge=0)
    exoneration_repas_applicable: bool = False
    autres_avantages_cout_reel: float = Field(default=0.0, ge=0)

    participation_salarie_hors_vehicule: float = Field(default=0.0, ge=0)

    vehicule_type: Optional[str] = None
    vehicule_carburant: float = Field(default=0.0, ge=0)
    vehicule_entretien: float = Field(default=0.0, ge=0)
    vehicule_assurance: float = Field(default=0.0, ge=0)
    vehicule_vignette: float = Field(default=0.0, ge=0)
    vehicule_autres: float = Field(default=0.0, ge=0)
    vehicule_nombre_beneficiaires: int = Field(default=1, ge=1)
    vehicule_forfait_mensuel: float = Field(default=0.0, ge=0)
    vehicule_valeur_reelle: float = Field(default=0.0, ge=0)
    vehicule_participation: float = Field(default=0.0, ge=0)
    vehicule_valeur_reelle_cnps: float = Field(default=0.0, ge=0)

    valeur_reelle_hors_vehicule_cnps: Optional[float] = Field(default=None, ge=0)
    est_persistant: bool = False


class SoldeToutCompteCompletRequest(BaseModel):
    """Calcule et enregistre le solde de tout compte complet d'un départ."""
    motif_fin_contrat: str
    sous_motif_fin_cdd: Optional[str] = None
    date_sortie: Optional[date] = None
    #: Ancienneté en mois complets, lorsque les dates ne sont pas fiables.
    anciennete_mois: Optional[int] = Field(default=None, ge=0)
    faute_lourde: bool = False
    conditions_retraite_remplies: bool = False
    smhc_mensuel: Optional[float] = Field(default=None, ge=0)
    salaires_12_mois: Optional[List[Optional[float]]] = None

    # Gratification annuelle
    gratification_annee: Optional[int] = Field(default=None, ge=2000, le=2100)
    gratification_jours_service: Optional[float] = Field(default=None, ge=0)
    gratification_taux_entreprise: float = Field(default=0.0, ge=0, le=5)

    # Congés payés
    conges_mois_service: Optional[float] = Field(default=None, ge=0)
    conges_jours_pris: float = Field(default=0.0, ge=0)
    conges_jours_supplementaires: float = Field(default=0.0, ge=0)
    conges_methode: str = METHODE_CONVENTIONNELLE
    conges_montant_manuel: Optional[float] = Field(default=None, ge=0)

    # Éléments complémentaires saisis par le gestionnaire
    indemnite_preavis: float = Field(default=0.0, ge=0)
    indemnite_autre: float = Field(default=0.0, ge=0)


# ─────────────────────────────────────────────
#  SORTIES
# ─────────────────────────────────────────────

class TrancheIndemniteOut(BaseModel):
    # Accepte directement les dataclasses du service de calcul.
    model_config = ConfigDict(from_attributes=True)

    libelle: str
    mois_retenus: float
    annees_equivalentes: float
    taux: float
    salaire_reference: float
    montant: float


class IndemniteRuptureOut(BaseModel):
    anciennete_mois: int
    anciennete_annees: float
    salaire_global_moyen: float
    total_salaires_retenus: float
    nombre_salaires_retenus: int
    eligible: bool
    motif_ineligibilite: Optional[str] = None
    tranches: List[TrancheIndemniteOut] = []
    montant: float


class IndemniteDecesOut(BaseModel):
    """Indemnité de décès : structure distincte de l'indemnité de rupture."""
    anciennete_mois: int
    salaire_global_moyen: float
    eligible: bool
    motif_eligibilite: str
    indemnite_rupture: float
    tranches: List[TrancheIndemniteOut] = []
    multiplicateur_frais_funeraires: int
    smhc_mensuel: float
    frais_funeraires: float
    total: float
    total_ayants_droit: float


class IndemniteFinCddOut(BaseModel):
    total_brut_cdd: float
    taux: float
    indemnite_theorique: float
    eligible: bool
    motif: str
    indemnite_due: float
    conges_estimes: float = 0.0
    solde_estime: float = 0.0


class GratificationOut(BaseModel):
    smhc_mensuel: float
    jours_service: float
    prorata: float
    minimum_annuel_temps_plein: float
    minimum_conventionnel_proratise: float
    montant_par_taux_entreprise: float
    montant_fixe_entreprise_proratise: float
    meilleur_montant_entreprise: float
    gratification_retenue: float
    alertes: List[str] = []


class CongesOut(BaseModel):
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
    montant_conventionnel: float
    montant_decret: float
    methode_retenue: str
    montant_retenu: float
    allocation_principale: float
    comparaison: str
    alertes: List[str] = []


class ComposanteAvantageOut(BaseModel):
    # Accepte directement les dataclasses du service de calcul.
    model_config = ConfigDict(from_attributes=True)

    code: str
    libelle: str
    base_calcul: str
    montant: float


class AvantageNatureOut(BaseModel):
    composantes: List[ComposanteAvantageOut] = []
    total_avant_participation: float
    participation_salarie: float
    avantage_imposable: float
    salaire_imposable: float
    salaire_brut_imposable: float
    base_cnps_indicative: Optional[float] = None
    ecart_fiscal_cnps: Optional[float] = None
    alertes: List[str] = []


class SoldeToutCompteCompletOut(BaseModel):
    contrat_id: int
    motif_fin_contrat: str
    anciennete_mois: int
    salaire_global_moyen: float
    indemnite_licenciement: float
    indemnite_retraite: float
    indemnite_deces: float
    frais_funeraires: float
    indemnite_fin_cdd: float
    gratification: float
    indemnite_conges_payes: float
    indemnite_preavis: float
    indemnite_autre: float
    total: float
    details: dict = {}
    alertes: List[str] = []
