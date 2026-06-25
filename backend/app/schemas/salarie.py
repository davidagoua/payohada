from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SalarieBase(BaseModel):
    matricule: Optional[str] = None
    nom: str
    prenom: str
    nom_usage: Optional[str] = None
    civilite: Optional[str] = None
    date_naissance: Optional[datetime] = None
    lieu_naissance: Optional[str] = None
    departement_naissance: Optional[str] = None
    pays_naissance: Optional[str] = None
    nationalite: Optional[str] = None
    numero_securite_sociale: Optional[str] = None
    adresse: Optional[str] = None
    adresse2: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = "France"
    email: Optional[str] = None
    telephone: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    is_active: Optional[bool] = True
    expatrie: Optional[bool] = False


class SalarieCreate(SalarieBase):
    pass


class SalarieUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    nom_usage: Optional[str] = None
    civilite: Optional[str] = None
    date_naissance: Optional[datetime] = None
    lieu_naissance: Optional[str] = None
    departement_naissance: Optional[str] = None
    pays_naissance: Optional[str] = None
    nationalite: Optional[str] = None
    numero_securite_sociale: Optional[str] = None
    adresse: Optional[str] = None
    adresse2: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    is_active: Optional[bool] = None
    expatrie: Optional[bool] = None


class SalarieOut(SalarieBase):
    id: int
    etablissement_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
