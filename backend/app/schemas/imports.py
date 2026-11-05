"""Schémas des imports Excel/CSV (données de base)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ImportErreur(BaseModel):
    ligne: int
    champ: Optional[str] = None
    message: str
    valeur: Optional[str] = None


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dossier_id: int
    type_import: str
    fichier_nom: str
    fichier_taille: int = 0
    statut: str
    total_lignes: int = 0
    lignes_valides: int = 0
    lignes_erreurs: int = 0
    execute_le: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ImportAnalyseOut(BaseModel):
    job: ImportJobOut
    colonnes: list[str] = Field(default_factory=list)
    mapping: dict[str, str] = Field(default_factory=dict)
    champs_manquants: list[str] = Field(default_factory=list)
    erreurs: list[ImportErreur] = Field(default_factory=list)
    apercu: list[dict] = Field(default_factory=list)
    message: Optional[str] = None


class ImportExecutionIn(BaseModel):
    #: Autorise l'import des seules lignes valides quand d'autres sont en erreur.
    ignorer_erreurs: bool = False


class ImportExecutionOut(BaseModel):
    job: ImportJobOut
    crees: int = 0
    mis_a_jour: int = 0
    ignores: int = 0
    erreurs: list[ImportErreur] = Field(default_factory=list)
    message: Optional[str] = None
