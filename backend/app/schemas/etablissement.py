from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────
#  SCHÉMAS ADRESSE ETABLISSEMENT
# ─────────────────────────────────────────

class AdresseEtablissementBase(BaseModel):
    adresse_postale: Optional[str] = None
    adresse_postale2: Optional[str] = None
    complement_adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    code_insee: Optional[str] = None
    code_distribution_etranger: Optional[str] = None
    pays: Optional[str] = "France"


class AdresseEtablissementCreate(AdresseEtablissementBase):
    pass


class AdresseEtablissementOut(AdresseEtablissementBase):
    id: int
    etablissement_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS GESTION CONGES PAYES
# ─────────────────────────────────────────

class GestionCongesPayesBase(BaseModel):
    mois_cloture_droits_cp: Optional[int] = 5
    report_automatique: Optional[bool] = True
    gestion_absences_heures_bulletins: Optional[bool] = True
    decompte_conges_payes: Optional[str] = "ouvrables"
    valorisation_conges_payes: Optional[str] = "maintien"
    bloquer_gestion_cp: Optional[bool] = False
    affilie_caisse_conges_payes: Optional[bool] = False


class GestionCongesPayesCreate(GestionCongesPayesBase):
    pass


class GestionCongesPayesOut(GestionCongesPayesBase):
    id: int
    etablissement_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS BANQUE ETABLISSEMENT
# ─────────────────────────────────────────

class BanqueEtablissementBase(BaseModel):
    virement: Optional[bool] = False
    code_bic: Optional[str] = None
    iban: Optional[str] = None


class BanqueEtablissementCreate(BanqueEtablissementBase):
    pass


class BanqueEtablissementOut(BanqueEtablissementBase):
    id: int
    etablissement_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS ETABLISSEMENT
# ─────────────────────────────────────────

class EtablissementBase(BaseModel):
    code: str
    raison_sociale: str
    etablissement_principal: Optional[bool] = False
    siret: Optional[str] = None
    forme_juridique: Optional[int] = None
    civilite: Optional[str] = None
    activite: Optional[str] = None
    ape: Optional[str] = None
    libelle_ape: Optional[str] = None
    ccn: Optional[int] = None
    ccn2: Optional[int] = None
    ccn3: Optional[int] = None
    ccn4: Optional[int] = None
    ccn5: Optional[int] = None
    avenant: Optional[bool] = False
    numero_cotisant: Optional[str] = None
    date_radiation: Optional[datetime] = None
    code_risque_at: Optional[str] = None
    taux_at: Optional[float] = 0.0
    is_taux_versement_transport: Optional[bool] = False
    taux_versement_transport: Optional[float] = 0.0
    cnps_matricule: Optional[str] = None
    cnps_code_activite: Optional[str] = None
    cnps_code_agence: Optional[str] = None
    cnps_code_etablissement: Optional[str] = None
    cnps_agence_rattachement: Optional[str] = None
    cnps_periodicite_paiement: Optional[str] = None
    cmu_periodicite_paiement: Optional[str] = None
    dgi_compte_contribuable: Optional[str] = None
    dgi_centre_impots: Optional[str] = None
    dgi_periodicite_declaration: Optional[str] = None
    dgi_regime_fiscal: Optional[str] = None


class EtablissementCreate(EtablissementBase):
    adresse: Optional[AdresseEtablissementCreate] = None
    banque: Optional[BanqueEtablissementCreate] = None
    gestion_conges: Optional[GestionCongesPayesCreate] = None


class EtablissementUpdate(BaseModel):
    raison_sociale: Optional[str] = None
    etablissement_principal: Optional[bool] = None
    siret: Optional[str] = None
    forme_juridique: Optional[int] = None
    civilite: Optional[str] = None
    activite: Optional[str] = None
    ape: Optional[str] = None
    libelle_ape: Optional[str] = None
    ccn: Optional[int] = None
    ccn2: Optional[int] = None
    ccn3: Optional[int] = None
    ccn4: Optional[int] = None
    ccn5: Optional[int] = None
    avenant: Optional[bool] = None
    numero_cotisant: Optional[str] = None
    date_radiation: Optional[datetime] = None
    code_risque_at: Optional[str] = None
    taux_at: Optional[float] = None
    is_taux_versement_transport: Optional[bool] = None
    taux_versement_transport: Optional[float] = None
    cnps_matricule: Optional[str] = None
    cnps_code_activite: Optional[str] = None
    cnps_code_agence: Optional[str] = None
    cnps_code_etablissement: Optional[str] = None
    cnps_agence_rattachement: Optional[str] = None
    cnps_periodicite_paiement: Optional[str] = None
    cmu_periodicite_paiement: Optional[str] = None
    dgi_compte_contribuable: Optional[str] = None
    dgi_centre_impots: Optional[str] = None
    dgi_periodicite_declaration: Optional[str] = None
    dgi_regime_fiscal: Optional[str] = None
    adresse: Optional[AdresseEtablissementCreate] = None
    banque: Optional[BanqueEtablissementCreate] = None


class EtablissementOut(EtablissementBase):
    id: int
    dossier_id: int
    created_at: datetime
    updated_at: datetime
    adresse: Optional[AdresseEtablissementOut] = None
    banque: Optional[BanqueEtablissementOut] = None
    gestion_conges: Optional[GestionCongesPayesOut] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS CAISSE COTISATION
# ─────────────────────────────────────────

class CaisseCotisationBase(BaseModel):
    nom_caisse: Optional[str] = None
    code_dsn: Optional[str] = None
    adresse_caisse: Optional[str] = None
    type_cotisation: str
    exclus_de_calcul_dsn: Optional[bool] = False
    numero_affiliation: Optional[str] = None
    type_paiement: Optional[str] = None
    periodicite_paiement: Optional[str] = None
    date_paiement: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None


class CaisseCotisationCreate(CaisseCotisationBase):
    pass


class CaisseCotisationOut(CaisseCotisationBase):
    id: int
    etablissement_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
