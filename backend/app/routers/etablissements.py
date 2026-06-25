from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Dossier, Etablissement, AdresseEtablissement, BanqueEtablissement, GestionCongesPayes, CaisseCotisation, Utilisateur
from app.schemas.etablissement import (
    EtablissementCreate, EtablissementUpdate, EtablissementOut,
    CaisseCotisationCreate, CaisseCotisationOut
)
from app.services.security import get_current_user

router = APIRouter(tags=["Etablissements"])


def check_dossier_ownership(dossier_id: int, user_id: int, db: Session) -> Dossier:
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id, Dossier.utilisateur_id == user_id).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable ou accès refusé."
        )
    return dossier


def check_etablissement_ownership(etablissement_id: int, user_id: int, db: Session) -> Etablissement:
    etab = db.query(Etablissement).join(Dossier).filter(
        Etablissement.id == etablissement_id,
        Dossier.utilisateur_id == user_id
    ).first()
    if not etab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Établissement introuvable ou accès refusé."
        )
    return etab


# ─────────────────────────────────────────
#  ROUTES ETABLISSEMENT
# ─────────────────────────────────────────

@router.get("/dossiers/{dossier_id}/etablissements", response_model=List[EtablissementOut])
def get_etablissements(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les établissements d'un dossier."""
    check_dossier_ownership(dossier_id, current_user.id, db)
    return db.query(Etablissement).filter(Etablissement.dossier_id == dossier_id).all()


@router.post("/dossiers/{dossier_id}/etablissements", response_model=EtablissementOut)
def create_etablissement(
    dossier_id: int,
    etab_in: EtablissementCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un établissement pour un dossier."""
    check_dossier_ownership(dossier_id, current_user.id, db)

    # Vérification unicité code établissement pour le dossier
    existing = db.query(Etablissement).filter(
        Etablissement.dossier_id == dossier_id,
        Etablissement.code == etab_in.code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un établissement avec ce code existe déjà dans ce dossier."
        )

    # Création établissement
    etab_dict = etab_in.model_dump(exclude={"adresse", "banque", "gestion_conges"})
    etab = Etablissement(**etab_dict, dossier_id=dossier_id)
    db.add(etab)
    db.commit()
    db.refresh(etab)

    # Création adresse
    if etab_in.adresse:
        adresse = AdresseEtablissement(**etab_in.adresse.model_dump(), etablissement_id=etab.id)
        db.add(adresse)

    # Création banque
    if etab_in.banque:
        banque = BanqueEtablissement(**etab_in.banque.model_dump(), etablissement_id=etab.id)
        db.add(banque)

    # Création conges
    if etab_in.gestion_conges:
        conges = GestionCongesPayes(**etab_in.gestion_conges.model_dump(), etablissement_id=etab.id)
        db.add(conges)

    db.commit()
    db.refresh(etab)
    return etab


@router.get("/etablissements/{etablissement_id}", response_model=EtablissementOut)
def get_etablissement(
    etablissement_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère un établissement par son ID."""
    return check_etablissement_ownership(etablissement_id, current_user.id, db)


@router.put("/etablissements/{etablissement_id}", response_model=EtablissementOut)
def update_etablissement(
    etablissement_id: int,
    etab_in: EtablissementUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour un établissement."""
    etab = check_etablissement_ownership(etablissement_id, current_user.id, db)

    # Mettre à jour les champs principaux de l'établissement
    etab_dict = etab_in.model_dump(exclude_unset=True, exclude={"adresse", "banque"})
    for field, value in etab_dict.items():
        setattr(etab, field, value)

    # Mettre à jour ou créer l'adresse
    if etab_in.adresse is not None:
        if etab.adresse:
            for field, value in etab_in.adresse.model_dump(exclude_unset=True).items():
                setattr(etab.adresse, field, value)
        else:
            adresse = AdresseEtablissement(**etab_in.adresse.model_dump(), etablissement_id=etab.id)
            db.add(adresse)

    # Mettre à jour ou créer la banque
    if etab_in.banque is not None:
        if etab.banque:
            for field, value in etab_in.banque.model_dump(exclude_unset=True).items():
                setattr(etab.banque, field, value)
        else:
            banque = BanqueEtablissement(**etab_in.banque.model_dump(), etablissement_id=etab.id)
            db.add(banque)

    db.commit()
    db.refresh(etab)
    return etab


@router.delete("/etablissements/{etablissement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_etablissement(
    etablissement_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un établissement."""
    etab = check_etablissement_ownership(etablissement_id, current_user.id, db)
    db.delete(etab)
    db.commit()
    return None


# ─────────────────────────────────────────
#  ROUTES CAISSES DE COTISATION
# ─────────────────────────────────────────

@router.get("/etablissements/{etablissement_id}/caisses", response_model=List[CaisseCotisationOut])
def get_caisses(
    etablissement_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les caisses de cotisation d'un établissement."""
    check_etablissement_ownership(etablissement_id, current_user.id, db)
    return db.query(CaisseCotisation).filter(CaisseCotisation.etablissement_id == etablissement_id).all()


@router.post("/etablissements/{etablissement_id}/caisses", response_model=CaisseCotisationOut)
def create_caisse(
    etablissement_id: int,
    caisse_in: CaisseCotisationCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Ajoute une caisse de cotisation à l'établissement."""
    check_etablissement_ownership(etablissement_id, current_user.id, db)

    caisse = CaisseCotisation(**caisse_in.model_dump(), etablissement_id=etablissement_id)
    db.add(caisse)
    db.commit()
    db.refresh(caisse)
    return caisse


@router.delete("/caisses/{caisse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_caisse(
    caisse_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime une caisse de cotisation."""
    caisse = db.query(CaisseCotisation).join(Etablissement).join(Dossier).filter(
        CaisseCotisation.id == caisse_id,
        Dossier.utilisateur_id == current_user.id
    ).first()

    if not caisse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caisse de cotisation introuvable ou accès refusé."
        )

    db.delete(caisse)
    db.commit()
    return None
