from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import PlanPaie, Utilisateur
from app.schemas.plan_paie import PlanPaieCreate, PlanPaieUpdate, PlanPaieOut
from app.services.security import get_current_user

router = APIRouter(prefix="/plan-paie", tags=["Plan Comptable de Paie"])

@router.get("", response_model=List[PlanPaieOut])
def get_plans_paie(
    pays: Optional[str] = None,
    est_actif: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les postes du plan de paie. Filtrable par pays et statut actif."""
    query = db.query(PlanPaie)
    if pays:
        query = query.filter(PlanPaie.pays == pays)
    if est_actif is not None:
        query = query.filter(PlanPaie.est_actif == est_actif)
    return query.all()

@router.get("/{plan_id}", response_model=PlanPaieOut)
def get_plan_paie(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère un poste de paie par son ID."""
    plan = db.query(PlanPaie).filter(PlanPaie.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poste de paie introuvable."
        )
    return plan

@router.post("", response_model=PlanPaieOut, status_code=status.HTTP_201_CREATED)
def create_plan_paie(
    plan_in: PlanPaieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un nouveau poste de paie. Réservé aux administrateurs."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis."
        )
    
    # Vérifier l'unicité du code/pays
    existing = db.query(PlanPaie).filter(
        PlanPaie.code == plan_in.code,
        PlanPaie.pays == plan_in.pays
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un poste de paie avec ce code existe déjà pour ce pays."
        )

    plan = PlanPaie(**plan_in.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.put("/{plan_id}", response_model=PlanPaieOut)
def update_plan_paie(
    plan_id: int,
    plan_in: PlanPaieUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour un poste de paie. Réservé aux administrateurs."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis."
        )
    
    plan = db.query(PlanPaie).filter(PlanPaie.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poste de paie introuvable."
        )

    # Si le code ou le pays est modifié, on vérifie l'unicité
    check_code = plan_in.code or plan.code
    check_pays = plan_in.pays or plan.pays
    if check_code != plan.code or check_pays != plan.pays:
        existing = db.query(PlanPaie).filter(
            PlanPaie.code == check_code,
            PlanPaie.pays == check_pays,
            PlanPaie.id != plan_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un poste de paie avec ce code existe déjà pour ce pays."
            )

    for field, value in plan_in.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_paie(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un poste de paie. Réservé aux administrateurs."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis."
        )
    
    plan = db.query(PlanPaie).filter(PlanPaie.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poste de paie introuvable."
        )

    db.delete(plan)
    db.commit()
    return None
