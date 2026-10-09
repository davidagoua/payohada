"""Génération du bulletin de paie au format Sage Saari, en HTML puis en PDF.

Le même gabarit HTML sert à l'aperçu et à la pièce jointe envoyée par email :
il n'y a donc qu'une seule source de vérité pour la mise en page, reprise du
composant Vue `BulletinPaieSaari.vue`.

La conversion HTML → PDF est assurée par xhtml2pdf (reportlab), retenu parce
qu'il est **entièrement en Python** : WeasyPrint exige pango, cairo, gobject et
harfbuzz, bibliothèques système absentes de l'environnement et coûteuses à
ajouter à l'image de déploiement.

Contrainte de rendu : xhtml2pdf ne gère pas les boîtes flex ni `border-collapse`.
La mise en page n'utilise donc que des tableaux, comme un état imprimé classique.
"""
from __future__ import annotations

import html as _html
from datetime import datetime
from io import BytesIO
from typing import Any, Optional, Sequence

MOIS_LABELS = (
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
)

#: Codes rattachés aux cotisations et retenues (alignés sur le moteur de paie).
CODES_COTISATIONS = (
    "IBS", "RICF", "CNPS_RETRAITE", "CMU_S", "CN", "TA", "TFC",
    "CNPS_PF", "CNPS_AT", "CNPS_MATERNITE", "CMU_P",
)
CODES_NET = (
    "TRANSPORT", "TELEPHONE", "ACOMPTE", "FRAIS_PROFESSIONNELS", "AUTRE_RETENUE",
)

LIGNES_CUMULS = (
    ("Heures / jours travaillés", "heures_jours"),
    ("Heures supplémentaires", "heures_supp"),
    ("Jours d'absence", "jours_absences"),
    ("Salaire brut", "salaire_brut"),
    ("Brut imposable (ITS)", "brut_imposable"),
    ("Brut CNPS", "brut_cnps"),
    ("Base congés payés", "brut_conges"),
    ("Impôt sur salaires (ITS)", "ibs"),
    ("RICF", "ricf"),
    ("CMU", "cmu"),
    ("Retraite CNPS", "cot_retraite"),
    ("Congés acquis", "conges_acquis"),
    ("Congés pris", "conges_pris"),
    ("Solde de congés", "conges_solde"),
)

LIBELLES_TYPE_CONTRAT = {
    10: "CDI", 20: "CDD", 29: "CDD", 30: "CDD",
    40: "Stage", 50: "Apprentissage",
}


# ─────────────────────────────────────────────
#  OUTILS DE FORMATAGE
# ─────────────────────────────────────────────

def _echappe(valeur: Any) -> str:
    """Échappe toute donnée destinée au HTML (noms, libellés saisis…)."""
    if valeur is None:
        return ""
    return _html.escape(str(valeur))


def _entier(valeur: Any) -> str:
    """Montant en francs CFA, séparateur de milliers, sans décimale."""
    try:
        nombre = float(valeur or 0)
    except (TypeError, ValueError):
        return ""
    if nombre == 0:
        return ""
    return f"{round(nombre):,}".replace(",", " ")


def _nombre(valeur: Any) -> str:
    """Nombre décimal lisible (heures, jours, bases)."""
    if valeur is None or valeur == "":
        return ""
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return ""
    if nombre == 0:
        return ""
    if abs(nombre - round(nombre)) < 1e-9:
        return f"{round(nombre):,}".replace(",", " ")
    return f"{nombre:,.2f}".replace(",", " ").replace(".", ",")


def _taux(valeur: Any, pourcentage: bool = True) -> str:
    """Met en forme la colonne « Taux ».

    La sémantique de `taux_s` dépend de la nature de la ligne : un pourcentage
    pour les cotisations et retenues (6,3 %), mais un **taux horaire ou
    journalier en francs** pour les lignes de rémunération (1 730,80 F/h). Le
    suffixe « % » ne doit donc apparaître que sur les premières, faute de quoi le
    bulletin afficherait « 1 730,8 % », ce qui n'a aucun sens.
    """
    if valeur is None or valeur == "":
        return ""
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return ""
    if nombre == 0:
        return ""

    if not pourcentage:
        return _nombre(nombre)

    pourcent = nombre * 100 if 0 < nombre < 1 else nombre
    texte = f"{pourcent:.3f}".rstrip("0").rstrip(".")
    return f"{texte.replace('.', ',')} %"


def _date(valeur: Any) -> str:
    if not valeur:
        return "—"
    if isinstance(valeur, datetime):
        return valeur.strftime("%d/%m/%Y")
    try:
        return datetime.strptime(str(valeur)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return _echappe(valeur)


def _valeur(source: Any, cle: str) -> Any:
    """Lit un cumul sur un objet Pydantic, un dataclass ou un dictionnaire."""
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(cle)
    return getattr(source, cle, None)


def _libelle_periode(bulletin: Any) -> str:
    mois = int(getattr(bulletin, "mois", 0) or 0)
    annee = getattr(bulletin, "annee", "")
    if not 1 <= mois <= 12:
        return "—"
    return f"{MOIS_LABELS[mois - 1]} {annee}"


def _adresse_etablissement(etablissement: Any) -> list[str]:
    if etablissement is None:
        return []
    brut = getattr(etablissement, "adresse", None)
    if not brut:
        return []
    if isinstance(brut, str):
        return [brut]
    # L'adresse est stockée en JSON : on assemble les lignes non vides.
    morceaux = [
        brut.get("adresse_postale"),
        brut.get("adresse_postale2"),
        " ".join(filter(None, [brut.get("code_postal"), brut.get("ville")])),
        brut.get("pays"),
    ]
    return [m for m in morceaux if m]


# ─────────────────────────────────────────────
#  GABARIT HTML
# ─────────────────────────────────────────────

_STYLES = """
@page { size: A4 portrait; margin: 8mm 7mm 9mm 7mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 7.5pt;
       color: #000; line-height: 1.3; }
table { width: 100%; }
td, th { border: 0.4pt solid #8a8a8a; padding: 1.4pt 2.4pt; vertical-align: top; }
th { background-color: #ececec; font-weight: bold; }
.groupe th { font-size: 7pt; text-align: center; text-transform: uppercase; }
.pat { background-color: #f6f6f6; }
.num { text-align: right; }
.code { font-family: Courier, monospace; font-size: 7pt; }
.section td { background-color: #dcdcdc; font-weight: bold; font-size: 7pt;
              text-transform: uppercase; }
.total td { background-color: #ededed; font-weight: bold; }
.synthese td { background-color: #f6f6f6; font-weight: bold; }
.net td { background-color: #1a1a1a; color: #ffffff; font-weight: bold;
          font-size: 9.5pt; text-transform: uppercase; }
.entete td { border: 0.8pt solid #000; }
.raison { font-size: 10.5pt; font-weight: bold; text-transform: uppercase; }
.titre-doc { font-size: 12pt; font-weight: bold; text-transform: uppercase;
             text-align: right; }
.periode { font-size: 10pt; font-weight: bold; text-transform: uppercase;
           border: 0.8pt solid #000; padding: 1.2pt 4pt; }
.ident th { background-color: transparent; border: 0; color: #444;
            font-weight: normal; text-align: left; width: 34%; padding-left: 0; }
.ident td { border: 0; font-weight: bold; }
.fort { font-weight: bold; }
.cadre { border: 0.8pt solid #000; margin-top: 5pt; }
.cadre-titre { background-color: #dcdcdc; font-weight: bold; font-size: 7pt;
               text-transform: uppercase; padding: 1.4pt 3pt;
               border-bottom: 0.8pt solid #000; }
.mentions { font-size: 6.5pt; color: #333; text-align: justify; }
.signature { text-align: center; padding-top: 16pt; }
.bloc-salarie th { background-color: #ececec; font-weight: normal; color: #333;
                   white-space: nowrap; width: 13%; }
.saut { page-break-before: always; }
"""


def _lignes_tableau(lignes: Sequence[Any]) -> str:
    """Construit les lignes du tableau des rubriques.

    Le taux n'est présenté en pourcentage que pour les cotisations et retenues :
    sur les lignes de rémunération, c'est un taux horaire ou journalier libellé
    en francs.
    """
    morceaux = []
    for ligne in lignes:
        est_cotisation = str(ligne.code or "").upper() in CODES_COTISATIONS
        morceaux.append(
            "<tr>"
            f'<td class="code">{_echappe(ligne.code)}</td>'
            f"<td>{_echappe(ligne.libelle or ligne.code)}</td>"
            f'<td class="num">{_nombre(ligne.base_s)}</td>'
            f'<td class="num">{_taux(ligne.taux_s, est_cotisation)}</td>'
            f'<td class="num">{_entier(ligne.montant_pr)}</td>'
            f'<td class="num">{_entier(ligne.montant_cs)}</td>'
            f'<td class="num pat">{_nombre(ligne.base_p)}</td>'
            f'<td class="num pat">{_taux(ligne.taux_p, True)}</td>'
            f'<td class="num pat">{_entier(ligne.montant_cp)}</td>'
            "</tr>"
        )
    return "".join(morceaux)


def construire_html_saari(
    bulletin: Any,
    contrat: Any = None,
    salarie: Any = None,
    etablissement: Any = None,
    dossier: Any = None,
    cumuls: Any = None,
    rang: Optional[int] = None,
    total: Optional[int] = None,
    saut_de_page: bool = False,
) -> str:
    """Produit le HTML du bulletin, au format Sage Saari.

    `cumuls` est fourni par l'appelant (`compute_bulletin_cumuls`) afin que ce
    module reste sans dépendance au routeur ni à la session de base de données.

    `saut_de_page` force un saut avant le document. Il doit rester **désactivé**
    pour un bulletin isolé : appliqué au premier élément, il laisse une page
    blanche en tête. Il ne sert qu'à enchaîner plusieurs bulletins dans un même
    fichier, à partir du deuxième.
    """
    lignes = list(getattr(bulletin, "lignes", None) or [])

    def est_cotisation(code: Any) -> bool:
        return str(code or "").upper() in CODES_COTISATIONS

    def est_net(code: Any) -> bool:
        c = str(code or "").upper()
        return c in CODES_NET or c.startswith("RET_")

    elements_brut = [l for l in lignes if not est_cotisation(l.code) and not est_net(l.code)]
    cotisations = [l for l in lignes if est_cotisation(l.code)]
    retenues = [l for l in lignes if est_net(l.code)]

    cumul_mensuel = getattr(cumuls, "mensuel", None)
    cumul_annuel = getattr(cumuls, "annuel", None)

    # ── En-tête ──────────────────────────────────────────────────────
    adresse = _adresse_etablissement(etablissement)
    raison_sociale = (
        getattr(etablissement, "raison_sociale", None)
        or getattr(dossier, "nom_dossier", None)
        or "—"
    )
    lignes_adresse = "".join(f"{_echappe(l)}<br/>" for l in adresse)
    activite = getattr(etablissement, "activite", None)

    entete = f"""
    <table class="entete">
      <tr>
        <td style="width:57%">
          <div class="raison">{_echappe(raison_sociale)}</div>
          <div>{lignes_adresse}</div>
          {f'<div>{_echappe(activite)}</div>' if activite else ''}
          <table class="ident">
            <tr>
              <th>NIF / RCCM</th><td>{_echappe(getattr(etablissement, 'siret', None) or '—')}</td>
              <th style="width:26%">Code établissement</th>
              <td>{_echappe(getattr(etablissement, 'code', None) or '—')}</td>
            </tr>
            <tr>
              <th>N° employeur CNPS</th><td>{_echappe(getattr(etablissement, 'numero_cotisant', None) or '—')}</td>
              <th>Code activité</th>
              <td>{_echappe(getattr(etablissement, 'ape', None) or '—')}</td>
            </tr>
          </table>
        </td>
        <td style="width:43%; text-align:right">
          <div class="titre-doc">Bulletin de paie</div>
          <div style="margin-top:3pt"><span class="periode">{_echappe(_libelle_periode(bulletin))}</span></div>
          <table class="ident" style="margin-top:3pt">
            <tr><th style="text-align:right">Payé le</th>
                <td style="text-align:right">{_date(getattr(bulletin, 'date_paiement', None))}</td></tr>
            <tr><th style="text-align:right">Règlement</th>
                <td style="text-align:right">Virement bancaire</td></tr>
            {f'<tr><th style="text-align:right">Bulletin</th><td style="text-align:right">{rang} / {total}</td></tr>' if rang else ''}
          </table>
        </td>
      </tr>
    </table>"""

    # ── Bloc salarié ─────────────────────────────────────────────────
    poste = getattr(contrat, "poste_salaire", None)
    categorie = " / ".join(
        filter(None, [
            getattr(poste, "categorie_professionnelle", None) if poste else None,
            getattr(poste, "echelon_categorie", None) if poste else None,
        ])
    ) or "—"
    type_contrat = LIBELLES_TYPE_CONTRAT.get(
        getattr(contrat, "type_contrat_travail", None), "—"
    )
    horaires = getattr(contrat, "horaires", None)
    if getattr(contrat, "unite_temps", None) == "Jours":
        base_temps = "30,00 jours / mois"
    else:
        base_temps = f"{_nombre(getattr(horaires, 'horaire_travail', None) or 173.33)} heures / mois"

    nom_complet = " ".join(
        filter(None, [
            (getattr(salarie, "nom", "") or "").upper(),
            getattr(salarie, "prenom", "") or "",
        ])
    )

    bloc_salarie = f"""
    <table class="bloc-salarie" style="margin-top:4pt">
      <tr>
        <th>Matricule</th><td class="code">{_echappe(getattr(salarie, 'matricule', None) or '—')}</td>
        <th>Nom et prénoms</th><td colspan="3" class="fort">{_echappe(nom_complet)}</td>
      </tr>
      <tr>
        <th>Emploi</th><td colspan="3">{_echappe(getattr(contrat, 'emploi', None) or '—')}</td>
        <th>Catégorie / échelon</th><td>{_echappe(categorie)}</td>
      </tr>
      <tr>
        <th>Type de contrat</th><td>{_echappe(type_contrat)}</td>
        <th>Date d'entrée</th><td>{_date(getattr(contrat, 'date_debut_contrat', None))}</td>
        <th>Base de temps</th><td>{_echappe(base_temps)}</td>
      </tr>
      <tr>
        <th>Situation familiale</th><td>{_echappe(getattr(salarie, 'situation_matrimoniale', None) or '—')}</td>
        <th>Enfants à charge</th><td>{_echappe(getattr(salarie, 'enfants_charge', 0) or 0)}</td>
        <th>N° CNPS salarié</th>
        <td class="code">{_echappe(getattr(salarie, 'numero_securite_sociale', None) or '—')}</td>
      </tr>
      <tr>
        <th>Nationalité</th><td>{_echappe(getattr(salarie, 'nationalite', None) or '—')}</td>
        <th>Date de naissance</th><td>{_date(getattr(salarie, 'date_naissance', None))}</td>
        <th>Régime</th>
        <td>{'Expatrié' if getattr(salarie, 'expatrie', False) else 'Local'}</td>
      </tr>
    </table>"""

    # ── Tableau des rubriques ────────────────────────────────────────
    tableau = f"""
    <table style="margin-top:4pt">
      <thead>
        <tr class="groupe">
          <th rowspan="2" style="width:11%">Code</th>
          <th rowspan="2">Désignation</th>
          <th colspan="4">Part salariale</th>
          <th colspan="3" class="pat">Part patronale</th>
        </tr>
        <tr class="groupe">
          <th style="width:8%">Base</th><th style="width:7%">Taux</th>
          <th style="width:10%">Gain</th><th style="width:10%">Retenue</th>
          <th class="pat" style="width:8%">Base</th>
          <th class="pat" style="width:7%">Taux</th>
          <th class="pat" style="width:10%">Montant</th>
        </tr>
      </thead>
      <tbody>
        <tr class="section"><td colspan="9">1 — Éléments de salaire brut</td></tr>
        {_lignes_tableau(elements_brut)}
        <tr class="total">
          <td colspan="4">Total salaire brut</td>
          <td class="num">{_entier(getattr(bulletin, 'salaire_brut', 0))}</td>
          <td></td><td class="pat"></td><td class="pat"></td>
          <td class="num pat">{_entier(getattr(bulletin, 'cotisations_patronales', 0))}</td>
        </tr>
        <tr class="section"><td colspan="9">2 — Cotisations et retenues</td></tr>
        {_lignes_tableau(cotisations)}
        <tr class="section"><td colspan="9">3 — Indemnités et retenues diverses</td></tr>
        {_lignes_tableau(retenues) or '<tr><td colspan="9">Néant</td></tr>'}
      </tbody>
      <tfoot>
        <tr class="total">
          <td colspan="4">Total des retenues salariales</td>
          <td></td>
          <td class="num">{_entier(getattr(bulletin, 'cotisations_salariales', 0))}</td>
          <td colspan="3" class="pat"></td>
        </tr>
        <tr class="synthese">
          <td colspan="4">Net imposable (ITS)</td>
          <td colspan="2" class="num">{_entier(getattr(bulletin, 'net_imposable', 0))}</td>
          <td colspan="3" class="pat"></td>
        </tr>
        <tr class="net">
          <td colspan="4">Net à payer</td>
          <td colspan="2" class="num">{_entier(getattr(bulletin, 'net_a_payer', 0))}</td>
          <td colspan="3" class="pat"></td>
        </tr>
      </tfoot>
    </table>"""

    # ── Cadre des cumuls ─────────────────────────────────────────────
    corps_cumuls = "".join(
        "<tr>"
        f"<td>{_echappe(libelle)}</td>"
        f'<td class="num">{_nombre(_valeur(cumul_mensuel, cle))}</td>'
        f'<td class="num">{_nombre(_valeur(cumul_annuel, cle))}</td>'
        "</tr>"
        for libelle, cle in LIGNES_CUMULS
    )
    cadre_cumuls = f"""
    <div class="cadre">
      <div class="cadre-titre">Cumuls</div>
      <table>
        <thead>
          <tr><th style="width:52%">Libellé</th><th>Mensuel</th><th>Annuel</th></tr>
        </thead>
        <tbody>{corps_cumuls}</tbody>
      </table>
    </div>"""

    # ── Pied ─────────────────────────────────────────────────────────
    pied = f"""
    <div class="cadre">
      <div class="cadre-titre">Congés payés</div>
      <table>
        <tr>
          <th style="width:16%">Acquis</th>
          <td class="num" style="width:17%">{_nombre(_valeur(cumul_mensuel, 'conges_acquis'))} j</td>
          <th style="width:16%">Pris</th>
          <td class="num" style="width:17%">{_nombre(_valeur(cumul_mensuel, 'conges_pris'))} j</td>
          <th style="width:16%">Solde</th>
          <td class="num fort">{_nombre(_valeur(cumul_mensuel, 'conges_solde'))} j</td>
        </tr>
      </table>
      <table style="margin-top:5pt">
        <tr>
          <td style="border:0; width:50%">
            <div class="signature">Le salarié<br/><span style="font-size:6.5pt">(Signature)</span></div>
          </td>
          <td style="border:0; width:50%">
            <div class="signature">L'employeur<br/><span style="font-size:6.5pt">(Signature et cachet)</span></div>
          </td>
        </tr>
      </table>
      <div class="mentions" style="padding:2pt 3pt">
        Bulletin à conserver sans limitation de durée. Les cotisations sociales sont
        calculées sur la base des taux en vigueur ; l'impôt sur les traitements et
        salaires est calculé selon le barème progressif et le réduit d'impôt pour
        charges de famille.
      </div>
    </div>"""

    classes = "bulletin saut" if saut_de_page else "bulletin"
    return (
        '<html><head><meta charset="utf-8"/>'
        f"<style>{_STYLES}</style></head><body>"
        f'<div class="{classes}">'
        f"{entete}{bloc_salarie}{tableau}{cadre_cumuls}{pied}"
        "</div></body></html>"
    )


# ─────────────────────────────────────────────
#  CONVERSION EN PDF
# ─────────────────────────────────────────────

def html_vers_pdf(html: str) -> bytes:
    """Convertit un document HTML en PDF (A4), sans dépendance système."""
    from xhtml2pdf import pisa

    tampon = BytesIO()
    resultat = pisa.CreatePDF(
        BytesIO(html.encode("utf-8")), dest=tampon, encoding="utf-8"
    )
    if resultat.err:
        raise RuntimeError(
            f"Échec de la conversion du bulletin en PDF ({resultat.err} erreur(s))."
        )
    return tampon.getvalue()


def generer_pdf_saari(
    bulletin: Any,
    contrat: Any = None,
    salarie: Any = None,
    etablissement: Any = None,
    dossier: Any = None,
    cumuls: Any = None,
    rang: Optional[int] = None,
    total: Optional[int] = None,
) -> bytes:
    """Bulletin de paie au format Sage Saari, sous forme de PDF."""
    html = construire_html_saari(
        bulletin, contrat, salarie, etablissement, dossier, cumuls, rang, total
    )
    return html_vers_pdf(html)


def nom_fichier_bulletin(salarie: Any, bulletin: Any, extension: str = "pdf") -> str:
    """Nom de pièce jointe explicite : bulletin_<matricule>_<MM>-<AAAA>.pdf."""
    matricule = str(getattr(salarie, "matricule", "") or "salarie")
    # On neutralise tout caractère susceptible de perturber un en-tête MIME.
    sur = "".join(c for c in matricule if c.isalnum() or c in "-_") or "salarie"
    mois = int(getattr(bulletin, "mois", 0) or 0)
    annee = getattr(bulletin, "annee", "")
    return f"bulletin_paie_{sur}_{mois:02d}-{annee}.{extension}"
