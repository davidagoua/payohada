from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────
#  SCHÉMAS NET ENTREPRISE
# ─────────────────────────────────────────

class NetEntrepriseBase(BaseModel):
    parametrage_domaine: Optional[bool] = False
    nom: str
    prenom: str
    siret: str
    civilite: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None


class NetEntrepriseCreate(NetEntrepriseBase):
    pass


class NetEntrepriseOut(NetEntrepriseBase):
    id: int
    dossier_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS DOSSIER
# ─────────────────────────────────────────

class DossierBase(BaseModel):
    code: str
    #: Identifiant ivoirien de la société (remplace le SIRET français).
    rccm: Optional[str] = None
    siret: Optional[str] = None
    #: Jour du mois où les salaires sont virés (1-31), récurrent.
    jour_virement: Optional[int] = Field(default=None, ge=1, le=31)
    nom_dossier: str
    adresse_email: Optional[str] = None
    telephone: Optional[str] = None
    nom_contact: Optional[str] = None
    qualite: Optional[int] = None
    annee: Optional[str] = None
    pays: Optional[str] = "Côte d'Ivoire"


class DossierCreate(DossierBase):
    net_entreprise: Optional[NetEntrepriseCreate] = None


class DossierUpdate(BaseModel):
    rccm: Optional[str] = None
    siret: Optional[str] = None
    jour_virement: Optional[int] = Field(default=None, ge=1, le=31)
    nom_dossier: Optional[str] = None
    adresse_email: Optional[str] = None
    telephone: Optional[str] = None
    nom_contact: Optional[str] = None
    qualite: Optional[int] = None
    annee: Optional[str] = None
    pays: Optional[str] = None


class DossierOut(DossierBase):
    id: int
    utilisateur_id: int
    created_at: datetime
    updated_at: datetime
    net_entreprise: Optional[NetEntrepriseOut] = None

    class Config:
        from_attributes = True
