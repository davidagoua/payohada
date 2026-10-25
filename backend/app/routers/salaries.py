from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

from app.config import settings
from app.database import get_db
from app.models.models import Salarie, Etablissement, Dossier, Utilisateur
from app.schemas.salarie import SalarieCreate, SalarieUpdate, SalarieOut
from app.services.email import send_email
from app.services.email_templates import email_acces_cree, lien_connexion
from app.services.security import (
    generate_password,
    get_current_user,
    get_password_hash,
)
from app.routers.etablissements import check_etablissement_ownership

from app.services.permissions import ROLE_SALARIE, peut_gerer_dossier, require_staff

router = APIRouter(tags=["Salariés"])


def check_salarie_ownership(salarie_id: int, user_id: int, db: Session) -> Salarie:
    user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
    salarie = db.query(Salarie).join(Etablissement).join(Dossier).filter(Salarie.id == salarie_id).first()
    if not salarie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salarié introuvable ou accès refusé."
        )
    if user and (
        peut_gerer_dossier(db, user, salarie.etablissement.dossier)
        or (user.role == ROLE_SALARIE and user.salarie_id == salarie_id)
    ):
        return salarie
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès non autorisé à ce salarié."
    )


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


def sync_salarie_user(salarie: Salarie, db: Session) -> Optional[str]:
    """Crée ou met à jour le compte d'accès du salarié.

    Retourne le mot de passe provisoire **uniquement** lorsqu'un compte vient
    d'être créé (c'est ce mot de passe qui part par email), sinon `None`.
    """
    if not salarie.email:
        return None

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
            return None

        # Un mot de passe aléatoire est généré par salarié : auparavant, tous
        # les comptes salariés étaient créés avec le mot de passe public
        # « Payohada@123 », connu de quiconque lit le dépôt. Le compte local
        # était en outre créé sans empreinte, donc définitivement inutilisable
        # puisque la connexion refuse les comptes sans mot de passe.
        mot_de_passe = generate_password()

        # Tentative d'enregistrement dans Supabase Auth
        supabase_uid = register_user_in_supabase(salarie.email, mot_de_passe)
        if not supabase_uid:
            import uuid
            supabase_uid = f"local-salarie-{uuid.uuid4()}"

        user = Utilisateur(
            email=salarie.email,
            nom=salarie.nom,
            prenom=salarie.prenom,
            hashed_password=get_password_hash(mot_de_passe),
            supabase_uid=supabase_uid,
            salarie_id=salarie.id,
            role="salarie",
            is_active=True,
            is_admin=False,
            # Le salarié doit définir son propre mot de passe à la première
            # connexion : celui-ci n'est communiqué par aucun canal durable.
            must_change_password=True,
        )
        db.add(user)
        db.commit()
        return mot_de_passe

    user.email = salarie.email
    user.nom = salarie.nom
    user.prenom = salarie.prenom
    db.commit()
    return None


def _envoyer_identifiants_salarie(salarie: Salarie, mot_de_passe: str) -> tuple[bool, str]:
    """Envoie au salarié ses identifiants d'accès à l'espace Salarié."""
    dossier = salarie.etablissement.dossier if salarie.etablissement else None
    sujet, contenu = email_acces_cree(
        salarie.prenom,
        salarie.nom,
        salarie.email,
        mot_de_passe,
        dossier.nom_dossier if dossier else None,
        lien_connexion(),
        changement_requis=True,
        espace_libelle="Espace Salarié",
        espace_usage="consulter vos bulletins de paie et suivre vos réclamations",
    )
    return send_email(salarie.email, sujet, contenu)


def _creer_acces_salarie(
    salarie: Salarie, db: Session
) -> tuple[Optional[bool], Optional[str], Optional[str]]:
    """Crée le compte du salarié s'il n'existe pas encore, et envoie ses identifiants.

    Retourne `(envoyé, motif, mot_de_passe)` ; les trois valent `None` lorsqu'il
    n'y a rien à envoyer (salarié sans email, ou compte déjà existant).
    """
    mot_de_passe = sync_salarie_user(salarie, db)
    if not mot_de_passe:
        return None, None, None
    envoye, motif = _envoyer_identifiants_salarie(salarie, mot_de_passe)
    return envoye, (None if envoye else motif), mot_de_passe


def _sortie_salarie(
    salarie: Salarie,
    envoye: Optional[bool] = None,
    motif: Optional[str] = None,
    mot_de_passe: Optional[str] = None,
) -> SalarieOut:
    """Fiche salarié enrichie du résultat de l'envoi des identifiants."""
    out = SalarieOut.model_validate(salarie)
    out.acces_email_envoye = envoye
    out.acces_email_message = motif
    out.mot_de_passe_initial = mot_de_passe
    return out


@router.post("/etablissements/{etablissement_id}/salaries", response_model=SalarieOut)
def create_salarie(
    etablissement_id: int,
    salarie_in: SalarieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un salarié pour un établissement."""
    require_staff(current_user)
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
    
    # Créer le compte d'accès et lui envoyer ses identifiants
    envoye, motif, mot_de_passe = _creer_acces_salarie(salarie, db)

    return _sortie_salarie(salarie, envoye, motif, mot_de_passe)


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
    require_staff(current_user)
    salarie = check_salarie_ownership(salarie_id, current_user.id, db)

    for field, value in salarie_in.model_dump(exclude_unset=True).items():
        setattr(salarie, field, value)

    db.commit()
    db.refresh(salarie)
    
    # Un email saisi plus tard crée le compte : ses identifiants partent alors.
    envoye, motif, mot_de_passe = _creer_acces_salarie(salarie, db)

    return _sortie_salarie(salarie, envoye, motif, mot_de_passe)


@router.post("/salaries/{salarie_id}/envoyer-acces")
def envoyer_acces_salarie(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Renvoie au salarié ses identifiants d'accès, par email.

    Le mot de passe précédent n'est pas récupérable — seul son hachage est
    stocké : un mot de passe provisoire est régénéré, puis envoyé. Il est
    également renvoyé au cabinet dans la réponse, qui peut le transmettre si
    l'email n'est pas parti.
    """
    salarie = check_salarie_ownership(salarie_id, current_user.id, db)
    require_staff(current_user)

    if not salarie.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Renseignez d'abord l'email personnel du salarié.",
        )

    compte = db.query(Utilisateur).filter(Utilisateur.salarie_id == salarie.id).first()
    if compte is None:
        # Salarié créé sans email, complété plus tard : le compte reste à créer.
        mot_de_passe = sync_salarie_user(salarie, db)
        if not mot_de_passe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Aucun compte n'a pu être créé pour ce salarié : cette "
                    "adresse email est peut-être déjà utilisée par un autre compte."
                ),
            )
    else:
        if not compte.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce compte est désactivé : réactivez-le avant d'envoyer les identifiants.",
            )
        mot_de_passe = generate_password()
        compte.hashed_password = get_password_hash(mot_de_passe)
        compte.must_change_password = True
        db.commit()
        db.refresh(compte)

    envoye, motif = _envoyer_identifiants_salarie(salarie, mot_de_passe)

    return {
        "status": "success" if envoye else "warning",
        "message": (
            f"Identifiants envoyés à {salarie.email}."
            if envoye
            else f"Envoi impossible ({motif}). Transmettez le mot de passe provisoire au salarié."
        ),
        "email_envoye": envoye,
        "email_message": None if envoye else motif,
        "mot_de_passe_provisoire": mot_de_passe,
    }


@router.delete("/salaries/{salarie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salarie(
    salarie_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un salarié de la base."""
    require_staff(current_user)
    salarie = check_salarie_ownership(salarie_id, current_user.id, db)
    db.delete(salarie)
    db.commit()
    return None

