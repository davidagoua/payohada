"""Demandes du salarié : congés et acomptes.

Le salarié dépose, l'entreprise décide, la paie applique :

* un congé validé crée une **absence « Congés payés »** : c'est elle, et non la
  demande, que consomme le moteur de paie (salaire neutralisé, jours comptés) ;
* un acompte validé est **retenu sur le bulletin de sa période** par le moteur,
  sans ressaisie.

La décision appartient au **gestionnaire de l'entreprise** (`client`). Le
cabinet, lui, ne décide pas : il voit les demandes de ses dossiers et les
retrouve déjà appliquées dans les bulletins.
"""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.models import (
    BulletinPaie, Contrat, DemandeAcompte, DemandeConge, Dossier, Etablissement,
    Salarie, SalarieAbsence, Utilisateur,
)
from app.schemas.demande import (
    DecisionDemande, DemandeAcompteCreate, DemandeAcompteOut, DemandeCongeCreate,
    DemandeCongeOut, SoldeCongesOut,
)
from app.services.conges import solde_conges
from app.services.security import get_current_user

router = APIRouter(prefix="/demandes", tags=["Demandes"])

EN_ATTENTE = "en_attente"
VALIDEE = "validee"
REFUSEE = "refusee"
DECIDABLES = (EN_ATTENTE,)

#: Un bulletin validé est figé : plus aucune demande ne peut y entrer.
STATUT_BULLETIN_VERROUILLE = "valide"

#: Type d'absence créé par une demande de congés validée. Le moteur reconnaît
#: les codes contenant « CONGE » et neutralise le salaire correspondant.
TYPE_ABSENCE_CONGES = "Congés payés"


# ─────────────────────────────────────────────
#  PORTÉE ET CONTRÔLES
# ─────────────────────────────────────────────

def _salarie_du_compte(user: Utilisateur) -> int:
    if not user.salarie_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un salarié peut déposer une demande.",
        )
    return user.salarie_id


def _dossier_du_gestionnaire(user: Utilisateur) -> int:
    """Dossier de l'entreprise dont l'utilisateur est le gestionnaire."""
    if user.role != "client" or not user.dossier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le gestionnaire de l'entreprise peut décider d'une demande.",
        )
    return user.dossier_id


def _salarie_de_l_entreprise(db: Session, salarie_id: int, dossier_id: int) -> Salarie:
    salarie = (
        db.query(Salarie)
        .join(Etablissement, Salarie.etablissement_id == Etablissement.id)
        .filter(Salarie.id == salarie_id, Etablissement.dossier_id == dossier_id)
        .first()
    )
    if not salarie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salarié introuvable dans votre entreprise.",
        )
    return salarie


def _filtrer_portee(db: Session, requete, modele, user: Utilisateur):
    """Restreint une requête aux demandes que l'utilisateur peut voir."""
    if user.salarie_id:
        return requete.filter(modele.salarie_id == user.salarie_id)
    if user.role == "client":
        return (
            requete.join(Salarie, modele.salarie_id == Salarie.id)
            .join(Etablissement, Salarie.etablissement_id == Etablissement.id)
            .filter(Etablissement.dossier_id == user.dossier_id)
        )
    # Cabinet : les demandes de ses dossiers ; l'administrateur voit tout.
    requete = (
        requete.join(Salarie, modele.salarie_id == Salarie.id)
        .join(Etablissement, Salarie.etablissement_id == Etablissement.id)
        .join(Dossier, Etablissement.dossier_id == Dossier.id)
    )
    if not user.is_admin:
        requete = requete.filter(Dossier.utilisateur_id == user.id)
    return requete


def _mois_couverts(debut: date, fin: date) -> list[tuple[int, int]]:
    mois: list[tuple[int, int]] = []
    annee, numero = debut.year, debut.month
    while (annee, numero) <= (fin.year, fin.month):
        mois.append((annee, numero))
        numero += 1
        if numero > 12:
            numero, annee = 1, annee + 1
    return mois


def _bulletins_verrouilles(
    db: Session, salarie_id: int, mois: list[tuple[int, int]]
) -> BulletinPaie | None:
    """Bulletin déjà validé couvrant l'un des mois demandés, s'il existe."""
    conditions = [
        and_(BulletinPaie.annee == annee, BulletinPaie.mois == numero)
        for annee, numero in mois
    ]
    if not conditions:
        return None
    return (
        db.query(BulletinPaie)
        .join(Contrat, BulletinPaie.contrat_id == Contrat.id)
        .filter(
            Contrat.salarie_id == salarie_id,
            BulletinPaie.statut == STATUT_BULLETIN_VERROUILLE,
            or_(*conditions),
        )
        .first()
    )


def _exiger_en_attente(demande) -> None:
    if demande.statut != EN_ATTENTE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cette demande a déjà été traitée (statut : {demande.statut}).",
        )


def _conge_out(demande: DemandeConge) -> DemandeCongeOut:
    out = DemandeCongeOut.model_validate(demande)
    _identite(demande, out)
    return out


def _acompte_out(demande: DemandeAcompte) -> DemandeAcompteOut:
    out = DemandeAcompteOut.model_validate(demande)
    _identite(demande, out)
    return out


def _identite(demande, out) -> None:
    salarie = demande.salarie
    if salarie:
        out.salarie_nom = salarie.nom
        out.salarie_prenom = salarie.prenom
        out.matricule = salarie.matricule


def _decider(demande, user: Utilisateur, commentaire: str | None, statut: str) -> None:
    demande.statut = statut
    demande.commentaire_gestionnaire = commentaire
    demande.decide_par_id = user.id
    demande.date_decision = datetime.now(timezone.utc)


# ─────────────────────────────────────────────
#  CONGÉS
# ─────────────────────────────────────────────

@router.post("/conges", response_model=DemandeCongeOut, status_code=status.HTTP_201_CREATED)
def creer_demande_conge(
    payload: DemandeCongeCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Dépose une demande de congés pour le salarié connecté."""
    salarie_id = _salarie_du_compte(current_user)

    chevauchement = (
        db.query(DemandeConge)
        .filter(
            DemandeConge.salarie_id == salarie_id,
            DemandeConge.statut.in_((EN_ATTENTE, VALIDEE)),
            DemandeConge.date_debut <= payload.date_fin,
            DemandeConge.date_fin >= payload.date_debut,
        )
        .first()
    )
    if chevauchement:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une demande en attente ou validée couvre déjà ces dates.",
        )

    demande = DemandeConge(
        salarie_id=salarie_id,
        date_debut=payload.date_debut,
        date_fin=payload.date_fin,
        nombre_jours=float((payload.date_fin - payload.date_debut).days + 1),
        motif=payload.motif,
        statut=EN_ATTENTE,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return _conge_out(demande)


@router.get("/conges/solde", response_model=SoldeCongesOut)
def solde_conges_salarie(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Solde de congés payés du salarié connecté, au mois en cours.

    Même calcul que le bulletin : ce que le salarié voit ici est ce que la paie
    appliquera. Le contrat retenu est le plus récent.
    """
    salarie_id = _salarie_du_compte(current_user)
    contrat = (
        db.query(Contrat)
        .filter(Contrat.salarie_id == salarie_id)
        .order_by(Contrat.date_debut_contrat.desc())
        .first()
    )
    if not contrat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun contrat rattaché à ce salarié.",
        )

    aujourdhui = date.today()
    solde = solde_conges(db, contrat, aujourdhui.year, aujourdhui.month)
    return SoldeCongesOut(
        annee=solde.annee,
        mois=solde.mois,
        acquis=solde.acquis,
        pris=solde.pris,
        pris_ce_mois=solde.pris_ce_mois,
        solde=solde.solde,
        mois_anciennete=solde.mois_anciennete,
        debut_anciennete=solde.debut_anciennete,
        periode_avant_contrat=solde.periode_avant_contrat,
    )


@router.get("/conges", response_model=list[DemandeCongeOut])
def lister_demandes_conges(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Les siennes pour un salarié, celles de son entreprise pour un client."""
    requete = _filtrer_portee(db, db.query(DemandeConge), DemandeConge, current_user)
    demandes = (
        requete.options(joinedload(DemandeConge.salarie))
        .order_by(DemandeConge.created_at.desc())
        .all()
    )
    return [_conge_out(d) for d in demandes]


@router.post("/conges/{demande_id}/valider", response_model=DemandeCongeOut)
def valider_demande_conge(
    demande_id: int,
    payload: DecisionDemande | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Valide une demande et crée l'absence de congés correspondante."""
    dossier_id = _dossier_du_gestionnaire(current_user)

    demande = db.query(DemandeConge).filter(DemandeConge.id == demande_id).first()
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable."
        )
    _salarie_de_l_entreprise(db, demande.salarie_id, dossier_id)
    _exiger_en_attente(demande)

    mois = _mois_couverts(demande.date_debut, demande.date_fin)
    verrou = _bulletins_verrouilles(db, demande.salarie_id, mois)
    if verrou:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Le bulletin de cette période est déjà validé : la demande ne "
                "peut plus être prise en compte. Rouvrez le bulletin avant de valider."
            ),
        )

    absence = SalarieAbsence(
        salarie_id=demande.salarie_id,
        type_absence=TYPE_ABSENCE_CONGES,
        date_debut_absence=demande.date_debut,
        date_fin_absence=demande.date_fin,
        justificatif_fourni=False,
    )
    db.add(absence)
    db.flush()

    demande.absence_id = absence.id
    _decider(demande, current_user, payload.commentaire if payload else None, VALIDEE)
    db.commit()
    db.refresh(demande)
    return _conge_out(demande)


@router.post("/conges/{demande_id}/refuser", response_model=DemandeCongeOut)
def refuser_demande_conge(
    demande_id: int,
    payload: DecisionDemande | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Refuse une demande, avec un motif facultatif."""
    dossier_id = _dossier_du_gestionnaire(current_user)

    demande = db.query(DemandeConge).filter(DemandeConge.id == demande_id).first()
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable."
        )
    _salarie_de_l_entreprise(db, demande.salarie_id, dossier_id)
    _exiger_en_attente(demande)

    _decider(demande, current_user, payload.commentaire if payload else None, REFUSEE)
    db.commit()
    db.refresh(demande)
    return _conge_out(demande)


# ─────────────────────────────────────────────
#  ACOMPTES
# ─────────────────────────────────────────────

@router.post("/acomptes", response_model=DemandeAcompteOut, status_code=status.HTTP_201_CREATED)
def creer_demande_acompte(
    payload: DemandeAcompteCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Dépose une demande d'acompte sur la paie d'un mois."""
    salarie_id = _salarie_du_compte(current_user)

    demande = DemandeAcompte(
        salarie_id=salarie_id,
        montant=round(payload.montant, 2),
        mois=payload.mois,
        annee=str(payload.annee),
        motif=payload.motif,
        statut=EN_ATTENTE,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return _acompte_out(demande)


@router.get("/acomptes", response_model=list[DemandeAcompteOut])
def lister_demandes_acomptes(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Les siennes pour un salarié, celles de son entreprise pour un client."""
    requete = _filtrer_portee(db, db.query(DemandeAcompte), DemandeAcompte, current_user)
    demandes = (
        requete.options(joinedload(DemandeAcompte.salarie))
        .order_by(DemandeAcompte.created_at.desc())
        .all()
    )
    return [_acompte_out(d) for d in demandes]


@router.post("/acomptes/{demande_id}/valider", response_model=DemandeAcompteOut)
def valider_demande_acompte(
    demande_id: int,
    payload: DecisionDemande | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Valide un acompte : le bulletin de la période le retiendra."""
    dossier_id = _dossier_du_gestionnaire(current_user)

    demande = db.query(DemandeAcompte).filter(DemandeAcompte.id == demande_id).first()
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable."
        )
    _salarie_de_l_entreprise(db, demande.salarie_id, dossier_id)
    _exiger_en_attente(demande)

    verrou = _bulletins_verrouilles(
        db, demande.salarie_id, [(int(demande.annee), demande.mois)]
    )
    if verrou:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Le bulletin de ce mois est déjà validé : l'acompte ne peut plus "
                "y être retenu."
            ),
        )

    _decider(demande, current_user, payload.commentaire if payload else None, VALIDEE)
    db.commit()
    db.refresh(demande)
    return _acompte_out(demande)


@router.post("/acomptes/{demande_id}/refuser", response_model=DemandeAcompteOut)
def refuser_demande_acompte(
    demande_id: int,
    payload: DecisionDemande | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Refuse une demande d'acompte, avec un motif facultatif."""
    dossier_id = _dossier_du_gestionnaire(current_user)

    demande = db.query(DemandeAcompte).filter(DemandeAcompte.id == demande_id).first()
    if not demande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable."
        )
    _salarie_de_l_entreprise(db, demande.salarie_id, dossier_id)
    _exiger_en_attente(demande)

    _decider(demande, current_user, payload.commentaire if payload else None, REFUSEE)
    db.commit()
    db.refresh(demande)
    return _acompte_out(demande)
