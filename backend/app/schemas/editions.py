"""Schémas du module « Éditions »."""
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class PeriodeEdition(BaseModel):
    """Périmètre d'une édition : un établissement et une période.

    L'établissement est le niveau auquel la paie est tenue dans l'application ;
    c'est donc lui qui délimite un état, et non le dossier.
    """
    etablissement_id: int
    mois_debut: int = Field(..., ge=1, le=12)
    annee_debut: int = Field(..., ge=2000, le=2100)
    mois_fin: int = Field(..., ge=1, le=12)
    annee_fin: int = Field(..., ge=2000, le=2100)

    @field_validator("annee_fin")
    @classmethod
    def _periode_coherente(cls, valeur: int, info):
        debut_annee = info.data.get("annee_debut")
        debut_mois = info.data.get("mois_debut")
        fin_mois = info.data.get("mois_fin")
        if None in (debut_annee, debut_mois, fin_mois):
            return valeur
        if (valeur, fin_mois) < (debut_annee, debut_mois):
            raise ValueError(
                "La fin de période doit être postérieure ou égale au début."
            )
        return valeur


class EditionOut(BaseModel):
    """Une édition du catalogue."""
    code: str
    libelle: str
    famille: str
    description: str
    formats: List[str]


class FamilleEditionsOut(BaseModel):
    famille: str
    editions: List[EditionOut]


class ColonneEditionOut(BaseModel):
    cle: str
    libelle: str
    type: str
    total: bool


class ResultatEditionOut(BaseModel):
    """Modèle tabulaire d'un état, tel qu'affiché en aperçu."""
    code: str
    titre: str
    colonnes: List[ColonneEditionOut]
    lignes: List[dict]
    totaux: dict
    contexte: dict
    notes: List[str]
    nombre_lignes: int


class EnvoiEditionIn(PeriodeEdition):
    """Envoi d'une édition par email, en PDF."""
    destinataire: str = Field(..., min_length=3)
    copie: Optional[str] = None
    objet: Optional[str] = None
    message: Optional[str] = None
