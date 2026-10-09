"""Calculateurs réglementaires ivoiriens exposés par l'API.

Regroupe les outils de calcul à la rupture du contrat : indemnités de
licenciement / retraite / décès, frais funéraires, indemnité de fin de CDD,
gratification annuelle, congés payés et avantages en nature.

Les calculs sont **déterministes et sans effet de bord** : les endpoints
`.../calculs/...` ne font que produire un résultat, seul
`.../solde-tout-compte/complet` enregistre le départ et le solde.
"""
import json
import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    AvantageEnNature, BulletinPaie, Contrat, DepartSalarie, SoldeToutCompte,
    Utilisateur,
)
from app.routers.contrats import check_contrat_ownership
from app.services.security import get_current_user
from app.schemas.calculs_ci import (
    AvantageNatureIn, AvantageNatureOut, CongesOut, CongesRequest, DecesRequest,
    FinCddRequest, GratificationOut, GratificationRequest, IndemniteDecesOut,
    IndemniteFinCddOut, IndemniteRuptureOut, RuptureRequest,
    SoldeToutCompteCompletOut, SoldeToutCompteCompletRequest,
)
from app.services.avantages_nature import (
    ResultatVehicule, calculer_avantage_vehicule, calculer_avantages_nature,
)
from app.services.conges_gratification import (
    METHODE_CONVENTIONNELLE, calculer_conges_payes, calculer_gratification,
)
from app.services.indemnites_rupture import (
    anciennete_en_mois, calculer_indemnite_deces, calculer_indemnite_fin_cdd,
    calculer_indemnite_rupture,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Calculateurs réglementaires CI"])

MOIS_PAR_AN = 12
NOMBRE_SALAIRES_REFERENCE = 12


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _smhc_du_contrat(contrat: Contrat, surcharge: Optional[float] = None) -> float:
    """Salaire minimum conventionnel mensuel de la catégorie.

    Priorité : valeur transmise explicitement, puis celle du contrat, puis la
    grille du poste de salaire rattaché.
    """
    if surcharge is not None and surcharge > 0:
        return float(surcharge)
    if contrat.smhc_mensuel and contrat.smhc_mensuel > 0:
        return float(contrat.smhc_mensuel)
    if contrat.poste_salaire and contrat.poste_salaire.salaire_mensuel_fcfa:
        return float(contrat.poste_salaire.salaire_mensuel_fcfa)
    return 0.0


def _douze_derniers_salaires(
    db: Session, contrat_id: int, date_situation: Optional[date]
) -> List[Optional[float]]:
    """Salaires bruts des 12 mois précédant la situation.

    Retourne moins de 12 valeurs si l'historique est incomplet. Sert de base par
    défaut au salaire global mensuel moyen du décret n° 2017-210.
    """
    requete = db.query(BulletinPaie).filter(BulletinPaie.contrat_id == contrat_id)

    if date_situation is not None:
        annee, mois = date_situation.year, date_situation.month
        requete = requete.filter(
            (BulletinPaie.annee < annee)
            | ((BulletinPaie.annee == annee) & (BulletinPaie.mois < mois))
        )

    bulletins = (
        requete.order_by(BulletinPaie.annee.desc(), BulletinPaie.mois.desc())
        .limit(NOMBRE_SALAIRES_REFERENCE)
        .all()
    )
    bulletins.reverse()
    # Un bulletin sans brut exploitable est conservé comme « non renseigné ».
    return [b.salaire_brut if b.salaire_brut else None for b in bulletins]


def _anciennete(contrat: Contrat, date_fin: Optional[date], surcharge: Optional[int]) -> int:
    if surcharge is not None:
        return max(0, int(surcharge))
    return anciennete_en_mois(contrat.date_debut_contrat, date_fin)


def _vehicule_depuis_modele(modele: AvantageNatureIn) -> Optional[ResultatVehicule]:
    if not modele.vehicule_type:
        return None
    return calculer_avantage_vehicule(
        modele.vehicule_type,
        couts_mensuels={
            "carburant": modele.vehicule_carburant,
            "entretien": modele.vehicule_entretien,
            "assurance": modele.vehicule_assurance,
            "vignette": modele.vehicule_vignette,
            "autres": modele.vehicule_autres,
        },
        nombre_beneficiaires=modele.vehicule_nombre_beneficiaires,
        forfait_mensuel_par_salarie=modele.vehicule_forfait_mensuel,
        valeur_reelle_mensuelle=modele.vehicule_valeur_reelle,
        participation_salarie=modele.vehicule_participation,
        valeur_reelle_cnps=modele.vehicule_valeur_reelle_cnps,
    )


def _resultat_avantage(
    modele: AvantageNatureIn, salaire_imposable: float
) -> AvantageNatureOut:
    resultat = calculer_avantages_nature(
        salaire_et_primes_imposables=salaire_imposable,
        logement_fourni=modele.logement_fourni,
        mobilier_fourni=modele.mobilier_fourni,
        electricite_prise_en_charge=modele.electricite_prise_en_charge,
        eau_prise_en_charge=modele.eau_prise_en_charge,
        nombre_pieces=modele.nombre_pieces,
        nombre_climatiseurs=modele.nombre_climatiseurs,
        piscine=modele.piscine,
        nombre_gardiens=modele.nombre_gardiens,
        nombre_employes_maison=modele.nombre_employes_maison,
        nombre_cuisiniers=modele.nombre_cuisiniers,
        cout_mensuel_repas=modele.cout_mensuel_repas,
        exoneration_repas_applicable=modele.exoneration_repas_applicable,
        autres_avantages_cout_reel=modele.autres_avantages_cout_reel,
        participation_salarie_hors_vehicule=modele.participation_salarie_hors_vehicule,
        vehicule=_vehicule_depuis_modele(modele),
        valeur_reelle_avantages_hors_vehicule_cnps=modele.valeur_reelle_hors_vehicule_cnps,
    )
    return AvantageNatureOut(**resultat.__dict__)


def _salaire_imposable_du_contrat(contrat: Contrat) -> float:
    """Salaire et primes imposables du contrat, hors avantages en nature."""
    return float(
        (contrat.salaire_mensuel or 0.0)
        + (contrat.sursalaire or 0.0)
    )


# ─────────────────────────────────────────────
#  INDEMNITÉ DE LICENCIEMENT / RETRAITE
# ─────────────────────────────────────────────

@router.post("/contrats/{contrat_id}/calculs/rupture", response_model=IndemniteRuptureOut)
def calculer_rupture(
    contrat_id: int,
    demande: RuptureRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Indemnité de licenciement (art. 4) ou de départ à la retraite (art. 5).

    Barème : 30 % jusqu'à 5 ans, 35 % de 6 à 10 ans, 40 % au-delà, sur le
    salaire global mensuel moyen des 12 derniers mois ; au moins un an
    d'ancienneté et absence de faute lourde.
    """
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    date_fin = demande.date_fin
    salaires = demande.salaires_12_mois or _douze_derniers_salaires(db, contrat_id, date_fin)
    anciennete = _anciennete(contrat, date_fin, demande.anciennete_mois)

    resultat = calculer_indemnite_rupture(
        salaires, anciennete,
        faute_lourde=demande.faute_lourde,
        depart_retraite=demande.depart_retraite,
    )
    return IndemniteRuptureOut(**resultat.__dict__)


# ─────────────────────────────────────────────
#  INDEMNITÉ DE DÉCÈS
# ─────────────────────────────────────────────

@router.post("/contrats/{contrat_id}/calculs/deces", response_model=IndemniteDecesOut)
def calculer_deces(
    contrat_id: int,
    demande: DecesRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Droits des ayants droit : indemnité équivalente au licenciement + frais funéraires.

    Les frais funéraires valent 3 × le SMHC jusqu'à 5 ans d'ancienneté, 4 × de
    6 à 10 ans, 6 × au-delà. L'indemnité est due dès un an d'ancienneté **ou**
    si les conditions de départ à la retraite étaient remplies.
    """
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    date_fin = demande.date_fin
    salaires = demande.salaires_12_mois or _douze_derniers_salaires(db, contrat_id, date_fin)
    anciennete = _anciennete(contrat, date_fin, demande.anciennete_mois)
    smhc = _smhc_du_contrat(contrat, demande.smhc_mensuel)

    resultat = calculer_indemnite_deces(
        salaires, anciennete, smhc,
        conditions_retraite_remplies=demande.conditions_retraite_remplies,
    )
    total_ayants_droit = (
        resultat.total + demande.salaire_presence
        + demande.conges_acquis + demande.autres_droits
    )
    return IndemniteDecesOut(
        **resultat.__dict__,
        total_ayants_droit=round(total_ayants_droit, 2),
    )


# ─────────────────────────────────────────────
#  INDEMNITÉ DE FIN DE CDD
# ─────────────────────────────────────────────

@router.post("/contrats/{contrat_id}/calculs/fin-cdd", response_model=IndemniteFinCddOut)
def calculer_fin_cdd(
    contrat_id: int,
    demande: FinCddRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Indemnité de fin de CDD : 3 % du total des rémunérations brutes du contrat.

    Le total est calculé depuis les bulletins du contrat si `total_brut_cdd`
    n'est pas fourni. Les congés payés non pris peuvent être ajoutés au solde.
    """
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)

    total = demande.total_brut_cdd
    if total is None:
        bulletins = db.query(BulletinPaie).filter(
            BulletinPaie.contrat_id == contrat_id
        ).all()
        total = sum(b.salaire_brut or 0.0 for b in bulletins)

    resultat = calculer_indemnite_fin_cdd(total, demande.sous_motif_fin_cdd)

    conges = 0.0
    if demande.conges_mois_service > 0:
        moyenne = demande.salaire_mensuel_moyen or _salaire_imposable_du_contrat(contrat)
        conges_resultat = calculer_conges_payes(
            [moyenne] * int(demande.conges_mois_service),
            demande.conges_mois_service,
            jours_pris=demande.conges_jours_pris,
        )
        conges = conges_resultat.montant_retenu

    return IndemniteFinCddOut(
        **resultat.__dict__,
        conges_estimes=round(conges, 2),
        solde_estime=round(resultat.indemnite_due + conges, 2),
    )


# ─────────────────────────────────────────────
#  GRATIFICATION ANNUELLE
# ─────────────────────────────────────────────

@router.get("/contrats/{contrat_id}/calculs/gratification", response_model=GratificationOut)
def calculer_gratification_contrat(
    contrat_id: int,
    annee: int = Query(..., ge=2000, le=2100),
    smhc_mensuel: Optional[float] = Query(default=None, ge=0),
    jours_service: Optional[float] = Query(default=None, ge=0),
    taux_entreprise: float = Query(default=0.0, ge=0, le=5),
    montant_fixe_annuel_entreprise: float = Query(default=0.0, ge=0),
    jours_a_deduire: float = Query(default=0.0, ge=0),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Gratification annuelle : au moins 75 % du salaire minimum conventionnel.

    Le prorata est calculé sur une année de 360 jours à partir des dates du
    contrat, sauf si `jours_service` est fourni explicitement.
    """
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    smhc = _smhc_du_contrat(contrat, smhc_mensuel)

    jours = jours_service
    if jours is None:
        from app.services.conges_gratification import jours_service_annuels
        jours = float(jours_service_annuels(
            contrat.date_debut_contrat,
            contrat.date_fin_previsionnelle_contrat,
            annee,
        ))

    resultat = calculer_gratification(
        smhc, jours,
        taux_entreprise=taux_entreprise,
        montant_fixe_annuel_entreprise=montant_fixe_annuel_entreprise,
        jours_a_deduire=jours_a_deduire,
    )
    return GratificationOut(**resultat.__dict__)


# ─────────────────────────────────────────────
#  CONGÉS PAYÉS
# ─────────────────────────────────────────────

@router.get("/contrats/{contrat_id}/calculs/conges", response_model=CongesOut)
def calculer_conges_contrat(
    contrat_id: int,
    mois_service: float = Query(..., ge=0),
    jours_supplementaires: float = Query(default=0.0, ge=0),
    jours_pris: float = Query(default=0.0, ge=0),
    anciennete_annees: Optional[float] = Query(default=None, ge=0),
    methode: str = Query(default=METHODE_CONVENTIONNELLE),
    montant_manuel: Optional[float] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Droits à congés (2,2 jours ouvrables par mois) et indemnité.

    Les rémunérations de la période de référence sont reprises des bulletins du
    contrat. `anciennete_annees` alimente l'indication des jours supplémentaires
    dus au titre de l'ancienneté.
    """
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)

    bulletins = (
        db.query(BulletinPaie)
        .filter(BulletinPaie.contrat_id == contrat_id)
        .order_by(BulletinPaie.annee.desc(), BulletinPaie.mois.desc())
        .limit(NOMBRE_SALAIRES_REFERENCE)
        .all()
    )
    remunerations = [b.salaire_brut for b in bulletins if b.salaire_brut]

    if anciennete_annees is None:
        anciennete_annees = _anciennete(contrat, date.today(), None) / MOIS_PAR_AN

    resultat = calculer_conges_payes(
        remunerations, mois_service,
        jours_supplementaires=jours_supplementaires,
        jours_pris=jours_pris,
        anciennete_annees=anciennete_annees,
        methode=methode,
        montant_manuel=montant_manuel,
    )
    return CongesOut(**resultat.__dict__)


# ─────────────────────────────────────────────
#  AVANTAGES EN NATURE
# ─────────────────────────────────────────────

@router.post("/contrats/{contrat_id}/calculs/avantages-nature", response_model=AvantageNatureOut)
def simuler_avantages_nature(
    contrat_id: int,
    modele: AvantageNatureIn,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Simule les avantages en nature d'un mois sans rien enregistrer."""
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)
    return _resultat_avantage(modele, _salaire_imposable_du_contrat(contrat))


@router.get("/contrats/{contrat_id}/avantages-nature", response_model=List[AvantageNatureIn])
def lister_avantages_nature(
    contrat_id: int,
    annee: Optional[str] = Query(default=None, min_length=4, max_length=4),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Liste les avantages en nature enregistrés pour un contrat."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    requete = db.query(AvantageEnNature).filter(AvantageEnNature.contrat_id == contrat_id)
    if annee:
        requete = requete.filter(AvantageEnNature.annee == annee)
    lignes = requete.order_by(AvantageEnNature.annee, AvantageEnNature.mois).all()
    return [
        AvantageNatureIn(**{
            c.name: getattr(ligne, c.name)
            for c in AvantageEnNature.__table__.columns
            if c.name in AvantageNatureIn.model_fields
        })
        for ligne in lignes
    ]


@router.post("/contrats/{contrat_id}/avantages-nature", response_model=AvantageNatureOut)
def enregistrer_avantages_nature(
    contrat_id: int,
    modele: AvantageNatureIn,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Enregistre (ou remplace) les avantages en nature d'un mois.

    Le calcul est renvoyé pour affichage immédiat ; les valeurs saisies sont
    conservées afin de pouvoir recalculer un bulletin avec un barème à jour.
    """
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)

    ligne = db.query(AvantageEnNature).filter(
        AvantageEnNature.contrat_id == contrat_id,
        AvantageEnNature.mois == modele.mois,
        AvantageEnNature.annee == modele.annee,
    ).first()

    donnees = modele.model_dump()
    if ligne is None:
        ligne = AvantageEnNature(contrat_id=contrat_id, **donnees)
        db.add(ligne)
    else:
        for champ, valeur in donnees.items():
            setattr(ligne, champ, valeur)

    db.commit()
    db.refresh(ligne)

    return _resultat_avantage(modele, _salaire_imposable_du_contrat(contrat))


@router.delete(
    "/contrats/{contrat_id}/avantages-nature/{mois}/{annee}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def supprimer_avantages_nature(
    contrat_id: int,
    mois: int,
    annee: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Supprime les avantages en nature d'un mois."""
    check_contrat_ownership(contrat_id, current_user.id, db)
    ligne = db.query(AvantageEnNature).filter(
        AvantageEnNature.contrat_id == contrat_id,
        AvantageEnNature.mois == mois,
        AvantageEnNature.annee == annee,
    ).first()
    if not ligne:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun avantage en nature enregistré pour cette période.",
        )
    db.delete(ligne)
    db.commit()
    return None


# ─────────────────────────────────────────────
#  SOLDE DE TOUT COMPTE COMPLET
# ─────────────────────────────────────────────

@router.post(
    "/contrats/{contrat_id}/solde-tout-compte/complet",
    response_model=SoldeToutCompteCompletOut,
)
def solde_tout_compte_complet(
    contrat_id: int,
    demande: SoldeToutCompteCompletRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Calcule **et enregistre** le solde de tout compte d'un départ.

    Sélectionne automatiquement les composantes dues selon le motif :

    * `licenciement` → indemnité de licenciement (30/35/40 %) ;
    * `retraite` → même barème, au titre de l'article 5 ;
    * `deces` → indemnité de décès + frais funéraires ;
    * `fin_cdd` → indemnité de 3 % (art. 15.8) ;
    * `demission` / `rupture` → aucune indemnité de rupture automatique.

    Dans tous les cas, l'indemnité compensatrice de congés payés est calculée, et
    la gratification annuelle est ajoutée si une année est renseignée.
    """
    contrat = check_contrat_ownership(contrat_id, current_user.id, db)

    if demande.motif_fin_contrat not in (
        "licenciement", "retraite", "deces", "fin_cdd", "demission", "rupture"
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Motif de fin de contrat invalide. Valeurs autorisées : "
                "licenciement, retraite, deces, fin_cdd, demission, rupture."
            ),
        )

    date_sortie = demande.date_sortie
    salaires = demande.salaires_12_mois or _douze_derniers_salaires(db, contrat_id, date_sortie)
    anciennete = _anciennete(contrat, date_sortie, demande.anciennete_mois)
    smhc = _smhc_du_contrat(contrat, demande.smhc_mensuel)

    details: dict = {
        "motif": demande.motif_fin_contrat,
        "date_sortie": date_sortie.isoformat() if date_sortie else None,
        "anciennete_mois": anciennete,
        "smhc_mensuel": smhc,
        "nombre_salaires_retenus": len([s for s in salaires if s]),
    }
    alertes: list[str] = []

    indemnite_rupture = 0.0
    indemnite_deces = 0.0
    frais_funeraires = 0.0
    indemnite_fin_cdd = 0.0
    gratification = 0.0
    salaire_moyen = 0.0

    # ── Indemnités de rupture ────────────────────────────────────────
    if demande.motif_fin_contrat in ("licenciement", "retraite", "deces"):
        rupture = calculer_indemnite_rupture(
            salaires, anciennete,
            faute_lourde=demande.faute_lourde,
            depart_retraite=(demande.motif_fin_contrat == "retraite"),
            anciennete_minimum_requise=not demande.conditions_retraite_remplies,
        )
        salaire_moyen = rupture.salaire_global_moyen
        details["rupture"] = {
            "eligible": rupture.eligible,
            "motif_ineligibilite": rupture.motif_ineligibilite,
            "salaire_global_moyen": rupture.salaire_global_moyen,
            "tranches": [t.__dict__ for t in rupture.tranches],
        }
        if rupture.motif_ineligibilite:
            alertes.append(rupture.motif_ineligibilite)

        if demande.motif_fin_contrat == "deces":
            deces = calculer_indemnite_deces(
                salaires, anciennete, smhc,
                conditions_retraite_remplies=demande.conditions_retraite_remplies,
            )
            indemnite_deces = deces.indemnite_rupture
            frais_funeraires = deces.frais_funeraires
            details["deces"] = {
                "multiplicateur_frais_funeraires": deces.multiplicateur_frais_funeraires,
                "motif_eligibilite": deces.motif_eligibilite,
            }
            if not deces.eligible:
                alertes.append(deces.motif_eligibilite)
        else:
            indemnite_rupture = rupture.montant

    # ── Indemnité de fin de CDD ──────────────────────────────────────
    if demande.motif_fin_contrat == "fin_cdd":
        sous_motif = demande.sous_motif_fin_cdd or "autre"
        bulletins = db.query(BulletinPaie).filter(
            BulletinPaie.contrat_id == contrat_id
        ).all()
        total_brut = sum(b.salaire_brut or 0.0 for b in bulletins)
        fin_cdd = calculer_indemnite_fin_cdd(total_brut, sous_motif)
        indemnite_fin_cdd = fin_cdd.indemnite_due
        details["fin_cdd"] = {
            "total_brut_cdd": fin_cdd.total_brut_cdd,
            "taux": fin_cdd.taux,
            "motif": fin_cdd.motif,
            "eligible": fin_cdd.eligible,
        }
        if not fin_cdd.eligible:
            alertes.append(fin_cdd.motif)

    # ── Gratification annuelle ───────────────────────────────────────
    if demande.gratification_annee:
        from app.services.conges_gratification import jours_service_annuels
        jours = demande.gratification_jours_service
        if jours is None:
            jours = float(jours_service_annuels(
                contrat.date_debut_contrat, date_sortie, demande.gratification_annee
            ))
        grat = calculer_gratification(
            smhc, jours, taux_entreprise=demande.gratification_taux_entreprise
        )
        gratification = grat.gratification_retenue
        details["gratification"] = grat.__dict__
        alertes.extend(grat.alertes)

    # ── Congés payés ─────────────────────────────────────────────────
    mois_service = demande.conges_mois_service
    if mois_service is None:
        mois_service = float(anciennete)
    bulletins_conges = (
        db.query(BulletinPaie)
        .filter(BulletinPaie.contrat_id == contrat_id)
        .order_by(BulletinPaie.annee.desc(), BulletinPaie.mois.desc())
        .limit(NOMBRE_SALAIRES_REFERENCE)
        .all()
    )
    remunerations = [b.salaire_brut for b in bulletins_conges if b.salaire_brut]
    conges = calculer_conges_payes(
        remunerations, mois_service,
        jours_supplementaires=demande.conges_jours_supplementaires,
        jours_pris=demande.conges_jours_pris,
        anciennete_annees=anciennete / MOIS_PAR_AN,
        methode=demande.conges_methode,
        montant_manuel=demande.conges_montant_manuel,
    )
    details["conges"] = {
        "jours_principaux_acquis": conges.jours_principaux_acquis,
        "solde_jours_ouvrables": conges.solde_jours_ouvrables,
        "solde_jours_calendaires": conges.solde_jours_calendaires,
        "salaire_journalier": conges.salaire_journalier,
        "methode_retenue": conges.methode_retenue,
        "montant_conventionnel": conges.montant_conventionnel,
        "montant_decret": conges.montant_decret,
        "comparaison": conges.comparaison,
    }
    alertes.extend(conges.alertes)

    total = (
        indemnite_rupture + indemnite_deces + frais_funeraires
        + indemnite_fin_cdd + gratification + conges.montant_retenu
        + demande.indemnite_preavis + demande.indemnite_autre
    )

    # ── Persistance ──────────────────────────────────────────────────
    depart = db.query(DepartSalarie).filter(
        DepartSalarie.contrat_id == contrat_id
    ).first()
    if depart is None:
        depart = DepartSalarie(contrat_id=contrat_id)
        db.add(depart)
    depart.date_sortie = date_sortie.isoformat() if date_sortie else depart.date_sortie
    depart.motif_fin_contrat = demande.motif_fin_contrat
    depart.sous_motif_fin_cdd = demande.sous_motif_fin_cdd
    depart.conditions_retraite_remplies = demande.conditions_retraite_remplies

    stc = db.query(SoldeToutCompte).filter(
        SoldeToutCompte.contrat_id == contrat_id
    ).first()
    if stc is None:
        stc = SoldeToutCompte(contrat_id=contrat_id)
        db.add(stc)

    stc.indemnite_licenciement = round(indemnite_rupture, 2)
    stc.indemnite_deces = round(indemnite_deces, 2)
    stc.frais_funeraires = round(frais_funeraires, 2)
    stc.indemnite_fin_cdd = round(indemnite_fin_cdd, 2)
    stc.gratification = round(gratification, 2)
    stc.indemnite_conges_payes = round(conges.montant_retenu, 2)
    stc.indemnite_preavis = round(demande.indemnite_preavis, 2)
    stc.indemnite_autre = round(demande.indemnite_autre, 2)
    stc.total = round(total, 2)
    stc.statut = "genere"
    stc.detail_calcul = json.dumps(details, ensure_ascii=False, default=str)

    contrat.statut = "termine"
    if date_sortie:
        contrat.date_fin_previsionnelle_contrat = date_sortie.isoformat()

    db.commit()
    db.refresh(stc)

    logger.info(
        "Solde de tout compte %s calculé pour le contrat %s (motif %s) : total %s",
        stc.id, contrat_id, demande.motif_fin_contrat, stc.total,
    )

    return SoldeToutCompteCompletOut(
        contrat_id=contrat_id,
        motif_fin_contrat=demande.motif_fin_contrat,
        anciennete_mois=anciennete,
        salaire_global_moyen=salaire_moyen,
        indemnite_licenciement=round(indemnite_rupture, 2),
        indemnite_retraite=round(indemnite_rupture, 2) if demande.motif_fin_contrat == "retraite" else 0.0,
        indemnite_deces=round(indemnite_deces, 2),
        frais_funeraires=round(frais_funeraires, 2),
        indemnite_fin_cdd=round(indemnite_fin_cdd, 2),
        gratification=round(gratification, 2),
        indemnite_conges_payes=round(conges.montant_retenu, 2),
        indemnite_preavis=round(demande.indemnite_preavis, 2),
        indemnite_autre=round(demande.indemnite_autre, 2),
        total=round(total, 2),
        details=details,
        alertes=alertes,
    )
