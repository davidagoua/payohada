from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReclamationBase(BaseModel):
    bulletin_id: int
    sujet: str
    description: str

class ReclamationCreate(ReclamationBase):
    pass

class ReclamationUpdate(BaseModel):
    statut: str  # "en_attente", "traite", "rejete"
    commentaire_gestionnaire: Optional[str] = None

class ReclamationOut(ReclamationBase):
    id: int
    salarie_id: int
    statut: str
    commentaire_gestionnaire: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Extra fields for UI convenience
    salarie_nom: Optional[str] = None
    salarie_prenom: Optional[str] = None
    bulletin_mois: Optional[int] = None
    bulletin_annee: Optional[int] = None

    class Config:
        from_attributes = True
