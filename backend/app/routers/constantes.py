from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import Constante, Utilisateur
from app.schemas.constantes import ConstanteCreate, ConstanteUpdate, ConstanteOut
from app.services.security import get_current_user

router = APIRouter(prefix="/constantes", tags=["Constantes de Paie"])

@router.get("", response_model=List[ConstanteOut])
def get_constantes(
    pays: Optional[str] = None,
    est_actif: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les constantes de paie. Filtrable par pays et statut actif."""
    query = db.query(Constante)
    if pays:
        query = query.filter(Constante.pays == pays)
    if est_actif is not None:
        query = query.filter(Constante.est_actif == est_actif)
    return query.all()

@router.get("/{constante_id}", response_model=ConstanteOut)
def get_constante(
    constante_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère une constante de paie par son ID."""
    constante = db.query(Constante).filter(Constante.id == constante_id).first()
    if not constante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Constante introuvable."
        )
    return constante

@router.post("", response_model=ConstanteOut, status_code=status.HTTP_201_CREATED)
def create_constante(
    constante_in: ConstanteCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée une nouvelle constante de paie. Réservé aux administrateurs."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis."
        )
    
    # Vérifier l'unicité du code/pays
    existing = db.query(Constante).filter(
        Constante.code == constante_in.code,
        Constante.pays == constante_in.pays
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une constante avec ce code existe déjà pour ce pays."
        )

    constante = Constante(**constante_in.model_dump())
    db.add(constante)
    db.commit()
    db.refresh(constante)
    return constante

@router.put("/{constante_id}", response_model=ConstanteOut)
def update_constante(
    constante_id: int,
    constante_in: ConstanteUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour une constante de paie. Réservé aux administrateurs."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis."
        )
    
    constante = db.query(Constante).filter(Constante.id == constante_id).first()
    if not constante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Constante introuvable."
        )

    # Si le code ou le pays est modifié, on vérifie l'unicité
    check_code = constante_in.code or constante.code
    check_pays = constante_in.pays or constante.pays
    if check_code != constante.code or check_pays != constante.pays:
        existing = db.query(Constante).filter(
            Constante.code == check_code,
            Constante.pays == check_pays,
            Constante.id != constante_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Une constante avec ce code existe déjà pour ce pays."
            )

    for field, value in constante_in.model_dump(exclude_unset=True).items():
        setattr(constante, field, value)

    db.commit()
    db.refresh(constante)
    return constante

@router.delete("/{constante_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_constante(
    constante_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime une constante de paie. Réservé aux administrateurs."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis."
        )
    
    constante = db.query(Constante).filter(Constante.id == constante_id).first()
    if not constante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Constante introuvable."
        )

    db.delete(constante)
    db.commit()
    return None
