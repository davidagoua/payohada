from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────
#  SCHÉMAS ABSENCE
# ─────────────────────────────────────────

class AbsenceBase(BaseModel):
    code: str  # CP, MAL, AT, etc.
    date_debut: datetime
    date_fin: datetime
    nbr_heure_by_user: Optional[float] = 0.0
    nbr_jour_by_user: Optional[float] = 0.0
    mois: int
    annee: str


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
    code: str  # HS25, HS50, etc.
    nombre: float
    mois: int
    annee: str


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
    code: str
    montant: float
    mois: int
    annee: str
    libelle: Optional[str] = None


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
