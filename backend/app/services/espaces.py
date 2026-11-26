"""Cloisonnement par cabinet : un sous-domaine par cabinet.

Chaque cabinet (propriétaire `role = cabinet`, `cabinet_owner_id IS NULL`)
porte un `sous_domaine` unique : `cabinet-x` est servi sur
`https://cabinet-x.<domaine de base>`. Tous les comptes du cabinet — membres,
gestionnaires, comptes clients de ses sociétés, salariés — ne se connectent
que sur ce sous-domaine ; le domaine principal est réservé à
l'administrateur plateforme.

Le cloisonnement n'est actif que si `DOMAINES_PLATEFORME` est renseigné ; en
local (localhost, adresses IP) il reste désactivé.

La base de données reste commune : les contrôles d'accès par dossier
(`services/permissions.py`) continuent de s'appliquer. Le sous-domaine ajoute
une barrière par adresse : un compte du cabinet X ne peut ni se connecter ni
utiliser son jeton sur l'adresse du cabinet Y.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session, object_session

from app.config import settings
from app.models.models import AccesDossier, Dossier, Utilisateur

#: Jeton de domaine porté par les sessions de l'administrateur plateforme.
DOMAINE_PLATEFORME = "plateforme"
#: Sous-domaines servis comme domaine principal (en plus du domaine nu).
ALIAS_PLATEFORME = ("app", "www")
#: Sous-domaines qu'aucun cabinet ne peut prendre.
SOUS_DOMAINES_RESERVES = frozenset({
    "app", "www", "api", "admin", "plateforme", "platform", "mail", "smtp", "ftp",
    "static", "cdn", "assets", "support", "aide", "status", "studio", "supabase",
    "auth", "login", "dev", "staging", "test", "demo",
})
_FORMAT = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$")
_HOTES_LOCAUX = ("localhost", "127.0.0.1", "::1", "[::1]", "testserver")


# ─────────────────────────────────────────
#  Domaines configurés
# ─────────────────────────────────────────

def domaines_de_base() -> list[str]:
    brut = getattr(settings, "DOMAINES_PLATEFORME", "") or ""
    return [d.strip().lower().lstrip(".") for d in brut.split(",") if d.strip()]


def cloisonnement_actif() -> bool:
    return bool(domaines_de_base())


@dataclass(frozen=True)
class Espace:
    """Espace désigné par l'adresse de la requête."""
    #: local (cloisonnement inactif) | plateforme | cabinet | inconnu
    type: str
    sous_domaine: Optional[str] = None
    domaine: Optional[str] = None

    @property
    def cle_jeton(self) -> Optional[str]:
        """Valeur attendue dans le jeton de session pour cet espace."""
        if self.type == "plateforme":
            return DOMAINE_PLATEFORME
        if self.type == "cabinet":
            return self.sous_domaine
        return None


def espace_depuis_hote(hote: Optional[str]) -> Espace:
    """« cabinet-x.payohada.cloud:443 » → espace du cabinet `cabinet-x`."""
    if not cloisonnement_actif():
        return Espace("local")
    nom = (hote or "").strip().lower()
    if nom.startswith("["):  # IPv6 entre crochets
        nom = nom.split("]")[0] + "]"
    else:
        nom = nom.split(":")[0]
    nom = nom.rstrip(".")
    if not nom or nom in _HOTES_LOCAUX or re.fullmatch(r"[\d.]+", nom):
        return Espace("local")
    for domaine in domaines_de_base():
        if nom == domaine:
            return Espace("plateforme", domaine=domaine)
        suffixe = f".{domaine}"
        if nom.endswith(suffixe):
            etiquette = nom[: -len(suffixe)]
            if "." in etiquette:
                return Espace("inconnu", domaine=domaine)
            if etiquette in ALIAS_PLATEFORME:
                return Espace("plateforme", domaine=domaine)
            return Espace("cabinet", sous_domaine=etiquette, domaine=domaine)
    return Espace("inconnu")


def espace_de_la_requete(request) -> Espace:
    return espace_depuis_hote(request.headers.get("host"))


# ─────────────────────────────────────────
#  Rattachement d'un compte à son cabinet
# ─────────────────────────────────────────

def _session(objet, db: Optional[Session]) -> Optional[Session]:
    return db or object_session(objet)


def _racine(db: Session, compte: Optional[Utilisateur]) -> Optional[Utilisateur]:
    """Remonte jusqu'au propriétaire du cabinet (`cabinet_owner_id` vide)."""
    vus = set()
    while compte is not None and compte.cabinet_owner_id and compte.id not in vus:
        vus.add(compte.id)
        compte = db.get(Utilisateur, compte.cabinet_owner_id)
    return compte


def cabinet_du_compte(compte: Utilisateur, db: Optional[Session] = None) -> Optional[Utilisateur]:
    """Propriétaire du cabinet auquel le compte appartient ; `None` pour la plateforme."""
    db = _session(compte, db)
    if compte.is_admin or db is None:
        return None
    if compte.role == "cabinet":
        return _racine(db, compte)
    if compte.role == "gestionnaire_paie":
        if compte.cabinet_owner_id:
            return _racine(db, compte)
        acces = db.query(AccesDossier).filter(AccesDossier.utilisateur_id == compte.id).first()
        dossier = db.get(Dossier, acces.dossier_id) if acces else None
        return _racine(db, dossier.proprietaire) if dossier else None
    if compte.role == "client":
        dossier = compte.dossier_client
        return _racine(db, dossier.proprietaire) if dossier else None
    if compte.role == "salarie" and compte.salarie is not None:
        etablissement = compte.salarie.etablissement
        dossier = etablissement.dossier if etablissement else None
        return _racine(db, dossier.proprietaire) if dossier else None
    return None


def sous_domaine_du_compte(compte: Utilisateur, db: Optional[Session] = None) -> Optional[str]:
    cabinet = cabinet_du_compte(compte, db)
    return cabinet.sous_domaine if cabinet else None


def sous_domaine_du_dossier(dossier: Optional[Dossier], db: Optional[Session] = None) -> Optional[str]:
    if dossier is None or dossier.proprietaire is None:
        return None
    racine = _racine(_session(dossier, db), dossier.proprietaire)
    return racine.sous_domaine if racine else None


def compte_autorise_sur(compte: Utilisateur, espace: Espace, db: Optional[Session] = None) -> bool:
    """Le compte peut-il se connecter sur l'espace désigné par l'adresse ?"""
    if espace.type == "local":
        return True
    if espace.type == "plateforme":
        return bool(compte.is_admin)
    if espace.type == "cabinet" and not compte.is_admin:
        return sous_domaine_du_compte(compte, db) == espace.sous_domaine
    return False


def cle_jeton_du_compte(compte: Utilisateur, db: Optional[Session] = None) -> Optional[str]:
    """Espace inscrit dans le jeton de session (`dom`), quand le cloisonnement est actif."""
    if not cloisonnement_actif():
        return None
    return DOMAINE_PLATEFORME if compte.is_admin else sous_domaine_du_compte(compte, db)


# ─────────────────────────────────────────
#  Sous-domaines : format, génération
# ─────────────────────────────────────────

def normaliser_sous_domaine(valeur: str) -> str:
    """« Cabinet Kouassi & Fils » → « cabinet-kouassi-fils »."""
    sans_accents = unicodedata.normalize("NFKD", valeur or "").encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", sans_accents.lower()).strip("-")
    return slug[:63].strip("-")


def erreur_sous_domaine(valeur: str) -> Optional[str]:
    """Message d'erreur si le sous-domaine est invalide, sinon `None`."""
    if not _FORMAT.fullmatch(valeur or ""):
        return "Sous-domaine invalide : 3 à 63 caractères, lettres minuscules, chiffres et tirets."
    if valeur in SOUS_DOMAINES_RESERVES:
        return f"Le sous-domaine « {valeur} » est réservé."
    return None


def sous_domaine_libre(db: Session, valeur: str, sauf_id: Optional[int] = None) -> bool:
    requete = db.query(Utilisateur.id).filter(Utilisateur.sous_domaine == valeur)
    if sauf_id is not None:
        requete = requete.filter(Utilisateur.id != sauf_id)
    return requete.first() is None


def generer_sous_domaine(db: Session, nom: str, sauf_id: Optional[int] = None) -> str:
    """Sous-domaine libre déduit du nom du cabinet (suffixe -2, -3… si pris)."""
    base = normaliser_sous_domaine(nom) or "cabinet"
    if len(base) < 3:
        base = f"cabinet-{base}"
    if base in SOUS_DOMAINES_RESERVES:
        base = f"cabinet-{base}"
    candidat, rang = base, 2
    while not sous_domaine_libre(db, candidat, sauf_id):
        suffixe = f"-{rang}"
        candidat = f"{base[: 63 - len(suffixe)]}{suffixe}"
        rang += 1
    return candidat


def attribuer_sous_domaines_manquants(db: Session) -> int:
    """Donne un sous-domaine aux cabinets qui n'en ont pas (au démarrage)."""
    cabinets = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.role == "cabinet",
            Utilisateur.cabinet_owner_id.is_(None),
            Utilisateur.is_admin.is_(False),
            Utilisateur.sous_domaine.is_(None),
        )
        .order_by(Utilisateur.id)
        .all()
    )
    for cabinet in cabinets:
        cabinet.sous_domaine = generer_sous_domaine(db, cabinet.cabinet_nom or cabinet.email.split("@")[0])
        db.flush()
    return len(cabinets)


# ─────────────────────────────────────────
#  Adresses publiques (emails)
# ─────────────────────────────────────────

def url_espace(sous_domaine: Optional[str] = None) -> str:
    """Adresse de l'espace : celle du cabinet, sinon l'adresse principale."""
    principale = (settings.FRONTEND_BASE_URL or "").rstrip("/")
    domaines = domaines_de_base()
    if not sous_domaine or not domaines:
        return principale
    schema = "http" if principale.startswith("http://") else "https"
    return f"{schema}://{sous_domaine}.{domaines[0]}"
