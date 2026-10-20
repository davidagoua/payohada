"""Soldes de congés payés : le calcul, une seule fois.

Il était fait deux fois — dans le bulletin et dans l'estimation du départ — avec
un test qui vérifiait qu'ils tombaient d'accord. Il est désormais produit ici et
consommé partout, y compris par l'espace salarié : un troisième calcul ne peut
plus diverger.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Contrat, SalarieAbsence
from app.services.conges_gratification import JOURS_CONGES_PAR_MOIS

#: Seul ce type d'absence consomme des congés payés.
TYPE_ABSENCE_CONGES = "Congés payés"


@dataclass(frozen=True)
class SoldeConges:
    annee: int
    mois: int
    #: Droits ouverts depuis le début de l'ancienneté jusqu'au mois demandé.
    acquis: float
    #: Jours pris depuis le début de l'ancienneté.
    pris: float
    #: Jours pris sur le mois demandé seulement.
    pris_ce_mois: float
    solde: float
    mois_anciennete: int
    debut_anciennete: date
    #: Vrai lorsque le mois demandé précède le début du contrat.
    periode_avant_contrat: bool


def _en_date(valeur) -> Optional[date]:
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    try:
        return datetime.strptime(str(valeur)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def debut_anciennete(contrat: Contrat, annee: int) -> date:
    """Date de départ de l'ancienneté, à défaut le 1er janvier de l'année.

    La date d'ancienneté prime sur la date de début de contrat : une reprise
    d'ancienneté ne doit pas être ignorée.
    """
    return (
        _en_date(contrat.date_anciennete or contrat.date_debut_contrat)
        or date(annee, 1, 1)
    )


def solde_conges(db: Session, contrat: Contrat, annee: int, mois: int) -> SoldeConges:
    """Droits acquis, jours pris et solde à la fin du mois demandé."""
    debut = debut_anciennete(contrat, annee)
    mois_anciennete = max(0, (annee - debut.year) * 12 + (mois - debut.month) + 1)
    acquis = round(mois_anciennete * JOURS_CONGES_PAR_MOIS, 2)

    _, dernier_jour = calendar.monthrange(annee, mois)
    debut_reference = date(annee, mois, 1)
    fin_reference = date(annee, mois, dernier_jour)

    pris = 0.0
    pris_ce_mois = 0.0
    absences = (
        db.query(SalarieAbsence)
        .filter(
            SalarieAbsence.salarie_id == contrat.salarie_id,
            SalarieAbsence.type_absence == TYPE_ABSENCE_CONGES,
        )
        .all()
    )
    for absence in absences:
        debut_absence = _en_date(absence.date_debut_absence)
        fin_absence = _en_date(absence.date_fin_absence)
        if not debut_absence or not fin_absence:
            continue
        if debut_absence <= fin_reference:
            pris += (min(fin_absence, fin_reference) - debut_absence).days + 1
        if debut_absence <= fin_reference and fin_absence >= debut_reference:
            pris_ce_mois += (
                min(fin_absence, fin_reference) - max(debut_absence, debut_reference)
            ).days + 1

    return SoldeConges(
        annee=annee,
        mois=mois,
        acquis=acquis,
        pris=round(pris, 2),
        pris_ce_mois=round(pris_ce_mois, 2),
        solde=round(acquis - pris, 2),
        mois_anciennete=mois_anciennete,
        debut_anciennete=debut,
        periode_avant_contrat=mois_anciennete <= 0,
    )
