from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DepartementBase(BaseModel):
    nom: str
    code: Optional[str] = None
    description: Optional[str] = None


class DepartementCreate(DepartementBase):
    pass


class DepartementUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class DepartementOut(DepartementBase):
    id: int
    dossier_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
