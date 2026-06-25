from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
    motif_sortie: Optional[int] = None
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


class ContratCreate(ContratBase):
    salarie_id: int
    etablissement_id: int
    jours_hebdomadaires: Optional[JoursHebdomadairesCreate] = None
    horaires: Optional[HorairesCreate] = None
    depart_salarie: Optional[DepartSalarieCreate] = None
    mois_a_exclure: Optional[MoisAExclureCreate] = None


class ContratUpdate(BaseModel):
    emploi: Optional[str] = None
    type_contrat_travail: Optional[int] = None
    salaire_mensuel: Optional[float] = None
    salaire_horaire: Optional[float] = None
    type_salaire: Optional[str] = None
    statut: Optional[str] = None
    unite_temps: Optional[str] = None
    sursalaire: Optional[float] = None
    indemnite_transport: Optional[float] = None
    dotation_telephonique: Optional[float] = None


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

    class Config:
        from_attributes = True
