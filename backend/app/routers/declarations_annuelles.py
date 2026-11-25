"""DISA et DASC d'un exercice, pour un établissement (onglet DSN).

* `GET …/declarations-annuelles/{annee}` : calcul, anomalies et montants à
  reporter sur e-CNPS ;
* `GET …/declarations-annuelles/{annee}/disa` : fichier Excel de la DISA ;
* `GET …/declarations-annuelles/{annee}/dasc` : DASC en PDF, à signer.
"""
from dataclasses import asdict
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Utilisateur
from app.routers.etablissements import check_etablissement_ownership
from app.services.bulletin_saari import _echappe, html_vers_pdf
from app.services.declarations_annuelles import MOIS_LABELS, calculer_declaration_annuelle
from app.services.permissions import require_staff
from app.services.security import get_current_user

router = APIRouter(tags=["Déclarations CNPS annuelles"])

Annee = Path(..., ge=2000, le=2100)


def _calcul(etablissement_id: int, annee: int, user: Utilisateur, db: Session):
    require_staff(user)
    etablissement = check_etablissement_ownership(etablissement_id, user.id, db)
    return etablissement, calculer_declaration_annuelle(db, etablissement, annee)


@router.get("/etablissements/{etablissement_id}/declarations-annuelles/{annee}")
def declaration_annuelle(
    etablissement_id: int,
    annee: int = Annee,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _, calcul = _calcul(etablissement_id, annee, current_user, db)
    return {
        "annee": calcul.annee,
        "lignes": [asdict(l) for l in calcul.lignes],
        "mois": [asdict(m) for m in calcul.mois],
        "regimes": [asdict(r) for r in calcul.regimes],
        "anomalies": [asdict(a) for a in calcul.anomalies],
        "totaux": calcul.totaux,
    }


@router.get("/etablissements/{etablissement_id}/declarations-annuelles/{annee}/disa")
def fichier_disa(
    etablissement_id: int,
    annee: int = Annee,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """DISA au format du fichier déposé sur e-CNPS (feuille « DISA »)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    etablissement, calcul = _calcul(etablissement_id, annee, current_user, db)
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "DISA"
    feuille.append(["EXERCICE", annee])
    numero_employeur = etablissement.cnps_matricule or ""
    feuille.append([
        "CNPS", int(numero_employeur) if numero_employeur.isdigit() else numero_employeur,
        "RAISON \nSOCIALE", etablissement.raison_sociale or "",
    ])
    feuille.append([
        "NUM \nORDRE", "NOM", "PRENOM", "NUM CNPS", "ANNEE \nNAISS.", "DATE \nEMBAUCHE",
        "DATE \nDEPART", "TYPE \nSALARIE", "SALAIRE \nBRUT.", "DUREE \nACTIVITE",
        "MONTANT \nPF/AT.", "MONTANT \nRETRAITE", "REGIME", "OBSERVATION",
    ])
    for cellule in feuille[3]:
        cellule.font = Font(bold=True)
        cellule.alignment = Alignment(wrap_text=True, vertical="center")

    def numero(valeur):
        return int(valeur) if valeur and valeur.isdigit() and not valeur.startswith("0") else valeur

    for ligne in calcul.lignes:
        feuille.append([
            ligne.ordre, ligne.nom, ligne.prenoms, numero(ligne.numero_cnps), ligne.annee_naissance,
            ligne.date_embauche, ligne.date_depart, ligne.type_salarie,
            int(round(ligne.salaire_brut)), ligne.duree_activite,
            int(round(ligne.montant_pf_at)), int(round(ligne.montant_retraite)),
            int(ligne.regime) if ligne.regime.isdigit() else ligne.regime, ligne.observation,
        ])
    for rangee in feuille.iter_rows(min_row=4):
        rangee[5].number_format = "DD/MM/YYYY"
        rangee[6].number_format = "DD/MM/YYYY"
    totaux = calcul.totaux
    feuille.append([
        "TOTAL", None, None, None, None, None, None, None,
        int(round(totaux.get("salaire_brut", 0))), None,
        int(round(totaux.get("montant_pf_at", 0))), int(round(totaux.get("montant_retraite", 0))),
    ])
    for cellule in feuille[feuille.max_row]:
        cellule.font = Font(bold=True)
    for colonne, largeur in zip("ABCDEFGHIJKLMN", (8, 18, 26, 16, 8, 12, 12, 8, 14, 9, 13, 14, 8, 14)):
        feuille.column_dimensions[colonne].width = largeur

    tampon = BytesIO()
    classeur.save(tampon)
    return Response(
        content=tampon.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="DISA_{annee}.xlsx"'},
    )


def _montant(valeur) -> str:
    """Francs CFA arrondis au franc le plus proche (0,5 vers le haut), « 0 » compris."""
    francs = int(Decimal(str(valeur or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{francs:,}".replace(",", " ")


def _taux_fr(taux: float) -> str:
    return f"{taux:g}".replace(".", ",")


_STYLES_DASC = """
@page { size: A4 landscape; margin: 9mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 8pt; color: #000; }
table { width: 100%; }
td, th { border: 0.5pt solid #000; padding: 2pt 3pt; vertical-align: middle; }
th { background-color: #e6e6e6; font-weight: bold; }
.sans-bord td { border: 0; padding: 1pt 2pt; }
.grille td { border: 0.5pt solid #000; padding: 2pt 3pt; }
.num { text-align: right; }
.titre { font-size: 12pt; font-weight: bold; text-align: center; }
.fort { font-weight: bold; }
.petit { font-size: 6.5pt; color: #333; }
"""


@router.get("/etablissements/{etablissement_id}/declarations-annuelles/{annee}/dasc")
def pdf_dasc(
    etablissement_id: int,
    annee: int = Annee,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """DASC de l'exercice, prête à être signée puis déposée sur e-CNPS."""
    etablissement, calcul = _calcul(etablissement_id, annee, current_user, db)
    t = calcul.totaux
    adresse = etablissement.adresse
    adresse_postale = (adresse.adresse_postale if adresse else None) or etablissement.adresse_postale or ""
    geographique = etablissement.adresse_commune or (adresse.ville if adresse else "") or ""

    rappel = "".join(
        f"<tr><td>01/{m.mois:02d}/{annee}</td>"
        f'<td class="num">{_montant(m.cotisations_declarees) if m.declaree else ""}</td>'
        f'<td class="num">{_montant(m.paiements_effectues) if m.paiements_effectues else ""}</td></tr>'
        for m in calcul.mois
    )
    regimes = "".join(
        f"<tr><td class=\"fort\">{_echappe(r.libelle.upper())}</td>"
        f'<td class="num">{_taux_fr(r.taux)} %</td>'
        f'<td class="num">{_montant(r.base_annuelle)}</td>'
        f'<td class="num">{_montant(r.cotisation)}</td></tr>'
        for r in calcul.regimes
    )
    html = f"""<html><head><meta charset="utf-8"/><style>{_STYLES_DASC}</style></head><body>
    <div class="titre">DÉCLARATION ANNUELLE DES SALAIRES ET DES COTISATIONS</div>
    <table class="sans-bord" style="margin-top:6pt">
      <tr>
        <td style="width:50%">Code établissement : <b>{_echappe(etablissement.cnps_code_etablissement or '')}</b>
          &nbsp;&nbsp; Code activité : <b>{_echappe(etablissement.cnps_code_activite or '')}</b></td>
        <td>Employeur, raison sociale : <b>{_echappe(etablissement.raison_sociale or '')}</b></td>
      </tr>
      <tr>
        <td>Exercice : <b>{annee}</b></td>
        <td>Adresse postale : <b>{_echappe(adresse_postale)}</b> &nbsp;&nbsp; Tél. : <b>{_echappe(etablissement.telephone or '')}</b></td>
      </tr>
      <tr>
        <td></td>
        <td>Adresse géographique : <b>{_echappe(geographique)}</b> &nbsp;&nbsp;
          Matricule CNPS : <b>{_echappe(etablissement.cnps_matricule or '')}</b></td>
      </tr>
    </table>
    <table class="sans-bord" style="margin-top:8pt"><tr>
      <td style="width:42%; vertical-align:top">
        <table class="grille">
          <tr><th colspan="3">Rappel des cotisations déclarées et des paiements effectués à la CNPS depuis le début de l'exercice</th></tr>
          <tr><th>Mois</th><th>Cotisations déclarées</th><th>Paiements effectués</th></tr>
          {rappel}
          <tr><td class="fort">TOTAUX</td><td class="num fort">{_montant(t['total_i'])}</td><td class="num fort">{_montant(t['total_ii'])}</td></tr>
          <tr><td></td><td class="num">TOTAL I</td><td class="num">TOTAL II</td></tr>
          <tr><td colspan="2" class="fort">Solde de l'exercice : TOTAL V = TOTAL I - TOTAL II</td><td class="num fort">{_montant(t['total_v'])}</td></tr>
        </table>
      </td>
      <td style="width:58%; vertical-align:top">
        <p class="petit">Complément indispensable à la DISA : document récapitulatif de la régularisation annuelle des
        cotisations, à retourner à la CNPS avec la Déclaration Individuelle des Salaires Annuels.</p>
        <table class="grille">
          <tr><th>Régimes</th><th>Taux</th><th>Total salaires annuels soumis à cotisations</th><th>Cotisations annuelles</th></tr>
          {regimes}
          <tr><td colspan="3" class="fort">TOTAL III — Cotisations annuelles à déclarer</td><td class="num fort">{_montant(t['total_iii'])}</td></tr>
          <tr><td colspan="3" class="fort">TOTAL IV = TOTAL III - TOTAL I — Régularisation annuelle</td><td class="num fort">{_montant(t['total_iv'])}</td></tr>
          <tr><td colspan="3" class="fort">SOLDE = TOTAL IV + TOTAL V</td><td class="num fort">{_montant(t['solde'])}</td></tr>
        </table>
        <table class="sans-bord" style="margin-top:14pt">
          <tr><td>À ........................................, le ..............................</td></tr>
          <tr><td style="padding-top:30pt">Signature et cachet</td></tr>
        </table>
      </td>
    </tr></table>
    </body></html>"""
    return Response(
        content=html_vers_pdf(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="DASC_{annee}.pdf"'},
    )
