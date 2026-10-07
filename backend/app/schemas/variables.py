from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

#: Statuts autorisés du cycle de paie d'une période.
STATUTS_PERIODE = frozenset({"saisie_en_cours", "transmis", "calcule", "valide"})


# ─────────────────────────────────────────
#  SCHÉMAS ABSENCE
# ─────────────────────────────────────────

class AbsenceBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)  # CP, MAL, AT, etc.
    date_debut: datetime
    date_fin: datetime
    nbr_heure_by_user: Optional[float] = Field(default=0.0, ge=0)
    nbr_jour_by_user: Optional[float] = Field(default=0.0, ge=0)
    mois: int = Field(ge=1, le=12)
    annee: str = Field(min_length=4, max_length=4)


class AbsenceCreate(AbsenceBase):
    pass


class AbsenceOut(AbsenceBase):
    id: int
    contrat_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS HEURE SUPPLEMENTAIRE
# ─────────────────────────────────────────

class HeureSupplementaireBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)  # HS15, HS25, HS50, HS75, HS100…
    nombre: float = Field(gt=0)
    mois: int = Field(ge=1, le=12)
    annee: str = Field(min_length=4, max_length=4)


class HeureSupplementaireCreate(HeureSupplementaireBase):
    pass


class HeureSupplementaireOut(HeureSupplementaireBase):
    id: int
    contrat_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS PRIME
# ─────────────────────────────────────────

class PrimeBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    montant: float = Field(ge=0)
    mois: int = Field(ge=1, le=12)
    annee: str = Field(min_length=4, max_length=4)
    libelle: Optional[str] = None
    base: Optional[float] = None
    taux: Optional[float] = None
    est_persistant: Optional[bool] = False


class PrimeCreate(PrimeBase):
    pass


class PrimeOut(PrimeBase):
    id: int
    contrat_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS OPTION (Avantages en nature, etc.)
# ─────────────────────────────────────────

class OptionBase(BaseModel):
    code: str
    valeur: Optional[str] = None
    valeur_numerique: Optional[float] = None
    mois: int
    annee: str
    libelle: Optional[str] = None
    est_persistant: Optional[bool] = False


class OptionCreate(OptionBase):
    pass


class OptionOut(OptionBase):
    id: int
    contrat_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS VARIABLE REPRISE DOSSIER
# ─────────────────────────────────────────

class VariableRepriseDossierBase(BaseModel):
    code: str
    valeur: Optional[float] = 0.0
    libelle: Optional[str] = None
    annee: str


class VariableRepriseDossierCreate(VariableRepriseDossierBase):
    pass


class VariableRepriseDossierOut(VariableRepriseDossierBase):
    id: int
    contrat_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS VARIABLE (RÉFÉRENTIEL)
# ─────────────────────────────────────────

class VariableBase(BaseModel):
    code: str
    libelle: Optional[str] = None
    type: Optional[str] = None  # absence, hs, prime, option, reprise
    description: Optional[str] = None
    is_active: Optional[bool] = True


class VariableCreate(VariableBase):
    pass


class VariableOut(VariableBase):
    id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS PÉRIODE DE PAIE & SAISIE COLLECTIVE
# ─────────────────────────────────────────

class PeriodePaieOut(BaseModel):
    id: Optional[int] = None
    dossier_id: int
    mois: int
    annee: str
    statut: str = "saisie_en_cours" # "saisie_en_cours", "transmis", "calcule", "valide"
    date_transmission: Optional[datetime] = None
    notes_client: Optional[str] = None
    notes_cabinet: Optional[str] = None

    class Config:
        from_attributes = True


class PeriodePaieTransmettre(BaseModel):
    notes: Optional[str] = None


class SalarieVariableRowOut(BaseModel):
    salarie_id: int
    matricule: str
    nom: str
    prenom: str
    contrat_id: int
    intitule_poste: Optional[str] = None
    salaire_base: Optional[float] = 0.0
    heures_supplementaires: list = []
    absences: list = []
    primes: list = []
    options: list = []
    has_bulletin: bool = False
    bulletin_id: Optional[int] = None
    bulletin_statut: Optional[str] = None
    net_a_payer: Optional[float] = None


class SalarieVariableBulkItem(BaseModel):
    contrat_id: int
    heures_supp: list[dict] = [] # [{"code": "HS15", "nombre": 4}]
    absences: list[dict] = [] # [{"code": "CP", "date_debut": "...", "date_fin": "...", "nbr_jour_by_user": 2}]
    primes: list[dict] = [] # [{"code": "PRIME_RENDEMENT", "montant": 25000, "libelle": "Prime"}]
