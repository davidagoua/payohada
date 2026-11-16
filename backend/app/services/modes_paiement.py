"""Règles des modes de paiement des salaires.

* L'administrateur plateforme gère le référentiel (`modes_paiement`).
* Un établissement choisit, parmi les modes actifs, ceux qu'il accepte.
* Un salarié est payé par l'un des modes acceptés par son établissement.

Un mode désactivé reste attaché aux établissements et salariés qui
l'utilisent déjà, mais ne peut plus être ajouté.
"""
import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Etablissement, ModePaiement, Salarie, etablissements_modes_paiement


def normaliser_code(code: str) -> str:
    """`mobile money` → `MOBILE_MONEY`, `prépayée` → `PREPAYEE` : codes stables."""
    sans_accents = unicodedata.normalize("NFKD", code).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", sans_accents.strip().upper()).strip("_")


def mode_utilise(db: Session, mode_id: int) -> bool:
    """Le mode est-il choisi par un établissement ou un salarié ?"""
    par_etablissement = (
        db.query(etablissements_modes_paiement.c.etablissement_id)
        .filter(etablissements_modes_paiement.c.mode_paiement_id == mode_id)
        .first()
    )
    par_salarie = db.query(Salarie.id).filter(Salarie.mode_paiement_id == mode_id).first()
    return par_etablissement is not None or par_salarie is not None


def definir_modes_etablissement(db: Session, etab: Etablissement, mode_ids: list[int]) -> None:
    """Remplace les modes acceptés par l'établissement.

    Refuse un mode inconnu, un mode inactif nouvellement ajouté, et le retrait
    d'un mode encore utilisé par un salarié de l'établissement.
    """
    ids = list(dict.fromkeys(mode_ids))
    modes = db.query(ModePaiement).filter(ModePaiement.id.in_(ids)).all() if ids else []
    if len(modes) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode de paiement inconnu.",
        )

    actuels = {mode.id for mode in etab.modes_paiement}
    for mode in modes:
        if not mode.est_actif and mode.id not in actuels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le mode de paiement « {mode.libelle} » n'est plus proposé.",
            )

    retires = actuels - set(ids)
    if retires:
        utilises = (
            db.query(ModePaiement.libelle)
            .join(Salarie, Salarie.mode_paiement_id == ModePaiement.id)
            .filter(Salarie.etablissement_id == etab.id, ModePaiement.id.in_(retires))
            .distinct()
            .all()
        )
        if utilises:
            noms = ", ".join(sorted(libelle for (libelle,) in utilises))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Mode(s) encore utilisé(s) par des salariés de l'établissement : {noms}. "
                    "Changez d'abord leur mode de paiement."
                ),
            )

    etab.modes_paiement = sorted(modes, key=lambda m: (m.ordre, m.libelle))


def verifier_mode_salarie(etab: Etablissement, mode_id: int | None) -> None:
    """Le mode d'un salarié doit être accepté par son établissement."""
    if mode_id is None:
        return
    if mode_id not in {mode.id for mode in etab.modes_paiement}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce mode de paiement n'est pas accepté par l'établissement du salarié.",
        )
