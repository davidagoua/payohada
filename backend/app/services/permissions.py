"""Contrôles de rôle et de portée (multi-tenant) réutilisables."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Dossier, Utilisateur

ROLE_CABINET = "cabinet"
ROLE_CLIENT = "client"
ROLE_SALARIE = "salarie"

#: Rôles autorisés à produire/valider la paie.
STAFF_ROLES = (ROLE_CABINET,)


def is_staff(user: Utilisateur) -> bool:
    """Un gestionnaire de paie : cabinet ou administrateur plateforme."""
    return bool(user.is_admin) or user.role == ROLE_CABINET


def require_staff(user: Utilisateur) -> None:
    """Réserve une action au cabinet / administrateur."""
    if not is_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action réservée au cabinet de paie.",
        )


def require_admin(user: Utilisateur) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès interdit. Rôle administrateur requis.",
        )


def can_access_dossier(user: Utilisateur, dossier: Dossier) -> bool:
    if user.is_admin:
        return True
    if user.role == ROLE_CLIENT:
        return user.dossier_id == dossier.id
    if user.role == ROLE_CABINET:
        return dossier.utilisateur_id == user.id
    return False


def get_dossier_or_403(dossier_id: int, user: Utilisateur, db: Session) -> Dossier:
    """Charge un dossier et vérifie que l'utilisateur y a accès (sinon 404/403)."""
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier introuvable.",
        )
    if not can_access_dossier(user, dossier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à ce dossier.",
        )
    return dossier
