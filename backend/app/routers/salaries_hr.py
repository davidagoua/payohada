import os
import shutil
import uuid
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from app.config import settings
from app.database import get_db
from app.models.models import (
    Utilisateur, EntretienEvaluation, VisiteMedicale, SuiviFormation,
    SalarieAbsence, PretSalarie, SalarieContratInfo, SalarieService,
    ArchivageDocument, Contrat, BulletinPaie
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
from app.services.payroll import calculate_payslip

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/salaries", tags=["Salariés RH"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────
#  FICHIER UPLOAD
# ─────────────────────────────────────────

def _validate_upload(file: UploadFile) -> str:
    """Contrôle l'extension et la taille du fichier téléversé.

    Retourne l'extension normalisée. Lève une 400/413 explicite sinon.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if not ext or ext not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Type de fichier non autorisé. Extensions acceptées : "
                + ", ".join(sorted(settings.allowed_upload_extensions))
            ),
        )

    # Taille : on lit le flux par blocs pour ne pas charger tout en mémoire.
    max_size = settings.MAX_UPLOAD_SIZE_BYTES
    total = 0
    try:
        file.file.seek(0)
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=(
                        "Fichier trop volumineux "
                        f"(maximum {max_size // (1024 * 1024)} Mo)."
                    ),
                )
    finally:
        file.file.seek(0)

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )

    return ext


@router.post("/{salarie_id}/upload-document")
async def upload_document(
    salarie_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Téléverse une pièce jointe RH pour un salarié.

    Le nom de fichier est généré côté serveur (`<salarie_id>_<uuid><ext>`) :
    le nom fourni par le client n'est jamais utilisé pour construire le chemin.
    """
    check_salarie_ownership(salarie_id, current_user.id, db)
    ext = _validate_upload(file)
    unique_filename = f"{salarie_id}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Le fichier n'est plus exposé publiquement : il est servi par
    # l'endpoint authentifié ci-dessous.
    return {
        "filename": file.filename,
        "url": f"/api/v1/salaries/documents/{unique_filename}",
    }


@router.get("/documents/{filename}")
def download_document(
    filename: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Sert une pièce jointe après contrôle d'accès.

    Le préfixe du nom (`<salarie_id>_…`) permet de retrouver le salarié
    propriétaire et d'appliquer la même règle de portée que le reste de l'API.
    """
    # Anti-traversée : un seul segment, pas de séparateur ni de « .. ».
    if not filename or os.path.basename(filename) != filename or filename.startswith("."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de fichier invalide.")

    try:
        salarie_id = int(filename.split("_", 1)[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    check_salarie_ownership(salarie_id, current_user.id, db)

    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    return FileResponse(file_path, filename=filename)


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


def auto_recalculate_payslips(db: Session, salarie_id: int, start_date: date, end_date: date):
    """Recherche et recalcule automatiquement les bulletins de paie brouillons chevauchant l'absence."""
    contracts = db.query(Contrat).filter(Contrat.salarie_id == salarie_id).all()
    contract_ids = [c.id for c in contracts]
    if not contract_ids:
        return
        
    # Déterminer la liste des mois et années concernés par l'absence
    months = []
    current = start_date
    while current <= end_date:
        months.append((current.month, current.year))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
            
    for c_id in contract_ids:
        for m, y in months:
            bulletin = db.query(BulletinPaie).filter(
                BulletinPaie.contrat_id == c_id,
                BulletinPaie.mois == m,
                BulletinPaie.annee == y
            ).first()
            if bulletin and bulletin.statut != "valide":
                try:
                    # Préserver l'acompte
                    from app.models.models import LigneBulletinPaie
                    acompte_line = db.query(LigneBulletinPaie).filter(
                        LigneBulletinPaie.bulletin_id == bulletin.id,
                        LigneBulletinPaie.code == "ACOMPTE"
                    ).first()
                    acompte_val = acompte_line.montant_cs if acompte_line else 0.0
                    
                    calculate_payslip(db, contrat_id=c_id, mois=m, annee=y, acompte=acompte_val)
                except Exception as e:
                    logger.error(f"Erreur lors du recalcul automatique du bulletin pour le contrat {c_id}, période {m}/{y}: {e}")


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
    auto_recalculate_payslips(db, salarie_id, db_item.date_debut_absence, db_item.date_fin_absence)
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
    
    old_start = db_item.date_debut_absence
    old_end = db_item.date_fin_absence
    salarie_id = db_item.salarie_id

    for field, value in absence_in.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    
    # Recalculer pour l'ancienne et la nouvelle période
    auto_recalculate_payslips(db, salarie_id, old_start, old_end)
    auto_recalculate_payslips(db, salarie_id, db_item.date_debut_absence, db_item.date_fin_absence)
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
    
    salarie_id = db_item.salarie_id
    old_start = db_item.date_debut_absence
    old_end = db_item.date_fin_absence
    
    db.delete(db_item)
    db.commit()
    
    auto_recalculate_payslips(db, salarie_id, old_start, old_end)
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
