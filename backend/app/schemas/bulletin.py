from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────────
#  SCHÉMAS LIGNE BULLETIN PAIE
# ─────────────────────────────────────────

class LigneBulletinPaieBase(BaseModel):
    code: str
    libelle: Optional[str] = None
    salaire_base: Optional[float] = 0.0
    base_s: Optional[float] = 0.0
    base_p: Optional[float] = 0.0
    taux_s: Optional[float] = 0.0
    taux_p: Optional[float] = 0.0
    montant_pr: Optional[float] = 0.0
    montant_cs: Optional[float] = 0.0
    montant_cp: Optional[float] = 0.0


class LigneBulletinPaieOut(LigneBulletinPaieBase):
    id: int
    bulletin_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS VARIABLE BULLETIN
# ─────────────────────────────────────────

class VariableBulletinBase(BaseModel):
    code: str
    libelle: Optional[str] = None
    valeur: Optional[float] = 0.0


class VariableBulletinOut(VariableBulletinBase):
    id: int
    bulletin_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS BULLETIN PAIE
# ─────────────────────────────────────────

class BulletinPaieBase(BaseModel):
    mois: int
    annee: int
    statut: Optional[str] = "brouillon"
    date_paiement: Optional[datetime] = None
    salaire_brut: Optional[float] = 0.0
    cotisations_salariales: Optional[float] = 0.0
    cotisations_patronales: Optional[float] = 0.0
    net_a_payer: Optional[float] = 0.0
    net_imposable: Optional[float] = 0.0
    commentaire: Optional[str] = None
    inclure_document_de_sortie: Optional[bool] = False


class BulletinPaieCreate(BaseModel):
    contrat_id: int
    mois: int
    annee: int
    commentaire: Optional[str] = None
    acompte: Optional[float] = 0.0


class BulletinCumulRow(BaseModel):
    heures_jours: Optional[float] = 0.0
    heures_supp: Optional[float] = 0.0
    jours_absences: Optional[float] = 0.0
    salaire_brut: Optional[float] = 0.0
    brut_imposable: Optional[float] = 0.0
    brut_cnps: Optional[float] = 0.0
    brut_conges: Optional[float] = 0.0
    ibs: Optional[float] = 0.0
    ricf: Optional[float] = 0.0
    cmu: Optional[float] = 0.0
    cot_retraite: Optional[float] = 0.0

class BulletinCumuls(BaseModel):
    mensuel: BulletinCumulRow
    annuel: BulletinCumulRow

class BulletinPaieOut(BulletinPaieBase):
    id: int
    contrat_id: int
    dossier_id: int
    created_at: datetime
    updated_at: datetime
    lignes: List[LigneBulletinPaieOut] = []
    variables_bulletin: List[VariableBulletinOut] = []
    cumuls: Optional[BulletinCumuls] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS SOLDE TOUT COMPTE
# ─────────────────────────────────────────

class SoldeToutCompteBase(BaseModel):
    indemnite_licenciement: Optional[float] = 0.0
    indemnite_conges_payes: Optional[float] = 0.0
    indemnite_preavis: Optional[float] = 0.0
    indemnite_autre: Optional[float] = 0.0
    total: Optional[float] = 0.0
    statut: Optional[str] = "genere"
    commentaire: Optional[str] = None


class SoldeToutCompteCreate(SoldeToutCompteBase):
    contrat_id: int


class SoldeToutCompteOut(SoldeToutCompteBase):
    id: int
    contrat_id: int
    date_generation: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS DSN
# ─────────────────────────────────────────

class DSNBase(BaseModel):
    mois: int
    annee: int
    statut: Optional[str] = "en_attente"
    contenu_txt: Optional[str] = None
    date_envoi: Optional[datetime] = None
    reference_envoi: Optional[str] = None


class DSNCreate(BaseModel):
    etablissement_id: int
    mois: int
    annee: int


class DSNOut(DSNBase):
    id: int
    dossier_id: int
    etablissement_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS SIMULATION
# ─────────────────────────────────────────

class SimulationAbsenceInput(BaseModel):
    code: str
    nbr_heures: Optional[float] = 0.0
    nbr_jours: Optional[float] = 0.0

class SimulationHeureSupInput(BaseModel):
    code: str
    nombre: float

class SimulationPrimeInput(BaseModel):
    code: str
    libelle: Optional[str] = None
    montant: float
    base: Optional[float] = None
    taux: Optional[float] = None

class SimulationInput(BaseModel):
    salaire_mensuel: Optional[float] = 0.0
    salaire_horaire: Optional[float] = 0.0
    type_salaire: str = "Mensuel"  # "Mensuel" ou "Horaire"
    horaire_mensuel_standard: Optional[float] = 173.33
    taux_at: Optional[float] = 3.0
    unite_temps: Optional[str] = "Heures"
    sursalaire: Optional[float] = 0.0
    expatrie: Optional[bool] = False
    indemnite_transport: Optional[float] = 0.0
    dotation_telephonique: Optional[float] = 0.0
    acompte: Optional[float] = 0.0
    absences: List[SimulationAbsenceInput] = []
    heures_sup: List[SimulationHeureSupInput] = []
    primes: List[SimulationPrimeInput] = []
    mode_calcul: Optional[str] = "base"  # "base", "brut" ou "net"

class LigneSimulationOut(BaseModel):
    code: str
    libelle: Optional[str] = None
    salaire_base: Optional[float] = 0.0
    base_s: Optional[float] = 0.0
    base_p: Optional[float] = 0.0
    taux_s: Optional[float] = 0.0
    taux_p: Optional[float] = 0.0
    montant_pr: Optional[float] = 0.0
    montant_cs: Optional[float] = 0.0
    montant_cp: Optional[float] = 0.0

class SimulationOut(BaseModel):
    salaire_brut: float
    cotisations_salariales: float
    cotisations_patronales: float
    net_a_payer: float
    net_imposable: float
    lignes: List[LigneSimulationOut]
    cumuls: Optional[BulletinCumuls] = None
