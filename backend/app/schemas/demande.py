"""Schémas des demandes du salarié : congés et acomptes."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class DemandeCongeCreate(BaseModel):
    """Demande de congés déposée par le salarié connecté."""
    date_debut: date
    date_fin: date
    motif: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _dates_coherentes(self):
        if self.date_fin < self.date_debut:
            raise ValueError("La date de fin doit être postérieure ou égale au début.")
        return self


class DemandeCongeOut(BaseModel):
    id: int
    salarie_id: int
    date_debut: date
    date_fin: date
    nombre_jours: float
    motif: Optional[str] = None
    statut: str
    commentaire_gestionnaire: Optional[str] = None
    date_decision: Optional[datetime] = None
    absence_id: Optional[int] = None
    created_at: datetime
    #: Identité du salarié, pour la file de validation du gestionnaire.
    salarie_nom: Optional[str] = None
    salarie_prenom: Optional[str] = None
    matricule: Optional[str] = None

    class Config:
        from_attributes = True


class DemandeAcompteCreate(BaseModel):
    """Demande d'acompte sur la paie d'un mois précis."""
    montant: float = Field(gt=0)
    mois: int = Field(ge=1, le=12)
    annee: int = Field(ge=2000, le=2100)
    motif: Optional[str] = Field(default=None, max_length=1000)


class DemandeAcompteOut(BaseModel):
    id: int
    salarie_id: int
    montant: float
    mois: int
    #: Stockée en texte (comme les absences) pour rester homogène avec la paie.
    annee: str
    motif: Optional[str] = None
    statut: str
    commentaire_gestionnaire: Optional[str] = None
    date_decision: Optional[datetime] = None
    created_at: datetime
    salarie_nom: Optional[str] = None
    salarie_prenom: Optional[str] = None
    matricule: Optional[str] = None

    class Config:
        from_attributes = True


class DecisionDemande(BaseModel):
    """Décision du gestionnaire entreprise : validation ou refus motivé."""
    commentaire: Optional[str] = Field(default=None, max_length=1000)


class SoldeCongesOut(BaseModel):
    """Solde de congés payés du salarié connecté, à un mois donné."""
    annee: int
    mois: int
    acquis: float
    pris: float
    pris_ce_mois: float
    solde: float
    mois_anciennete: int
    debut_anciennete: date
    #: Vrai lorsque le mois demandé précède le début du contrat.
    periode_avant_contrat: bool
