"""Référentiel des modes de paiement des salaires.

Lecture : tout utilisateur connecté (les établissements y choisissent leurs
modes). Écriture : administrateur plateforme uniquement.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import ModePaiement, Utilisateur
from app.schemas.mode_paiement import ModePaiementCreate, ModePaiementOut, ModePaiementUpdate
from app.services.modes_paiement import mode_utilise, normaliser_code
from app.services.permissions import require_admin
from app.services.security import get_current_user

router = APIRouter(prefix="/modes-paiement", tags=["Modes de paiement"])


def _mode_ou_404(db: Session, mode_id: int) -> ModePaiement:
    mode = db.query(ModePaiement).filter(ModePaiement.id == mode_id).first()
    if not mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mode de paiement introuvable.")
    return mode


def _code_libre(db: Session, code: str, sauf_id: int | None = None) -> str:
    code = normaliser_code(code)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le code est obligatoire.")
    query = db.query(ModePaiement.id).filter(ModePaiement.code == code)
    if sauf_id is not None:
        query = query.filter(ModePaiement.id != sauf_id)
    if query.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un mode de paiement porte déjà ce code.")
    return code


@router.get("", response_model=List[ModePaiementOut])
def lister_modes(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Modes de paiement : tous pour la plateforme, les actifs pour les autres."""
    query = db.query(ModePaiement)
    if not current_user.is_admin:
        query = query.filter(ModePaiement.est_actif.is_(True))
    return query.order_by(ModePaiement.ordre, ModePaiement.libelle).all()


@router.post("", response_model=ModePaiementOut, status_code=status.HTTP_201_CREATED)
def creer_mode(
    payload: ModePaiementCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    require_admin(current_user)
    donnees = payload.model_dump()
    donnees["code"] = _code_libre(db, payload.code)
    donnees["libelle"] = payload.libelle.strip()
    mode = ModePaiement(**donnees)
    db.add(mode)
    db.commit()
    db.refresh(mode)
    return mode


@router.put("/{mode_id}", response_model=ModePaiementOut)
def modifier_mode(
    mode_id: int,
    payload: ModePaiementUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    require_admin(current_user)
    mode = _mode_ou_404(db, mode_id)
    donnees = payload.model_dump(exclude_unset=True)
    if "code" in donnees:
        donnees["code"] = _code_libre(db, donnees["code"], sauf_id=mode.id)
    if "libelle" in donnees:
        donnees["libelle"] = donnees["libelle"].strip()
    for champ, valeur in donnees.items():
        setattr(mode, champ, valeur)
    db.commit()
    db.refresh(mode)
    return mode


@router.delete("/{mode_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_mode(
    mode_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Supprime un mode jamais utilisé ; sinon, il faut le désactiver."""
    require_admin(current_user)
    mode = _mode_ou_404(db, mode_id)
    if mode_utilise(db, mode.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce mode de paiement est utilisé par des établissements ou des salariés : désactivez-le plutôt.",
        )
    db.delete(mode)
    db.commit()
    return None
