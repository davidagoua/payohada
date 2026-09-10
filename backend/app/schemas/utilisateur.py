from pydantic import BaseModel, EmailStr
from typing import Optional


class UtilisateurBase(BaseModel):
    email: EmailStr
    nom: Optional[str] = None
    prenom: Optional[str] = None
    role: str = "cabinet" # "cabinet", "client", "salarie"
    dossier_id: Optional[int] = None


class UtilisateurCreate(UtilisateurBase):
    supabase_uid: str


class UtilisateurOut(UtilisateurBase):
    id: int
    supabase_uid: str
    is_active: bool
    is_admin: bool
    salarie_id: Optional[int] = None
    nom_dossier: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class CompteClientCreate(BaseModel):
    email: EmailStr
    nom: str
    prenom: str
    password: Optional[str] = "Payohada@123"

