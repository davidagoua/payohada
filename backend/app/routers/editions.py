"""Module « Éditions » : catalogue, génération, export et envoi des états.

Reprend le principe du menu Éditions des logiciels de paie : on choisit un état
dans un catalogue, on précise une période, on visualise le résultat dans
l'application, puis on l'exporte (PDF, Excel, CSV) ou on l'envoie par email.

Un seul pipeline alimente toutes les sorties, à partir du **même modèle
tabulaire** : ce que l'aperçu affiche est exactement ce que le fichier contient.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Utilisateur
from app.schemas.editions import (
    ColonneEditionOut, EditionOut, EnvoiEditionIn, FamilleEditionsOut,
    PeriodeEdition, ResultatEditionOut,
)
from app.services import editions as service

# L'import enregistre les états du catalogue : sans lui, le module serait vide.
import app.services.editions_paie  # noqa: F401  (effet de bord : enregistrement)
from app.services.email import send_email
from app.services.permissions import get_dossier_or_403, require_staff
from app.services.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Éditions"])

def _contexte(demande: PeriodeEdition) -> service.ContexteEdition:
    try:
        return service.ContexteEdition(
            dossier_id=demande.dossier_id,
            mois_debut=demande.mois_debut,
            annee_debut=demande.annee_debut,
            mois_fin=demande.mois_fin,
            annee_fin=demande.annee_fin,
            etablissement_id=demande.etablissement_id,
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erreur)
        )


#: Les états collectifs exposent l'ensemble des rémunérations d'un dossier :
#: ils sont réservés au cabinet, comme les autres traitements de paie.
def _verifier_acces(demande: PeriodeEdition, utilisateur: Utilisateur, db: Session) -> None:
    require_staff(utilisateur)
    get_dossier_or_403(demande.dossier_id, utilisateur, db)


def _definition_ou_404(code: str) -> service.DefinitionEdition:
    try:
        return service.edition(code)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Édition inconnue : {code}.",
        )


# ─────────────────────────────────────────────
#  CATALOGUE
# ─────────────────────────────────────────────

@router.get("/editions", response_model=List[FamilleEditionsOut])
def lister_editions(
    current_user: Utilisateur = Depends(get_current_user),
):
    """Catalogue des éditions disponibles, groupées par famille."""
    return [
        FamilleEditionsOut(
            famille=famille,
            editions=[
                EditionOut(
                    code=d.code, libelle=d.libelle, famille=d.famille,
                    description=d.description, formats=list(d.formats),
                )
                for d in definitions
            ],
        )
        for famille, definitions in service.catalogue_par_famille().items()
    ]


# ─────────────────────────────────────────────
#  APERÇU
# ─────────────────────────────────────────────

@router.post("/editions/{code}/generer", response_model=ResultatEditionOut)
def generer_edition(
    code: str,
    demande: PeriodeEdition,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Génère un état et le retourne sous forme tabulaire, pour l'aperçu."""
    return _generer(code, demande, db, current_user)


# ─────────────────────────────────────────────
#  EXPORT
# ─────────────────────────────────────────────

@router.post("/editions/{code}/export")
def exporter_edition(
    code: str,
    demande: PeriodeEdition,
    format: str = Query("pdf", pattern="^(pdf|excel|csv)$"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Exporte un état au format demandé (PDF, Excel ou CSV)."""
    definition, resultat = _generer_complet(code, demande, db, current_user)

    if format not in definition.formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"L'édition « {definition.libelle} » n'est pas disponible en {format}.",
        )

    try:
        contenu = service.rendre(resultat, format, paysage=definition.paysage)
    except Exception:
        logger.exception("Rendu %s impossible pour l'édition %s", format, code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La génération du fichier a échoué.",
        )

    nom = service.nom_fichier(resultat, format)
    logger.info(
        "Édition %s exportée en %s (%d lignes, %d octets) par %s",
        code, format, resultat.nombre_lignes, len(contenu), current_user.email,
    )
    return Response(
        content=contenu,
        media_type=service.TYPES_MIME[format],
        headers={
            "Content-Disposition": f'attachment; filename="{nom}"',
            "X-Nombre-Lignes": str(resultat.nombre_lignes),
        },
    )


# ─────────────────────────────────────────────
#  ENVOI PAR EMAIL
# ─────────────────────────────────────────────

@router.post("/editions/{code}/envoyer")
def envoyer_edition(
    code: str,
    demande: EnvoiEditionIn,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Envoie un état en pièce jointe PDF à un ou plusieurs destinataires."""
    definition, resultat = _generer_complet(code, demande, db, current_user)

    try:
        pdf = service.rendre(resultat, "pdf", paysage=definition.paysage)
    except Exception:
        logger.exception("Rendu PDF impossible pour l'envoi de l'édition %s", code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La génération du PDF a échoué.",
        )

    nom = service.nom_fichier(resultat, "pdf")
    objet = demande.objet or f"{definition.libelle} — {resultat.contexte.get('periode', '')}"

    # Le corps du message reprend le bandeau de l'état : le destinataire
    # identifie la société et la période sans ouvrir la pièce jointe.
    lignes_contexte = "".join(
        f"<li><strong>{cle} :</strong> {valeur}</li>"
        for cle, valeur in resultat.contexte.items() if valeur
    )
    corps_utilisateur = (
        f"<p>{demande.message}</p>" if demande.message else ""
    )
    contenu_html = f"""<html><body style="font-family: Arial, sans-serif;
        font-size: 14px; color: #161616;">
      <p>Bonjour,</p>
      {corps_utilisateur}
      <p>Veuillez trouver ci-joint l'état suivant :</p>
      <p><strong>{definition.libelle}</strong></p>
      <ul>{lignes_contexte}</ul>
      <p>{resultat.nombre_lignes} ligne(s).</p>
      <p style="font-size: 12px; color: #6f6f6f;">
        Ce message a été généré automatiquement par payohada.
      </p>
    </body></html>"""

    destinataires = [demande.destinataire]
    if demande.copie:
        destinataires.append(demande.copie)

    resultats = []
    for destinataire in destinataires:
        succes, message = send_email(
            destinataire, objet, contenu_html,
            pieces_jointes=[(nom, pdf, "application/pdf")],
        )
        resultats.append((destinataire, succes, message))
        if not succes:
            logger.error("Envoi de l'édition %s à %s refusé : %s", code, destinataire, message)

    echecs = [r for r in resultats if not r[1]]
    if echecs:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "L'envoi a échoué pour : "
                + ", ".join(f"{dest} ({msg})" for dest, _, msg in echecs)
            ),
        )

    return {
        "status": "success",
        "message": (
            f"État « {definition.libelle} » envoyé à "
            + ", ".join(dest for dest, _, _ in resultats)
        ),
        "piece_jointe": nom,
        "lignes": resultat.nombre_lignes,
    }


# ─────────────────────────────────────────────
#  OUTILS INTERNES
# ─────────────────────────────────────────────

def _generer_complet(code: str, demande: PeriodeEdition, db: Session, utilisateur: Utilisateur):
    definition = _definition_ou_404(code)
    _verifier_acces(demande, utilisateur, db)
    contexte = _contexte(demande)
    try:
        resultat = service.generer_edition(db, definition.code, contexte)
    except Exception:
        logger.exception("Génération de l'édition %s impossible", code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"La génération de l'état « {definition.libelle} » a échoué.",
        )
    return definition, resultat


def _generer(code: str, demande: PeriodeEdition, db: Session, utilisateur: Utilisateur):
    _, resultat = _generer_complet(code, demande, db, utilisateur)
    return ResultatEditionOut(
        code=resultat.code,
        titre=resultat.titre,
        colonnes=[
            ColonneEditionOut(
                cle=c.cle, libelle=c.libelle, type=c.type, total=c.total
            )
            for c in resultat.colonnes
        ],
        lignes=resultat.lignes,
        totaux=resultat.totaux,
        contexte=resultat.contexte,
        notes=resultat.notes,
        nombre_lignes=resultat.nombre_lignes,
    )
