"""Contrôles de rôle et de portée (multi-tenant) réutilisables.

Un seul endroit décide qui peut toucher quel dossier : les routeurs s'y ramènent
tous (`check_etablissement_ownership`, `check_salarie_ownership`,
`check_contrat_ownership`, l'accès aux bulletins…). Auparavant la même condition
de rôle était recopiée dans cinq fichiers : ajouter un rôle demandait de
retrouver chaque copie, et une seule oubliée ouvrait une brèche.

L'administrateur plateforme (`is_admin`) gère le SaaS — cabinets, référentiels,
indicateurs agrégés — mais n'a **aucun accès** aux sociétés, salariés et
bulletins des cabinets : il n'est ni « staff » ni propriétaire d'un dossier,
même si son compte porte le rôle `cabinet`.
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
    """Un gestionnaire de paie : cabinet ou gestionnaire affecté.

    L'administrateur plateforme en est exclu : il ne produit pas la paie.
    """
    return not user.is_admin and user.role in STAFF_ROLES


def require_staff(user: Utilisateur) -> None:
    """Réserve une action au cabinet / gestionnaire de paie."""
    if not is_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action réservée au gestionnaire de paie.",
        )


def require_saisie_variables(user: Utilisateur) -> None:
    """Réserve la saisie des variables au cabinet, au gestionnaire et à l'entreprise."""
    if not is_staff(user) and (user.is_admin or user.role != ROLE_CLIENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Saisie des variables non autorisée.",
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


def racine_cabinet(user: Utilisateur) -> int | None:
    """Propriétaire du cabinet dont l'utilisateur fait partie.

    Le propriétaire (gestionnaire référent) est sa propre racine ; un membre
    rattaché pointe vers lui via `cabinet_owner_id`. Retourne `None` pour les
    rôles hors cabinet.
    """
    if user.role == ROLE_CABINET:
        return user.cabinet_owner_id or user.id
    return None


def est_admin_cabinet(user: Utilisateur) -> bool:
    """Peut administrer les membres d'un cabinet : rôle cabinet, hors plateforme."""
    return not user.is_admin and user.role == ROLE_CABINET


def membres_du_cabinet(db: Session, user: Utilisateur):
    """Comptes du personnel du cabinet, dans la portée de l'utilisateur.

    * propriétaire ou co-administrateur : le propriétaire, les membres qui lui
      sont rattachés, et — pour les bases antérieures à `cabinet_owner_id` —
      les gestionnaires affectés à l'une de ses sociétés.
    """
    query = db.query(Utilisateur).filter(Utilisateur.role.in_(STAFF_ROLES))
    if not est_admin_cabinet(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administration réservée au cabinet.",
        )

    racine = racine_cabinet(user)
    affectes = (
        db.query(AccesDossier.utilisateur_id)
        .join(Dossier, Dossier.id == AccesDossier.dossier_id)
        .filter(Dossier.utilisateur_id == racine)
        .all()
    )
    ids_affectes = [ligne[0] for ligne in affectes]
    return (
        query.filter(
            or_(
                Utilisateur.id == racine,
                Utilisateur.cabinet_owner_id == racine,
                and_(
                    Utilisateur.role == ROLE_GESTIONNAIRE_PAIE,
                    Utilisateur.cabinet_owner_id.is_(None),
                    Utilisateur.id.in_(ids_affectes) if ids_affectes else False,
                ),
            )
        )
        .order_by(Utilisateur.id)
    )


def peut_gerer_dossier(db: Session, user: Utilisateur, dossier: Dossier) -> bool:
    """Accès à un dossier, tous rôles confondus.

    * administrateur plateforme : aucun ;
    * cabinet / gestionnaire de paie : propriétaire du dossier ou affecté ;
    * client : son entreprise ;
    * salarié : aucun accès au dossier (il passe par ses propres bulletins).
    """
    if user.is_admin:
        return False
    if user.role in STAFF_ROLES:
        if dossier.utilisateur_id == user.id or est_affecte(db, user, dossier.id):
            return True
        # Co-administrateur rattaché au propriétaire : accès à ses sociétés.
        if user.role == ROLE_CABINET and user.cabinet_owner_id:
            return dossier.utilisateur_id == user.cabinet_owner_id
        return False
    if user.role == ROLE_CLIENT:
        return user.dossier_id == dossier.id
    return False


def dossiers_gérés(user: Utilisateur, db: Session):
    """Requête des dossiers visibles pour l'utilisateur, selon son rôle."""
    if user.is_admin:
        return db.query(Dossier).filter(False)
    if user.role in STAFF_ROLES:
        conditions = [
            Dossier.utilisateur_id == user.id,
            and_(
                AccesDossier.utilisateur_id == user.id,
                AccesDossier.utilisateur_id.isnot(None),
            ),
        ]
        # Co-administrateur : toutes les sociétés du propriétaire du cabinet.
        if user.role == ROLE_CABINET and user.cabinet_owner_id:
            conditions.append(Dossier.utilisateur_id == user.cabinet_owner_id)
        return (
            db.query(Dossier)
            .outerjoin(AccesDossier, AccesDossier.dossier_id == Dossier.id)
            .filter(or_(*conditions))
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
