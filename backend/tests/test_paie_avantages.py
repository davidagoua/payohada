"""Tests d'intégration des avantages en nature dans le calcul du bulletin.

Vérifient que l'avantage :
* augmente le **brut imposable** (donc la base de l'ITS) ;
* n'est **pas versé en espèces** (retenue compensatoire sur le net) ;
* utilise la **valeur réelle** pour l'assiette CNPS lorsqu'elle est saisie ;
* se reporte sur les mois suivants quand il est déclaré persistant.
"""
import unittest

from tests import base
from tests.base import SessionLocal, make_contrat, make_tenant, reset_database

from app.models import models as M
from app.services.payroll import calculate_payslip


class AvantagesNatureDansLeBulletinTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-an-paie")
        self.contrat = self.t["contrat"]

    def tearDown(self):
        self.db.close()

    def _avantage(self, **kwargs):
        champs = dict(
            contrat_id=self.contrat.id, mois=6, annee="2025",
            logement_fourni=True, nombre_pieces=1,
        )
        champs.update(kwargs)
        ligne = M.AvantageEnNature(**champs)
        self.db.add(ligne)
        self.db.commit()
        return ligne

    def _lignes(self, bulletin):
        return {l.code: l for l in bulletin.lignes}

    # ── Brut et imposable ─────────────────────────────────────────────

    def test_avantage_ajoute_au_brut_imposable(self):
        """Un logement d'une pièce (60 000) porte le brut de 300 000 à 360 000."""
        self._avantage()
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)

        self.assertAlmostEqual(bulletin.salaire_brut, 360_000.0, places=2)
        lignes = self._lignes(bulletin)
        self.assertIn("AN_LOGEMENT", lignes)
        self.assertAlmostEqual(lignes["AN_LOGEMENT"].montant_pr, 60_000.0, places=2)

    def test_base_its_inclut_l_avantage(self):
        """Le net imposable doit être calculé sur le brut avantage inclus."""
        self._avantage()
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        lignes = self._lignes(bulletin)

        # La ligne d'impôt doit porter sur la base incluant l'avantage
        self.assertAlmostEqual(lignes["IBS"].base_s, bulletin.net_imposable, places=2)
        # Brut 360 000 → retraite 6,3 % = 22 680 ; CMU 500
        self.assertAlmostEqual(
            bulletin.net_imposable, 360_000.0 - 22_680.0 - 500.0, places=2
        )

    def test_impot_augmente_avec_l_avantage(self):
        sans = calculate_payslip(self.db, self.contrat.id, 5, 2025)
        self._avantage(mois=6)
        avec = calculate_payslip(self.db, self.contrat.id, 6, 2025)

        # Le même mois sans avantage servirait de témoin : on compare l'impôt
        # au prorata des bases.
        impot_sans = self._lignes(sans)["IBS"].montant_cs
        impot_avec = self._lignes(avec)["IBS"].montant_cs
        self.assertGreater(impot_avec, impot_sans)

    # ── Neutralité sur le net ─────────────────────────────────────────

    def test_avantage_retire_du_net_a_payer(self):
        """Un avantage en nature ne se paie pas deux fois."""
        self._avantage()
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        lignes = self._lignes(bulletin)

        self.assertIn("RETENUE_AVANTAGES_NATURE", lignes)
        self.assertAlmostEqual(
            lignes["RETENUE_AVANTAGES_NATURE"].montant_cs, 60_000.0, places=2
        )

    def test_net_coherent_avec_les_cotisations(self):
        """Net = brut − cotisations salariales − avantage non décaissé."""
        self._avantage()
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)

        attendu = bulletin.salaire_brut - bulletin.cotisations_salariales - 60_000.0
        self.assertAlmostEqual(bulletin.net_a_payer, attendu, places=2)

    def test_avantage_reduit_le_net_par_les_cotisations_supplementaires(self):
        """L'avantage est imposable : le net baisse du montant des cotisations."""
        sans = calculate_payslip(self.db, self.contrat.id, 5, 2025)
        self._avantage(mois=6)
        avec = calculate_payslip(self.db, self.contrat.id, 6, 2025)

        # Le net avec avantage reste inférieur au net sans avantage, puisque les
        # cotisations portent sur un brut plus élevé.
        self.assertLess(avec.net_a_payer, sans.net_a_payer)

    # ── Assiette CNPS ─────────────────────────────────────────────────

    def test_assiette_cnps_utilise_la_valeur_reelle(self):
        """Le fisc retient le forfait (60 000), la CNPS la valeur réelle saisie."""
        self._avantage(valeur_reelle_hors_vehicule_cnps=25_000.0)
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        lignes = self._lignes(bulletin)

        # Base CNPS = 360 000 (brut fiscal) − 60 000 (forfait) + 25 000 (réel)
        #           = 300 000 (salaire hors avantage) + 25 000 = 325 000
        self.assertAlmostEqual(lignes["CNPS_RETRAITE"].base_s, 325_000.0, places=2)
        # L'assiette fiscale, elle, reste à 360 000
        self.assertAlmostEqual(bulletin.salaire_brut, 360_000.0, places=2)

    def test_assiette_cnps_par_defaut_egale_au_brut(self):
        """Sans valeur réelle saisie, l'assiette sociale suit le brut fiscal."""
        self._avantage()
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        lignes = self._lignes(bulletin)
        self.assertAlmostEqual(lignes["CNPS_RETRAITE"].base_s, 360_000.0, places=2)

    # ── Véhicule et récurrence ────────────────────────────────────────

    def test_vehicule_de_fonction_non_imposable(self):
        self._avantage(mois=6, vehicule_type="fonction_service", vehicule_carburant=50_000.0)
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        self.assertAlmostEqual(bulletin.salaire_brut, 360_000.0, places=2)  # logement seul

    def test_transport_collectif_imposable_apres_plafond(self):
        self._avantage(
            mois=6, logement_fourni=False,
            vehicule_type="transport_collectif_forfait",
            vehicule_forfait_mensuel=50_000.0,
        )
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        # 300 000 + (50 000 − 30 000) = 320 000
        self.assertAlmostEqual(bulletin.salaire_brut, 320_000.0, places=2)

    def test_avantage_persistant_s_applique_aux_mois_suivants(self):
        self._avantage(mois=6, est_persistant=True)

        juin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        juillet = calculate_payslip(self.db, self.contrat.id, 7, 2025)
        self.assertAlmostEqual(juin.salaire_brut, 360_000.0, places=2)
        self.assertAlmostEqual(juillet.salaire_brut, 360_000.0, places=2)

    def test_avantage_non_persistant_ne_deborde_pas(self):
        self._avantage(mois=6, est_persistant=False)
        juillet = calculate_payslip(self.db, self.contrat.id, 7, 2025)
        self.assertAlmostEqual(juillet.salaire_brut, 300_000.0, places=2)

    def test_aucun_avantage_aucun_changement(self):
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        codes = {l.code for l in bulletin.lignes}
        self.assertFalse({c for c in codes if c.startswith("AN_")})
        self.assertNotIn("RETENUE_AVANTAGES_NATURE", codes)
        self.assertAlmostEqual(bulletin.salaire_brut, 300_000.0, places=2)

    def test_avantage_a_zero_ne_produit_aucune_ligne(self):
        self._avantage(logement_fourni=False)
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        codes = {l.code for l in bulletin.lignes}
        self.assertNotIn("AN_LOGEMENT", codes)
        self.assertNotIn("RETENUE_AVANTAGES_NATURE", codes)

    def test_domesticite_et_repas_cumules(self):
        self._avantage(
            logement_fourni=False, nombre_gardiens=1, nombre_cuisiniers=1,
            cout_mensuel_repas=40_000.0, exoneration_repas_applicable=True,
        )
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        # 50 000 (gardien) + 90 000 (cuisinier) + 10 000 (repas après exonération)
        self.assertAlmostEqual(bulletin.salaire_brut, 300_000.0 + 150_000.0, places=2)


if __name__ == "__main__":
    unittest.main()
