"""Déclarations CNPS annuelles : DISA et DASC d'un exercice.

* **DISA** — Déclaration Individuelle des Salaires Annuels : une ligne par
  salarié (brut annuel, durée d'activité, base PF/AT plafonnée, base
  retraite, régime), au format du fichier Excel déposé sur e-CNPS.
* **DASC** — Déclaration Annuelle des Salaires et des Cotisations : rappel
  mensuel des cotisations déclarées (total I) et payées (total II),
  cotisations annuelles par régime (total III), régularisation (IV = III − I),
  solde de l'exercice (V = I − II) et solde à payer (IV + V). Elle est déposée
  en PDF signé.

Les deux sont construites à partir des déclarations mensuelles **figées** de
l'exercice et de leurs paiements : elles reprennent ce qui a été déclaré.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import DSN, BulletinPaie, Constante, Contrat, Etablissement
from app.services.declarations_cnps import ALERTE, BLOQUANT, TYPE_CNPS_MENSUELLE, STATUT_DEPOSEE, Anomalie

MOIS_LABELS = (
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
)


@dataclass
class LigneDisa:
    ordre: int
    nom: str
    prenoms: str
    numero_cnps: Optional[str]
    annee_naissance: Optional[int]
    date_embauche: Optional[date]
    date_depart: Optional[date]
    type_salarie: str
    salaire_brut: float
    duree_activite: int
    montant_pf_at: float
    montant_retraite: float
    regime: str
    observation: str = ""


@dataclass
class MoisDasc:
    mois: int
    cotisations_declarees: float
    paiements_effectues: float
    declaree: bool


@dataclass
class RegimeDasc:
    code: str
    libelle: str
    taux: float
    base_annuelle: float
    cotisation: float


@dataclass
class DeclarationAnnuelle:
    annee: int
    lignes: list[LigneDisa] = field(default_factory=list)
    mois: list[MoisDasc] = field(default_factory=list)
    regimes: list[RegimeDasc] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    totaux: dict = field(default_factory=dict)


def francs(valeur) -> int:
    """Montant arrondi au franc le plus proche (0,5 vers le haut), comme à la CNPS."""
    return int(Decimal(str(valeur or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _taux(db: Session, code: str, defaut: float) -> float:
    constante = db.query(Constante).filter(
        Constante.code == code, Constante.pays == "CI", Constante.est_actif.is_(True)
    ).first()
    return float(constante.montant) if constante else defaut


def taux_cnps(db: Session, etablissement: Etablissement) -> dict[str, float]:
    """Taux annuels (en %), alignés sur ceux du moteur de paie."""
    taux_at = etablissement.taux_at if etablissement.taux_at and etablissement.taux_at > 0 else 2.0
    return {
        "maternite": _taux(db, "CNPS_MATERNITE_TAUX_P", 0.75),
        "prestations_familiales": _taux(db, "CNPS_PF_TAUX_P", 5.0),
        "accidents_travail": float(taux_at),
        "retraite": _taux(db, "CNPS_RETRAITE_TAUX_S", 6.3) + _taux(db, "CNPS_RETRAITE_TAUX_P", 7.7),
    }


def _mois_avec_bulletins(db: Session, etablissement: Etablissement, annee: int) -> set[int]:
    return {
        mois for (mois,) in (
            db.query(BulletinPaie.mois)
            .join(Contrat, Contrat.id == BulletinPaie.contrat_id)
            .filter(Contrat.etablissement_id == etablissement.id, BulletinPaie.annee == annee)
            .distinct()
        )
    }


def calculer_declaration_annuelle(db: Session, etablissement: Etablissement, annee: int) -> DeclarationAnnuelle:
    resultat = DeclarationAnnuelle(annee=annee)
    declarations = {
        d.mois: d
        for d in db.query(DSN).filter(
            DSN.etablissement_id == etablissement.id,
            DSN.type_declaration == TYPE_CNPS_MENSUELLE,
            DSN.annee == annee,
        )
    }

    if not declarations:
        resultat.anomalies.append(Anomalie(BLOQUANT, "—", f"Aucune déclaration mensuelle pour {annee}."))
    for mois in sorted(_mois_avec_bulletins(db, etablissement, annee) - set(declarations)):
        resultat.anomalies.append(Anomalie(
            ALERTE, "—", f"{MOIS_LABELS[mois - 1]} : des bulletins existent mais aucune déclaration n'a été générée."
        ))
    for mois, declaration in sorted(declarations.items()):
        if declaration.statut != STATUT_DEPOSEE:
            resultat.anomalies.append(Anomalie(ALERTE, "—", f"{MOIS_LABELS[mois - 1]} : déclaration non déposée."))

    # ── DISA : une ligne par salarié, à partir des lignes figées ──────────
    par_salarie: dict = {}
    for mois, declaration in sorted(declarations.items()):
        for ligne in declaration.lignes:
            cle = ligne.salarie_id or (ligne.numero_cnps, ligne.nom, ligne.prenoms)
            cumul = par_salarie.setdefault(cle, {"lignes": [], "mois": set()})
            cumul["lignes"].append(ligne)
            cumul["mois"].add(mois)

    lignes_disa = []
    for cumul in par_salarie.values():
        lignes = cumul["lignes"]
        derniere = lignes[-1]
        departs = [l.date_depart for l in lignes if l.date_depart]
        branches = sorted({c for l in lignes for c in (l.branches or "")})
        lignes_disa.append(LigneDisa(
            ordre=0,
            nom=derniere.nom or "",
            prenoms=derniere.prenoms or "",
            numero_cnps=derniere.numero_cnps,
            annee_naissance=derniere.date_naissance.year if derniere.date_naissance else None,
            date_embauche=derniere.date_embauche,
            date_depart=max(departs) if departs else None,
            type_salarie=derniere.type_salarie or "M",
            salaire_brut=round(sum(l.salaire_brut or 0.0 for l in lignes), 2),
            duree_activite=len(cumul["mois"]),
            montant_pf_at=round(sum(l.base_pf_at_am or 0.0 for l in lignes), 2),
            montant_retraite=round(sum(l.base_retraite or 0.0 for l in lignes), 2),
            regime="".join(branches) or "123",
        ))
        if not derniere.numero_cnps:
            resultat.anomalies.append(Anomalie(ALERTE, f"{derniere.nom} {derniere.prenoms}".strip(), "N° CNPS manquant."))
    lignes_disa.sort(key=lambda l: (l.nom, l.prenoms))
    for ordre, ligne in enumerate(lignes_disa, start=1):
        ligne.ordre = ordre
    resultat.lignes = lignes_disa

    # ── DASC : rappel mensuel ─────────────────────────────────────────────
    for mois in range(1, 13):
        declaration = declarations.get(mois)
        resultat.mois.append(MoisDasc(
            mois=mois,
            cotisations_declarees=francs(declaration.total_cotisations) if declaration else 0,
            paiements_effectues=francs(declaration.montant_paye) if declaration else 0,
            declaree=declaration is not None,
        ))
    # Les totaux de la DASC se calculent en francs entiers.
    total_i = sum(m.cotisations_declarees for m in resultat.mois)
    total_ii = sum(m.paiements_effectues for m in resultat.mois)

    # ── DASC : cotisations annuelles par régime ───────────────────────────
    toutes = [l for d in declarations.values() for l in d.lignes]
    base_pf_am = round(sum(l.base_pf_at_am or 0.0 for l in toutes if "3" in (l.branches or "")), 2)
    base_at = round(sum(l.base_pf_at_am or 0.0 for l in toutes if "2" in (l.branches or "")), 2)
    base_retraite = round(sum(l.base_retraite or 0.0 for l in toutes if "1" in (l.branches or "")), 2)
    taux = taux_cnps(db, etablissement)
    regimes = [
        ("maternite", "Assurance maternité", taux["maternite"], base_pf_am),
        ("prestations_familiales", "Prestations familiales", taux["prestations_familiales"], base_pf_am),
        ("accidents_travail", "Accidents du travail", taux["accidents_travail"], base_at),
        ("retraite", "Régime général de retraite", taux["retraite"], base_retraite),
    ]
    resultat.regimes = [
        RegimeDasc(code, libelle, taux_regime, base, francs(base * taux_regime / 100))
        for code, libelle, taux_regime, base in regimes
    ]
    total_iii = sum(r.cotisation for r in resultat.regimes)
    total_iv = total_iii - total_i
    total_v = total_i - total_ii

    salaire_brut = round(sum(l.salaire_brut for l in lignes_disa), 2)
    resultat.totaux = {
        "effectif": len(lignes_disa),
        "salaire_brut": salaire_brut,
        "montant_pf_at": round(sum(l.montant_pf_at for l in lignes_disa), 2),
        "montant_retraite": round(sum(l.montant_retraite for l in lignes_disa), 2),
        "total_i": total_i,
        "total_ii": total_ii,
        "total_iii": total_iii,
        "total_iv": total_iv,
        "total_v": total_v,
        "solde": total_iv + total_v,
        # Montants à reporter dans le formulaire DISA/DASC d'e-CNPS.
        "e_cnps": {
            "effectif_disa": len(lignes_disa),
            "salaire_brut_non_plafonne": salaire_brut,
            "salaire_pf": base_pf_am,
            "salaire_at": base_at,
            "salaire_am": base_pf_am,
            "salaire_retraite": base_retraite,
            "solde_dasc": total_iv + total_v,
        },
    }
    return resultat
