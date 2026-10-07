"""Réinitialisation de mot de passe : jetons à usage unique et à durée limitée.

Principes retenus :

* le jeton en clair n'est **jamais stocké** — seul son condensat SHA-256 l'est,
  ce qui rend inexploitable une fuite de la base ;
* un jeton est **à usage unique** et **périssable** ;
* demander un nouveau jeton **invalide les précédents** ;
* l'API ne révèle jamais si une adresse correspond à un compte (pas
  d'énumération) : c'est à l'appelant de renvoyer un message générique.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import PasswordResetToken, Utilisateur

logger = logging.getLogger(__name__)

#: Longueur du jeton en clair (URL-safe, ~43 caractères pour 32 octets).
JETON_OCTETS = 32


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _normaliser(valeur: Optional[datetime]) -> Optional[datetime]:
    """Ramène une date à un datetime conscient du fuseau.

    PostgreSQL renvoie des dates avec fuseau (`TIMESTAMP WITH TIME ZONE`),
    SQLite des dates naïves : sans normalisation, la comparaison lève un
    `TypeError` selon le moteur utilisé.
    """
    if valeur is None:
        return None
    if valeur.tzinfo is None:
        return valeur.replace(tzinfo=timezone.utc)
    return valeur


def hacher_jeton(jeton: str) -> str:
    """Condensat SHA-256 (hexadécimal) du jeton."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def creer_jeton(
    db: Session,
    utilisateur: Utilisateur,
    adresse_ip: Optional[str] = None,
) -> str:
    """Crée un jeton de réinitialisation et retourne sa valeur en clair.

    Les jetons encore valides de cet utilisateur sont invalidés : un seul lien
    actif à la fois, ce qui limite la fenêtre d'exploitation d'un email
    intercepté.
    """
    _invalider_jetons_en_cours(db, utilisateur.id)

    jeton = secrets.token_urlsafe(JETON_OCTETS)
    db.add(PasswordResetToken(
        utilisateur_id=utilisateur.id,
        token_hash=hacher_jeton(jeton),
        expires_at=_maintenant() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        requested_ip=adresse_ip,
    ))
    db.commit()
    return jeton


def _invalider_jetons_en_cours(db: Session, utilisateur_id: int) -> None:
    db.query(PasswordResetToken).filter(
        PasswordResetToken.utilisateur_id == utilisateur_id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": _maintenant()}, synchronize_session=False)
    db.flush()


def obtenir_jeton_valide(db: Session, jeton: Optional[str]) -> Optional[PasswordResetToken]:
    """Retourne le jeton s'il existe, n'a pas été utilisé et n'a pas expiré."""
    if not jeton:
        return None

    enregistrement = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hacher_jeton(jeton)
    ).first()

    if enregistrement is None:
        return None

    if enregistrement.used_at is not None:
        logger.info("Jeton de réinitialisation déjà utilisé (utilisateur %s)", enregistrement.utilisateur_id)
        return None

    expiration = _normaliser(enregistrement.expires_at)
    if expiration is None or expiration < _maintenant():
        logger.info("Jeton de réinitialisation expiré (utilisateur %s)", enregistrement.utilisateur_id)
        return None

    return enregistrement


def consommer_jeton(db: Session, enregistrement: PasswordResetToken) -> None:
    """Marque le jeton comme utilisé (usage unique)."""
    enregistrement.used_at = _maintenant()
    db.flush()


def invalider_tous_les_jetons(db: Session, utilisateur_id: int) -> int:
    """Invalide tous les jetons en cours d'un utilisateur.

    Appelé après un changement de mot de passe (y compris via le profil) : un
    lien de réinitialisation encore valide ne doit pas survivre au changement.
    """
    nombre = db.query(PasswordResetToken).filter(
        PasswordResetToken.utilisateur_id == utilisateur_id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": _maintenant()}, synchronize_session=False)
    return nombre


def purger_jetons_obsoletes(db: Session, jours: int = 7) -> int:
    """Supprime les jetons expirés depuis plus de `jours` jours.

    Évite que la table croisse indéfiniment : un jeton de réinitialisation n'a
    aucune valeur d'archive.
    """
    limite = _maintenant() - timedelta(days=jours)
    supprimes = db.query(PasswordResetToken).filter(
        PasswordResetToken.expires_at < limite
    ).delete(synchronize_session=False)
    if supprimes:
        logger.info("Purge de %s jeton(s) de réinitialisation obsolète(s)", supprimes)
    return supprimes


def construire_lien_reinitialisation(jeton: str) -> str:
    """URL à envoyer par email vers la page frontend de réinitialisation."""
    base = (settings.FRONTEND_BASE_URL or "").rstrip("/")
    return f"{base}/reset-password?token={jeton}"
