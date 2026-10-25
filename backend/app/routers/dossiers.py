from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import (
    AccesDossier, Dossier, Etablissement, NetEntreprise, Salarie, Utilisateur,
)
from app.schemas.dossier import DossierCreate, DossierUpdate, DossierOut, NetEntrepriseCreate, NetEntrepriseOut
from app.schemas.utilisateur import (
    CompteClientCreate, CompteGestionnaireCreate, UtilisateurOut,
)
from app.services.email import send_email
from app.services.email_templates import email_acces_cree, lien_connexion
from app.services.security import (
    get_current_user, get_password_hash, generate_password, validate_password_strength,
)
from app.services.permissions import (
    ROLE_GESTIONNAIRE_PAIE, dossiers_gérés, est_affecte, get_dossier_or_403,
    is_staff, require_staff,
)
import uuid

router = APIRouter(prefix="/dossiers", tags=["Dossiers"])


def check_dossier_ownership(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    """Vérifie que l'utilisateur a accès au dossier (cabinet propriétaire,
    client rattaché ou administrateur)."""
    return get_dossier_or_403(dossier_id, user, db)


def _get_owned_dossier_for_write(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    """Écriture d'un dossier : réservé au cabinet propriétaire (ou admin)."""
    require_staff(user)
    dossier = get_dossier_or_403(dossier_id, user, db)
    if not user.is_admin and dossier.utilisateur_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le cabinet propriétaire peut modifier ce dossier.",
        )
    return dossier


@router.get("", response_model=List[DossierOut])
def get_dossiers(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les dossiers accessibles par l'utilisateur connecté.

    Propriétaire, affecté (`acces_dossiers`), entreprise du client ou société du
    salarié : la règle vit dans `services.permissions`.
    """
    return dossiers_gérés(current_user, db).all()


@router.post("", response_model=DossierOut)
def create_dossier(
    dossier_in: DossierCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un nouveau dossier d'entreprise (réservé au cabinet).

    Le contrôle ne visait auparavant que le rôle « client » : un salarié
    authentifié pouvait donc créer des dossiers. `require_staff` n'autorise que
    le cabinet et l'administrateur.
    """
    require_staff(current_user)

    # Vérifier si le code existe déjà
    existing = db.query(Dossier).filter(Dossier.code == dossier_in.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un dossier avec ce code existe déjà."
        )

    # Création du dossier
    dossier_dict = dossier_in.model_dump(exclude={"net_entreprise"})
    dossier = Dossier(**dossier_dict, utilisateur_id=current_user.id)
    db.add(dossier)
    db.commit()
    db.refresh(dossier)

    # Création de NetEntreprise si fourni
    if dossier_in.net_entreprise:
        net_ent = NetEntreprise(
            **dossier_in.net_entreprise.model_dump(),
            dossier_id=dossier.id
        )
        db.add(net_ent)
        db.commit()
        db.refresh(dossier)

    return dossier


@router.get("/{dossier_id}", response_model=DossierOut)
def get_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère les détails d'un dossier."""
    return check_dossier_ownership(dossier_id, current_user, db)


@router.put("/{dossier_id}", response_model=DossierOut)
def update_dossier(
    dossier_id: int,
    dossier_in: DossierUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Met à jour un dossier (cabinet propriétaire uniquement)."""
    dossier = _get_owned_dossier_for_write(dossier_id, current_user, db)

    for field, value in dossier_in.model_dump(exclude_unset=True).items():
        setattr(dossier, field, value)

    db.commit()
    db.refresh(dossier)
    return dossier


@router.delete("/{dossier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un dossier (cabinet propriétaire uniquement)."""
    dossier = _get_owned_dossier_for_write(dossier_id, current_user, db)

    db.delete(dossier)
    db.commit()
    return None


@router.post("/{dossier_id}/net-entreprise", response_model=NetEntrepriseOut)
def create_or_update_net_entreprise(
    dossier_id: int,
    net_ent_in: NetEntrepriseCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Configure ou met à jour NetEntreprise pour un dossier."""
    _get_owned_dossier_for_write(dossier_id, current_user, db)

    net_ent = db.query(NetEntreprise).filter(NetEntreprise.dossier_id == dossier_id).first()
    if net_ent:
        for field, value in net_ent_in.model_dump().items():
            setattr(net_ent, field, value)
    else:
        net_ent = NetEntreprise(**net_ent_in.model_dump(), dossier_id=dossier_id)
        db.add(net_ent)

    db.commit()
    db.refresh(net_ent)
    return net_ent


# ─────────────────────────────────────────
#  GESTION DES COMPTES D'ACCÈS CLIENTS
# ─────────────────────────────────────────

@router.get("/{dossier_id}/comptes-clients", response_model=List[UtilisateurOut])
def get_comptes_clients(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les comptes d'accès pour un dossier d'entreprise.

    Réservé au cabinet : la réponse contient les adresses email des comptes,
    qui n'ont pas à être exposées au rôle client.
    """
    check_dossier_ownership(dossier_id, current_user, db)
    require_staff(current_user)
    return db.query(Utilisateur).filter(
        Utilisateur.dossier_id == dossier_id,
        Utilisateur.role == "client"
    ).all()


ESPACE_GESTIONNAIRE = (
    "Espace Paie",
    "gérer la paie des sociétés qui vous sont confiées",
)


def _envoyer_identifiants(
    compte: Utilisateur,
    dossier: Dossier | None,
    mot_de_passe: str,
    changement_requis: bool,
    espace_libelle: str = "Espace Entreprise",
    espace_usage: str = (
        "saisir les variables de paie du mois et de consulter les bulletins "
        "de l'entreprise"
    ),
) -> tuple[bool, str]:
    """Envoie les identifiants d'un compte client par email.

    L'échec n'est jamais bloquant : le mot de passe reste renvoyé au cabinet
    dans la réponse, qui peut le transmettre par un autre canal. On retourne
    donc `(envoyé, motif)` pour que l'écran puisse le signaler.
    """
    sujet, contenu = email_acces_cree(
        compte.prenom,
        compte.nom,
        compte.email,
        mot_de_passe,
        dossier.nom_dossier if dossier else None,
        lien_connexion(),
        changement_requis=changement_requis,
        espace_libelle=espace_libelle,
        espace_usage=espace_usage,
    )
    return send_email(compte.email, sujet, contenu)


@router.post("/{dossier_id}/comptes-clients", response_model=UtilisateurOut)
def create_compte_client(
    dossier_id: int,
    request: CompteClientCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Crée un compte d'accès pour l'entreprise cliente et lui envoie ses identifiants.

    Le cabinet ne peut pas communiquer un mot de passe qu'il n'a pas vu : les
    identifiants partent donc par email dès la création. Le mot de passe reste
    aussi renvoyé une seule fois (`mot_de_passe_initial`), pour le cas où
    l'envoi échoue (SMTP indisponible) : le cabinet peut alors le transmettre.
    """
    dossier = check_dossier_ownership(dossier_id, current_user, db)
    if not is_staff(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un gestionnaire de paie peut créer un compte client.",
        )

    email = (request.email or "").strip().lower()
    existing = (
        db.query(Utilisateur)
        .filter(func.lower(Utilisateur.email) == email)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse email est déjà utilisée par un autre compte."
        )

    password_genere = None
    if request.password:
        validate_password_strength(request.password, minimum=8)
        pwd = request.password
        must_change = False
    else:
        pwd = generate_password()
        password_genere = pwd
        must_change = True

    new_user = Utilisateur(
        email=email,
        nom=request.nom,
        prenom=request.prenom,
        hashed_password=get_password_hash(pwd),
        supabase_uid=f"local-client-{uuid.uuid4()}",
        is_active=True,
        is_admin=False,
        must_change_password=must_change,
        role="client",
        dossier_id=dossier_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    envoye, motif = _envoyer_identifiants(new_user, dossier, pwd, must_change)

    out = UtilisateurOut.model_validate(new_user)
    out.nom_dossier = dossier.nom_dossier if dossier else None
    out.is_default_password = bool(new_user.must_change_password)
    out.mot_de_passe_initial = password_genere
    out.email_envoye = envoye
    out.email_message = None if envoye else motif
    return out


@router.post("/{dossier_id}/comptes-clients/{user_id}/envoyer-acces")
def envoyer_acces_client(
    dossier_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Renvoie les identifiants d'un compte client, par email.

    Le mot de passe précédent n'est pas récupérable — il n'est stocké que
    haché : un mot de passe provisoire est donc régénéré, puis envoyé. Il est
    également renvoyé au cabinet dans la réponse, qui peut le transmettre si
    l'email n'est pas parti.
    """
    dossier = _get_owned_dossier_for_write(dossier_id, current_user, db)

    compte = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.id == user_id,
            Utilisateur.dossier_id == dossier_id,
            Utilisateur.role == "client",
        )
        .first()
    )
    if not compte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun compte client de ce dossier ne porte cet identifiant.",
        )
    if not compte.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce compte est désactivé : réactivez-le avant d'envoyer les identifiants.",
        )

    mot_de_passe = generate_password()
    compte.hashed_password = get_password_hash(mot_de_passe)
    # Le mot de passe envoyé par email est provisoire : il doit être remplacé.
    compte.must_change_password = True
    db.commit()
    db.refresh(compte)

    envoye, motif = _envoyer_identifiants(compte, dossier, mot_de_passe, True)

    return {
        "status": "success" if envoye else "warning",
        "message": (
            f"Identifiants envoyés à {compte.email}."
            if envoye
            else f"Envoi impossible ({motif}). Transmettez le mot de passe provisoire au client."
        ),
        "email_envoye": envoye,
        "email_message": None if envoye else motif,
        "mot_de_passe_provisoire": mot_de_passe,
    }



# ─────────────────────────────────────────
#  GESTIONNAIRES DE PAIE (affectation à une société)
# ─────────────────────────────────────────

@router.get("/{dossier_id}/gestionnaires", response_model=List[UtilisateurOut])
def get_gestionnaires(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Gestionnaires de paie affectés à cette société.

    Réservé au propriétaire du dossier (ou à l'administrateur) : c'est lui qui
    distribue les accès, pas un gestionnaire affecté.
    """
    _get_owned_dossier_for_write(dossier_id, current_user, db)
    return (
        db.query(Utilisateur)
        .join(AccesDossier, AccesDossier.utilisateur_id == Utilisateur.id)
        .filter(
            AccesDossier.dossier_id == dossier_id,
            Utilisateur.role == ROLE_GESTIONNAIRE_PAIE,
        )
        .order_by(Utilisateur.id)
        .all()
    )


@router.post("/{dossier_id}/gestionnaires", response_model=UtilisateurOut)
def create_gestionnaire(
    dossier_id: int,
    request: CompteGestionnaireCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Crée (ou rattache) un gestionnaire de paie à cette société.

    Un compte existant déjà gestionnaire de paie peut être affecté à une
    nouvelle société sans changer de mot de passe : seul un compte neuf reçoit
    des identifiants par email.
    """
    dossier = _get_owned_dossier_for_write(dossier_id, current_user, db)

    email = (request.email or "").strip().lower()
    compte = (
        db.query(Utilisateur).filter(func.lower(Utilisateur.email) == email).first()
    )

    mot_de_passe = None
    must_change = True
    if compte:
        if compte.role != ROLE_GESTIONNAIRE_PAIE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cette adresse email est déjà utilisée par un autre type de compte.",
            )
        if not compte.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce compte est désactivé : réactivez-le avant de l'affecter.",
            )
        if est_affecte(db, compte, dossier_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce gestionnaire est déjà affecté à cette société.",
            )
    else:
        if request.password:
            validate_password_strength(request.password, minimum=8)
            pwd = request.password
            must_change = False
        else:
            pwd = generate_password()
            mot_de_passe = pwd

        compte = Utilisateur(
            email=email,
            nom=request.nom,
            prenom=request.prenom,
            hashed_password=get_password_hash(pwd),
            supabase_uid=f"local-gestionnaire-{uuid.uuid4()}",
            is_active=True,
            is_admin=False,
            must_change_password=must_change,
            role=ROLE_GESTIONNAIRE_PAIE,
        )
        db.add(compte)
        db.flush()

    db.add(AccesDossier(utilisateur_id=compte.id, dossier_id=dossier_id))
    db.commit()
    db.refresh(compte)

    envoye = None
    motif_email = None
    if mot_de_passe:
        envoye, motif_email = _envoyer_identifiants(
            compte, dossier, mot_de_passe, must_change, *ESPACE_GESTIONNAIRE
        )

    out = UtilisateurOut.model_validate(compte)
    out.nom_dossier = dossier.nom_dossier
    out.is_default_password = bool(compte.must_change_password)
    out.mot_de_passe_initial = mot_de_passe
    out.email_envoye = envoye
    out.email_message = None if envoye else motif_email
    return out


@router.post("/{dossier_id}/gestionnaires/{user_id}/envoyer-acces")
def envoyer_acces_gestionnaire(
    dossier_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Renvoie les identifiants d'un gestionnaire de paie de cette société."""
    dossier = _get_owned_dossier_for_write(dossier_id, current_user, db)

    compte = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.id == user_id,
            Utilisateur.role == ROLE_GESTIONNAIRE_PAIE,
        )
        .first()
    )
    if not compte or not est_affecte(db, compte, dossier_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun gestionnaire de paie de cette société ne porte cet identifiant.",
        )
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

    envoye, motif = _envoyer_identifiants(
        compte, dossier, mot_de_passe, True, *ESPACE_GESTIONNAIRE
    )

    return {
        "status": "success" if envoye else "warning",
        "message": (
            f"Identifiants envoyés à {compte.email}."
            if envoye
            else f"Envoi impossible ({motif}). Transmettez le mot de passe provisoire."
        ),
        "email_envoye": envoye,
        "email_message": None if envoye else motif,
        "mot_de_passe_provisoire": mot_de_passe,
    }


@router.delete(
    "/{dossier_id}/gestionnaires/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def retirer_gestionnaire(
    dossier_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Retire l'affectation d'un gestionnaire à cette société.

    Son compte n'est pas supprimé — il peut gérer d'autres sociétés. S'il ne lui
    reste plus aucun accès et qu'il ne possède aucun dossier, il est désactivé :
    un compte actif sans portée n'a aucune raison d'exister.
    """
    _get_owned_dossier_for_write(dossier_id, current_user, db)

    acces = (
        db.query(AccesDossier)
        .filter(
            AccesDossier.dossier_id == dossier_id,
            AccesDossier.utilisateur_id == user_id,
        )
        .first()
    )
    if not acces:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette affectation n'existe pas.",
        )

    db.delete(acces)
    db.commit()

    restants = (
        db.query(AccesDossier)
        .filter(AccesDossier.utilisateur_id == user_id)
        .count()
    )
    possede = db.query(Dossier).filter(Dossier.utilisateur_id == user_id).count()
    if restants == 0 and possede == 0:
        compte = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
        if compte:
            compte.is_active = False
            db.commit()

    return None
