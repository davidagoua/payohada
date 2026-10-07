from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional


RoleUtilisateur = Literal["cabinet", "client", "salarie"]


class UtilisateurBase(BaseModel):
    email: EmailStr
    nom: Optional[str] = None
    prenom: Optional[str] = None
    role: RoleUtilisateur = "cabinet"
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
    cabinet_nom: Optional[str] = None
    cabinet_telephone: Optional[str] = None
    cabinet_ville: Optional[str] = None
    #: `True` lorsque l'utilisateur doit définir son propre mot de passe.
    is_default_password: Optional[bool] = False
    #: Mot de passe généré, renvoyé UNE SEULE FOIS à la création du compte.
    mot_de_passe_initial: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class MotDePasseOublieRequest(BaseModel):
    """Demande d'envoi d'un lien de réinitialisation."""
    email: EmailStr


class ReinitialisationMotDePasseRequest(BaseModel):
    """Consommation d'un lien de réinitialisation."""
    token: str = Field(min_length=16, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class CompteClientCreate(BaseModel):
    email: EmailStr
    nom: str
    prenom: str
    #: Laisser vide pour que le serveur génère un mot de passe aléatoire
    #: (recommandé : plus aucun mot de passe partagé par défaut).
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class CabinetSignupRequest(BaseModel):
    """Données nécessaires pour la création d'un compte cabinet."""
    # Identité du responsable
    prenom: str
    nom: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # Informations du cabinet
    cabinet_nom: str
    cabinet_telephone: Optional[str] = None
    cabinet_ville: Optional[str] = None
