"""Limiteur de débit en mémoire, sans dépendance externe.

Suffisant pour une instance unique (déploiement actuel). Pour un déploiement
multi-instances, remplacer par un compteur partagé (Redis).
"""
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from app.config import settings


class SlidingWindowRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Lève une 429 si la clé a dépassé le quota sur la fenêtre glissante."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_attempts:
                retry_after = int(self.window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Trop de tentatives de connexion. "
                        f"Réessayez dans {retry_after} secondes."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset_all(self) -> None:
        """Vide le compteur (tests, ou réinitialisation administrative)."""
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    """Adresse source réelle de l'appelant.

    L'application est servie derrière un reverse proxy (Caddy) qui renseigne
    `X-Forwarded-For`. Sans cette prise en compte, tous les utilisateurs
    partageraient le compteur de l'IP du proxy — et se bloqueraient mutuellement.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Premier maillon de la chaîne = client d'origine.
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


#: Quota par compte ciblé : protège un compte précis du bourrage d'identifiants.
compte_rate_limiter = SlidingWindowRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
)

#: Quota par adresse source : volontairement plus large, pour ne pas bloquer
#: tout un réseau (NAT d'entreprise) à cause d'un seul utilisateur.
ip_rate_limiter = SlidingWindowRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS * 5,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
)

#: Quotas dédiés à la réinitialisation de mot de passe. Ils sont séparés de
#: ceux de la connexion pour qu'un utilisateur bloqué en connexion puisse
#: toujours récupérer son accès.
reinitialisation_compte_limiter = SlidingWindowRateLimiter(
    max_attempts=5,
    window_seconds=900,
)
reinitialisation_ip_limiter = SlidingWindowRateLimiter(
    max_attempts=20,
    window_seconds=900,
)
#: Protège l'endpoint de consommation du jeton (le jeton fait 256 bits, mais on
#: ne laisse pas pour autant un attaquant marteler l'API).
reset_token_limiter = SlidingWindowRateLimiter(
    max_attempts=20,
    window_seconds=900,
)

# Compatibilité avec les imports existants.
login_rate_limiter = compte_rate_limiter

#: Tous les limiteurs de l'application. Tenir cette liste à jour évite qu'un
#: nouveau quota échappe à la réinitialisation des tests.
TOUS_LES_LIMITEURS = (
    compte_rate_limiter,
    ip_rate_limiter,
    reinitialisation_compte_limiter,
    reinitialisation_ip_limiter,
    reset_token_limiter,
)


def reinitialiser_tous_les_limiteurs() -> None:
    """Remet tous les compteurs à zéro."""
    for limiteur in TOUS_LES_LIMITEURS:
        limiteur.reset_all()
