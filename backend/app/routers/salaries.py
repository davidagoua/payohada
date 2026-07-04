from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

from app.config import settings
from app.database import get_db
from app.models.models import Salarie, Etablissement, Dossier, Utilisateur
from app.schemas.salarie import SalarieCreate, SalarieUpdate, SalarieOut
from app.services.security import get_current_user
from app.routers.etablissements import check_etablissement_ownership

router = APIRouter(tags=["Salariés"])


def check_salarie_ownership(salarie_id: int, user_id: int, db: Session) -> Salarie:
    salarie = db.query(Salarie).join(Etablissement).join(Dossier).filter(
        Salarie.id == salarie_id,
        Dossier.utilisateur_id == user_id
    ).first()
    if not salarie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salarié introuvable ou accès refusé."
        )
    return salarie


@router.get("/etablissements/{etablissement_id}/salaries", response_model=List[SalarieOut])
def get_salaries(
    etablissement_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste tous les salariés d'un établissement."""
    check_etablissement_ownership(etablissement_id, current_user.id, db)
    return db.query(Salarie).filter(Salarie.etablissement_id == etablissement_id).all()


def register_user_in_supabase(email: str, password: str) -> Optional[str]:
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_ANON_KEY
    if not url or not key or "changez-ceci" in key:
        return None
    try:
        response = httpx.post(
            f"{url}/auth/v1/signup",
            headers={
                "apikey": key,
                "Content-Type": "application/json"
            },
            json={
                "email": email,
                "password": password
            },
            timeout=5.0
        )
        if response.status_code in [200, 201]:
            data = response.json()
            if "id" in data:
                return data["id"]
            elif "user" in data and isinstance(data["user"], dict) and "id" in data["user"]:
                return data["user"]["id"]
        else:
            print(f"Supabase Auth registration returned status {response.status_code}: {response.text}")
    except Exception as e:
        print("Error registering user in Supabase:", e)
    return None


def sync_salarie_user(salarie: Salarie, db: Session):
    if not salarie.email:
        return
    
    # Check if a user already exists for this salarie
    user = db.query(Utilisateur).filter(Utilisateur.salarie_id == salarie.id).first()
    if not user:
        # Check if email is already taken by another user
        existing_user = db.query(Utilisateur).filter(Utilisateur.email == salarie.email).first()
        if existing_user:
            existing_user.salarie_id = salarie.id
            existing_user.nom = salarie.nom
            existing_user.prenom = salarie.prenom
            db.commit()
            return
            
        # Tentative d'enregistrement dans Supabase Auth
        supabase_uid = register_user_in_supabase(salarie.email, "Payohada@123")
        if not supabase_uid:
            import uuid
            supabase_uid = f"local-salarie-{uuid.uuid4()}"
            
        user = Utilisateur(
            email=salarie.email,
            nom=salarie.nom,
            prenom=salarie.prenom,
            supabase_uid=supabase_uid,
            salarie_id=salarie.id,
            is_active=True,
            is_admin=False
        )
        db.add(user)
    else:
        user.email = salarie.email
        user.nom = salarie.nom
        user.prenom = salarie.prenom
    db.commit()


@router.post("/etablissements/{etablissement_id}/salaries", response_model=SalarieOut)
def create_salarie(
    etablissement_id: int,
    salarie_in: SalarieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un salarié pour un établissement."""
    check_etablissement_ownership(etablissement_id, current_user.id, db)

    # Génération dynamique et unique du matricule
    existing_count = db.query(Salarie).filter(Salarie.etablissement_id == etablissement_id).count()
    generated_matricule = f"EMP-{etablissement_id}-{(existing_count + 1):04d}"
    
    while db.query(Salarie).filter(
        Salarie.etablissement_id == etablissement_id,
        Salarie.matricule == generated_matricule
    ).first():
        existing_count += 1
        generated_matricule = f"EMP-{etablissement_id}-{(existing_count + 1):04d}"

    salarie_data = salarie_in.model_dump()
    salarie_data["matricule"] = generated_matricule

    salarie = Salarie(**salarie_data, etablissement_id=etablissement_id)
    db.add(salarie)
    db.commit()
    db.refresh(salarie)
    
    # Synchroniser l'utilisateur local
    sync_salarie_user(salarie, db)
    
    return salarie


@router.get("/salaries/{salarie_id}", response_model=SalarieOut)
def get_salarie(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère un salarié par son ID."""
    return check_salarie_ownership(salarie_id, current_user.id, db)


@router.put("/salaries/{salarie_id}", response_model=SalarieOut)
def update_salarie(
    salarie_id: int,
    salarie_in: SalarieUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour les informations d'un salarié."""
    salarie = check_salarie_ownership(salarie_id, current_user.id, db)

    for field, value in salarie_in.model_dump(exclude_unset=True).items():
        setattr(salarie, field, value)

    db.commit()
    db.refresh(salarie)
    
    # Synchroniser l'utilisateur local
    sync_salarie_user(salarie, db)
    
    return salarie


@router.delete("/salaries/{salarie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salarie(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un salarié de la base."""
    salarie = check_salarie_ownership(salarie_id, current_user.id, db)
    db.delete(salarie)
    db.commit()
    return None

