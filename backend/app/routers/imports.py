"""Imports de données de base (Excel/CSV) pour les dossiers clients."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Dossier, ImportJob, Utilisateur
from app.schemas.imports import (
    ImportAnalyseOut,
    ImportExecutionIn,
    ImportExecutionOut,
    ImportJobOut,
)
from app.services import imports as service
from app.services.permissions import get_dossier_or_403, require_staff
from app.services.security import get_current_user

router = APIRouter(prefix="/imports", tags=["Imports de données"])
logger = logging.getLogger("app.imports")


def _dossier_pour_import(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    require_staff(user)
    return get_dossier_or_403(dossier_id, user, db)


def _job_pour_lecture(job_id: int, user: Utilisateur, db: Session) -> ImportJob:
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import introuvable.")
    _dossier_pour_import(job.dossier_id, user, db)
    return job


def _lire_mapping_override(mapping: str | None) -> dict[str, str] | None:
    if not mapping:
        return None
    try:
        valeur = json.loads(mapping)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mapping des colonnes est invalide.",
        )
    if not isinstance(valeur, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mapping des colonnes doit être un objet JSON.",
        )
    return {str(cle): str(source) for cle, source in valeur.items()}


def _job_out(job: ImportJob) -> ImportJobOut:
    return ImportJobOut.model_validate(job)


def _rapport_pour_job(analyse: service.Analyse, limite_erreurs: int = 500) -> dict:
    return {
        "colonnes": analyse.entetes,
        "champs_manquants": analyse.champs_manquants,
        "erreurs_total": len(analyse.erreurs),
        "erreurs": analyse.erreurs[:limite_erreurs],
        "apercu": analyse.apercu,
    }


@router.get("/types")
def lister_types_import(current_user: Utilisateur = Depends(get_current_user)):
    """Types d'import disponibles et colonnes attendues (pour l'assistant)."""
    require_staff(current_user)
    return [
        {
            "code": code,
            "libelle": service.TYPES_LIBELLES[code],
            "description": service.TYPES_DESCRIPTIONS[code],
            "champs": [
                {
                    "cle": champ.cle,
                    "libelle": champ.libelle,
                    "obligatoire": champ.obligatoire,
                    "aide": champ.aide,
                    "exemple": champ.exemple,
                }
                for champ in service.CHAMPS[code]
            ],
        }
        for code in service.TYPES_LIBELLES
    ]


@router.get("/diagnostic")
def diagnostic_imports(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Vérifie l'état du module (table, dossier d'écriture) sans exposer de données.

    Utile en production pour distinguer une migration manquante d'un problème
    de droits sur le volume d'uploads.
    """
    require_staff(current_user)
    try:
        table_imports = inspect(db.get_bind()).has_table("imports")
    except Exception:  # noqa: BLE001
        table_imports = False
    dossier = service.DOSSIER_IMPORTS.resolve()
    ecriture = False
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        sonde = dossier / ".ecriture"
        sonde.write_text("ok")
        sonde.unlink(missing_ok=True)
        ecriture = True
    except OSError:
        ecriture = False
    return {
        "table_imports": table_imports,
        "dossier_imports": str(dossier),
        "ecriture_possible": ecriture,
        "taille_max_mo": service.MAX_IMPORT_BYTES // (1024 * 1024),
    }


@router.get("/modeles/{type_import}")
def telecharger_modele(
    type_import: str,
    current_user: Utilisateur = Depends(get_current_user),
):
    """Télécharge le modèle Excel officiel d'un type d'import."""
    require_staff(current_user)
    if type_import not in service.CHAMPS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type d'import inconnu.")
    contenu = service.generer_modele(type_import)
    nom = f"modele-{type_import}.xlsx"
    return Response(
        content=contenu,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


@router.post("/analyser", response_model=ImportAnalyseOut, status_code=status.HTTP_201_CREATED)
async def analyser_fichier(
    dossier_id: int = Form(..., description="Dossier client cible"),
    type_import: str = Form(..., description="etablissements | salaries | contrats"),
    fichier: UploadFile = File(..., description="Fichier .xlsx, .xlsm ou .csv"),
    mapping: str | None = Form(None, description="Mapping JSON colonne canonique -> colonne du fichier"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Analyse un fichier sans écrire en base et retourne le rapport d'erreurs."""
    dossier = _dossier_pour_import(dossier_id, current_user, db)
    if type_import not in service.CHAMPS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type d'import inconnu.")

    contenu = await fichier.read()
    chemin = None
    try:
        service.verifier_fichier(fichier.filename or "", len(contenu))
        chemin = service.enregistrer_fichier(fichier.filename or "import.xlsx", contenu)
        analyse = service.analyser_contenu(
            db, dossier, type_import, fichier.filename or "", contenu,
            _lire_mapping_override(mapping),
        )
    except ValueError as exc:
        service.supprimer_fichier(chemin)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        service.supprimer_fichier(chemin)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    job = ImportJob(
        dossier_id=dossier.id,
        utilisateur_id=current_user.id,
        type_import=type_import,
        fichier_nom=(fichier.filename or "import")[:255],
        fichier_chemin=chemin,
        fichier_taille=len(contenu),
        statut=analyse.statut,
        total_lignes=analyse.total_lignes,
        lignes_valides=len(analyse.valides),
        lignes_erreurs=analyse.lignes_erreurs,
        mapping=json.dumps(analyse.mapping, ensure_ascii=False),
        rapport=json.dumps(_rapport_pour_job(analyse), ensure_ascii=False),
    )
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except (ProgrammingError, OperationalError):
        db.rollback()
        service.supprimer_fichier(chemin)
        logger.exception("Table imports absente ou base indisponible pendant l'analyse")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "La base de données ne contient pas encore la table des imports. "
                "Appliquez les migrations (python apply_migrations.py) puis "
                "redémarrez l'API."
            ),
        )

    return ImportAnalyseOut(
        job=_job_out(job),
        colonnes=analyse.entetes,
        mapping=analyse.mapping,
        champs_manquants=analyse.champs_manquants,
        erreurs=analyse.erreurs[:200],
        apercu=analyse.apercu,
        message=(
            "Le mapping est incomplet : associez les colonnes manquantes."
            if analyse.champs_manquants
            else f"{len(analyse.valides)} ligne(s) valide(s), {analyse.lignes_erreurs} ligne(s) en erreur."
        ),
    )


@router.post("/{job_id}/executer", response_model=ImportExecutionOut)
def executer_import(
    job_id: int,
    payload: ImportExecutionIn,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Exécute l'import des lignes valides, de façon idempotente."""
    job = _job_pour_lecture(job_id, current_user, db)
    if job.statut == "termine":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cet import a déjà été exécuté.")

    try:
        contenu = service.lire_fichier_job(job.fichier_chemin)
        mapping_override = json.loads(job.mapping or "{}")
        analyse = service.analyser_contenu(
            db, job.dossier, job.type_import, job.fichier_nom, contenu, mapping_override,
        )
        if analyse.champs_manquants:
            raise ValueError("Le mapping des colonnes est incomplet : relancez l'analyse.")
        execution = service.executer_analyse(db, job, analyse, payload.ignorer_erreurs)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (ProgrammingError, OperationalError):
        db.rollback()
        logger.exception("Erreur de schéma/base pendant l'exécution de l'import")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "La base de données ne contient pas encore la table des imports. "
                "Appliquez les migrations (python apply_migrations.py) puis "
                "redémarrez l'API."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec inattendu de l'import")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"L'import a échoué : {exc}",
        )

    rapport = service.rapport_json(job)
    rapport["execution"] = {
        "crees": execution.crees,
        "mis_a_jour": execution.mis_a_jour,
        "ignores": execution.ignores,
        "erreurs": execution.erreurs[:200],
        "execute_le": datetime.now(timezone.utc).isoformat(),
    }
    job.statut = "termine"
    job.execute_le = datetime.now(timezone.utc)
    job.total_lignes = analyse.total_lignes
    job.lignes_valides = len(analyse.valides)
    job.lignes_erreurs = len(execution.erreurs) + analyse.lignes_erreurs
    job.rapport = json.dumps(rapport, ensure_ascii=False)
    service.supprimer_fichier(job.fichier_chemin)
    job.fichier_chemin = None
    db.commit()
    db.refresh(job)

    return ImportExecutionOut(
        job=_job_out(job),
        crees=execution.crees,
        mis_a_jour=execution.mis_a_jour,
        ignores=execution.ignores,
        erreurs=execution.erreurs[:200],
        message=(
            f"{execution.crees} création(s), {execution.mis_a_jour} mise(s) à jour, "
            f"{execution.ignores} ligne(s) ignorée(s)."
        ),
    )


@router.get("", response_model=list[ImportJobOut])
def lister_imports(
    dossier_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Historique des imports d'un dossier (50 derniers)."""
    dossier = _dossier_pour_import(dossier_id, current_user, db)
    jobs = (
        db.query(ImportJob)
        .filter(ImportJob.dossier_id == dossier.id)
        .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
        .limit(50)
        .all()
    )
    return [_job_out(job) for job in jobs]


@router.get("/{job_id}")
def detail_import(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Détail d'un import, avec son rapport d'analyse/exécution."""
    job = _job_pour_lecture(job_id, current_user, db)
    return {
        "job": _job_out(job).model_dump(),
        "rapport": service.rapport_json(job),
    }
