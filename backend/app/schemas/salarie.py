from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SalarieBase(BaseModel):
    matricule: Optional[str] = None
    nom: str
    prenom: str
    nom_usage: Optional[str] = None
    civilite: Optional[str] = None
    date_naissance: Optional[datetime] = None
    lieu_naissance: Optional[str] = None
    departement_naissance: Optional[str] = None
    pays_naissance: Optional[str] = None
    nationalite: Optional[str] = None
    numero_securite_sociale: Optional[str] = None
    adresse: Optional[str] = None
    adresse2: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = "France"
    email: Optional[str] = None
    telephone: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    is_active: Optional[bool] = True
    expatrie: Optional[bool] = False
    situation_matrimoniale: Optional[str] = None
    enfants_charge: Optional[int] = 0


class SalarieCreate(SalarieBase):
    pass


class SalarieUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    nom_usage: Optional[str] = None
    civilite: Optional[str] = None
    date_naissance: Optional[datetime] = None
    lieu_naissance: Optional[str] = None
    departement_naissance: Optional[str] = None
    pays_naissance: Optional[str] = None
    nationalite: Optional[str] = None
    numero_securite_sociale: Optional[str] = None
    adresse: Optional[str] = None
    adresse2: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    pays: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    is_active: Optional[bool] = None
    expatrie: Optional[bool] = None
    situation_matrimoniale: Optional[str] = None
    enfants_charge: Optional[int] = None


class SalarieOut(SalarieBase):
    id: int
    etablissement_id: int
    created_at: datetime
    updated_at: datetime
    #: Résultat de l'envoi des identifiants d'accès par email (création d'un
    #: compte, renvoi). `None` lorsqu'aucun compte n'a été créé à cette occasion.
    acces_email_envoye: Optional[bool] = None
    acces_email_message: Optional[str] = None
    #: Mot de passe provisoire, renvoyé UNE SEULE FOIS à la création du compte
    #: (utile si l'email n'a pas pu partir).
    mot_de_passe_initial: Optional[str] = None

    class Config:
        from_attributes = True
