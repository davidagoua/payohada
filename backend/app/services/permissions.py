"""Contrôles de rôle et de portée (multi-tenant) réutilisables.

Un seul endroit décide qui peut toucher quel dossier : les routeurs s'y ramènent
tous (`check_etablissement_ownership`, `check_salarie_ownership`,
`check_contrat_ownership`, l'accès aux bulletins…). Auparavant la même condition
de rôle était recopiée dans cinq fichiers : ajouter un rôle demandait de
retrouver chaque copie, et une seule oubliée ouvrait une brèche.
"""
from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.models import AccesDossier, Dossier, Etablissement, Salarie, Utilisateur

ROLE_CABINET = "cabinet"
#: Gestionnaire de paie : rôle plateforme, rattaché aux sociétés qu'il gère par
#: une affectation (`acces_dossiers`). Il n'en est pas propriétaire.
ROLE_GESTIONNAIRE_PAIE = "gestionnaire_paie"
ROLE_CLIENT = "client"
ROLE_SALARIE = "salarie"

#: Rôles autorisés à produire/valider la paie.
STAFF_ROLES = (ROLE_CABINET, ROLE_GESTIONNAIRE_PAIE)


def is_staff(user: Utilisateur) -> bool:
    """Un gestionnaire de paie : cabinet, gestionnaire affecté ou administrateur."""
    return bool(user.is_admin) or user.role in STAFF_ROLES


def require_staff(user: Utilisateur) -> None:
    """Réserve une action au cabinet / gestionnaire de paie / administrateur."""
    if not is_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action réservée au gestionnaire de paie.",
        )


def require_admin(user: Utilisateur) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis.",
        )


def est_affecte(db: Session, user: Utilisateur, dossier_id: int) -> bool:
    """L'utilisateur est-il gestionnaire de paie de cette société ?"""
    return (
        db.query(AccesDossier)
        .filter(
            AccesDossier.utilisateur_id == user.id,
            AccesDossier.dossier_id == dossier_id,
        )
        .first()
        is not None
    )


def peut_gerer_dossier(db: Session, user: Utilisateur, dossier: Dossier) -> bool:
    """Accès à un dossier, tous rôles confondus.

    * administrateur : tout ;
    * cabinet / gestionnaire de paie : propriétaire du dossier ou affecté ;
    * client : son entreprise ;
    * salarié : aucun accès au dossier (il passe par ses propres bulletins).
    """
    if user.is_admin:
        return True
    if user.role in STAFF_ROLES:
        return dossier.utilisateur_id == user.id or est_affecte(db, user, dossier.id)
    if user.role == ROLE_CLIENT:
        return user.dossier_id == dossier.id
    return False


def dossiers_gérés(user: Utilisateur, db: Session):
    """Requête des dossiers visibles pour l'utilisateur, selon son rôle."""
    if user.is_admin:
        return db.query(Dossier)
    if user.role in STAFF_ROLES:
        return (
            db.query(Dossier)
            .outerjoin(AccesDossier, AccesDossier.dossier_id == Dossier.id)
            .filter(
                or_(
                    Dossier.utilisateur_id == user.id,
                    and_(
                        AccesDossier.utilisateur_id == user.id,
                        AccesDossier.utilisateur_id.isnot(None),
                    ),
                )
            )
            .distinct()
        )
    if user.role == ROLE_CLIENT:
        if not user.dossier_id:
            return db.query(Dossier).filter(False)
        return db.query(Dossier).filter(Dossier.id == user.dossier_id)
    if user.role == ROLE_SALARIE and user.salarie_id:
        # Le salarié ne voit que la société de son établissement.
        return (
            db.query(Dossier)
            .join(Etablissement, Etablissement.dossier_id == Dossier.id)
            .join(Salarie, Salarie.etablissement_id == Etablissement.id)
            .filter(Salarie.id == user.salarie_id)
        )
    return db.query(Dossier).filter(False)


def get_dossier_or_403(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    """Charge un dossier et vérifie que l'utilisateur y a accès (sinon 404/403)."""
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable.",
        )
    if not peut_gerer_dossier(db, user, dossier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à ce dossier.",
        )
    return dossier
