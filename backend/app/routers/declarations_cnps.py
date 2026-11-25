"""Déclarations CNPS mensuelles d'un établissement (onglet DSN).

Cycle d'une déclaration :
    aperçu (calcul, rien n'est écrit)
    → générée (lignes figées ; regénérable tant qu'elle n'est pas déposée)
    → déposée (sur e-CNPS : date et référence du reçu ; verrouillée)

Le fichier de cotisation nominative se télécharge au format du modèle CNPS,
prêt à être chargé sur e-CNPS.
"""
import json
from datetime import datetime, time, timezone
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    DSN, BulletinPaie, Contrat, LigneDeclarationCnps, PaiementCotisationCnps, Utilisateur,
)
from app.routers.etablissements import check_etablissement_ownership
from app.schemas.declaration_cnps import (
    ApercuDeclarationOut, DeclarationDetailOut, DeclarationOut, DepotDeclarationIn,
    LigneDeclarationOut, MoisDeclarationOut, PaiementCnpsIn, PaiementCnpsOut,
)
from app.services.declarations_cnps import (
    ENTETES_FICHIER, STATUT_DEPOSEE, STATUT_GENEREE, TYPE_CNPS_MENSUELLE,
    calculer_declaration, ligne_vers_dict,
)
from app.services.permissions import require_staff
from app.services.security import get_current_user

router = APIRouter(tags=["Déclarations CNPS"])

Annee = Path(..., ge=2000, le=2100)
Mois = Path(..., ge=1, le=12)


# ─────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────

def _etablissement(etablissement_id: int, user: Utilisateur, db: Session):
    require_staff(user)
    return check_etablissement_ownership(etablissement_id, user.id, db)


def _declaration_ou_404(declaration_id: int, user: Utilisateur, db: Session) -> DSN:
    require_staff(user)
    declaration = (
        db.query(DSN)
        .filter(DSN.id == declaration_id, DSN.type_declaration == TYPE_CNPS_MENSUELLE)
        .first()
    )
    if not declaration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Déclaration introuvable.")
    check_etablissement_ownership(declaration.etablissement_id, user.id, db)
    return declaration


def _masse_actuelle(db: Session, declaration: DSN) -> float:
    total = (
        db.query(func.coalesce(func.sum(BulletinPaie.salaire_brut), 0.0))
        .join(Contrat, Contrat.id == BulletinPaie.contrat_id)
        .filter(
            Contrat.etablissement_id == declaration.etablissement_id,
            BulletinPaie.annee == declaration.annee,
            BulletinPaie.mois == declaration.mois,
        )
        .scalar()
    )
    return round(float(total or 0.0), 2)


#: Écart toléré (arrondis) pour considérer une déclaration comme soldée.
TOLERANCE_PAIEMENT = 0.5


def _etat_paiement(declaration: DSN) -> tuple[float, float, str]:
    du = round(declaration.total_cotisations or 0.0, 2)
    paye = declaration.montant_paye
    reste = round(max(0.0, du - paye), 2)
    if paye <= 0:
        etat = "non_paye"
    elif reste <= TOLERANCE_PAIEMENT:
        etat = "paye"
    else:
        etat = "partiel"
    return paye, reste, etat


def _sortie(db: Session, declaration: DSN, avec_lignes: bool = False):
    paye, reste, etat = _etat_paiement(declaration)
    donnees = dict(
        montant_paye=paye,
        reste_a_payer=reste,
        statut_paiement=etat,
        id=declaration.id,
        etablissement_id=declaration.etablissement_id,
        annee=declaration.annee,
        mois=declaration.mois,
        statut=declaration.statut,
        effectif=declaration.effectif or 0,
        masse_salariale=declaration.masse_salariale or 0.0,
        total_cotisations=declaration.total_cotisations or 0.0,
        totaux=json.loads(declaration.totaux) if declaration.totaux else {},
        date_depot=declaration.date_envoi,
        reference_depot=declaration.reference_envoi,
        ecart_bulletins=abs(_masse_actuelle(db, declaration) - (declaration.masse_salariale or 0.0)) > 0.5,
        created_at=declaration.created_at,
        updated_at=declaration.updated_at,
    )
    if avec_lignes:
        return DeclarationDetailOut(
            **donnees,
            lignes=[LigneDeclarationOut.model_validate(l) for l in declaration.lignes],
            paiements=[PaiementCnpsOut.model_validate(p) for p in declaration.paiements],
        )
    return DeclarationOut(**donnees)


def _apercu(calcul) -> ApercuDeclarationOut:
    return ApercuDeclarationOut(
        annee=calcul.annee,
        mois=calcul.mois,
        effectif=calcul.effectif,
        masse_salariale=calcul.masse_salariale,
        total_cotisations=calcul.total_cotisations,
        totaux=calcul.totaux,
        bloquee=calcul.bloquee,
        anomalies=[a.__dict__ for a in calcul.anomalies],
        lignes=[LigneDeclarationOut(**ligne_vers_dict(l)) for l in calcul.lignes],
    )


# ─────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────

@router.get("/etablissements/{etablissement_id}/declarations-cnps", response_model=List[MoisDeclarationOut])
def lister_declarations(
    etablissement_id: int,
    annee: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Les douze mois de l'année : déclaration éventuelle et état des bulletins."""
    _etablissement(etablissement_id, current_user, db)
    declarations = {
        d.mois: d
        for d in db.query(DSN).filter(
            DSN.etablissement_id == etablissement_id,
            DSN.type_declaration == TYPE_CNPS_MENSUELLE,
            DSN.annee == annee,
        )
    }
    comptes = {
        mois: (total, valides)
        for mois, total, valides in (
            db.query(
                BulletinPaie.mois,
                func.count(BulletinPaie.id),
                func.sum(case((BulletinPaie.statut == "valide", 1), else_=0)),
            )
            .join(Contrat, Contrat.id == BulletinPaie.contrat_id)
            .filter(Contrat.etablissement_id == etablissement_id, BulletinPaie.annee == annee)
            .group_by(BulletinPaie.mois)
        )
    }
    resultat = []
    for mois in range(1, 13):
        total, valides = comptes.get(mois, (0, 0))
        declaration = declarations.get(mois)
        resultat.append(MoisDeclarationOut(
            mois=mois,
            declaration=_sortie(db, declaration) if declaration else None,
            bulletins=int(total or 0),
            bulletins_valides=int(valides or 0),
        ))
    return resultat


@router.get(
    "/etablissements/{etablissement_id}/declarations-cnps/{annee}/{mois}/apercu",
    response_model=ApercuDeclarationOut,
)
def apercu_declaration(
    etablissement_id: int,
    annee: int = Annee,
    mois: int = Mois,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Calcule la déclaration du mois et ses anomalies, sans rien enregistrer."""
    etablissement = _etablissement(etablissement_id, current_user, db)
    return _apercu(calculer_declaration(db, etablissement, annee, mois))


@router.post(
    "/etablissements/{etablissement_id}/declarations-cnps/{annee}/{mois}",
    response_model=DeclarationDetailOut,
)
def generer_declaration(
    etablissement_id: int,
    annee: int = Annee,
    mois: int = Mois,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Génère (ou regénère) la déclaration du mois et fige ses lignes.

    Refusée si une anomalie bloquante subsiste, ou si la déclaration est déjà
    déposée (il faut d'abord annuler le dépôt).
    """
    etablissement = _etablissement(etablissement_id, current_user, db)
    calcul = calculer_declaration(db, etablissement, annee, mois)
    if calcul.bloquee:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Déclaration impossible : corrigez d'abord les anomalies bloquantes.",
                "anomalies": [a.__dict__ for a in calcul.anomalies],
            },
        )

    declaration = db.query(DSN).filter(
        DSN.etablissement_id == etablissement.id,
        DSN.type_declaration == TYPE_CNPS_MENSUELLE,
        DSN.annee == annee,
        DSN.mois == mois,
    ).first()
    if declaration and declaration.statut == STATUT_DEPOSEE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette déclaration est déposée : annulez le dépôt pour la regénérer.",
        )
    if declaration is None:
        declaration = DSN(
            dossier_id=etablissement.dossier_id,
            etablissement_id=etablissement.id,
            type_declaration=TYPE_CNPS_MENSUELLE,
            annee=annee,
            mois=mois,
        )
        db.add(declaration)

    declaration.statut = STATUT_GENEREE
    declaration.effectif = calcul.effectif
    declaration.masse_salariale = calcul.masse_salariale
    declaration.total_cotisations = calcul.total_cotisations
    declaration.totaux = json.dumps(calcul.totaux, ensure_ascii=False)
    declaration.lignes = [LigneDeclarationCnps(**ligne_vers_dict(l)) for l in calcul.lignes]
    db.commit()
    db.refresh(declaration)
    return _sortie(db, declaration, avec_lignes=True)


@router.get("/declarations-cnps/{declaration_id}", response_model=DeclarationDetailOut)
def lire_declaration(
    declaration_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return _sortie(db, _declaration_ou_404(declaration_id, current_user, db), avec_lignes=True)


@router.put("/declarations-cnps/{declaration_id}/depot", response_model=DeclarationOut)
def marquer_deposee(
    declaration_id: int,
    depot: DepotDeclarationIn,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Enregistre le dépôt sur e-CNPS : la déclaration est verrouillée."""
    declaration = _declaration_ou_404(declaration_id, current_user, db)
    declaration.statut = STATUT_DEPOSEE
    declaration.date_envoi = datetime.combine(depot.date_depot, time(12, 0), tzinfo=timezone.utc)
    declaration.reference_envoi = (depot.reference_depot or "").strip() or None
    db.commit()
    db.refresh(declaration)
    return _sortie(db, declaration)


@router.delete("/declarations-cnps/{declaration_id}/depot", response_model=DeclarationOut)
def annuler_depot(
    declaration_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Revient à l'état « générée » (dépôt saisi par erreur, rejet de la CNPS…)."""
    declaration = _declaration_ou_404(declaration_id, current_user, db)
    declaration.statut = STATUT_GENEREE
    declaration.date_envoi = None
    declaration.reference_envoi = None
    db.commit()
    db.refresh(declaration)
    return _sortie(db, declaration)


@router.delete("/declarations-cnps/{declaration_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_declaration(
    declaration_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    declaration = _declaration_ou_404(declaration_id, current_user, db)
    if declaration.statut == STATUT_DEPOSEE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une déclaration déposée ne se supprime pas : annulez d'abord le dépôt.",
        )
    if declaration.paiements:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette déclaration a des paiements enregistrés : supprimez-les d'abord.",
        )
    db.delete(declaration)
    db.commit()
    return None


@router.get("/declarations-cnps/{declaration_id}/paiements", response_model=List[PaiementCnpsOut])
def lister_paiements(
    declaration_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return _declaration_ou_404(declaration_id, current_user, db).paiements


@router.post(
    "/declarations-cnps/{declaration_id}/paiements",
    response_model=DeclarationDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def ajouter_paiement(
    declaration_id: int,
    paiement: PaiementCnpsIn,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Enregistre un paiement à la CNPS ; renvoie la déclaration et son solde."""
    declaration = _declaration_ou_404(declaration_id, current_user, db)
    donnees = paiement.model_dump()
    donnees["reference"] = (donnees.get("reference") or "").strip() or None
    declaration.paiements.append(PaiementCotisationCnps(**donnees))
    db.commit()
    db.refresh(declaration)
    return _sortie(db, declaration, avec_lignes=True)


@router.delete("/paiements-cnps/{paiement_id}", response_model=DeclarationDetailOut)
def supprimer_paiement(
    paiement_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Supprime un paiement saisi par erreur ; renvoie la déclaration à jour."""
    require_staff(current_user)
    paiement = db.query(PaiementCotisationCnps).filter(PaiementCotisationCnps.id == paiement_id).first()
    if not paiement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable.")
    declaration = _declaration_ou_404(paiement.declaration_id, current_user, db)
    db.delete(paiement)
    db.commit()
    db.refresh(declaration)
    return _sortie(db, declaration, avec_lignes=True)


@router.get("/declarations-cnps/{declaration_id}/fichier")
def telecharger_fichier(
    declaration_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Fichier de cotisation nominative au format du modèle e-CNPS (.xlsx)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    declaration = _declaration_ou_404(declaration_id, current_user, db)
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Feuil1"
    feuille.append(list(ENTETES_FICHIER))
    for cellule in feuille[1]:
        cellule.font = Font(bold=True)
        cellule.alignment = Alignment(wrap_text=True, vertical="center")

    def nombre_ou_texte(valeur):
        # Le modèle CNPS porte le numéro en nombre ; un zéro de tête le ferait perdre.
        if valeur and valeur.isdigit() and not valeur.startswith("0"):
            return int(valeur)
        return valeur

    def entier_si_rond(valeur):
        return int(valeur) if float(valeur).is_integer() else valeur

    for ligne in declaration.lignes:
        feuille.append([
            nombre_ou_texte(ligne.numero_cnps),
            ligne.nom,
            ligne.prenoms,
            ligne.date_naissance,
            ligne.date_embauche,
            ligne.date_depart,
            ligne.type_salarie,
            entier_si_rond(ligne.duree_travaillee or 0),
            int(round(ligne.salaire_brut or 0)),
            int(ligne.branches) if (ligne.branches or "").isdigit() else ligne.branches,
        ])
    for ligne in feuille.iter_rows(min_row=2):
        for indice in (3, 4, 5):
            ligne[indice].number_format = "DD/MM/YYYY"
    for colonne, largeur in zip("ABCDEFGHIJ", (16, 18, 24, 14, 14, 14, 14, 12, 14, 16)):
        feuille.column_dimensions[colonne].width = largeur

    tampon = BytesIO()
    classeur.save(tampon)
    nom = f"cotisation_nominative_CNPS_{declaration.mois:02d}-{declaration.annee}.xlsx"
    return Response(
        content=tampon.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
