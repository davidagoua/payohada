"""Schémas du référentiel des modes de paiement des salaires."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModePaiementBase(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    libelle: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    est_actif: bool = True
    ordre: int = 0


class ModePaiementCreate(ModePaiementBase):
    pass


class ModePaiementUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=30)
    libelle: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    est_actif: Optional[bool] = None
    ordre: Optional[int] = None


class ModePaiementOut(ModePaiementBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
