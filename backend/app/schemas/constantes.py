from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ConstanteBase(BaseModel):
    code: str
    description: str
    montant: float = 0.0
    unite: Optional[str] = None
    pays: str = "CI"
    est_actif: bool = True

class ConstanteCreate(ConstanteBase):
    pass

class ConstanteUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    montant: Optional[float] = None
    unite: Optional[str] = None
    pays: Optional[str] = None
    est_actif: Optional[bool] = None

class ConstanteOut(ConstanteBase):
    id: int
    date_creation: datetime
    date_modification: datetime

    class Config:
        from_attributes = True
