from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PlanPaieBase(BaseModel):
    type: str  # B, I, NS, C, A
    code: str
    libelle: str
    mode_calcul: str = "Sémi-auto"
    sens: str = "Gain"
    masque_si_nul: bool = False
    imprimable: bool = True
    compte_debit: Optional[str] = None
    compte_credit: Optional[str] = None
    pays: str = "CI"
    est_actif: bool = True

class PlanPaieCreate(PlanPaieBase):
    pass

class PlanPaieUpdate(BaseModel):
    type: Optional[str] = None
    code: Optional[str] = None
    libelle: Optional[str] = None
    mode_calcul: Optional[str] = None
    sens: Optional[str] = None
    masque_si_nul: Optional[bool] = None
    imprimable: Optional[bool] = None
    compte_debit: Optional[str] = None
    compte_credit: Optional[str] = None
    pays: Optional[str] = None
    est_actif: Optional[bool] = None

class PlanPaieOut(PlanPaieBase):
    id: int
    date_creation: datetime
    date_modification: datetime

    class Config:
        from_attributes = True
