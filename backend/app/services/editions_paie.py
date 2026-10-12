"""États de paie collectifs (famille « États de paie »).

Cinq éditions, construites par agrégation des bulletins et de leurs lignes :

* **Journal de paie** — synthèse par salarié et par mois ;
* **Livre de paie** — détail de toutes les rubriques, ligne à ligne ;
* **État des cotisations CNPS** — bases et parts salariale et patronale par
  branche (retraite, prestations familiales, accidents du travail, maternité) ;
* **État de l'ITS** — brut imposable, impôt brut, réduit pour charges de
  famille et impôt net ;
* **Récapitulatif des charges patronales** — toutes les contributions
  employeur, y compris les taxes assises sur les salaires.

Ces états ne recalculent rien : ils agrègent les lignes déjà produites par le
moteur de paie, ce qui garantit qu'un état ne peut pas diverger d'un bulletin.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import BulletinPaie, Contrat, Etablissement, Salarie
from app.services.editions import (
    FAMILLE_PAIE,
    TYPE_MONTANT,
    TYPE_NOMBRE,
    TYPE_TEXTE,
    Colonne,
    ContexteEdition,
    DefinitionEdition,
    ResultatEdition,
    enregistrer,
)

#: Codes de lignes utilisés par les états.
CODE_RETRAITE = "CNPS_RETRAITE"
CODE_PF = "CNPS_PF"
CODE_AT = "CNPS_AT"
CODE_MATERNITE = "CNPS_MATERNITE"
CODE_CMU_S = "CMU_S"
CODE_CMU_P = "CMU_P"
CODE_CN = "CN"
CODE_TA = "TA"
CODE_TFC = "TFC"
CODE_IBS = "IBS"
CODE_RICF = "RICF"

#: L'effectif de l'impôt (nombre de parts) n'est pas persisté : il n'apparaît
#: que dans le libellé de la ligne RICF. On l'en extrait, sans jamais échouer.
_PARTS_RE = re.compile(r"\((\d+(?:[.,]\d+)?)\s*parts?\)", re.IGNORECASE)


# ─────────────────────────────────────────────
#  OUTILS PARTAGÉS
# ─────────────────────────────────────────────

def _bulletins(db: Session, contexte: ContexteEdition) -> list[BulletinPaie]:
    """Bulletins calculés ou validés de l'établissement, triés par période.

    Le périmètre est l'établissement : c'est à ce niveau que la paie est tenue.
    Les brouillons sont écartés, un état de paie ne devant refléter que des
    bulletins arrêtés.
    """
    requete = (
        db.query(BulletinPaie)
        .join(Contrat, BulletinPaie.contrat_id == Contrat.id)
        .filter(Contrat.etablissement_id == contexte.etablissement_id)
        .filter(BulletinPaie.statut.in_(["calcule", "valide"]))
    )

    periodes = set(contexte.periodes)
    bulletins = [b for b in requete.all() if (b.annee, b.mois) in periodes]
    return sorted(
        bulletins,
        key=lambda b: (
            b.annee, b.mois,
            (b.contrat.salarie.nom or "") if b.contrat and b.contrat.salarie else "",
            (b.contrat.salarie.prenom or "") if b.contrat and b.contrat.salarie else "",
        ),
    )


def _salarie(bulletin: BulletinPaie) -> Optional[Salarie]:
    contrat = bulletin.contrat
    return contrat.salarie if contrat else None


def _montants(bulletin: BulletinPaie) -> dict[str, float]:
    """Montants par code de rubrique, pour un bulletin.

    Somme les lignes de même code : un bulletin peut en porter plusieurs
    (plusieurs absences, plusieurs primes au même code).
    """
    cumul: dict[str, float] = {}
    for ligne in bulletin.lignes or []:
        code = (ligne.code or "").upper()
        cumul[code] = cumul.get(code, 0.0) + float(ligne.montant_cs or 0.0)
    return cumul


def _montants_patronaux(bulletin: BulletinPaie) -> dict[str, float]:
    cumul: dict[str, float] = {}
    for ligne in bulletin.lignes or []:
        code = (ligne.code or "").upper()
        cumul[code] = cumul.get(code, 0.0) + float(ligne.montant_cp or 0.0)
    return cumul


def _base_cnps(bulletin: BulletinPaie) -> float:
    """Base des cotisations sociales : celle de la ligne retraite."""
    for ligne in bulletin.lignes or []:
        if (ligne.code or "").upper() == CODE_RETRAITE:
            return float(ligne.base_s or ligne.base_p or 0.0)
    return float(bulletin.salaire_brut or 0.0)


def _periode_courte(bulletin: BulletinPaie) -> str:
    from app.services.editions import MOIS_LABELS
    mois = int(bulletin.mois or 0)
    libelle = MOIS_LABELS[mois - 1][:4] if 1 <= mois <= 12 else "?"
    return f"{libelle} {bulletin.annee}"


def _identite(bulletin: BulletinPaie) -> tuple[str, str, str]:
    salarie = _salarie(bulletin)
    if not salarie:
        return "—", "Salarié inconnu", "—"
    nom = f"{(salarie.nom or '').upper()} {salarie.prenom or ''}".strip()
    return salarie.matricule or "—", nom, salarie.numero_securite_sociale or "—"


def _contexte_etat(db: Session, contexte: ContexteEdition, titre: str) -> dict:
    """Bandeau d'identification de l'état : établissement, dossier, période."""
    etab = (
        db.query(Etablissement)
        .filter(Etablissement.id == contexte.etablissement_id)
        .first()
    )
    dossier = etab.dossier if etab else None

    return {
        "etablissement": etab.raison_sociale if etab else "Établissement inconnu",
        "societe": dossier.nom_dossier if dossier else "",
        "periode": contexte.libelle_periode,
        "genere_le": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    }


def _nombre_de_parts(bulletin: BulletinPaie) -> Optional[float]:
    for ligne in bulletin.lignes or []:
        if (ligne.code or "").upper() == CODE_RICF and ligne.libelle:
            trouve = _PARTS_RE.search(ligne.libelle)
            if trouve:
                return float(trouve.group(1).replace(",", "."))
    return None


# ─────────────────────────────────────────────
#  1. JOURNAL DE PAIE
# ─────────────────────────────────────────────

def _journal_de_paie(db: Session, contexte: ContexteEdition) -> ResultatEdition:
    colonnes = [
        Colonne("periode", "Période", TYPE_TEXTE, largeur=8),
        Colonne("matricule", "Matricule", TYPE_TEXTE, largeur=9),
        Colonne("nom", "Nom et prénoms", TYPE_TEXTE, largeur=22),
        Colonne("brut", "Salaire brut", TYPE_MONTANT, total=True, largeur=12),
        Colonne("cotisations", "Cotisations", TYPE_MONTANT, total=True, largeur=12),
        Colonne("net_imposable", "Net imposable", TYPE_MONTANT, total=True, largeur=12),
        Colonne("its", "ITS", TYPE_MONTANT, total=True, largeur=11),
        Colonne("net_a_payer", "Net à payer", TYPE_MONTANT, total=True, largeur=12),
    ]

    lignes = []
    for bulletin in _bulletins(db, contexte):
        matricule, nom, _ = _identite(bulletin)
        impots = _montants(bulletin)
        lignes.append({
            "periode": _periode_courte(bulletin),
            "matricule": matricule,
            "nom": nom,
            "brut": float(bulletin.salaire_brut or 0.0),
            "cotisations": float(bulletin.cotisations_salariales or 0.0),
            "net_imposable": float(bulletin.net_imposable or 0.0),
            "its": round(impots.get(CODE_IBS, 0.0) + impots.get(CODE_RICF, 0.0), 2),
            "net_a_payer": float(bulletin.net_a_payer or 0.0),
        })

    resultat = ResultatEdition(
        code="JOURNAL_PAIE",
        titre="Journal de paie",
        colonnes=colonnes,
        lignes=lignes,
        contexte=_contexte_etat(db, contexte, "Journal de paie"),
    )
    if not lignes:
        resultat.notes.append(
            "Aucun bulletin calculé ou validé sur la période pour ce périmètre."
        )
    return resultat


enregistrer(DefinitionEdition(
    code="JOURNAL_PAIE",
    libelle="Journal de paie",
    famille=FAMILLE_PAIE,
    description=(
        "Synthèse par salarié et par mois : salaire brut, cotisations, net "
        "imposable, impôt sur les traitements et salaires et net à payer."
    ),
    fonction=_journal_de_paie,
    paysage=True,
))


# ─────────────────────────────────────────────
#  2. LIVRE DE PAIE
# ─────────────────────────────────────────────

def _livre_de_paie(db: Session, contexte: ContexteEdition) -> ResultatEdition:
    colonnes = [
        Colonne("periode", "Période", TYPE_TEXTE, largeur=7),
        Colonne("matricule", "Matricule", TYPE_TEXTE, largeur=8),
        Colonne("nom", "Nom et prénoms", TYPE_TEXTE, largeur=18),
        Colonne("code", "Code", TYPE_TEXTE, largeur=10),
        Colonne("libelle", "Rubrique", TYPE_TEXTE, largeur=24),
        Colonne("base", "Base", TYPE_NOMBRE, largeur=9),
        Colonne("taux", "Taux", TYPE_NOMBRE, largeur=7),
        Colonne("gain", "Gain", TYPE_MONTANT, total=True, largeur=10),
        Colonne("retenue", "Retenue", TYPE_MONTANT, total=True, largeur=10),
        Colonne("montant_patronal", "Part patronale", TYPE_MONTANT, total=True, largeur=11),
    ]

    lignes = []
    for bulletin in _bulletins(db, contexte):
        matricule, nom, _ = _identite(bulletin)
        for ligne in bulletin.lignes or []:
            lignes.append({
                "periode": _periode_courte(bulletin),
                "matricule": matricule,
                "nom": nom,
                "code": ligne.code or "",
                "libelle": ligne.libelle or ligne.code or "",
                "base": float(ligne.base_s or ligne.base_p or 0.0),
                "taux": float(ligne.taux_s or ligne.taux_p or 0.0),
                "gain": float(ligne.montant_pr or 0.0),
                "retenue": float(ligne.montant_cs or 0.0),
                "montant_patronal": float(ligne.montant_cp or 0.0),
            })

    resultat = ResultatEdition(
        code="LIVRE_PAIE",
        titre="Livre de paie",
        colonnes=colonnes,
        lignes=lignes,
        contexte=_contexte_etat(db, contexte, "Livre de paie"),
    )
    if not lignes:
        resultat.notes.append(
            "Aucune rubrique sur la période : vérifiez que les bulletins sont calculés."
        )
    return resultat


enregistrer(DefinitionEdition(
    code="LIVRE_PAIE",
    libelle="Livre de paie",
    famille=FAMILLE_PAIE,
    description=(
        "Détail complet des rubriques, ligne à ligne : base, taux, gain, "
        "retenue et part patronale, pour chaque salarié et chaque mois."
    ),
    fonction=_livre_de_paie,
    paysage=True,
))


# ─────────────────────────────────────────────
#  3. ÉTAT DES COTISATIONS CNPS
# ─────────────────────────────────────────────

def _etat_cotisations_cnps(db: Session, contexte: ContexteEdition) -> ResultatEdition:
    colonnes = [
        Colonne("periode", "Période", TYPE_TEXTE, largeur=7),
        Colonne("matricule", "Matricule", TYPE_TEXTE, largeur=8),
        Colonne("nom", "Nom et prénoms", TYPE_TEXTE, largeur=18),
        Colonne("cnps", "N° CNPS", TYPE_TEXTE, largeur=10),
        Colonne("base", "Base CNPS", TYPE_MONTANT, total=True, largeur=10),
        Colonne("retraite_s", "Retraite sal.", TYPE_MONTANT, total=True, largeur=9),
        Colonne("retraite_p", "Retraite pat.", TYPE_MONTANT, total=True, largeur=9),
        Colonne("pf", "Prest. familiales", TYPE_MONTANT, total=True, largeur=9),
        Colonne("at", "Accidents trav.", TYPE_MONTANT, total=True, largeur=9),
        Colonne("maternite", "Maternité", TYPE_MONTANT, total=True, largeur=8),
        Colonne("total_salarial", "Total salarial", TYPE_MONTANT, total=True, largeur=9),
        Colonne("total_patronal", "Total patronal", TYPE_MONTANT, total=True, largeur=10),
    ]

    lignes = []
    for bulletin in _bulletins(db, contexte):
        matricule, nom, cnps = _identite(bulletin)
        salariales = _montants(bulletin)
        patronales = _montants_patronaux(bulletin)
        retraite_s = salariales.get(CODE_RETRAITE, 0.0)
        retraite_p = patronales.get(CODE_RETRAITE, 0.0)
        pf = patronales.get(CODE_PF, 0.0)
        at = patronales.get(CODE_AT, 0.0)
        maternite = patronales.get(CODE_MATERNITE, 0.0)
        lignes.append({
            "periode": _periode_courte(bulletin),
            "matricule": matricule,
            "nom": nom,
            "cnps": cnps,
            "base": _base_cnps(bulletin),
            "retraite_s": retraite_s,
            "retraite_p": retraite_p,
            "pf": pf,
            "at": at,
            "maternite": maternite,
            "total_salarial": round(retraite_s, 2),
            "total_patronal": round(retraite_p + pf + at + maternite, 2),
        })

    resultat = ResultatEdition(
        code="CNPS_COTISATIONS",
        titre="État des cotisations CNPS",
        colonnes=colonnes,
        lignes=lignes,
        contexte=_contexte_etat(db, contexte, "État des cotisations CNPS"),
    )
    if not lignes:
        resultat.notes.append("Aucun bulletin sur la période pour ce périmètre.")
    resultat.notes.append(
        "Les taux appliqués sont ceux du moteur de paie ; en cas de taux "
        "d'accident du travail spécifique à l'établissement, ils en tiennent compte."
    )
    return resultat


enregistrer(DefinitionEdition(
    code="CNPS_COTISATIONS",
    libelle="État des cotisations CNPS",
    famille=FAMILLE_PAIE,
    description=(
        "Par salarié : base CNPS, retraite salariale et patronale, prestations "
        "familiales, accidents du travail et maternité, avec totaux."
    ),
    fonction=_etat_cotisations_cnps,
    paysage=True,
))


# ─────────────────────────────────────────────
#  4. ÉTAT DE L'ITS
# ─────────────────────────────────────────────

def _etat_its(db: Session, contexte: ContexteEdition) -> ResultatEdition:
    colonnes = [
        Colonne("periode", "Période", TYPE_TEXTE, largeur=8),
        Colonne("matricule", "Matricule", TYPE_TEXTE, largeur=10),
        Colonne("nom", "Nom et prénoms", TYPE_TEXTE, largeur=26),
        Colonne("brut_imposable", "Brut imposable", TYPE_MONTANT, total=True, largeur=13),
        Colonne("parts", "Parts", TYPE_NOMBRE, largeur=7),
        Colonne("impot_brut", "Impôt brut", TYPE_MONTANT, total=True, largeur=12),
        Colonne("ricf", "RICF", TYPE_MONTANT, total=True, largeur=12),
        Colonne("its_net", "ITS net", TYPE_MONTANT, total=True, largeur=12),
    ]

    lignes = []
    for bulletin in _bulletins(db, contexte):
        matricule, nom, _ = _identite(bulletin)
        montants = _montants(bulletin)
        impot_brut = montants.get(CODE_IBS, 0.0)
        # La RICF est stockée en négatif sur la ligne : on la présente en
        # déduction positive, plus lisible dans un état.
        ricf = abs(montants.get(CODE_RICF, 0.0))
        lignes.append({
            "periode": _periode_courte(bulletin),
            "matricule": matricule,
            "nom": nom,
            "brut_imposable": float(bulletin.net_imposable or 0.0),
            "parts": _nombre_de_parts(bulletin),
            "impot_brut": impot_brut,
            "ricf": ricf,
            "its_net": round(impot_brut - ricf, 2),
        })

    resultat = ResultatEdition(
        code="ITS",
        titre="État de l'impôt sur les traitements et salaires",
        colonnes=colonnes,
        lignes=lignes,
        contexte=_contexte_etat(db, contexte, "État de l'ITS"),
    )
    if not lignes:
        resultat.notes.append("Aucun bulletin sur la période pour ce périmètre.")
    return resultat


enregistrer(DefinitionEdition(
    code="ITS",
    libelle="État de l'ITS",
    famille=FAMILLE_PAIE,
    description=(
        "Par salarié : brut imposable, nombre de parts, impôt brut, réduit "
        "d'impôt pour charges de famille et impôt net à reverser."
    ),
    fonction=_etat_its,
))


# ─────────────────────────────────────────────
#  5. RÉCAPITULATIF DES CHARGES PATRONALES
# ─────────────────────────────────────────────

def _recapitulatif_charges(db: Session, contexte: ContexteEdition) -> ResultatEdition:
    colonnes = [
        Colonne("periode", "Période", TYPE_TEXTE, largeur=6),
        Colonne("matricule", "Matricule", TYPE_TEXTE, largeur=8),
        Colonne("nom", "Nom et prénoms", TYPE_TEXTE, largeur=17),
        Colonne("retraite", "Retraite", TYPE_MONTANT, total=True, largeur=8),
        Colonne("pf", "Prest. fam.", TYPE_MONTANT, total=True, largeur=8),
        Colonne("at", "Accid. trav.", TYPE_MONTANT, total=True, largeur=8),
        Colonne("maternite", "Maternité", TYPE_MONTANT, total=True, largeur=8),
        Colonne("cmu", "CMU", TYPE_MONTANT, total=True, largeur=7),
        Colonne("cn", "Contribution nat.", TYPE_MONTANT, total=True, largeur=9),
        Colonne("ta", "Taxe apprent.", TYPE_MONTANT, total=True, largeur=8),
        Colonne("tfc", "Formation cont.", TYPE_MONTANT, total=True, largeur=8),
        Colonne("total", "Total charges", TYPE_MONTANT, total=True, largeur=10),
    ]

    lignes = []
    for bulletin in _bulletins(db, contexte):
        matricule, nom, _ = _identite(bulletin)
        patronales = _montants_patronaux(bulletin)
        valeurs = {
            "retraite": patronales.get(CODE_RETRAITE, 0.0),
            "pf": patronales.get(CODE_PF, 0.0),
            "at": patronales.get(CODE_AT, 0.0),
            "maternite": patronales.get(CODE_MATERNITE, 0.0),
            "cmu": patronales.get(CODE_CMU_P, 0.0),
            "cn": patronales.get(CODE_CN, 0.0),
            "ta": patronales.get(CODE_TA, 0.0),
            "tfc": patronales.get(CODE_TFC, 0.0),
        }
        valeurs["total"] = round(sum(valeurs.values()), 2)
        lignes.append({
            "periode": _periode_courte(bulletin),
            "matricule": matricule,
            "nom": nom,
            **valeurs,
        })

    resultat = ResultatEdition(
        code="CHARGES_PATRONALES",
        titre="Récapitulatif des charges patronales",
        colonnes=colonnes,
        lignes=lignes,
        contexte=_contexte_etat(db, contexte, "Récapitulatif des charges patronales"),
    )
    if not lignes:
        resultat.notes.append("Aucun bulletin sur la période pour ce périmètre.")
    return resultat


enregistrer(DefinitionEdition(
    code="CHARGES_PATRONALES",
    libelle="Récapitulatif des charges patronales",
    famille=FAMILLE_PAIE,
    description=(
        "Toutes les contributions employeur : CNPS (retraite, prestations "
        "familiales, accidents du travail, maternité), CMU, contribution "
        "nationale, taxe d'apprentissage et taxe de formation continue."
    ),
    fonction=_recapitulatif_charges,
    paysage=True,
))
