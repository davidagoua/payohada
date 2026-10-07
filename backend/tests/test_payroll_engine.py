"""Tests de non-régression du moteur de paie (services/payroll.py)."""
import unittest
from datetime import date, datetime

from tests import base
from tests.base import SessionLocal, make_contrat, make_tenant, reset_database

from app.models import models as M
from app.services.payroll import calculate_payslip, _hs_majoration


class HsMajorationTests(unittest.TestCase):
    """Les majorations d'heures supplémentaires doivent couvrir tout le barème."""

    def test_bareme_complet(self):
        attendu = {
            "HS15": 1.15, "HS_15": 1.15, "HS-15": 1.15, "hs15": 1.15,
            "HS25": 1.25, "HS_25": 1.25,
            "HS50": 1.50, "HS_50": 1.50,
            "HS75": 1.75, "HS_75": 1.75,
            "HS100": 2.00, "HS_100": 2.00,
        }
        for code, majoration in attendu.items():
            with self.subTest(code=code):
                self.assertAlmostEqual(_hs_majoration(code), majoration, places=4)

    def test_code_inconnu_non_majore(self):
        self.assertEqual(_hs_majoration("HEURE_SUP"), 1.0)
        self.assertEqual(_hs_majoration(None), 1.0)


class MoteurPaieTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-moteur")
        self.contrat = self.t["contrat"]

    def tearDown(self):
        self.db.close()

    def test_bulletin_de_reference(self):
        """Vérifie le calcul complet sur un cas connu (300 000 FCFA, marié, 2 enfants)."""
        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)

        # Brut = salaire mensuel
        self.assertAlmostEqual(bulletin.salaire_brut, 300000.0, places=2)

        lignes = {l.code: l for l in bulletin.lignes}

        # CNPS retraite : 6,3 % salarié / 7,7 % patronal, plafond 3 375 000
        self.assertAlmostEqual(lignes["CNPS_RETRAITE"].montant_cs, 18900.0, places=2)
        self.assertAlmostEqual(lignes["CNPS_RETRAITE"].montant_cp, 23100.0, places=2)

        # CMU : 500 + 500
        self.assertAlmostEqual(lignes["CMU_S"].montant_cs, 500.0, places=2)
        self.assertAlmostEqual(lignes["CMU_P"].montant_cp, 500.0, places=2)

        # Base imposable = brut - retraite salariale - CMU salariale
        base_imposable = 300000.0 - 18900.0 - 500.0
        self.assertAlmostEqual(bulletin.net_imposable, base_imposable, places=2)

        # ITS progressif sur 280 600 : 165 000×16 % + 40 600×21 %
        its_attendu = 165000 * 0.16 + 40600 * 0.21
        self.assertAlmostEqual(lignes["IBS"].montant_cs, its_attendu, places=2)

        # RICF : marié + 2 enfants = 3 parts → 2 parts × 11 000
        self.assertAlmostEqual(lignes["RICF"].montant_cs, -22000.0, places=2)

        # Cohérence globale du net à payer
        cot_salariales = 18900.0 + its_attendu - 22000.0 + 500.0
        self.assertAlmostEqual(bulletin.cotisations_salariales, cot_salariales, places=2)
        self.assertAlmostEqual(bulletin.net_a_payer, 300000.0 - cot_salariales, places=2)

    def test_net_imposable_correspond_a_la_base_its(self):
        """Le net imposable stocké doit être exactement la base de l'ITS."""
        self.db.add(M.Prime(contrat_id=self.contrat.id, code="PRIME13", montant=50000.0,
                            mois=6, annee="2025"))
        self.db.commit()

        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        lignes = {l.code: l for l in bulletin.lignes}

        self.assertAlmostEqual(lignes["IBS"].base_s, bulletin.net_imposable, places=2)

    def test_deux_absences_meme_code(self):
        """Régression : deux absences de même nature faisaient échouer le bulletin."""
        for debut, fin in ((2, 3), (16, 17)):
            self.db.add(M.Absence(
                contrat_id=self.contrat.id,
                code="MALADIE",
                date_debut=datetime(2025, 6, debut),
                date_fin=datetime(2025, 6, fin),
                nbr_heure_by_user=16.0,
                nbr_jour_by_user=2.0,
                mois=6,
                annee="2025",
            ))
        self.db.commit()

        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)

        codes = [l.code for l in bulletin.lignes]
        self.assertIn("ABS_MALADIE", codes)
        self.assertIn("ABS_MALADIE_2", codes)
        self.assertEqual(len(codes), len(set(codes)), "les codes de lignes doivent être uniques")

    def test_deux_heures_sup_meme_code(self):
        """Régression : deux lignes d'heures supplémentaires de même code."""
        for mois in (6,):
            self.db.add(M.HeureSupplementaire(contrat_id=self.contrat.id, code="HS25",
                                              nombre=4.0, mois=mois, annee="2025"))
            self.db.add(M.HeureSupplementaire(contrat_id=self.contrat.id, code="HS25",
                                              nombre=6.0, mois=mois, annee="2025"))
        self.db.commit()

        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        codes = [l.code for l in bulletin.lignes]
        self.assertIn("HS25", codes)
        self.assertIn("HS25_2", codes)

    def test_majoration_hs75_et_hs100(self):
        """HS75 et HS100 étaient payées au taux de base (majoration 1.0)."""
        self.db.add(M.HeureSupplementaire(contrat_id=self.contrat.id, code="HS75",
                                          nombre=10.0, mois=6, annee="2025"))
        self.db.add(M.HeureSupplementaire(contrat_id=self.contrat.id, code="HS100",
                                          nombre=10.0, mois=6, annee="2025"))
        self.db.commit()

        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        lignes = {l.code: l for l in bulletin.lignes}

        taux_base = 300000.0 / 173.33
        self.assertAlmostEqual(lignes["HS75"].taux_s, round(taux_base * 1.75, 2), places=2)
        self.assertAlmostEqual(lignes["HS100"].taux_s, round(taux_base * 2.00, 2), places=2)

    def test_prime_persistante_null_est_prise_en_compte(self):
        """Régression : `est_persistant` NULL excluait silencieusement la prime."""
        prime = M.Prime(contrat_id=self.contrat.id, code="PRIMEX", montant=25000.0,
                        mois=6, annee="2025", est_persistant=None)
        self.db.add(prime)
        self.db.commit()

        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        self.assertAlmostEqual(bulletin.salaire_brut, 325000.0, places=2)

    def test_journee_absence_coherente_avec_horaire_hebdo(self):
        """40 h/semaine sur 5 jours → 8 h par jour, comme le module RH."""
        self.db.add(M.Absence(
            contrat_id=self.contrat.id,
            code="ABSENCE",
            date_debut=datetime(2025, 6, 2),
            date_fin=datetime(2025, 6, 3),
            nbr_heure_by_user=0.0,
            nbr_jour_by_user=1.0,
            mois=6,
            annee="2025",
        ))
        self.db.commit()

        bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        ligne = next(l for l in bulletin.lignes if l.code == "ABS_ABSENCE")

        self.assertAlmostEqual(ligne.base_s, 8.0, places=2)
        self.assertAlmostEqual(ligne.montant_pr, -round(300000.0 / 173.33 * 8.0, 2), places=2)

    def test_bulletin_valide_non_recalculable(self):
        """Régression : un recalcul écrasait un bulletin validé."""
        bulletin = calculate_payslip(self.db, self.contrat.id, 7, 2025)
        bulletin.statut = "valide"
        self.db.commit()
        montant_initial = bulletin.net_a_payer

        with self.assertRaises(ValueError) as ctx:
            calculate_payslip(self.db, self.contrat.id, 7, 2025)
        self.assertIn("validé", str(ctx.exception))

        self.db.expire_all()
        apres = self.db.query(M.BulletinPaie).filter(M.BulletinPaie.id == bulletin.id).first()
        self.assertEqual(apres.statut, "valide")
        self.assertAlmostEqual(apres.net_a_payer, montant_initial, places=2)

    def test_pret_non_rembourse_deux_fois(self):
        """Un bulletin validé ne peut plus être recalculé, donc plus revalidé.

        C'est ce qui provoquait un double remboursement du même mois de prêt.
        Le cycle complet validation / invalidation est couvert par les tests
        d'API (test_api_securite.py).
        """
        pret = M.PretSalarie(
            salarie_id=self.t["salarie"].id,
            montant_pret=120000.0,
            date_deblocage=date(2025, 1, 1),
            montant_mensualite=10000.0,
            reste_a_rembourser=120000.0,
        )
        self.db.add(pret)
        self.db.commit()

        bulletin = calculate_payslip(self.db, self.contrat.id, 8, 2025)
        ligne_pret = next((l for l in bulletin.lignes if l.pret_id), None)
        self.assertIsNotNone(ligne_pret, "une ligne de retenue sur prêt est attendue")
        self.assertAlmostEqual(ligne_pret.montant_cs, 10000.0, places=2)

        # Le bulletin est validé : sa retenue a été appliquée au prêt.
        bulletin.statut = "valide"
        pret.reste_a_rembourser = round(pret.reste_a_rembourser - ligne_pret.montant_cs, 2)
        self.db.commit()
        self.assertAlmostEqual(pret.reste_a_rembourser, 110000.0, places=2)

        # Tout recalcul est désormais refusé : le prêt ne peut plus être débité
        # une seconde fois pour la même période.
        with self.assertRaises(ValueError):
            calculate_payslip(self.db, self.contrat.id, 8, 2025)
        self.db.refresh(pret)
        self.assertAlmostEqual(pret.reste_a_rembourser, 110000.0, places=2)

    def test_contrat_net_inverse_le_brut(self):
        """Le mode « net » doit retrouver un brut cohérent."""
        contrat = make_contrat(
            self.db, self.t["dossier"], self.t["etablissement"], self.t["salarie"],
            numero="C-NET", salaire_mensuel=250000.0, mode_calcul="net",
        )
        bulletin = calculate_payslip(self.db, contrat.id, 9, 2025)
        self.assertTrue(bulletin.salaire_brut > 250000.0)
        # Le net cible doit être approché à moins de 100 FCFA (hors transport).
        self.assertAlmostEqual(bulletin.net_a_payer, 250000.0, delta=100.0)

    def test_recacul_idempotent(self):
        """Deux calculs successifs d'un brouillon donnent le même résultat."""
        premier = calculate_payslip(self.db, self.contrat.id, 10, 2025)
        montant = premier.net_a_payer
        self.db.expire_all()
        second = calculate_payslip(self.db, self.contrat.id, 10, 2025)
        self.assertEqual(second.statut, "calcule")
        self.assertAlmostEqual(second.net_a_payer, montant, places=2)
        # Aucune ligne en double
        codes = [l.code for l in second.lignes]
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
