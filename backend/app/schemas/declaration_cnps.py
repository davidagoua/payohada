"""Schémas des déclarations CNPS mensuelles."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AnomalieOut(BaseModel):
    niveau: str
    salarie: str
    message: str


class LigneDeclarationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ordre: int
    salarie_id: Optional[int] = None
    contrat_id: Optional[int] = None
    numero_cnps: Optional[str] = None
    nom: Optional[str] = None
    prenoms: Optional[str] = None
    date_naissance: Optional[date] = None
    date_embauche: Optional[date] = None
    date_depart: Optional[date] = None
    type_salarie: Optional[str] = None
    duree_travaillee: float = 0.0
    salaire_brut: float = 0.0
    branches: Optional[str] = None
    base_retraite: float = 0.0
    base_pf_at_am: float = 0.0
    cotisation_retraite: float = 0.0
    cotisation_pf: float = 0.0
    cotisation_at: float = 0.0
    cotisation_am: float = 0.0


class ApercuDeclarationOut(BaseModel):
    """Calcul du mois, sans enregistrement."""
    annee: int
    mois: int
    effectif: int
    masse_salariale: float
    total_cotisations: float
    totaux: dict
    bloquee: bool
    anomalies: list[AnomalieOut] = []
    lignes: list[LigneDeclarationOut] = []


class DeclarationOut(BaseModel):
    id: int
    etablissement_id: int
    annee: int
    mois: int
    statut: str
    effectif: int = 0
    masse_salariale: float = 0.0
    total_cotisations: float = 0.0
    totaux: dict = {}
    date_depot: Optional[datetime] = None
    reference_depot: Optional[str] = None
    #: Les bulletins du mois ont changé depuis la génération.
    ecart_bulletins: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeclarationDetailOut(DeclarationOut):
    lignes: list[LigneDeclarationOut] = []


class MoisDeclarationOut(BaseModel):
    """Une ligne du tableau annuel : le mois et sa déclaration éventuelle."""
    mois: int
    declaration: Optional[DeclarationOut] = None
    bulletins: int = 0
    bulletins_valides: int = 0


class DepotDeclarationIn(BaseModel):
    date_depot: date
    reference_depot: Optional[str] = Field(default=None, max_length=100)
