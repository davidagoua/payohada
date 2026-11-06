from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.database import get_db
from app.models.models import BulletinPaie, Contrat, Dossier, Utilisateur, Salarie, PretSalarie, Etablissement, PeriodePaie
from app.schemas.bulletin import (
    LotPdfRequest,
    BulletinPaieOut, BulletinPaieCreate, SimulationInput, SimulationOut,
    LotCalculOut, ErreurCalculLot
)
from app.services.security import get_current_user
from app.services.permissions import (
    ROLE_CABINET, get_dossier_or_403, peut_gerer_dossier, require_staff,
)
from app.routers.contrats import check_contrat_ownership
from app.services.bulletin_cumuls import compute_bulletin_cumuls
from app.services.bulletin_saari import (
    generer_pdf_lot_saari, generer_pdf_saari, nom_fichier_bulletin,
)
from app.services.payroll import calculate_payslip
from app.services.simulation_paie import simuler_bulletin
from app.services.email import send_email
from app.services.email_templates import email_bulletin_employe, email_bulletin_gestionnaire

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bulletins de Paie"])


def check_bulletin_ownership(bulletin_id: int, user_id: int, db: Session) -> BulletinPaie:
    user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable."
        )

    bulletin = db.query(BulletinPaie).filter(BulletinPaie.id == bulletin_id).first()
    if not bulletin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulletin de paie introuvable."
        )

    if user.salarie_id or user.role == "salarie":
        if bulletin.contrat.salarie_id == user.salarie_id:
            return bulletin
    elif peut_gerer_dossier(db, user, bulletin.dossier):
        return bulletin

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès non autorisé à ce bulletin de paie."
    )


@router.get("/dossiers/{dossier_id}/bulletins", response_model=List[BulletinPaieOut])
def get_dossier_bulletins(
    dossier_id: int,
    mois: Optional[int] = None,
    annee: Optional[int] = None,
    contrat_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les bulletins de paie d'un dossier avec filtre de période ou de contrat."""
    if current_user.salarie_id:
        query = db.query(BulletinPaie).join(Contrat).filter(
            BulletinPaie.dossier_id == dossier_id,
            Contrat.salarie_id == current_user.salarie_id
        )
    elif current_user.role == "client":
        if current_user.dossier_id != dossier_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé à ce dossier."
            )
        query = db.query(BulletinPaie).filter(BulletinPaie.dossier_id == dossier_id)
    else:
        dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
        if not dossier or not peut_gerer_dossier(db, current_user, dossier):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable ou accès refusé."
            )
        query = db.query(BulletinPaie).filter(BulletinPaie.dossier_id == dossier_id)
        
    if mois:
        query = query.filter(BulletinPaie.mois == mois)
    if annee:
        query = query.filter(BulletinPaie.annee == annee)
    if contrat_id:
        if current_user.salarie_id:
            contract = db.query(Contrat).filter(Contrat.id == contrat_id, Contrat.salarie_id == current_user.salarie_id).first()
            if not contract:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
        query = query.filter(BulletinPaie.contrat_id == contrat_id)
        
    bulletins = query.all()
    
    # Injecter les cumuls dynamiquement pour chaque bulletin
    result = []
    for b in bulletins:
        bout = BulletinPaieOut.model_validate(b)
        bout.cumuls = compute_bulletin_cumuls(db, b)
        result.append(bout)
        
    return result


@router.post("/dossiers/{dossier_id}/bulletins/calculer-lot", response_model=LotCalculOut)
def calculate_dossier_bulletins_lot(
    dossier_id: int,
    mois: int = Query(..., ge=1, le=12),
    annee: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Calcule ou recalcule en masse tous les bulletins de paie d'un dossier pour
    la période indiquée, et met à jour le statut de la période.

    Réservé au cabinet propriétaire du dossier (ou à un administrateur) : le
    calcul de la paie n'est pas une opération client. Les échecs par salarié
    sont renvoyés dans `erreurs` au lieu d'être avalés.
    """
    dossier = get_dossier_or_403(dossier_id, current_user, db)
    require_staff(current_user)
    # Co-administrateur du cabinet : même droit que le propriétaire.
    co_admin = (
        current_user.role == ROLE_CABINET
        and current_user.cabinet_owner_id is not None
        and dossier.utilisateur_id == current_user.cabinet_owner_id
    )
    if not current_user.is_admin and dossier.utilisateur_id != current_user.id and not co_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le cabinet propriétaire peut calculer la paie de ce dossier.",
        )

    # Récupérer tous les contrats du dossier
    contrats = (
        db.query(Contrat)
        .join(Etablissement, Contrat.etablissement_id == Etablissement.id)
        .filter(Etablissement.dossier_id == dossier_id)
        .all()
    )

    result_bulletins: List[BulletinPaieOut] = []
    erreurs: List[ErreurCalculLot] = []

    for c in contrats:
        try:
            bulletin = calculate_payslip(
                db=db,
                contrat_id=c.id,
                mois=mois,
                annee=annee,
                acompte=0.0
            )
            bout = BulletinPaieOut.model_validate(bulletin)
            bout.cumuls = compute_bulletin_cumuls(db, bulletin)
            result_bulletins.append(bout)
        except Exception as e:
            db.rollback()
            salarie = db.query(Salarie).filter(Salarie.id == c.salarie_id).first()
            logger.exception(
                "Échec du calcul de paie pour le contrat %s (dossier %s, %s/%s)",
                c.id, dossier_id, mois, annee,
            )
            erreurs.append(
                ErreurCalculLot(
                    contrat_id=c.id,
                    salarie_id=c.salarie_id,
                    matricule=c.matricule_salarie,
                    nom_complet=(
                        f"{salarie.prenom} {salarie.nom}" if salarie else None
                    ),
                    message=str(e) or e.__class__.__name__,
                )
            )

    # Mettre à jour la période à "calcule" uniquement si au moins un bulletin
    # a été produit et qu'aucune erreur n'est survenue.
    if result_bulletins and not erreurs:
        periode = db.query(PeriodePaie).filter(
            PeriodePaie.dossier_id == dossier_id,
            PeriodePaie.annee == str(annee),
            PeriodePaie.mois == mois
        ).first()
        if periode:
            periode.statut = "calcule"
            db.commit()

    return LotCalculOut(
        periode=f"{mois:02d}/{annee}",
        bulletins=result_bulletins,
        erreurs=erreurs,
        total_contrats=len(contrats),
        total_calcules=len(result_bulletins),
        total_erreurs=len(erreurs),
    )


@router.get("/salaries/me/bulletins", response_model=List[BulletinPaieOut])
def get_my_bulletins(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Liste les bulletins de paie du salarié actuellement connecté."""
    if not current_user.salarie_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'utilisateur connecté n'est pas un salarié."
        )
        
    bulletins = db.query(BulletinPaie).join(Contrat).filter(
        Contrat.salarie_id == current_user.salarie_id
    ).all()
    
    result = []
    for b in bulletins:
        bout = BulletinPaieOut.model_validate(b)
        bout.cumuls = compute_bulletin_cumuls(db, b)
        result.append(bout)
        
    return result


@router.post("/bulletins/calculer", response_model=BulletinPaieOut)
def calculate_bulletin_paie(
    bulletin_in: BulletinPaieCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Calcule ou recalcul le bulletin de paie pour un contrat et une période donnée."""
    require_staff(current_user)
    check_contrat_ownership(bulletin_in.contrat_id, current_user.id, db)

    try:
        bulletin = calculate_payslip(
            db=db,
            contrat_id=bulletin_in.contrat_id,
            mois=bulletin_in.mois,
            annee=bulletin_in.annee,
            acompte=bulletin_in.acompte or 0.0
        )
        if bulletin_in.commentaire:
            bulletin.commentaire = bulletin_in.commentaire
            db.commit()
            db.refresh(bulletin)
            
        bout = BulletinPaieOut.model_validate(bulletin)
        bout.cumuls = compute_bulletin_cumuls(db, bulletin)
        return bout
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de calcul de paie: {str(e)}"
        )


@router.get("/bulletins/{bulletin_id}", response_model=BulletinPaieOut)
def get_bulletin(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère les détails d'un bulletin de paie (avec ses lignes de calcul)."""
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    bout = BulletinPaieOut.model_validate(bulletin)
    bout.cumuls = compute_bulletin_cumuls(db, bulletin)
    return bout


@router.put("/bulletins/{bulletin_id}/valider", response_model=BulletinPaieOut)
def validate_bulletin(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Valide définitivement un bulletin de paie (cabinet / administrateur)."""
    require_staff(current_user)
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    if bulletin.statut != "valide":
        for line in bulletin.lignes:
            if line.pret_id:
                loan = db.query(PretSalarie).filter(PretSalarie.id == line.pret_id).first()
                if loan:
                    loan.reste_a_rembourser = round(max(0.0, loan.reste_a_rembourser - line.montant_cs), 2)
        bulletin.statut = "valide"
        db.commit()
        db.refresh(bulletin)
    
    bout = BulletinPaieOut.model_validate(bulletin)
    bout.cumuls = compute_bulletin_cumuls(db, bulletin)
    return bout


@router.put("/bulletins/{bulletin_id}/invalider", response_model=BulletinPaieOut)
def invalidate_bulletin(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Invalide (dé-valide) un bulletin de paie s'il s'agit du plus récent validé.

    Opération réservée au cabinet : elle rouvre la période et restaure les
    remboursements de prêts appliqués lors de la validation.
    """
    require_staff(current_user)
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    if bulletin.statut != "valide":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le bulletin n'est pas validé."
        )

    # Vérifier s'il y a un bulletin validé plus récent pour le même contrat
    later_validated = db.query(BulletinPaie).filter(
        BulletinPaie.contrat_id == bulletin.contrat_id,
        BulletinPaie.statut == "valide",
        (
            (BulletinPaie.annee > bulletin.annee) |
            ((BulletinPaie.annee == bulletin.annee) & (BulletinPaie.mois > bulletin.mois))
        )
    ).first()

    if later_validated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'invalider ce bulletin : un bulletin plus récent a déjà été validé pour ce salarié."
        )

    for line in bulletin.lignes:
        if line.pret_id:
            loan = db.query(PretSalarie).filter(PretSalarie.id == line.pret_id).first()
            if loan:
                loan.reste_a_rembourser = round(loan.reste_a_rembourser + line.montant_cs, 2)

    bulletin.statut = "brouillon"
    db.commit()
    db.refresh(bulletin)

    bout = BulletinPaieOut.model_validate(bulletin)
    bout.cumuls = compute_bulletin_cumuls(db, bulletin)
    return bout


@router.delete("/bulletins/{bulletin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bulletin(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprime un bulletin de paie (si encore à l'état brouillon ou calculé)."""
    require_staff(current_user)
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    if bulletin.statut == "valide":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer un bulletin de paie validé."
        )

    db.delete(bulletin)
    db.commit()
    return None


def _piece_jointe_bulletin(
    db: Session,
    bulletin: BulletinPaie,
    contrat: Contrat,
    salarie: Salarie,
) -> list:
    """Bulletin au format Sage Saari, prêt à être joint à un email.

    Retourne une liste vide si la génération échoue : l'email part alors sans
    pièce jointe plutôt que d'échouer entièrement. L'incident est journalisé.
    """
    try:
        cumuls = compute_bulletin_cumuls(db, bulletin)
        pdf = generer_pdf_saari(
            bulletin,
            contrat=contrat,
            salarie=salarie,
            etablissement=getattr(contrat, "etablissement", None),
            dossier=getattr(bulletin, "dossier", None),
            cumuls=cumuls,
        )
        nom = nom_fichier_bulletin(salarie, bulletin)
        logger.info("Bulletin PDF généré pour l'envoi : %s (%d octets)", nom, len(pdf))
        return [(nom, pdf, "application/pdf")]
    except Exception:
        logger.exception(
            "Génération du bulletin PDF impossible pour le bulletin %s : "
            "l'email sera envoyé sans pièce jointe.",
            getattr(bulletin, "id", "?"),
        )
        return []


@router.get("/bulletins/{bulletin_id}/pdf")
def telecharger_bulletin_pdf(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Télécharge le bulletin de paie au format Sage Saari (PDF)."""
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    contrat = bulletin.contrat
    if not contrat:
        raise HTTPException(status_code=404, detail="Contrat associé introuvable.")
    salarie = contrat.salarie
    if not salarie:
        raise HTTPException(status_code=404, detail="Salarié associé introuvable.")

    cumuls = compute_bulletin_cumuls(db, bulletin)
    try:
        pdf = generer_pdf_saari(
            bulletin,
            contrat=contrat,
            salarie=salarie,
            etablissement=getattr(contrat, "etablissement", None),
            dossier=getattr(bulletin, "dossier", None),
            cumuls=cumuls,
        )
    except Exception:
        logger.exception("Génération du PDF impossible pour le bulletin %s", bulletin_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La génération du bulletin au format PDF a échoué.",
        )

    nom = nom_fichier_bulletin(salarie, bulletin)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nom}"'},
    )


@router.post("/bulletins/pdf-lot")
def telecharger_bulletins_pdf_lot(
    demande: LotPdfRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Réunit plusieurs bulletins dans un seul PDF, au format Sage Saari.

    Un bulletin par page. Chaque bulletin est vérifié individuellement : la
    demande est rejetée si l'un d'eux appartient à un autre cabinet.
    """
    elements = []
    for index, bulletin_id in enumerate(demande.bulletin_ids):
        # check_bulletin_ownership lève 403/404 : le lot entier est refusé
        # plutôt que de produire un document partiel.
        bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
        contrat = bulletin.contrat
        if not contrat or not contrat.salarie:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le bulletin {bulletin_id} n'a pas de contrat ou de salarié associé.",
            )
        elements.append({
            "bulletin": bulletin,
            "contrat": contrat,
            "salarie": contrat.salarie,
            "etablissement": getattr(contrat, "etablissement", None),
            "dossier": getattr(bulletin, "dossier", None),
            "cumuls": compute_bulletin_cumuls(db, bulletin),
            "rang": index + 1,
            "total": len(demande.bulletin_ids),
        })

    try:
        pdf = generer_pdf_lot_saari(elements)
    except Exception:
        logger.exception("Génération du PDF groupé impossible (%d bulletins)", len(elements))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La génération du PDF groupé a échoué.",
        )

    logger.info("PDF groupé généré : %d bulletins, %d octets", len(elements), len(pdf))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="bulletins_paie.pdf"',
            "X-Nombre-Bulletins": str(len(elements)),
        },
    )


@router.post("/bulletins/simuler", response_model=SimulationOut)
def simulate_bulletin_paie(
    sim_in: SimulationInput,
    db: Session = Depends(get_db)
):
    """Simule en mémoire un bulletin de paie pour la zone UEMOA sans persister de données."""
    try:
        return simuler_bulletin(sim_in, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de simulation de paie: {str(e)}"
        )


@router.post("/bulletins/{bulletin_id}/envoyer-employe")
def send_bulletin_to_employee(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Envoie le bulletin de paie par email à l'employé (cabinet uniquement)."""
    require_staff(current_user)
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    contrat = bulletin.contrat
    if not contrat:
        raise HTTPException(status_code=404, detail="Contrat associé introuvable.")
    salarie = contrat.salarie
    if not salarie:
        raise HTTPException(status_code=404, detail="Salarié associé introuvable.")
    
    email_dest = salarie.email
    if not email_dest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le salarié {salarie.prenom} {salarie.nom} n'a pas d'adresse email configurée dans sa fiche."
        )
    
    # Le PDF est préparé avant le corps du message afin que celui-ci puisse
    # annoncer exactement ce qui est joint.
    pieces_jointes = _piece_jointe_bulletin(db, bulletin, contrat, salarie)
    subject, html_content = email_bulletin_employe(
        bulletin, salarie, avec_piece_jointe=bool(pieces_jointes)
    )

    success, message = send_email(
        email_dest, subject, html_content, pieces_jointes=pieces_jointes
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )

    precision = (
        f" avec le bulletin au format PDF ({pieces_jointes[0][0]})"
        if pieces_jointes else " (sans pièce jointe : génération du PDF impossible)"
    )
    return {
        "status": "success",
        "message": f"Bulletin envoyé à l'employé {salarie.prenom} {salarie.nom} ({email_dest}){precision}",
        "piece_jointe": pieces_jointes[0][0] if pieces_jointes else None,
    }


@router.post("/bulletins/{bulletin_id}/envoyer-gestionnaire")
def send_bulletin_to_manager(
    bulletin_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user)
):
    """Envoie le bulletin de paie par email au gestionnaire du dossier (cabinet uniquement)."""
    require_staff(current_user)
    bulletin = check_bulletin_ownership(bulletin_id, current_user.id, db)
    dossier = bulletin.dossier
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier associé introuvable.")
    contrat = bulletin.contrat
    if not contrat:
        raise HTTPException(status_code=404, detail="Contrat associé introuvable.")
    salarie = contrat.salarie
    if not salarie:
        raise HTTPException(status_code=404, detail="Salarié associé introuvable.")
        
    email_dest = dossier.adresse_email or current_user.email
    if not email_dest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune adresse e-mail n'est configurée pour le dossier ou l'utilisateur connecté."
        )
        
    pieces_jointes = _piece_jointe_bulletin(db, bulletin, contrat, salarie)
    subject, html_content = email_bulletin_gestionnaire(
        bulletin, salarie, avec_piece_jointe=bool(pieces_jointes)
    )

    success, message = send_email(
        email_dest, subject, html_content, pieces_jointes=pieces_jointes
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )

    precision = (
        f" avec le bulletin au format PDF ({pieces_jointes[0][0]})"
        if pieces_jointes else " (sans pièce jointe : génération du PDF impossible)"
    )
    return {
        "status": "success",
        "message": f"Bulletin envoyé au gestionnaire du dossier {dossier.nom_dossier} ({email_dest}){precision}",
        "piece_jointe": pieces_jointes[0][0] if pieces_jointes else None,
    }

