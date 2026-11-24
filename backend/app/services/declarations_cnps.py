"""Déclaration CNPS mensuelle : la cotisation nominative déposée sur e-CNPS.

Les lignes sont construites à partir des bulletins du mois de l'établissement,
avec les colonnes du « modèle de fichier de paie » de la CNPS :

    N° CNPS · nom · prénoms · date de naissance · date d'embauche ·
    date de départ · type de salarié (M/J/H) · durée travaillée ·
    salaire brut · branches cotisées (123)

Les bases et cotisations par branche viennent des lignes du bulletin
(CNPS_RETRAITE, CNPS_PF, CNPS_AT, CNPS_MATERNITE) : la déclaration reprend
exactement ce que la paie a calculé. Une branche non cotisée (contrat) est
ramenée à zéro.

Ce module ne fait qu'un calcul : l'enregistrement et le verrouillage sont
dans le routeur.
"""
from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import BulletinPaie, Contrat, DepartSalarie, Etablissement
from app.services.indemnites_rupture import _en_date

TYPE_CNPS_MENSUELLE = "cnps_mensuelle"
STATUT_GENEREE = "generee"
STATUT_DEPOSEE = "deposee"

BLOQUANT = "bloquant"
ALERTE = "alerte"

#: Heures d'une journée de travail, pour convertir les heures d'un journalier.
HEURES_PAR_JOUR = 8.0

#: En-têtes du modèle de fichier e-CNPS, dans l'ordre et avec leur libellé.
ENTETES_FICHIER = (
    "NUMERO CNPS",
    "NOM",
    "PRENOMS",
    "ANNEE DE NAISSANCE",
    "DATE D'EMBAUCHE",
    "DATE DE DEPART",
    "TYPE SALARIE \nM: Mensuel \nJ : Journalier \nH: Horaire",
    "DUREE TRAVAILLEE",
    "SALAIRE BRUT",
    "BRANCHE COTISEE\n1: Retraite \n2 : Accidents du Travail et Maladies Professionnelles \n"
    "3: Prestations Familiales et Assurance Maternite",
)


@dataclass
class Anomalie:
    niveau: str
    salarie: str
    message: str


@dataclass
class LigneCalculee:
    salarie_id: Optional[int]
    contrat_id: Optional[int]
    bulletin_id: Optional[int]
    ordre: int
    numero_cnps: Optional[str]
    nom: str
    prenoms: str
    date_naissance: Optional[date]
    date_embauche: Optional[date]
    date_depart: Optional[date]
    type_salarie: str
    duree_travaillee: float
    salaire_brut: float
    branches: str
    base_retraite: float = 0.0
    base_pf_at_am: float = 0.0
    cotisation_retraite: float = 0.0
    cotisation_pf: float = 0.0
    cotisation_at: float = 0.0
    cotisation_am: float = 0.0


@dataclass
class DeclarationCalculee:
    annee: int
    mois: int
    lignes: list[LigneCalculee] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    totaux: dict = field(default_factory=dict)

    @property
    def bloquee(self) -> bool:
        return any(a.niveau == BLOQUANT for a in self.anomalies)

    @property
    def effectif(self) -> int:
        return len(self.lignes)

    @property
    def masse_salariale(self) -> float:
        return round(sum(l.salaire_brut for l in self.lignes), 2)

    @property
    def total_cotisations(self) -> float:
        return round(self.totaux.get("total_cotisations", 0.0), 2)


def bornes_du_mois(annee: int, mois: int) -> tuple[date, date]:
    return date(annee, mois, 1), date(annee, mois, calendar.monthrange(annee, mois)[1])


def _nom_complet(salarie) -> str:
    if salarie is None:
        return "Salarié inconnu"
    return f"{(salarie.nom or '').upper()} {salarie.prenom or ''}".strip()


def _ligne(bulletin: BulletinPaie, code: str):
    return next((l for l in bulletin.lignes or [] if (l.code or "").upper() == code), None)


def _duree_travaillee(type_salarie: str, contrat: Contrat, bulletin: BulletinPaie) -> float:
    """Mensuel : 1 mois ; horaire : heures payées ; journalier : jours payés."""
    if type_salarie == "M":
        return 1.0
    base = _ligne(bulletin, "BASE")
    quantite = float(base.base_s or 0.0) if base else 0.0
    if type_salarie == "J" and (contrat.unite_temps or "Heures") != "Jours":
        quantite = quantite / HEURES_PAR_JOUR
    return round(quantite, 2)


def _depart_dans_le_mois(depart: Optional[DepartSalarie], debut: date, fin: date) -> Optional[date]:
    date_sortie = _en_date(depart.date_sortie) if depart else None
    if date_sortie and debut <= date_sortie <= fin:
        return date_sortie
    return None


def _bulletins_du_mois(db: Session, etablissement: Etablissement, annee: int, mois: int) -> list[BulletinPaie]:
    return (
        db.query(BulletinPaie)
        .join(Contrat, Contrat.id == BulletinPaie.contrat_id)
        .filter(
            Contrat.etablissement_id == etablissement.id,
            BulletinPaie.annee == annee,
            BulletinPaie.mois == mois,
        )
        .all()
    )


def _contrats_actifs_sans_bulletin(
    db: Session, etablissement: Etablissement, debut: date, fin: date, avec_bulletin: set[int]
) -> list[Contrat]:
    """Contrats en cours sur le mois qui n'ont pas de bulletin : à signaler."""
    resultat = []
    for contrat in db.query(Contrat).filter(Contrat.etablissement_id == etablissement.id).all():
        if contrat.id in avec_bulletin:
            continue
        entree = _en_date(contrat.date_debut_contrat)
        sortie = _en_date(contrat.depart_salarie.date_sortie) if contrat.depart_salarie else None
        if entree and entree > fin:
            continue
        if sortie and sortie < debut:
            continue
        if contrat.statut == "termine" and sortie is None:
            continue
        resultat.append(contrat)
    return resultat


def calculer_declaration(db: Session, etablissement: Etablissement, annee: int, mois: int) -> DeclarationCalculee:
    """Construit la déclaration du mois : lignes, anomalies et totaux."""
    debut, fin = bornes_du_mois(annee, mois)
    declaration = DeclarationCalculee(annee=annee, mois=mois)
    bulletins = _bulletins_du_mois(db, etablissement, annee, mois)

    if not bulletins:
        declaration.anomalies.append(Anomalie(BLOQUANT, "—", "Aucun bulletin calculé pour ce mois."))

    lignes = []
    for bulletin in bulletins:
        contrat = bulletin.contrat
        salarie = contrat.salarie if contrat else None
        nom = _nom_complet(salarie)

        if bulletin.statut != "valide":
            declaration.anomalies.append(Anomalie(BLOQUANT, nom, "Bulletin non validé."))
        numero = (salarie.numero_securite_sociale or "").strip() if salarie else ""
        if not numero:
            declaration.anomalies.append(Anomalie(BLOQUANT, nom, "N° CNPS manquant (fiche salarié)."))
        elif not numero.isdigit() or len(numero) != 12:
            declaration.anomalies.append(Anomalie(ALERTE, nom, f"N° CNPS inhabituel : « {numero} » (12 chiffres attendus)."))
        if salarie is not None and not salarie.date_naissance:
            declaration.anomalies.append(Anomalie(ALERTE, nom, "Date de naissance manquante."))
        if not (bulletin.salaire_brut or 0):
            declaration.anomalies.append(Anomalie(ALERTE, nom, "Salaire brut nul."))

        type_salarie = contrat.type_salarie_cnps
        branches = contrat.cnps_branches or "123"
        retraite = _ligne(bulletin, "CNPS_RETRAITE")
        pf = _ligne(bulletin, "CNPS_PF")
        at = _ligne(bulletin, "CNPS_AT")
        am = _ligne(bulletin, "CNPS_MATERNITE")

        ligne = LigneCalculee(
            salarie_id=salarie.id if salarie else None,
            contrat_id=contrat.id if contrat else None,
            bulletin_id=bulletin.id,
            ordre=0,
            numero_cnps=numero or None,
            nom=(salarie.nom or "").upper() if salarie else "",
            prenoms=(salarie.prenom or "") if salarie else "",
            date_naissance=_en_date(salarie.date_naissance) if salarie else None,
            date_embauche=_en_date(contrat.date_debut_contrat),
            date_depart=_depart_dans_le_mois(contrat.depart_salarie, debut, fin),
            type_salarie=type_salarie,
            duree_travaillee=_duree_travaillee(type_salarie, contrat, bulletin),
            salaire_brut=round(float(bulletin.salaire_brut or 0.0), 2),
            branches=branches,
        )
        if "1" in branches and retraite:
            ligne.base_retraite = float(retraite.base_p or retraite.base_s or 0.0)
            ligne.cotisation_retraite = float(retraite.montant_cs or 0.0) + float(retraite.montant_cp or 0.0)
        if "3" in branches:
            if pf:
                ligne.base_pf_at_am = float(pf.base_p or 0.0)
                ligne.cotisation_pf = float(pf.montant_cp or 0.0)
            if am:
                ligne.base_pf_at_am = ligne.base_pf_at_am or float(am.base_p or 0.0)
                ligne.cotisation_am = float(am.montant_cp or 0.0)
        if "2" in branches and at:
            ligne.base_pf_at_am = ligne.base_pf_at_am or float(at.base_p or 0.0)
            ligne.cotisation_at = float(at.montant_cp or 0.0)
        lignes.append(ligne)

    lignes.sort(key=lambda l: (l.nom, l.prenoms))
    for ordre, ligne in enumerate(lignes, start=1):
        ligne.ordre = ordre
    declaration.lignes = lignes

    for contrat in _contrats_actifs_sans_bulletin(db, etablissement, debut, fin, {l.contrat_id for l in lignes}):
        declaration.anomalies.append(Anomalie(ALERTE, _nom_complet(contrat.salarie), "Contrat en cours sans bulletin ce mois-ci."))

    def somme(attribut):
        return round(sum(getattr(l, attribut) for l in lignes), 2)

    cotisations = {
        "retraite": somme("cotisation_retraite"),
        "prestations_familiales": somme("cotisation_pf"),
        "accidents_travail": somme("cotisation_at"),
        "assurance_maternite": somme("cotisation_am"),
    }
    declaration.totaux = {
        "effectif": len(lignes),
        "masse_salariale": somme("salaire_brut"),
        "base_retraite": somme("base_retraite"),
        "base_pf_at_am": somme("base_pf_at_am"),
        "cotisations": cotisations,
        "total_cotisations": round(sum(cotisations.values()), 2),
    }
    return declaration


def ligne_vers_dict(ligne: LigneCalculee) -> dict:
    return asdict(ligne)
