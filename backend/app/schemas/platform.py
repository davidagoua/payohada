"""Schémas de l'administration plateforme (cabinets)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CabinetAdminCreate(BaseModel):
    prenom: str = Field(min_length=1, max_length=100)
    nom: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: Optional[str] = None


class CabinetCreate(BaseModel):
    cabinet_nom: str = Field(min_length=1, max_length=200)
    cabinet_telephone: Optional[str] = Field(default=None, max_length=30)
    cabinet_ville: Optional[str] = Field(default=None, max_length=100)
    #: `entreprise` : une seule société, créée avec le compte (dossier et
    #: établissement au nom du cabinet).
    type_cabinet: Literal["cabinet", "entreprise"] = "cabinet"
    #: Sous-domaine de connexion (cabinet-x) ; déduit du nom s'il est absent.
    sous_domaine: Optional[str] = Field(default=None, max_length=63)
    administrateur: CabinetAdminCreate


class CabinetSousDomaineUpdate(BaseModel):
    sous_domaine: str = Field(min_length=3, max_length=63)


class CabinetStatutUpdate(BaseModel):
    suspendu: bool


class CabinetAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    prenom: str
    nom: str
    role: str
    is_active: bool
    must_change_password: bool = False
    est_proprietaire: bool = False


class CabinetAdminCreationOut(CabinetAdminOut):
    mot_de_passe_initial: Optional[str] = None
    email_envoye: Optional[bool] = None
    email_message: Optional[str] = None


class AdminPlateformeOut(BaseModel):
    """Administrateur de la plateforme (`is_admin`)."""
    id: int
    email: str
    prenom: str
    nom: str
    is_active: bool
    must_change_password: bool = False
    #: Le compte connecté (on ne peut pas se désactiver soi-même).
    est_moi: bool = False
    created_at: Optional[datetime] = None


class AdminPlateformeCreationOut(AdminPlateformeOut):
    mot_de_passe_initial: Optional[str] = None
    email_envoye: Optional[bool] = None
    email_message: Optional[str] = None


class AdminPlateformeStatutUpdate(BaseModel):
    actif: bool


class CabinetOut(BaseModel):
    id: int
    cabinet_nom: Optional[str] = None
    email: str
    prenom: str
    nom: str
    telephone: Optional[str] = None
    ville: Optional[str] = None
    type_cabinet: str = "cabinet"
    sous_domaine: Optional[str] = None
    #: Adresse de connexion du cabinet (sous-domaine).
    url_espace: Optional[str] = None
    suspendu: bool = False
    is_active: bool = True
    membres: int = 0
    dossiers: int = 0
    administrateurs: list[CabinetAdminOut] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class CabinetCreationOut(CabinetOut):
    mot_de_passe_initial: Optional[str] = None
    email_envoye: Optional[bool] = None
    email_message: Optional[str] = None


# ─── Tableau de bord SaaS (indicateurs agrégés, aucune donnée de paie) ───

class IndicateursCabinets(BaseModel):
    total: int = 0
    actifs: int = 0
    suspendus: int = 0
    nouveaux_30_jours: int = 0


class ActiviteMensuelle(BaseModel):
    mois: int
    annee: int
    bulletins: int = 0
    bulletins_valides: int = 0


class UsageCabinet(BaseModel):
    id: int
    cabinet_nom: Optional[str] = None
    suspendu: bool = False
    utilisateurs: int = 0
    societes: int = 0
    salaries_actifs: int = 0
    bulletins_mois_courant: int = 0
    derniere_activite: Optional[datetime] = None


class TableauDeBordPlateforme(BaseModel):
    cabinets: IndicateursCabinets
    utilisateurs_par_role: dict[str, int] = Field(default_factory=dict)
    societes: int = 0
    salaries_actifs: int = 0
    bulletins_mois_courant: int = 0
    activite: list[ActiviteMensuelle] = Field(default_factory=list)
    usage_cabinets: list[UsageCabinet] = Field(default_factory=list)
