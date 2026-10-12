"""Socle du module « Éditions » : états de paie et leurs exports.

Le principe reprend celui des logiciels de paie classiques : un **catalogue
d'éditions** déclaratif, un **modèle tabulaire** unique, et plusieurs sorties
(PDF, Excel, CSV, email) produites depuis ce même modèle.

Chaque édition se contente donc de décrire ses colonnes et ses lignes ; elle
n'a rien à savoir des formats de sortie. Ajouter une édition revient à écrire
une fonction de génération et à l'enregistrer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from typing import Any, Callable, Iterable, Optional, Sequence

# ─────────────────────────────────────────────
#  MODÈLE TABULAIRE
# ─────────────────────────────────────────────

#: Types de colonne reconnus, qui pilotent l'alignement et le formatage.
TYPE_MONTANT = "montant"
TYPE_NOMBRE = "nombre"
TYPE_TEXTE = "texte"
TYPE_DATE = "date"
TYPES = (TYPE_MONTANT, TYPE_NOMBRE, TYPE_TEXTE, TYPE_DATE)

#: Familles d'éditions, pour regrouper le catalogue dans l'interface.
FAMILLE_PAIE = "Etats de paie"
FAMILLE_SOCIAL = "Declarations sociales"
FAMILLE_COMPTABLE = "Ecritures comptables"
FAMILLE_GESTION = "Etats de gestion"
FAMILLE_INDIVIDUEL = "Documents individuels"


@dataclass(frozen=True)
class Colonne:
    """Description d'une colonne d'édition."""
    cle: str
    libelle: str
    type: str = TYPE_MONTANT
    #: La colonne est-elle totalisée en pied d'état ?
    total: bool = False
    #: Largeur indicative, en pourcentage de la page.
    largeur: Optional[float] = None

    def __post_init__(self):
        if self.type not in TYPES:
            raise ValueError(f"Type de colonne inconnu : {self.type!r}")


@dataclass
class ResultatEdition:
    """Un état généré, prêt à être rendu dans n'importe quel format."""
    code: str
    titre: str
    colonnes: list[Colonne]
    lignes: list[dict]
    #: Totaux de pied, indexés par clé de colonne.
    totaux: dict = field(default_factory=dict)
    #: Informations d'en-tête : dossier, établissement, période…
    contexte: dict = field(default_factory=dict)
    #: Avertissements affichés sous l'état (données incomplètes, etc.).
    notes: list[str] = field(default_factory=list)

    @property
    def nombre_lignes(self) -> int:
        return len(self.lignes)

    def valeur(self, ligne: dict, colonne: Colonne) -> Any:
        return ligne.get(colonne.cle)


@dataclass(frozen=True)
class DefinitionEdition:
    """Une édition du catalogue."""
    code: str
    libelle: str
    famille: str
    description: str
    fonction: Callable[..., ResultatEdition]
    formats: tuple[str, ...] = ("pdf", "excel", "csv")
    #: Orientations acceptées par le rendu PDF.
    paysage: bool = False


# ─────────────────────────────────────────────
#  CATALOGUE
# ─────────────────────────────────────────────

_CATALOGUE: dict[str, DefinitionEdition] = {}


def enregistrer(definition: DefinitionEdition) -> DefinitionEdition:
    """Ajoute une édition au catalogue (utilisé comme décorateur)."""
    if definition.code in _CATALOGUE:
        raise ValueError(f"Édition déjà enregistrée : {definition.code}")
    _CATALOGUE[definition.code] = definition
    return definition


def edition(code: str) -> DefinitionEdition:
    if code not in _CATALOGUE:
        raise KeyError(code)
    return _CATALOGUE[code]


def catalogue() -> list[DefinitionEdition]:
    """Éditions disponibles, triées par famille puis par code."""
    return sorted(_CATALOGUE.values(), key=lambda d: (d.famille, d.code))


def catalogue_par_famille() -> dict[str, list[DefinitionEdition]]:
    groupes: dict[str, list[DefinitionEdition]] = {}
    for definition in catalogue():
        groupes.setdefault(definition.famille, []).append(definition)
    return groupes


# ─────────────────────────────────────────────
#  CONTEXTE ET PÉRIODES
# ─────────────────────────────────────────────

@dataclass
class ContexteEdition:
    """Paramètres d'exécution d'une édition.

    Le périmètre est l'**établissement** : c'est le niveau auquel la paie est
    tenue dans l'application, et celui attendu par les utilisateurs. Le dossier
    est déduit de l'établissement pour l'en-tête de l'état.
    """
    etablissement_id: int
    mois_debut: int
    annee_debut: int
    mois_fin: int
    annee_fin: int

    def __post_init__(self):
        for mois in (self.mois_debut, self.mois_fin):
            if not 1 <= mois <= 12:
                raise ValueError("Le mois doit être compris entre 1 et 12.")

    @property
    def periodes(self) -> list[tuple[int, int]]:
        """Suite des couples `(année, mois)` couverts, dans l'ordre."""
        resultat: list[tuple[int, int]] = []
        annee, mois = self.annee_debut, self.mois_debut
        while (annee, mois) <= (self.annee_fin, self.mois_fin):
            resultat.append((annee, mois))
            mois += 1
            if mois > 12:
                mois, annee = 1, annee + 1
        return resultat

    @property
    def libelle_periode(self) -> str:
        """« Juin 2025 » ou « Janvier 2025 – Mars 2025 »."""
        premier = f"{MOIS_LABELS[self.mois_debut - 1]} {self.annee_debut}"
        if (self.mois_debut, self.annee_debut) == (self.mois_fin, self.annee_fin):
            return premier
        return f"{premier} – {MOIS_LABELS[self.mois_fin - 1]} {self.annee_fin}"

    def contient(self, annee: Any, mois: Any) -> bool:
        try:
            return (int(annee), int(mois)) in set(self.periodes)
        except (TypeError, ValueError):
            return False


MOIS_LABELS = (
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
)


# ─────────────────────────────────────────────
#  FORMATAGE DES VALEURS
# ─────────────────────────────────────────────

def format_montant(valeur: Any) -> str:
    """Montant en francs CFA, séparateur de milliers, sans décimale."""
    if valeur is None or valeur == "":
        return ""
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return str(valeur)
    if nombre == 0:
        return "0"
    return f"{round(nombre):,}".replace(",", " ")


def format_nombre(valeur: Any) -> str:
    if valeur is None or valeur == "":
        return ""
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return str(valeur)
    if abs(nombre - round(nombre)) < 1e-9:
        return f"{round(nombre)}"
    return f"{nombre:.2f}".replace(".", ",")


def format_valeur(valeur: Any, colonne: Colonne) -> str:
    if colonne.type == TYPE_MONTANT:
        return format_montant(valeur)
    if colonne.type == TYPE_NOMBRE:
        return format_nombre(valeur)
    if colonne.type == TYPE_DATE:
        if isinstance(valeur, (date,)):
            return valeur.strftime("%d/%m/%Y")
        return "" if valeur is None else str(valeur)
    return "" if valeur is None else str(valeur)


def calculer_totaux(colonnes: Sequence[Colonne], lignes: Iterable[dict]) -> dict:
    """Somme les colonnes marquées `total`."""
    totaux: dict[str, float] = {}
    for colonne in colonnes:
        if not colonne.total:
            continue
        cumul = 0.0
        for ligne in lignes:
            valeur = ligne.get(colonne.cle)
            if isinstance(valeur, (int, float)):
                cumul += float(valeur)
        totaux[colonne.cle] = round(cumul, 2)
    return totaux


# ─────────────────────────────────────────────
#  GÉNÉRATION
# ─────────────────────────────────────────────

def generer_edition(db, code: str, contexte: ContexteEdition) -> ResultatEdition:
    """Exécute une édition du catalogue et retourne son modèle tabulaire."""
    definition = edition(code)
    resultat = definition.fonction(db, contexte)
    # Les totaux sont calculés une seule fois pour toutes les sorties.
    if not resultat.totaux:
        resultat.totaux = calculer_totaux(resultat.colonnes, resultat.lignes)
    resultat.contexte.setdefault("periode", contexte.libelle_periode)
    return resultat


# ─────────────────────────────────────────────
#  RENDUS
# ─────────────────────────────────────────────

_STYLES_ETAT = """
@page { size: A4 %(orientation)s; margin: 10mm 8mm 12mm 8mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 7.5pt; color: #000; }
h1 { font-size: 12pt; text-transform: uppercase; margin: 0 0 1mm; }
.contexte { font-size: 8pt; color: #333; margin-bottom: 1mm; }
.titre-etat { font-size: 10pt; font-weight: bold; text-transform: uppercase;
              margin-top: 2mm; }
table { width: 100%%; border-collapse: collapse; margin-top: 2mm; }
th { background-color: #e0e0e0; font-size: 7pt; text-align: center;
     border: 0.4pt solid #8d8d8d; padding: 1.5pt 2.5pt; }
td { border: 0.4pt solid #c6c6c6; padding: 1.2pt 2.5pt; vertical-align: top; }
.num { text-align: right; }
.mono { font-family: Courier, monospace; }
tfoot td { background-color: #ededed; font-weight: bold; }
.notes { margin-top: 3mm; font-size: 6.5pt; color: #525252; }
.genere { margin-top: 4mm; font-size: 6.5pt; color: #6f6f6f; text-align: right; }
"""


def _echapper(valeur: Any) -> str:
    import html as _html
    if valeur is None:
        return ""
    return _html.escape(str(valeur))


def rendre_pdf(resultat: ResultatEdition, paysage: bool = False) -> bytes:
    """Rendu PDF d'un état, par le même moteur que le bulletin de paie."""
    from xhtml2pdf import pisa

    entetes = "".join(
        f'<th style="width:{colonne.largeur}%">{_echapper(colonne.libelle)}</th>'
        if colonne.largeur else f"<th>{_echapper(colonne.libelle)}</th>"
        for colonne in resultat.colonnes
    )

    def cellules(ligne: dict, balise: str = "td") -> str:
        morceaux = []
        for colonne in resultat.colonnes:
            classes = []
            if colonne.type in (TYPE_MONTANT, TYPE_NOMBRE):
                classes.append("num")
            if colonne.type == TYPE_MONTANT:
                classes.append("mono")
            attribut = f' class="{" ".join(classes)}"' if classes else ""
            valeur = format_valeur(ligne.get(colonne.cle), colonne)
            morceaux.append(f"<{balise}{attribut}>{_echapper(valeur)}</{balise}>")
        return "".join(morceaux)

    corps = "".join(f"<tr>{cellules(ligne)}</tr>" for ligne in resultat.lignes)

    pied = ""
    if resultat.totaux:
        pied = f'<tfoot><tr>{cellules(resultat.totaux)}</tr></tfoot>'

    contexte = " — ".join(
        str(v) for v in resultat.contexte.values() if v
    )
    notes = "".join(f"<div>{_echapper(n)}</div>" for n in resultat.notes)

    html = f"""<html><head><meta charset="utf-8"/>
    <style>{_STYLES_ETAT % {"orientation": "landscape" if paysage else "portrait"}}</style>
    </head><body>
      <h1>{_echapper(resultat.contexte.get("societe") or resultat.titre)}</h1>
      <div class="contexte">{_echapper(contexte)}</div>
      <div class="titre-etat">{_echapper(resultat.titre)}</div>
      <table>
        <thead><tr>{entetes}</tr></thead>
        <tbody>{corps if resultat.lignes else '<tr><td colspan="99">Aucune donnée sur la période.</td></tr>'}</tbody>
        {pied}
      </table>
      {f'<div class="notes">{notes}</div>' if notes else ''}
      <div class="genere">État généré par payohada — {_echapper(resultat.contexte.get("genere_le", ""))}</div>
    </body></html>"""

    tampon = BytesIO()
    conversion = pisa.CreatePDF(BytesIO(html.encode("utf-8")), dest=tampon, encoding="utf-8")
    if conversion.err:
        raise RuntimeError(
            f"Échec de la conversion de l'état « {resultat.titre} » en PDF "
            f"({conversion.err} erreur(s))."
        )
    return tampon.getvalue()


def rendre_excel(resultat: ResultatEdition) -> bytes:
    """Rendu Excel d'un état : en-tête figé, filtres, colonnes ajustées."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    classeur = Workbook()
    feuille = classeur.active
    feuille.title = resultat.code[:31] or "Etat"

    bord = Border(*[Side(style="thin", color="C6C6C6")] * 4)
    entete_font = Font(bold=True, size=9)
    entete_fond = PatternFill("solid", fgColor="E0E0E0")

    # Bandeau d'identification, sur trois lignes au-dessus du tableau
    feuille.append([resultat.contexte.get("societe") or ""])
    feuille.append([resultat.titre])
    feuille.append([" — ".join(str(v) for v in resultat.contexte.values() if v)])
    ligne_entete = 4

    feuille.append([colonne.libelle for colonne in resultat.colonnes])
    for index, colonne in enumerate(resultat.colonnes, start=1):
        cellule = feuille.cell(row=ligne_entete, column=index)
        cellule.font = entete_font
        cellule.fill = entete_fond
        cellule.border = bord
        cellule.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        feuille.column_dimensions[get_column_letter(index)].width = (
            colonne.largeur * 0.9 if colonne.largeur else 14
        )

    for ligne in resultat.lignes:
        feuille.append([ligne.get(colonne.cle) for colonne in resultat.colonnes])

    if resultat.totaux:
        feuille.append([resultat.totaux.get(colonne.cle) for colonne in resultat.colonnes])
        for index in range(1, len(resultat.colonnes) + 1):
            feuille.cell(row=feuille.max_row, column=index).font = Font(bold=True)

    # Formatage des colonnes numériques et bordures sur tout le tableau
    for index, colonne in enumerate(resultat.colonnes, start=1):
        lettre = get_column_letter(index)
        for ligne in range(ligne_entete + 1, feuille.max_row + 1):
            cellule = feuille.cell(row=ligne, column=index)
            cellule.border = bord
            if colonne.type == TYPE_MONTANT:
                cellule.number_format = '#,##0'
                cellule.alignment = Alignment(horizontal="right")
            elif colonne.type == TYPE_NOMBRE:
                cellule.number_format = '#,##0.00'
                cellule.alignment = Alignment(horizontal="right")

    feuille.freeze_panes = f"A{ligne_entete + 1}"
    feuille.auto_filter.ref = (
        f"A{ligne_entete}:{get_column_letter(len(resultat.colonnes))}{feuille.max_row}"
    )

    for note in resultat.notes:
        feuille.append([])
        feuille.append([note])

    tampon = BytesIO()
    classeur.save(tampon)
    return tampon.getvalue()


def rendre_csv(resultat: ResultatEdition) -> bytes:
    """Rendu CSV, séparateur point-virgule et encodage UTF-8 avec BOM.

    Le BOM et le point-virgule sont ce qu'attendent Excel et les logiciels
    comptables francophones à l'ouverture d'un CSV.
    """
    import csv
    import io

    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\r\n")
    ecrivain.writerow([colonne.libelle for colonne in resultat.colonnes])
    for ligne in resultat.lignes:
        ecrivain.writerow([
            format_valeur(ligne.get(colonne.cle), colonne) if colonne.type != TYPE_MONTANT
            else (ligne.get(colonne.cle) if ligne.get(colonne.cle) is not None else "")
            for colonne in resultat.colonnes
        ])
    if resultat.totaux:
        ecrivain.writerow([
            resultat.totaux.get(colonne.cle, "") for colonne in resultat.colonnes
        ])
    return b"\xef\xbb\xbf" + tampon.getvalue().encode("utf-8")


RENDUS: dict[str, Callable[..., bytes]] = {
    "pdf": rendre_pdf,
    "excel": rendre_excel,
    "csv": rendre_csv,
}

EXTENSIONS = {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}
TYPES_MIME = {
    "pdf": "application/pdf",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
}


def rendre(resultat: ResultatEdition, format_sortie: str, paysage: bool = False) -> bytes:
    if format_sortie not in RENDUS:
        raise ValueError(f"Format de sortie inconnu : {format_sortie!r}")
    if format_sortie == "pdf":
        return rendre_pdf(resultat, paysage=paysage)
    return RENDUS[format_sortie](resultat)


def nom_fichier(resultat: ResultatEdition, format_sortie: str) -> str:
    """Nom de fichier explicite, sans caractère problématique."""
    base = f"{resultat.code}_{resultat.contexte.get('periode', '')}"
    base = base.replace(" ", "_").replace("–", "-")
    sur = "".join(c for c in base if c.isalnum() or c in "-_.") or "etat"
    return f"{sur}.{EXTENSIONS.get(format_sortie, 'dat')}"
