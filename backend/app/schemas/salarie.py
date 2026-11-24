from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

from app.schemas.mode_paiement import ModePaiementOut


#: Longueur usuelle d'un numéro d'immatriculation CNPS.
LONGUEUR_NUMERO_CNPS = 12


def normaliser_numero_cnps(valeur):
    """« 2021 0010 8350 » → « 202100108350 » ; refuse tout caractère non numérique.

    La longueur n'est pas imposée (anciens numéros), mais la déclaration
    signale un numéro qui n'a pas 12 chiffres.
    """
    if valeur is None:
        return None
    numero = "".join(c for c in str(valeur) if c not in " .-/")
    if not numero:
        return None
    if not numero.isdigit():
        raise ValueError("Le N° CNPS ne contient que des chiffres.")
    if len(numero) > 15:
        raise ValueError("Le N° CNPS comporte au plus 15 chiffres.")
    return numero


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
    #: Mode de versement du salaire, parmi ceux de l'établissement.
    mode_paiement_id: Optional[int] = None
    is_active: Optional[bool] = True
    expatrie: Optional[bool] = False
    situation_matrimoniale: Optional[str] = None
    enfants_charge: Optional[int] = 0


class SalarieCreate(SalarieBase):
    @field_validator("numero_securite_sociale")
    @classmethod
    def _numero_cnps(cls, valeur):
        return normaliser_numero_cnps(valeur)


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
    mode_paiement_id: Optional[int] = None
    is_active: Optional[bool] = None
    expatrie: Optional[bool] = None
    situation_matrimoniale: Optional[str] = None
    enfants_charge: Optional[int] = None

    @field_validator("numero_securite_sociale")
    @classmethod
    def _numero_cnps(cls, valeur):
        return normaliser_numero_cnps(valeur)


class SalarieOut(SalarieBase):
    id: int
    etablissement_id: int
    created_at: datetime
    updated_at: datetime
    mode_paiement: Optional[ModePaiementOut] = None
    #: Résultat de l'envoi des identifiants d'accès par email (création d'un
    #: compte, renvoi). `None` lorsqu'aucun compte n'a été créé à cette occasion.
    acces_email_envoye: Optional[bool] = None
    acces_email_message: Optional[str] = None
    #: Mot de passe provisoire, renvoyé UNE SEULE FOIS à la création du compte
    #: (utile si l'email n'a pas pu partir).
    mot_de_passe_initial: Optional[str] = None

    class Config:
        from_attributes = True
