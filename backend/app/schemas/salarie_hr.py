from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


# ─────────────────────────────────────────
#  ENTRETIENS EVALUATIONS
# ─────────────────────────────────────────

class EntretienEvaluationBase(BaseModel):
    date_entretien: date
    nom_evaluateur: str
    note_globale: Optional[float] = None
    commentaires: Optional[str] = None


class EntretienEvaluationCreate(EntretienEvaluationBase):
    pass


class EntretienEvaluationUpdate(BaseModel):
    date_entretien: Optional[date] = None
    nom_evaluateur: Optional[str] = None
    note_globale: Optional[float] = None
    commentaires: Optional[str] = None


class EntretienEvaluationOut(EntretienEvaluationBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  VISITES MEDICALES
# ─────────────────────────────────────────

class VisiteMedicaleBase(BaseModel):
    date_visite: date
    type_visite: str  # Embauche, Reprise, Périodique
    aptitude: str     # Apte, Inapte, Apte avec réserves
    prochaine_visite: Optional[date] = None


class VisiteMedicaleCreate(VisiteMedicaleBase):
    pass


class VisiteMedicaleUpdate(BaseModel):
    date_visite: Optional[date] = None
    type_visite: Optional[str] = None
    aptitude: Optional[str] = None
    prochaine_visite: Optional[date] = None


class VisiteMedicaleOut(VisiteMedicaleBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SUIVI FORMATIONS
# ─────────────────────────────────────────

class SuiviFormationBase(BaseModel):
    intitule_formation: str
    organisme: str
    date_debut: date
    date_fin: date
    statut_formation: str  # Demandée, En cours, Terminée


class SuiviFormationCreate(SuiviFormationBase):
    pass


class SuiviFormationUpdate(BaseModel):
    intitule_formation: Optional[str] = None
    organisme: Optional[str] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    statut_formation: Optional[str] = None


class SuiviFormationOut(SuiviFormationBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SALARIÉ ABSENCES
# ─────────────────────────────────────────

class SalarieAbsenceBase(BaseModel):
    type_absence: str  # Congés payés, Maladie, Maternité/Paternité, Sans solde
    date_debut_absence: date
    date_fin_absence: date
    justificatif_fourni: Optional[bool] = False


class SalarieAbsenceCreate(SalarieAbsenceBase):
    pass


class SalarieAbsenceUpdate(BaseModel):
    type_absence: Optional[str] = None
    date_debut_absence: Optional[date] = None
    date_fin_absence: Optional[date] = None
    justificatif_fourni: Optional[bool] = None


class SalarieAbsenceOut(SalarieAbsenceBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  PRÊTS SALARIÉS
# ─────────────────────────────────────────

class PretSalarieBase(BaseModel):
    montant_pret: float
    date_deblocage: date
    montant_mensualite: float
    reste_a_rembourser: float


class PretSalarieCreate(PretSalarieBase):
    pass


class PretSalarieUpdate(BaseModel):
    montant_pret: Optional[float] = None
    date_deblocage: Optional[date] = None
    montant_mensualite: Optional[float] = None
    reste_a_rembourser: Optional[float] = None


class PretSalarieOut(PretSalarieBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SALARIÉ CONTRAT INFO
# ─────────────────────────────────────────

class SalarieContratInfoBase(BaseModel):
    type_contrat: str  # CDI, CDD, Apprentissage, Stage
    date_embauche: date
    date_fin_contrat: Optional[date] = None
    fin_periode_essai: Optional[date] = None


class SalarieContratInfoCreate(SalarieContratInfoBase):
    pass


class SalarieContratInfoUpdate(BaseModel):
    type_contrat: Optional[str] = None
    date_embauche: Optional[date] = None
    date_fin_contrat: Optional[date] = None
    fin_periode_essai: Optional[date] = None


class SalarieContratInfoOut(SalarieContratInfoBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SALARIÉ SERVICE
# ─────────────────────────────────────────

class SalarieServiceBase(BaseModel):
    departement: str
    poste_occupe: str
    manager: str
    dotation_materiel: Optional[str] = None


class SalarieServiceCreate(SalarieServiceBase):
    pass


class SalarieServiceUpdate(BaseModel):
    departement: Optional[str] = None
    poste_occupe: Optional[str] = None
    manager: Optional[str] = None
    dotation_materiel: Optional[str] = None


class SalarieServiceOut(SalarieServiceBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  ARCHIVAGE DOCUMENT
# ─────────────────────────────────────────

class ArchivageDocumentBase(BaseModel):
    type_document: str
    fichier_joint: Optional[str] = None
    date_ajout: date


class ArchivageDocumentCreate(ArchivageDocumentBase):
    pass


class ArchivageDocumentUpdate(BaseModel):
    type_document: Optional[str] = None
    fichier_joint: Optional[str] = None
    date_ajout: Optional[date] = None


class ArchivageDocumentOut(ArchivageDocumentBase):
    id: int
    salarie_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
