import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import (
    Utilisateur, EntretienEvaluation, VisiteMedicale, SuiviFormation,
    SalarieAbsence, PretSalarie, SalarieContratInfo, SalarieService,
    ArchivageDocument
)
from app.schemas.salarie_hr import (
    EntretienEvaluationCreate, EntretienEvaluationUpdate, EntretienEvaluationOut,
    VisiteMedicaleCreate, VisiteMedicaleUpdate, VisiteMedicaleOut,
    SuiviFormationCreate, SuiviFormationUpdate, SuiviFormationOut,
    SalarieAbsenceCreate, SalarieAbsenceUpdate, SalarieAbsenceOut,
    PretSalarieCreate, PretSalarieUpdate, PretSalarieOut,
    SalarieContratInfoCreate, SalarieContratInfoUpdate, SalarieContratInfoOut,
    SalarieServiceCreate, SalarieServiceUpdate, SalarieServiceOut,
    ArchivageDocumentCreate, ArchivageDocumentUpdate, ArchivageDocumentOut
)
from app.services.security import get_current_user
from app.routers.salaries import check_salarie_ownership

router = APIRouter(prefix="/salaries", tags=["Salariés RH"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────
#  FICHIER UPLOAD
# ─────────────────────────────────────────

@router.post("/{salarie_id}/upload-document")
async def upload_document(
    salarie_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{salarie_id}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": file.filename, "url": f"/uploads/{unique_filename}"}


# ─────────────────────────────────────────
#  ENTRETIENS EVALUATIONS
# ─────────────────────────────────────────

@router.get("/{salarie_id}/entretiens", response_model=List[EntretienEvaluationOut])
def get_entretiens(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(EntretienEvaluation).filter(EntretienEvaluation.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/entretiens", response_model=EntretienEvaluationOut)
def create_entretien(
    salarie_id: int,
    entretien_in: EntretienEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = EntretienEvaluation(**entretien_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/entretiens/{id}", response_model=EntretienEvaluationOut)
def update_entretien(
    id: int,
    entretien_in: EntretienEvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(EntretienEvaluation).filter(EntretienEvaluation.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Entretien introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in entretien_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/entretiens/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entretien(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(EntretienEvaluation).filter(EntretienEvaluation.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Entretien introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None


# ─────────────────────────────────────────
#  VISITES MEDICALES
# ─────────────────────────────────────────

@router.get("/{salarie_id}/visites-medicales", response_model=List[VisiteMedicaleOut])
def get_visites(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(VisiteMedicale).filter(VisiteMedicale.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/visites-medicales", response_model=VisiteMedicaleOut)
def create_visite(
    salarie_id: int,
    visite_in: VisiteMedicaleCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = VisiteMedicale(**visite_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/visites-medicales/{id}", response_model=VisiteMedicaleOut)
def update_visite(
    id: int,
    visite_in: VisiteMedicaleUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(VisiteMedicale).filter(VisiteMedicale.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Visite médicale introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in visite_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/visites-medicales/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visite(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(VisiteMedicale).filter(VisiteMedicale.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Visite médicale introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None


# ─────────────────────────────────────────
#  SUIVI FORMATIONS
# ─────────────────────────────────────────

@router.get("/{salarie_id}/formations", response_model=List[SuiviFormationOut])
def get_formations(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(SuiviFormation).filter(SuiviFormation.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/formations", response_model=SuiviFormationOut)
def create_formation(
    salarie_id: int,
    formation_in: SuiviFormationCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = SuiviFormation(**formation_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/formations/{id}", response_model=SuiviFormationOut)
def update_formation(
    id: int,
    formation_in: SuiviFormationUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SuiviFormation).filter(SuiviFormation.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Formation introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in formation_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/formations/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_formation(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SuiviFormation).filter(SuiviFormation.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Formation introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None


# ─────────────────────────────────────────
#  SALARIÉ ABSENCES
# ─────────────────────────────────────────

@router.get("/{salarie_id}/absences-hr", response_model=List[SalarieAbsenceOut])
def get_absences_hr(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(SalarieAbsence).filter(SalarieAbsence.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/absences-hr", response_model=SalarieAbsenceOut)
def create_absence_hr(
    salarie_id: int,
    absence_in: SalarieAbsenceCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = SalarieAbsence(**absence_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/absences-hr/{id}", response_model=SalarieAbsenceOut)
def update_absence_hr(
    id: int,
    absence_in: SalarieAbsenceUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SalarieAbsence).filter(SalarieAbsence.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Absence introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in absence_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/absences-hr/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_absence_hr(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SalarieAbsence).filter(SalarieAbsence.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Absence introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None


# ─────────────────────────────────────────
#  PRÊTS SALARIÉS
# ─────────────────────────────────────────

@router.get("/{salarie_id}/prets", response_model=List[PretSalarieOut])
def get_prets(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(PretSalarie).filter(PretSalarie.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/prets", response_model=PretSalarieOut)
def create_pret(
    salarie_id: int,
    pret_in: PretSalarieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = PretSalarie(**pret_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/prets/{id}", response_model=PretSalarieOut)
def update_pret(
    id: int,
    pret_in: PretSalarieUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(PretSalarie).filter(PretSalarie.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Prêt introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in pret_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/prets/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pret(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(PretSalarie).filter(PretSalarie.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Prêt introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None


# ─────────────────────────────────────────
#  SALARIÉ CONTRAT INFO
# ─────────────────────────────────────────

@router.get("/{salarie_id}/contrats-info", response_model=List[SalarieContratInfoOut])
def get_contrats_info(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(SalarieContratInfo).filter(SalarieContratInfo.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/contrats-info", response_model=SalarieContratInfoOut)
def create_contrat_info(
    salarie_id: int,
    contrat_in: SalarieContratInfoCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = SalarieContratInfo(**contrat_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/contrats-info/{id}", response_model=SalarieContratInfoOut)
def update_contrat_info(
    id: int,
    contrat_in: SalarieContratInfoUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SalarieContratInfo).filter(SalarieContratInfo.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Informations de contrat introuvables.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in contrat_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/contrats-info/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contrat_info(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SalarieContratInfo).filter(SalarieContratInfo.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Informations de contrat introuvables.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None


# ─────────────────────────────────────────
#  SALARIÉ SERVICES
# ─────────────────────────────────────────

@router.get("/{salarie_id}/services", response_model=List[SalarieServiceOut])
def get_services(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(SalarieService).filter(SalarieService.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/services", response_model=SalarieServiceOut)
def create_service(
    salarie_id: int,
    service_in: SalarieServiceCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = SalarieService(**service_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/services/{id}", response_model=SalarieServiceOut)
def update_service(
    id: int,
    service_in: SalarieServiceUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SalarieService).filter(SalarieService.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Informations de service introuvables.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in service_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/services/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(SalarieService).filter(SalarieService.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Informations de service introuvables.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    db.delete(db_item)
    db.commit()
    return None


# ─────────────────────────────────────────
#  ARCHIVAGE DOCUMENT
# ─────────────────────────────────────────

@router.get("/{salarie_id}/archivages", response_model=List[ArchivageDocumentOut])
def get_archivages(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    return db.query(ArchivageDocument).filter(ArchivageDocument.salarie_id == salarie_id).all()


@router.post("/{salarie_id}/archivages", response_model=ArchivageDocumentOut)
def create_archivage(
    salarie_id: int,
    archivage_in: ArchivageDocumentCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    check_salarie_ownership(salarie_id, current_user.id, db)
    db_item = ArchivageDocument(**archivage_in.model_dump(), salarie_id=salarie_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/archivages/{id}", response_model=ArchivageDocumentOut)
def update_archivage(
    id: int,
    archivage_in: ArchivageDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(ArchivageDocument).filter(ArchivageDocument.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Document archivé introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    for field, value in archivage_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/archivages/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_archivage(
    id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    db_item = db.query(ArchivageDocument).filter(ArchivageDocument.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Document archivé introuvable.")
    check_salarie_ownership(db_item.salarie_id, current_user.id, db)
    # Optional: Delete actual file from disk if we want to clean up
    if db_item.fichier_joint:
        try:
            filename = db_item.fichier_joint.split("/uploads/")[-1]
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print("Error deleting document file:", e)
            
    db.delete(db_item)
    db.commit()
    return None
