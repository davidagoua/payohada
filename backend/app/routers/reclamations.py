from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import Reclamation, BulletinPaie, Contrat, Dossier, Salarie, Utilisateur
from app.schemas.reclamation import ReclamationCreate, ReclamationUpdate, ReclamationOut
from app.services.security import get_current_user

router = APIRouter(prefix="/reclamations", tags=["Réclamations"])


@router.post("", response_model=ReclamationOut)
def create_reclamation(
    request: ReclamationCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Crée une réclamation sur un bulletin. Seul un salarié peut faire cela.
    """
    if not current_user.salarie_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les salariés peuvent soumettre une réclamation."
        )

    # Vérifie que le bulletin appartient au salarié connecté
    bulletin = db.query(BulletinPaie).join(Contrat).filter(
        BulletinPaie.id == request.bulletin_id,
        Contrat.salarie_id == current_user.salarie_id
    ).first()

    if not bulletin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulletin de paie introuvable ou accès refusé."
        )

    reclamation = Reclamation(
        bulletin_id=request.bulletin_id,
        salarie_id=current_user.salarie_id,
        sujet=request.sujet,
        description=request.description,
        statut="en_attente"
    )
    db.add(reclamation)
    db.commit()
    db.refresh(reclamation)
    return reclamation


@router.get("", response_model=List[ReclamationOut])
def list_reclamations(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Liste les réclamations.
    - Les salariés ne voient que leurs réclamations.
    - Les gestionnaires voient toutes les réclamations des salariés de leurs dossiers.
    """
    if current_user.salarie_id:
        reclamations = db.query(Reclamation).filter(
            Reclamation.salarie_id == current_user.salarie_id
        ).order_by(Reclamation.created_at.desc()).all()
    else:
        # Pour les gestionnaires, on récupère les réclamations liées aux dossiers possédés
        reclamations = db.query(Reclamation)\
            .join(BulletinPaie, BulletinPaie.id == Reclamation.bulletin_id)\
            .join(Dossier, Dossier.id == BulletinPaie.dossier_id)\
            .filter(Dossier.utilisateur_id == current_user.id)\
            .order_by(Reclamation.created_at.desc()).all()

    # Charger dynamiquement les champs pratiques pour la liste
    results = []
    for r in reclamations:
        salarie = db.query(Salarie).filter(Salarie.id == r.salarie_id).first()
        bulletin = db.query(BulletinPaie).filter(BulletinPaie.id == r.bulletin_id).first()
        
        rout = ReclamationOut.model_validate(r)
        if salarie:
            rout.salarie_nom = salarie.nom
            rout.salarie_prenom = salarie.prenom
        if bulletin:
            rout.bulletin_mois = bulletin.mois
            rout.bulletin_annee = bulletin.annee
        results.append(rout)

    return results


@router.put("/{reclamation_id}", response_model=ReclamationOut)
def update_reclamation(
    reclamation_id: int,
    request: ReclamationUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Permet à un gestionnaire de traiter ou rejeter une réclamation.
    """
    if current_user.salarie_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les salariés ne peuvent pas modifier le statut des réclamations."
        )

    # Récupérer la réclamation et vérifier qu'elle appartient à un dossier du gestionnaire connecté
    reclamation = db.query(Reclamation)\
        .join(BulletinPaie, BulletinPaie.id == Reclamation.bulletin_id)\
        .join(Dossier, Dossier.id == BulletinPaie.dossier_id)\
        .filter(Reclamation.id == reclamation_id, Dossier.utilisateur_id == current_user.id)\
        .first()

    if not reclamation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Réclamation introuvable ou accès refusé."
        )

    reclamation.statut = request.statut
    reclamation.commentaire_gestionnaire = request.commentaire_gestionnaire
    db.commit()
    db.refresh(reclamation)

    # Ajouter les métadonnées pour la réponse
    salarie = db.query(Salarie).filter(Salarie.id == reclamation.salarie_id).first()
    bulletin = db.query(BulletinPaie).filter(BulletinPaie.id == reclamation.bulletin_id).first()
    
    rout = ReclamationOut.model_validate(reclamation)
    if salarie:
        rout.salarie_nom = salarie.nom
        rout.salarie_prenom = salarie.prenom
    if bulletin:
        rout.bulletin_mois = bulletin.mois
        rout.bulletin_annee = bulletin.annee
        
    return rout
