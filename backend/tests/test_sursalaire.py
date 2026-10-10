"""Le sursalaire est une composante du salaire brut, jamais un ajout.

Le formulaire de contrat calcule `sursalaire = salaire saisi − salaire de la
grille` : le montant porté dans « Salaire Mensuel Brut » **est** le brut. Ces
tests verrouillent l'invariant `salaire de base + sursalaire == salaire brut`,
et vérifient que les assiettes (ITS, CNPS) ne sont plus gonflées.
"""
import unittest
from datetime import datetime

from tests import base
from tests.base import SessionLocal, make_contrat, make_tenant, reset_database

from app.models import models as M
from app.services.payroll import calculate_payslip, resoudre_brut_et_sursalaire


class DecompositionSalaireTests(unittest.TestCase):
    """Tests unitaires du helper de décomposition."""

    def test_contrat_mensuel(self):
        brut, base_part, sursalaire = resoudre_brut_et_sursalaire(
            unite="Heures", type_salaire="Mensuel", base_standard=173.33,
            montant_saisi=500_000.0, sursalaire_contrat=100_000.0,
        )
        self.assertAlmostEqual(brut, 500_000.0, places=2)
        self.assertAlmostEqual(base_part, 400_000.0, places=2)
        self.assertAlmostEqual(sursalaire, 100_000.0, places=2)
        self.assertAlmostEqual(base_part + sursalaire, brut, places=2)

    def test_sans_sursalaire(self):
        brut, base_part, sursalaire = resoudre_brut_et_sursalaire(
            unite="Heures", type_salaire="Mensuel", base_standard=173.33,
            montant_saisi=300_000.0, sursalaire_contrat=0.0,
        )
        self.assertAlmostEqual(brut, 300_000.0, places=2)
        self.assertAlmostEqual(base_part, 300_000.0, places=2)
        self.assertEqual(sursalaire, 0.0)

    def test_unite_jours(self):
        brut, base_part, sursalaire = resoudre_brut_et_sursalaire(
            unite="Jours", type_salaire="Mensuel", base_standard=30.0,
            montant_saisi=450_000.0, sursalaire_contrat=50_000.0,
        )
        self.assertAlmostEqual(brut, 450_000.0, places=2)
        self.assertAlmostEqual(base_part, 400_000.0, places=2)
        self.assertAlmostEqual(sursalaire, 50_000.0, places=2)

    def test_contrat_horaire_ramene_au_mois(self):
        """Sur un contrat horaire, le sursalaire est un écart de taux horaire."""
        brut, base_part, sursalaire = resoudre_brut_et_sursalaire(
            unite="Heures", type_salaire="Horaire", base_standard=173.33,
            montant_saisi=3_000.0, sursalaire_contrat=200.0,
        )
        self.assertAlmostEqual(brut, 3_000.0 * 173.33, places=2)
        self.assertAlmostEqual(sursalaire, 200.0 * 173.33, places=2)
        self.assertAlmostEqual(base_part, 2_800.0 * 173.33, places=2)
        self.assertAlmostEqual(base_part + sursalaire, brut, places=2)

    def test_sursalaire_superieur_au_brut_est_plafonne(self):
        """Donnée incohérente : la base ne doit jamais devenir négative."""
        brut, base_part, sursalaire = resoudre_brut_et_sursalaire(
            unite="Heures", type_salaire="Mensuel", base_standard=173.33,
            montant_saisi=200_000.0, sursalaire_contrat=500_000.0,
        )
        self.assertAlmostEqual(brut, 200_000.0, places=2)
        self.assertAlmostEqual(sursalaire, 200_000.0, places=2)
        self.assertEqual(base_part, 0.0)

    def test_valeurs_absentes(self):
        brut, base_part, sursalaire = resoudre_brut_et_sursalaire(
            unite="Heures", type_salaire="Mensuel", base_standard=173.33,
            montant_saisi=None, sursalaire_contrat=None,
        )
        self.assertEqual((brut, base_part, sursalaire), (0.0, 0.0, 0.0))


class BulletinSursalaireTests(unittest.TestCase):
    """Le bulletin ne doit pas gonfler le brut du montant du sursalaire."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-sursalaire")
        self.contrat = self.t["contrat"]

    def tearDown(self):
        self.db.close()

    def _contrat_avec_sursalaire(self, **kwargs):
        """Contrat dont le brut saisi (500 000) comprend un sursalaire de 100 000."""
        salarie = self.t["salarie"]
        return make_contrat(
            self.db, self.t["dossier"], self.t["etablissement"], salarie,
            numero="C-SUR",
            salaire_mensuel=kwargs.pop("salaire_mensuel", 500_000.0),
            sursalaire=kwargs.pop("sursalaire", 100_000.0),
            **kwargs,
        )

    def test_brut_egal_au_salaire_mensuel_saisi(self):
        contrat = self._contrat_avec_sursalaire()
        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)

        self.assertAlmostEqual(bulletin.salaire_brut, 500_000.0, places=2)

    def test_decomposition_base_plus_sursalaire(self):
        contrat = self._contrat_avec_sursalaire()
        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)
        lignes = {l.code: l for l in bulletin.lignes}

        self.assertIn("BASE", lignes)
        self.assertIn("SURSALAIRE", lignes)
        self.assertAlmostEqual(lignes["BASE"].montant_pr, 400_000.0, places=2)
        self.assertAlmostEqual(lignes["SURSALAIRE"].montant_pr, 100_000.0, places=2)
        # Invariant : la somme des deux lignes reconstitue exactement le brut
        self.assertAlmostEqual(
            lignes["BASE"].montant_pr + lignes["SURSALAIRE"].montant_pr,
            bulletin.salaire_brut, places=2,
        )

    def test_le_sursalaire_figure_bien_sur_le_bulletin(self):
        """Corriger le double comptage ne doit pas faire disparaître la ligne."""
        contrat = self._contrat_avec_sursalaire()
        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)
        codes = {l.code for l in bulletin.lignes}
        self.assertIn("SURSALAIRE", codes)

    def test_assiette_its_non_gonflee(self):
        contrat = self._contrat_avec_sursalaire()
        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)

        # Brut 500 000 → retraite 6,3 % = 31 500 ; CMU 500
        self.assertAlmostEqual(bulletin.net_imposable, 500_000.0 - 31_500.0 - 500.0, places=2)

    def test_assiette_cnps_non_gonflee(self):
        contrat = self._contrat_avec_sursalaire()
        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)
        lignes = {l.code: l for l in bulletin.lignes}

        self.assertAlmostEqual(lignes["CNPS_RETRAITE"].base_s, 500_000.0, places=2)
        # 6,3 % de 500 000 (et non de 600 000)
        self.assertAlmostEqual(lignes["CNPS_RETRAITE"].montant_cs, 31_500.0, places=2)

    def test_contrat_sans_sursalaire_inchange(self):
        contrat = self._contrat_avec_sursalaire(salaire_mensuel=300_000.0, sursalaire=0.0)
        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)
        lignes = {l.code: l for l in bulletin.lignes}

        self.assertAlmostEqual(bulletin.salaire_brut, 300_000.0, places=2)
        self.assertAlmostEqual(lignes["BASE"].montant_pr, 300_000.0, places=2)
        self.assertNotIn("SURSALAIRE", lignes)

    def test_contrat_horaire_avec_sursalaire(self):
        """Contrat horaire : le brut mensuel reste le taux horaire × la base."""
        contrat = self._contrat_avec_sursalaire(
            salaire_mensuel=0.0, type_salaire="Horaire",
            salaire_horaire=3_000.0, sursalaire=200.0,
        )
        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)
        lignes = {l.code: l for l in bulletin.lignes}
        attendu = 3_000.0 * 173.33

        self.assertAlmostEqual(bulletin.salaire_brut, attendu, places=2)
        self.assertAlmostEqual(lignes["SURSALAIRE"].montant_pr, 200.0 * 173.33, places=2)
        self.assertAlmostEqual(lignes["BASE"].montant_pr, 2_800.0 * 173.33, places=2)

    def test_absorption_absence_utilise_le_taux_plein(self):
        """Le taux journalier d'absence couvre le brut, sursalaire inclus."""
        contrat = self._contrat_avec_sursalaire(
            salaire_mensuel=500_000.0, sursalaire=100_000.0, unite_temps="Jours",
        )
        self.db.add(M.Absence(
            contrat_id=contrat.id, code="ABS_NP",
            date_debut=datetime(2025, 6, 2), date_fin=datetime(2025, 6, 3),
            nbr_jour_by_user=2.0, nbr_heure_by_user=0.0, mois=6, annee="2025",
        ))
        self.db.commit()

        bulletin = calculate_payslip(self.db, contrat.id, 6, 2025)
        # 2 jours × (500 000 / 30) = 33 333,33 déduits — et non sur 600 000
        self.assertAlmostEqual(bulletin.salaire_brut, 500_000.0 - 33_333.33, places=1)


class IndemniteCongesSursalaireTests(unittest.TestCase):
    """L'indemnité de congés payés se calcule aussi sur le brut réel."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-sursalaire-conges")

    def tearDown(self):
        self.db.close()

    def test_depart_utilise_le_salaire_mensuel_sans_ajout(self):
        from tests.base import API, auth_headers, client

        contrat = make_contrat(
            self.db, self.t["dossier"], self.t["etablissement"], self.t["salarie"],
            numero="C-SUR-2", salaire_mensuel=500_000.0, sursalaire=100_000.0,
        )
        # 12 bulletins au brut réel de 500 000
        for mois in range(1, 13):
            self.db.add(M.BulletinPaie(
                contrat_id=contrat.id, dossier_id=self.t["dossier"].id,
                mois=mois, annee=2025, statut="calcule", salaire_brut=500_000.0,
            ))
        self.db.commit()

        r = client.post(
            f"{API}/contrats/{contrat.id}/solde-tout-compte/complet",
            headers=auth_headers(self.t["user"]),
            json={
                "motif_fin_contrat": "licenciement",
                "date_sortie": "2025-12-31",
                "anciennete_mois": 60,
                "conges_mois_service": 12,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        # 5 ans × 30 % × 500 000 = 750 000 (et non 900 000 sur 600 000)
        self.assertAlmostEqual(corps["indemnite_licenciement"], 750_000.0, places=2)
        # Congés : journalier 500 000/30 = 16 666,67 × 37,5 jours calendaires
        # (12 mois × 2,5 = 30 jours ouvrables × 1,25)
        self.assertAlmostEqual(corps["indemnite_conges_payes"], 625_000.0, places=2)


if __name__ == "__main__":
    unittest.main()
