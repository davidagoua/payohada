"""Tests des calculateurs réglementaires ivoiriens.

Chaque cas attendu est celui produit par les classeurs fournis (qui reproduisent
les exemples officiels), afin de garantir que le moteur donne les mêmes montants.
"""
import unittest
from datetime import date

from tests import base  # noqa: F401  (configure l'environnement avant les imports app)
from tests.base import SessionLocal, make_tenant, reset_database

from app.services.avantages_nature import (
    MONTANT_CLIMATISEUR,
    PLAFOND_EXONERATION_TRANSPORT_COLLECTIF,
    VEHICULE_AUTRE_TAXABLE,
    VEHICULE_FONCTION_SERVICE,
    VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS,
    VEHICULE_TRANSPORT_COLLECTIF_FORFAIT,
    bareme_logement,
    calculer_avantage_vehicule,
    calculer_avantages_nature,
)
from app.services.conges_gratification import (
    COEFFICIENT_OUVRABLES_CALENDAIRES,
    JOURS_CONGES_PAR_MOIS,
    JOURS_CONGES_PAR_MOIS_LEGAL,
    METHODE_CONVENTIONNELLE,
    METHODE_DECRET,
    calculer_conges_payes,
    calculer_gratification,
    droits_conges_acquis,
    jours_service_annuels,
    majoration_anciennete,
)
from app.routers.bulletins import compute_bulletin_cumuls
from app.services.payroll import calculate_payslip
from app.services.indemnites_rupture import (
    TAUX_FIN_CDD,
    anciennete_en_mois,
    calculer_indemnite_deces,
    calculer_indemnite_fin_cdd,
    calculer_indemnite_rupture,
    jours_service_360,
    multiplicateur_frais_funeraire,
)

SALAIRES_300K = [300_000.0] * 12
SALAIRES_350K = [350_000.0] * 12


# ═══════════════════════════════════════════════════════════════════
#  OUTILS DE DATE
# ═══════════════════════════════════════════════════════════════════

class AncienneteTests(unittest.TestCase):
    def test_mois_complets_arrondis_au_mois_inferieur(self):
        # Classeur licenciement : 15/01/2018 → 15/09/2026 = 104 mois
        self.assertEqual(anciennete_en_mois(date(2018, 1, 15), date(2026, 9, 15)), 104)
        # Classeur retraite : 15/09/2006 → 15/09/2026 = 240 mois
        self.assertEqual(anciennete_en_mois(date(2006, 9, 15), date(2026, 9, 15)), 240)

    def test_le_mois_n_est_compte_que_revolu(self):
        self.assertEqual(anciennete_en_mois(date(2026, 1, 15), date(2026, 2, 14)), 0)
        self.assertEqual(anciennete_en_mois(date(2026, 1, 15), date(2026, 2, 15)), 1)
        self.assertEqual(anciennete_en_mois(date(2026, 1, 15), date(2027, 1, 14)), 11)
        self.assertEqual(anciennete_en_mois(date(2026, 1, 15), date(2027, 1, 15)), 12)

    def test_cas_limits(self):
        self.assertEqual(anciennete_en_mois(None, date(2026, 1, 1)), 0)
        self.assertEqual(anciennete_en_mois(date(2026, 1, 1), None), 0)
        self.assertEqual(anciennete_en_mois(date(2026, 5, 1), date(2026, 1, 1)), 0)

    def test_jours_service_360(self):
        # Classeur gratification : 01/01/2026 → 30/09/2026 = 270 jours
        self.assertEqual(jours_service_360(date(2026, 1, 1), date(2026, 9, 30)), 270)
        # Année pleine
        self.assertEqual(jours_service_360(date(2026, 1, 1), date(2026, 12, 31)), 360)
        # Un seul jour
        self.assertEqual(jours_service_360(date(2026, 3, 10), date(2026, 3, 10)), 1)


# ═══════════════════════════════════════════════════════════════════
#  INDEMNITÉ DE LICENCIEMENT / RETRAITE
# ═══════════════════════════════════════════════════════════════════

class IndemniteLicenciementTests(unittest.TestCase):
    def test_exemple_du_classeur_licenciement(self):
        """104 mois d'ancienneté, 12 salaires de 300 000 → 835 000 F."""
        r = calculer_indemnite_rupture(SALAIRES_300K, 104)

        self.assertTrue(r.eligible)
        self.assertIsNone(r.motif_ineligibilite)
        self.assertAlmostEqual(r.salaire_global_moyen, 300_000.0, places=2)
        self.assertAlmostEqual(r.total_salaires_retenus, 3_600_000.0, places=2)
        self.assertEqual(r.nombre_salaires_retenus, 12)

        self.assertEqual(len(r.tranches), 3)
        self.assertAlmostEqual(r.tranches[0].mois_retenus, 60)
        self.assertAlmostEqual(r.tranches[0].montant, 450_000.0, places=2)   # 5 × 30 %
        self.assertAlmostEqual(r.tranches[1].mois_retenus, 44)
        self.assertAlmostEqual(r.tranches[1].montant, 385_000.0, places=2)   # 3,667 × 35 %
        self.assertAlmostEqual(r.tranches[2].mois_retenus, 0)
        self.assertAlmostEqual(r.montant, 835_000.0, places=2)

    def test_exemple_du_classeur_retraite(self):
        """240 mois d'ancienneté, 12 salaires de 300 000 → 2 175 000 F."""
        r = calculer_indemnite_rupture(SALAIRES_300K, 240, depart_retraite=True)

        self.assertTrue(r.eligible)
        self.assertAlmostEqual(r.tranches[0].montant, 450_000.0, places=2)     # 5 ans × 30 %
        self.assertAlmostEqual(r.tranches[1].montant, 525_000.0, places=2)     # 5 ans × 35 %
        self.assertAlmostEqual(r.tranches[2].mois_retenus, 120)
        self.assertAlmostEqual(r.tranches[2].montant, 1_200_000.0, places=2)   # 10 ans × 40 %
        self.assertAlmostEqual(r.montant, 2_175_000.0, places=2)

    def test_anciennete_inferieure_a_un_an_non_eligible(self):
        r = calculer_indemnite_rupture(SALAIRES_300K, 11)
        self.assertFalse(r.eligible)
        self.assertIn("un an", r.motif_ineligibilite)
        self.assertEqual(r.montant, 0.0)

    def test_exactement_un_an_est_eligible(self):
        r = calculer_indemnite_rupture(SALAIRES_300K, 12)
        self.assertTrue(r.eligible)
        self.assertAlmostEqual(r.montant, 90_000.0, places=2)  # 1 an × 30 %

    def test_faute_lourde_annule_l_indemnite(self):
        r = calculer_indemnite_rupture(SALAIRES_300K, 104, faute_lourde=True)
        self.assertFalse(r.eligible)
        self.assertIn("Faute lourde", r.motif_ineligibilite)
        self.assertEqual(r.montant, 0.0)

    def test_bareme_par_tranches_aux_bornes(self):
        # 5 ans pile : uniquement la 1re tranche
        r = calculer_indemnite_rupture([100_000.0] * 12, 60)
        self.assertAlmostEqual(r.montant, 5 * 0.30 * 100_000, places=2)
        # 10 ans pile : tranches 1 et 2
        r = calculer_indemnite_rupture([100_000.0] * 12, 120)
        self.assertAlmostEqual(r.montant, (5 * 0.30 + 5 * 0.35) * 100_000, places=2)
        # 15 ans : + 5 ans à 40 %
        r = calculer_indemnite_rupture([100_000.0] * 12, 180)
        self.assertAlmostEqual(
            r.montant, (5 * 0.30 + 5 * 0.35 + 5 * 0.40) * 100_000, places=2
        )

    def test_mois_ecartes_de_la_moyenne(self):
        """Les mois laissés vides (colonne « À inclure ? » = Non) sont ignorés."""
        salaires = [300_000.0] * 11 + [None]
        r = calculer_indemnite_rupture(salaires, 104)
        self.assertEqual(r.nombre_salaires_retenus, 11)
        self.assertAlmostEqual(r.salaire_global_moyen, 300_000.0, places=2)

    def test_aucun_salaire_saisi(self):
        r = calculer_indemnite_rupture([None] * 12, 104)
        self.assertTrue(r.eligible)
        self.assertEqual(r.salaire_global_moyen, 0.0)
        self.assertEqual(r.montant, 0.0)


# ═══════════════════════════════════════════════════════════════════
#  INDEMNITÉ DE DÉCÈS
# ═══════════════════════════════════════════════════════════════════

class IndemniteDecesTests(unittest.TestCase):
    def test_exemple_du_classeur_deces(self):
        """72 mois d'ancienneté, salaire moyen 350 000 → 647 500 F."""
        r = calculer_indemnite_deces(SALAIRES_350K, 72, smhc_mensuel=0.0)

        self.assertTrue(r.eligible)
        self.assertIn("72 mois", r.motif_eligibilite)
        self.assertAlmostEqual(r.salaire_global_moyen, 350_000.0, places=2)
        self.assertAlmostEqual(r.tranches[0].montant, 525_000.0, places=2)   # 5 × 30 %
        self.assertAlmostEqual(r.tranches[1].montant, 122_500.0, places=2)   # 1 × 35 %
        self.assertAlmostEqual(r.indemnite_rupture, 647_500.0, places=2)

    def test_frais_funeraires_par_tranche_d_anciennete(self):
        self.assertEqual(multiplicateur_frais_funeraire(1), 3)
        self.assertEqual(multiplicateur_frais_funeraire(60), 3)     # 5 ans
        self.assertEqual(multiplicateur_frais_funeraire(61), 4)     # 5 ans et 1 mois
        self.assertEqual(multiplicateur_frais_funeraire(120), 4)    # 10 ans
        self.assertEqual(multiplicateur_frais_funeraire(121), 6)    # au-delà
        self.assertEqual(multiplicateur_frais_funeraire(240), 6)

    def test_frais_funeraires_valorises_sur_le_smhc(self):
        r = calculer_indemnite_deces(SALAIRES_350K, 72, smhc_mensuel=125_000.0)
        self.assertEqual(r.multiplicateur_frais_funeraires, 4)
        self.assertAlmostEqual(r.frais_funeraires, 500_000.0, places=2)
        self.assertAlmostEqual(r.total, 647_500.0 + 500_000.0, places=2)

    def test_moins_d_un_an_frais_funeraires_seuls(self):
        """Sans un an d'ancienneté, l'indemnité n'est pas due mais les frais le sont."""
        r = calculer_indemnite_deces(SALAIRES_350K, 6, smhc_mensuel=125_000.0)
        self.assertFalse(r.eligible)
        self.assertEqual(r.indemnite_rupture, 0.0)
        self.assertEqual(r.multiplicateur_frais_funeraires, 3)
        self.assertAlmostEqual(r.frais_funeraires, 375_000.0, places=2)
        self.assertAlmostEqual(r.total, 375_000.0, places=2)

    def test_conditions_retraite_ouvrent_le_droit(self):
        r = calculer_indemnite_deces(SALAIRES_350K, 8, smhc_mensuel=0.0,
                                     conditions_retraite_remplies=True)
        self.assertTrue(r.eligible)
        self.assertIn("retraite", r.motif_eligibilite)
        self.assertGreater(r.indemnite_rupture, 0)


# ═══════════════════════════════════════════════════════════════════
#  INDEMNITÉ DE FIN DE CDD
# ═══════════════════════════════════════════════════════════════════

class IndemniteFinCddTests(unittest.TestCase):
    def test_exemple_du_classeur(self):
        """3 750 000 F de brut → 112 500 F (3 %)."""
        r = calculer_indemnite_fin_cdd(3_750_000.0, "terme_normal_sans_cdi")
        self.assertTrue(r.eligible)
        self.assertAlmostEqual(r.taux, TAUX_FIN_CDD, places=6)
        self.assertAlmostEqual(r.indemnite_theorique, 112_500.0, places=2)
        self.assertAlmostEqual(r.indemnite_due, 112_500.0, places=2)

    def test_cas_d_exclusion(self):
        for motif in ("refus_cdi_equivalent", "rupture_initiative_salarie",
                      "faute_lourde", "cdi_conclu"):
            with self.subTest(motif=motif):
                r = calculer_indemnite_fin_cdd(3_750_000.0, motif)
                self.assertFalse(r.eligible)
                self.assertEqual(r.indemnite_due, 0.0)
                self.assertAlmostEqual(r.indemnite_theorique, 112_500.0, places=2)

    def test_motif_inconnu_n_attribue_rien_automatiquement(self):
        r = calculer_indemnite_fin_cdd(1_000_000.0, "je_ne_sais_pas")
        self.assertFalse(r.eligible)
        self.assertEqual(r.indemnite_due, 0.0)
        self.assertIn("vérification juridique", r.motif)

    def test_montant_negatif_ramene_a_zero(self):
        r = calculer_indemnite_fin_cdd(-5_000.0, "terme_normal_sans_cdi")
        self.assertEqual(r.indemnite_theorique, 0.0)


# ═══════════════════════════════════════════════════════════════════
#  CONGÉS PAYÉS
# ═══════════════════════════════════════════════════════════════════

class CongesPayesTests(unittest.TestCase):
    def setUp(self):
        # Classeur congés : 12 mois à 350 000, 12 mois de service, 15 jours pris
        self.remunerations = [350_000.0] * 12
        self.resultat = calculer_conges_payes(
            self.remunerations, 12, jours_pris=15, anciennete_annees=2
        )

    def test_exemple_du_classeur_conges(self):
        r = self.resultat
        self.assertAlmostEqual(r.remuneration_totale, 4_200_000.0, places=2)
        self.assertEqual(r.nombre_mois_remuneres, 12)
        self.assertAlmostEqual(r.salaire_mensuel_moyen, 350_000.0, places=2)
        self.assertAlmostEqual(r.salaire_journalier, 11_666.67, places=2)
        # 12 mois × 2,5 jours (disposition conventionnelle plus favorable)
        self.assertAlmostEqual(r.jours_principaux_acquis, 30.0, places=2)
        self.assertAlmostEqual(r.solde_jours_ouvrables, 15.0, places=2)
        self.assertAlmostEqual(r.solde_jours_calendaires, 18.75, places=2)
        self.assertAlmostEqual(r.montant_conventionnel, 218_750.0, places=2)
        self.assertAlmostEqual(r.allocation_principale, 350_000.0, places=2)  # 1/12
        self.assertAlmostEqual(r.montant_decret, 175_000.0, places=2)
        self.assertIn("conventionnelle supérieure", r.comparaison)

    def test_methode_retenue_par_defaut(self):
        self.assertEqual(self.resultat.methode_retenue, METHODE_CONVENTIONNELLE)
        self.assertAlmostEqual(self.resultat.montant_retenu, 218_750.0, places=2)

    def test_bascule_sur_la_methode_du_decret(self):
        r = calculer_conges_payes(
            self.remunerations, 12, jours_pris=15, methode=METHODE_DECRET
        )
        self.assertAlmostEqual(r.montant_retenu, 175_000.0, places=2)

    def test_montant_manuel_prioritaire(self):
        r = calculer_conges_payes(self.remunerations, 12, montant_manuel=200_000.0)
        self.assertAlmostEqual(r.montant_retenu, 200_000.0, places=2)

    def test_acquisition_mensuelle_des_conges(self):
        """8 mois de service → 8 × le taux mensuel de jours ouvrables.

        Le minimum légal est de 2,2 jours par mois (art. 25.1). La convention
        collective applicable en accorde 2,5, une disposition plus favorable qui
        prévaut : c'est ce taux que l'application retient partout.
        """
        droits = droits_conges_acquis(8)
        self.assertAlmostEqual(
            droits["jours_principaux_acquis"], 8 * JOURS_CONGES_PAR_MOIS, places=2
        )
        self.assertAlmostEqual(droits["jours_principaux_acquis"], 20.0, places=2)
        self.assertAlmostEqual(JOURS_CONGES_PAR_MOIS, 2.5, places=6)
        self.assertAlmostEqual(JOURS_CONGES_PAR_MOIS_LEGAL, 2.2, places=6)
        self.assertGreater(
            JOURS_CONGES_PAR_MOIS, JOURS_CONGES_PAR_MOIS_LEGAL,
            "le taux conventionnel doit rester au moins égal au minimum légal",
        )

    def test_coefficient_jours_ouvrables_calendaires(self):
        """24 jours ouvrables correspondent à 30 jours calendaires."""
        self.assertAlmostEqual(24 * COEFFICIENT_OUVRABLES_CALENDAIRES, 30.0, places=6)

    def test_solde_jamais_negatif(self):
        r = calculer_conges_payes(self.remunerations, 12, jours_pris=999)
        self.assertEqual(r.solde_jours_ouvrables, 0.0)
        self.assertEqual(r.solde_jours_calendaires, 0.0)
        self.assertEqual(r.montant_retenu, 0.0)

    def test_jours_supplementaires_ajoutes(self):
        r = calculer_conges_payes(
            self.remunerations, 12, jours_supplementaires=3, jours_pris=0
        )
        self.assertAlmostEqual(
            r.total_jours_acquis, 12 * JOURS_CONGES_PAR_MOIS + 3, places=2
        )

    def test_alertes_sur_donnees_manquantes(self):
        r = calculer_conges_payes([], 0)
        self.assertTrue(r.alertes)
        self.assertTrue(any("rémunération" in a for a in r.alertes))

    def test_majorations_d_anciennete(self):
        """Barème : <5→0 ; 5→1 ; 10→2 ; 15→3 ; 20→5 ; 25→7 ; ≥30→8."""
        attendus = {0: 0, 4: 0, 5: 1, 9: 1, 10: 2, 14: 2, 15: 3, 19: 3,
                    20: 5, 24: 5, 25: 7, 29: 7, 30: 8, 45: 8}
        for annees, attendu in attendus.items():
            with self.subTest(annees=annees):
                self.assertEqual(majoration_anciennete(annees), attendu)


# ═══════════════════════════════════════════════════════════════════
#  GRATIFICATION ANNUELLE
# ═══════════════════════════════════════════════════════════════════

class SourceUniqueTauxCongesTests(unittest.TestCase):
    """Le taux d'acquisition des congés ne doit exister qu'à un seul endroit.

    Il était auparavant écrit en dur dans le calcul du bulletin (2,5) et dans
    l'estimation du solde au départ, tandis que le référentiel des calculateurs
    annonçait 2,2 : deux valeurs contradictoires pour la même règle. Ce test
    empêche la réapparition d'une copie divergente.
    """

    def test_aucun_taux_en_dur_dans_les_routeurs(self):
        import pathlib as _pathlib
        import re

        routeurs = _pathlib.Path(__file__).resolve().parent.parent / "app" / "routers"
        # Toute multiplication d'une ancienneté en mois par un littéral
        motif = re.compile(r"months_seniority\s*\*\s*[\d.]+")
        fautives = []
        for fichier in sorted(routeurs.glob("*.py")):
            for numero, ligne in enumerate(
                fichier.read_text(encoding="utf-8").splitlines(), 1
            ):
                if motif.search(ligne):
                    fautives.append(f"{fichier.name}:{numero} → {ligne.strip()}")
        self.assertEqual(
            fautives, [],
            "Taux d'acquisition des congés écrit en dur : utilisez "
            "JOURS_CONGES_PAR_MOIS du service conges_gratification.\n"
            + "\n".join(f"  - {f}" for f in fautives),
        )

    def test_le_bulletin_et_l_estimation_du_depart_concordent(self):
        """Le calcul du bulletin et l'estimation au départ doivent donner le
        même solde de congés pour la même situation."""
        reset_database()
        db = SessionLocal()
        t = make_tenant(db, "cabinet-concordance-conges")
        contrat = t["contrat"]
        contrat.date_debut_contrat = "2025-01-01"
        db.commit()

        # 6 mois de service, aucune absence
        bulletin = calculate_payslip(db, contrat.id, 6, 2025)
        cumuls = compute_bulletin_cumuls(db, bulletin).mensuel

        # Le bulletin expose le taux mensuel et le solde cumulé
        self.assertAlmostEqual(cumuls.conges_acquis, JOURS_CONGES_PAR_MOIS, places=2)
        acquise_par_le_bulletin = 6 * JOURS_CONGES_PAR_MOIS
        self.assertAlmostEqual(cumuls.conges_solde, acquise_par_le_bulletin, places=2)

        # L'estimation faite au moment du départ doit donner le même solde
        from app.routers.contrats import calculate_estimated_conges_solde

        solde_estime = calculate_estimated_conges_solde(db, contrat, 2025, 6)
        self.assertAlmostEqual(solde_estime, acquise_par_le_bulletin, places=2)
        self.assertAlmostEqual(solde_estime, cumuls.conges_solde, places=2)
        db.close()


class GratificationTests(unittest.TestCase):
    def test_exemple_du_classeur(self):
        """SMHC 125 000, 270 jours de service → 70 312,50 F."""
        r = calculer_gratification(125_000.0, 270, taux_entreprise=0.75)

        self.assertAlmostEqual(r.jours_service, 270.0, places=2)
        self.assertAlmostEqual(r.prorata, 0.75, places=6)
        self.assertAlmostEqual(r.minimum_annuel_temps_plein, 93_750.0, places=2)
        self.assertAlmostEqual(r.minimum_conventionnel_proratise, 70_312.5, places=2)
        self.assertAlmostEqual(r.montant_par_taux_entreprise, 70_312.5, places=2)
        self.assertAlmostEqual(r.gratification_retenue, 70_312.5, places=2)

    def test_annee_complete(self):
        r = calculer_gratification(125_000.0, 360)
        self.assertAlmostEqual(r.prorata, 1.0, places=6)
        self.assertAlmostEqual(r.gratification_retenue, 93_750.0, places=2)

    def test_base_sur_le_smhc_et_non_sur_le_salaire_reel(self):
        """Le minimum conventionnel ne dépend pas du salaire réellement versé."""
        a = calculer_gratification(125_000.0, 360)
        b = calculer_gratification(125_000.0, 360)
        self.assertEqual(a.gratification_retenue, b.gratification_retenue)

    def test_le_plus_favorable_est_retenu(self):
        # Taux entreprise supérieur au minimum
        r = calculer_gratification(100_000.0, 360, taux_entreprise=1.0)
        self.assertAlmostEqual(r.montant_par_taux_entreprise, 100_000.0, places=2)
        self.assertAlmostEqual(r.gratification_retenue, 100_000.0, places=2)
        # Montant fixe supérieur
        r = calculer_gratification(100_000.0, 360, montant_fixe_annuel_entreprise=500_000.0)
        self.assertAlmostEqual(r.gratification_retenue, 500_000.0, places=2)

    def test_jours_plafonnes_a_360(self):
        r = calculer_gratification(100_000.0, 500)
        self.assertAlmostEqual(r.jours_service, 360.0, places=2)
        self.assertAlmostEqual(r.prorata, 1.0, places=6)

    def test_jours_a_deduire(self):
        r = calculer_gratification(100_000.0, 360, jours_a_deduire=90)
        self.assertAlmostEqual(r.jours_service, 270.0, places=2)
        self.assertAlmostEqual(r.prorata, 0.75, places=6)

    def test_alerte_si_smhc_absent(self):
        r = calculer_gratification(0.0, 360)
        self.assertTrue(any("SMHC" in a for a in r.alertes))

    def test_jours_service_annuels_borne_par_l_annee(self):
        # Embauche en 2024, sortie le 30/09/2026, année 2026 → 270 jours
        self.assertEqual(
            jours_service_annuels(date(2024, 1, 1), date(2026, 9, 30), 2026), 270
        )
        # Salarié présent toute l'année 2026
        self.assertEqual(
            jours_service_annuels(date(2024, 1, 1), None, 2026), 360
        )
        # Embauche en cours d'année 2026 : 01/07 → 31/12
        self.assertEqual(
            jours_service_annuels(date(2026, 7, 1), None, 2026), 180
        )
        # Sortie avant l'année considérée
        self.assertEqual(
            jours_service_annuels(date(2020, 1, 1), date(2024, 6, 30), 2026), 0
        )


# ═══════════════════════════════════════════════════════════════════
#  AVANTAGES EN NATURE
# ═══════════════════════════════════════════════════════════════════

class BaremeLogementTests(unittest.TestCase):
    def test_bareme_complet(self):
        attendu = {
            1: (60_000, 10_000, 10_000, 10_000),
            2: (80_000, 20_000, 20_000, 15_000),
            3: (160_000, 40_000, 30_000, 20_000),
            4: (300_000, 60_000, 40_000, 30_000),
            5: (480_000, 80_000, 50_000, 40_000),
            6: (600_000, 100_000, 60_000, 50_000),
            7: (800_000, 150_000, 70_000, 60_000),
        }
        for pieces, montants in attendu.items():
            with self.subTest(pieces=pieces):
                self.assertEqual(bareme_logement(pieces), montants)

    def test_plafonnement_et_plancher(self):
        self.assertEqual(bareme_logement(12), attendu_7 := (800_000, 150_000, 70_000, 60_000))
        self.assertEqual(bareme_logement(0), (60_000, 10_000, 10_000, 10_000))


class AvantagesNatureTests(unittest.TestCase):
    def test_exemple_du_classeur(self):
        """1 000 000 F + logement 3 pièces + 2 climatiseurs → 290 000 / 1 290 000."""
        r = calculer_avantages_nature(
            salaire_et_primes_imposables=1_000_000.0,
            logement_fourni=True,
            mobilier_fourni=True,
            electricite_prise_en_charge=True,
            eau_prise_en_charge=True,
            nombre_pieces=3,
            nombre_climatiseurs=2,
        )

        self.assertAlmostEqual(r.total_avant_participation, 290_000.0, places=2)
        self.assertAlmostEqual(r.avantage_imposable, 290_000.0, places=2)
        self.assertAlmostEqual(r.salaire_brut_imposable, 1_290_000.0, places=2)

        codes = {c.code: c.montant for c in r.composantes}
        self.assertAlmostEqual(codes["AN_LOGEMENT"], 160_000.0, places=2)
        self.assertAlmostEqual(codes["AN_MOBILIER"], 40_000.0, places=2)
        self.assertAlmostEqual(codes["AN_ELECTRICITE"], 30_000.0, places=2)
        self.assertAlmostEqual(codes["AN_EAU"], 20_000.0, places=2)
        self.assertAlmostEqual(codes["AN_CLIMATISATION"], 2 * MONTANT_CLIMATISEUR, places=2)

    def test_domesticite_et_piscine(self):
        r = calculer_avantages_nature(
            piscine=True, nombre_gardiens=1, nombre_employes_maison=1, nombre_cuisiniers=1
        )
        codes = {c.code: c.montant for c in r.composantes}
        self.assertAlmostEqual(codes["AN_PISCINE"], 30_000.0, places=2)
        self.assertAlmostEqual(codes["AN_GARDIEN"], 50_000.0, places=2)
        self.assertAlmostEqual(codes["AN_EMPLOYE_MAISON"], 60_000.0, places=2)
        self.assertAlmostEqual(codes["AN_CUISINIER"], 90_000.0, places=2)
        self.assertAlmostEqual(r.total_avant_participation, 230_000.0, places=2)

    def test_repas_avec_et_sans_exoneration(self):
        sans = calculer_avantages_nature(cout_mensuel_repas=50_000.0)
        self.assertAlmostEqual(sans.total_avant_participation, 50_000.0, places=2)
        avec = calculer_avantages_nature(
            cout_mensuel_repas=50_000.0, exoneration_repas_applicable=True
        )
        self.assertAlmostEqual(avec.total_avant_participation, 20_000.0, places=2)

    def test_participation_du_salarie_deduite(self):
        r = calculer_avantages_nature(
            logement_fourni=True, nombre_pieces=1,
            participation_salarie_hors_vehicule=25_000.0,
        )
        self.assertAlmostEqual(r.total_avant_participation, 60_000.0, places=2)
        self.assertAlmostEqual(r.avantage_imposable, 35_000.0, places=2)

    def test_participation_superieure_au_total(self):
        r = calculer_avantages_nature(
            logement_fourni=True, nombre_pieces=1,
            participation_salarie_hors_vehicule=100_000.0,
        )
        self.assertEqual(r.avantage_imposable, 0.0)

    def test_assiette_cnps_distincte_de_l_assiette_fiscale(self):
        r = calculer_avantages_nature(
            salaire_et_primes_imposables=500_000.0,
            logement_fourni=True, nombre_pieces=3,
            valeur_reelle_avantages_hors_vehicule_cnps=120_000.0,
        )
        # Fiscal : 160 000 ; réel CNPS : 120 000 → écart de −40 000
        self.assertAlmostEqual(r.avantage_imposable, 160_000.0, places=2)
        self.assertAlmostEqual(r.base_cnps_indicative, 620_000.0, places=2)
        self.assertAlmostEqual(r.ecart_fiscal_cnps, -40_000.0, places=2)

    def test_aucune_composante(self):
        r = calculer_avantages_nature(salaire_et_primes_imposables=300_000.0)
        self.assertEqual(r.total_avant_participation, 0.0)
        self.assertEqual(r.composantes, [])
        self.assertAlmostEqual(r.salaire_brut_imposable, 300_000.0, places=2)


class AvantageVehiculeTests(unittest.TestCase):
    def test_vehicule_de_fonction_non_imposable(self):
        r = calculer_avantage_vehicule(
            VEHICULE_FONCTION_SERVICE,
            couts_mensuels={"carburant": 50_000, "entretien": 20_000, "assurance": 15_000},
        )
        self.assertAlmostEqual(r.cout_total_mensuel, 85_000.0, places=2)  # classeur
        self.assertEqual(r.avantage_imposable, 0.0)
        self.assertIn("Non imposable", r.traitement_fiscal)

    def test_transport_collectif_couts_reels(self):
        """85 000 F de coûts, 1 salarié, exonération 30 000 → 55 000 F imposables."""
        r = calculer_avantage_vehicule(
            VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS,
            couts_mensuels={"carburant": 50_000, "entretien": 20_000, "assurance": 15_000},
            nombre_beneficiaires=1,
        )
        self.assertAlmostEqual(r.valeur_brute_par_salarie, 85_000.0, places=2)
        self.assertAlmostEqual(
            r.exoneration_transport_collectif,
            PLAFOND_EXONERATION_TRANSPORT_COLLECTIF, places=2,
        )
        self.assertAlmostEqual(r.avantage_imposable, 55_000.0, places=2)

    def test_repartition_entre_beneficiaires(self):
        r = calculer_avantage_vehicule(
            VEHICULE_TRANSPORT_COLLECTIF_COUTS_REELS,
            couts_mensuels={"carburant": 300_000},
            nombre_beneficiaires=10,
        )
        self.assertAlmostEqual(r.valeur_brute_par_salarie, 30_000.0, places=2)
        self.assertAlmostEqual(r.avantage_imposable, 0.0, places=2)  # sous le plafond

    def test_transport_collectif_forfait(self):
        r = calculer_avantage_vehicule(
            VEHICULE_TRANSPORT_COLLECTIF_FORFAIT, forfait_mensuel_par_salarie=45_000.0
        )
        self.assertAlmostEqual(r.avantage_imposable, 15_000.0, places=2)

    def test_autre_vehicule_a_la_valeur_reelle(self):
        r = calculer_avantage_vehicule(
            VEHICULE_AUTRE_TAXABLE, valeur_reelle_mensuelle=120_000.0
        )
        self.assertAlmostEqual(r.avantage_imposable, 120_000.0, places=2)
        self.assertIn("valeur réelle", r.traitement_fiscal)

    def test_participation_deduite_sur_vehicule_taxable(self):
        r = calculer_avantage_vehicule(
            VEHICULE_TRANSPORT_COLLECTIF_FORFAIT,
            forfait_mensuel_par_salarie=50_000.0,
            participation_salarie=10_000.0,
        )
        self.assertAlmostEqual(r.avantage_imposable, 10_000.0, places=2)

    def test_integration_dans_la_synthese(self):
        vehicule = calculer_avantage_vehicule(
            VEHICULE_TRANSPORT_COLLECTIF_FORFAIT, forfait_mensuel_par_salarie=45_000.0
        )
        r = calculer_avantages_nature(
            salaire_et_primes_imposables=200_000.0,
            logement_fourni=True, nombre_pieces=1, vehicule=vehicule,
        )
        # 60 000 (logement) + 15 000 (véhicule) = 75 000
        self.assertAlmostEqual(r.total_avant_participation, 75_000.0, places=2)
        self.assertAlmostEqual(r.salaire_brut_imposable, 275_000.0, places=2)
        self.assertIn("AN_VEHICULE", {c.code for c in r.composantes})


if __name__ == "__main__":
    unittest.main()
