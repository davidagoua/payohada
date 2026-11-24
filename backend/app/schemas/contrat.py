from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


TYPES_SALARIE_CNPS = ("M", "J", "H")


def _valider_type_salarie_cnps(valeur):
    if valeur in (None, ""):
        return None
    valeur = str(valeur).strip().upper()
    if valeur not in TYPES_SALARIE_CNPS:
        raise ValueError("Type de salarié CNPS : M (mensuel), J (journalier) ou H (horaire).")
    return valeur


def _valider_branches_cnps(valeur):
    """« 123 », « 23 »… : branches distinctes parmi 1, 2 et 3, dans l'ordre."""
    if valeur in (None, ""):
        return None
    chiffres = sorted(set(str(valeur).replace(" ", "")))
    if not chiffres or any(c not in "123" for c in chiffres):
        raise ValueError("Branches cotisées : combinaison de 1 (retraite), 2 (AT/MP) et 3 (PF et maternité).")
    return "".join(chiffres)


# ─────────────────────────────────────────
#  SCHÉMAS JOURS HEBDOMADAIRES
# ─────────────────────────────────────────

class JoursHebdomadairesBase(BaseModel):
    jours_hebdo: Optional[float] = 5.0
    jour_lundi: Optional[float] = 1.0
    jour_mardi: Optional[float] = 1.0
    jour_mercredi: Optional[float] = 1.0
    jour_jeudi: Optional[float] = 1.0
    jour_vendredi: Optional[float] = 1.0
    jour_samedi: Optional[float] = 0.0
    jour_dimanche: Optional[float] = 0.0


class JoursHebdomadairesCreate(JoursHebdomadairesBase):
    pass


class JoursHebdomadairesOut(JoursHebdomadairesBase):
    id: int
    contrat_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS HORAIRES
# ─────────────────────────────────────────

class HorairesBase(BaseModel):
    horaire_travail: Optional[float] = 151.67
    horaire_hebdo: Optional[float] = 35.0
    horaire_lundi: Optional[float] = 7.0
    horaire_mardi: Optional[float] = 7.0
    horaire_mercredi: Optional[float] = 7.0
    horaire_jeudi: Optional[float] = 7.0
    horaire_vendredi: Optional[float] = 7.0
    horaire_samedi: Optional[float] = 0.0
    horaire_dimanche: Optional[float] = 0.0


class HorairesCreate(HorairesBase):
    pass


class HorairesOut(HorairesBase):
    id: int
    contrat_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS DEPART SALARIE
# ─────────────────────────────────────────

class DepartSalarieBase(BaseModel):
    date_sortie: Optional[str] = None
    bulletin_post_contrat: Optional[bool] = False
    bulletin_post_contrat_du: Optional[str] = None
    bulletin_post_contrat_au: Optional[str] = None
    #: Code du motif de sortie (`services/depart.MOTIFS_SORTIE`).
    motif_sortie: Optional[int] = None
    #: Motif normalisé des calculs ; déduit du motif de sortie s'il est absent.
    motif_fin_contrat: Optional[str] = None
    sous_motif_fin_cdd: Optional[str] = None
    conditions_retraite_remplies: Optional[bool] = False
    date_notification_rupture: Optional[str] = None
    date_notification_signature: Optional[str] = None
    date_engagement_procedure: Optional[str] = None
    maintien_affiliation: Optional[bool] = False
    transaction_en_cours: Optional[bool] = False
    dernier_jour_travaille: Optional[str] = None
    statut_particulier: Optional[int] = None
    type_paiement_preavis01: Optional[int] = None
    preavis_de01: Optional[str] = None
    preavis_au01: Optional[str] = None
    type_paiement_preavis02: Optional[int] = None
    preavis_de02: Optional[str] = None
    preavis_au02: Optional[str] = None
    type_paiement_preavis03: Optional[int] = None
    preavis_de03: Optional[str] = None
    preavis_au03: Optional[str] = None

    @field_validator("motif_sortie")
    @classmethod
    def _motif_connu(cls, valeur):
        from app.services.depart import MOTIFS_SORTIE
        if valeur is not None and valeur not in MOTIFS_SORTIE:
            raise ValueError("Motif de sortie inconnu.")
        return valeur

    @field_validator("type_paiement_preavis01", "type_paiement_preavis02", "type_paiement_preavis03")
    @classmethod
    def _preavis_connu(cls, valeur):
        from app.services.depart import TYPES_PREAVIS
        if valeur is not None and valeur not in TYPES_PREAVIS:
            raise ValueError("Type de préavis inconnu.")
        return valeur


class DepartSalarieCreate(DepartSalarieBase):
    pass


class DepartSalarieOut(DepartSalarieBase):
    id: int
    contrat_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS MOIS A EXCLURE
# ─────────────────────────────────────────

class MoisAExclureBase(BaseModel):
    exclure_janvier: Optional[bool] = False
    exclure_fevrier: Optional[bool] = False
    exclure_mars: Optional[bool] = False
    exclure_avril: Optional[bool] = False
    exclure_mai: Optional[bool] = False
    exclure_juin: Optional[bool] = False
    exclure_juillet: Optional[bool] = False
    exclure_aout: Optional[bool] = False
    exclure_septembre: Optional[bool] = False
    exclure_octobre: Optional[bool] = False
    exclure_novembre: Optional[bool] = False
    exclure_decembre: Optional[bool] = False


class MoisAExclureCreate(MoisAExclureBase):
    pass


class MoisAExclureOut(MoisAExclureBase):
    id: int
    contrat_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS CONTRAT
# ─────────────────────────────────────────

class ContratBase(BaseModel):
    numero_contrat: str
    poste_salaire_id: Optional[int] = None
    ancien_numero_contrat_dsn: Optional[str] = None
    emploi_conventionnel: Optional[int] = None
    ccn: Optional[int] = None
    idcc: Optional[int] = None
    emploi: Optional[str] = None
    type_contrat_travail: int  # CDI=10, CDD=29, etc.
    type_contrat_temps_partiel: Optional[int] = None
    statut_professionnel: int
    regime_retraite: Optional[int] = None
    cas_particuliers: Optional[int] = None
    salaire_mensuel: Optional[float] = 0.0
    salaire_horaire: Optional[float] = 0.0
    type_salaire: Optional[str] = "Mensuel"
    nbr_heures_travail_mensuel_majorees: Optional[float] = 0.0
    date_debut_contrat: Optional[str] = None
    date_fin_previsionnelle_contrat: Optional[str] = None
    date_anciennete: Optional[str] = None
    salarie_temps_partiel: Optional[bool] = False
    forfait_jour: Optional[bool] = False
    ne_pas_calculer_premier_bulletin: Optional[bool] = False
    nbr_jour_annuels_prevus: Optional[float] = 218.0
    tags: Optional[str] = None
    statut: Optional[str] = "actif"
    unite_temps: Optional[str] = "Heures"
    sursalaire: Optional[float] = 0.0
    indemnite_transport: Optional[float] = 0.0
    dotation_telephonique: Optional[float] = 0.0
    mode_calcul: Optional[str] = "brut"
    cnps_type_salarie: Optional[str] = None
    cnps_branches: Optional[str] = "123"

    @field_validator("cnps_type_salarie")
    @classmethod
    def _type_cnps(cls, valeur):
        return _valider_type_salarie_cnps(valeur)

    @field_validator("cnps_branches")
    @classmethod
    def _branches_cnps(cls, valeur):
        return _valider_branches_cnps(valeur) or "123"


class ContratCreate(ContratBase):
    salarie_id: int
    etablissement_id: int
    jours_hebdomadaires: Optional[JoursHebdomadairesCreate] = None
    horaires: Optional[HorairesCreate] = None
    depart_salarie: Optional[DepartSalarieCreate] = None
    mois_a_exclure: Optional[MoisAExclureCreate] = None


class ContratUpdate(BaseModel):
    emploi: Optional[str] = None
    poste_salaire_id: Optional[int] = None
    type_contrat_travail: Optional[int] = None
    salaire_mensuel: Optional[float] = None
    salaire_horaire: Optional[float] = None
    type_salaire: Optional[str] = None
    statut: Optional[str] = None
    unite_temps: Optional[str] = None
    sursalaire: Optional[float] = None
    indemnite_transport: Optional[float] = None
    dotation_telephonique: Optional[float] = None
    mode_calcul: Optional[str] = None
    #: Dates modifiables après coup : une date d'embauche saisie de travers
    #: fausse l'ancienneté, donc l'acquisition des congés.
    date_debut_contrat: Optional[str] = None
    date_anciennete: Optional[str] = None
    cnps_type_salarie: Optional[str] = None
    cnps_branches: Optional[str] = None

    @field_validator("cnps_type_salarie")
    @classmethod
    def _type_cnps(cls, valeur):
        return _valider_type_salarie_cnps(valeur)

    @field_validator("cnps_branches")
    @classmethod
    def _branches_cnps(cls, valeur):
        # Vider le champ revient à la valeur par défaut : toutes les branches.
        return _valider_branches_cnps(valeur) or "123"


class ContratOut(ContratBase):
    id: int
    dossier_id: int
    salarie_id: int
    etablissement_id: int
    code_etablissement: str
    matricule_salarie: str
    created_at: datetime
    updated_at: datetime
    jours_hebdomadaires: Optional[JoursHebdomadairesOut] = None
    horaires: Optional[HorairesOut] = None
    depart_salarie: Optional[DepartSalarieOut] = None
    mois_a_exclure: Optional[MoisAExclureOut] = None
    #: Salaire minimum de la catégorie (contrat, sinon grille du poste), en lecture.
    smhc_reference: Optional[float] = None
    #: Type de salarié déclaré à la CNPS (choisi, sinon déduit du salaire).
    type_salarie_cnps: Optional[str] = None

    class Config:
        from_attributes = True
