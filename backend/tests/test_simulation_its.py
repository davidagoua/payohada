"""Le simulateur doit calculer l'ITS comme le moteur de paie.

Depuis la réforme de 2024, l'ITS est assis sur le brut imposable : ces tests
verrouillent à la fois la base, le barème progressif et la RICF, côté simulation.
"""
import unittest

from tests import base  # noqa: F401 - configure l'environnement de test
from tests.base import API, SessionLocal, client, make_tenant, reset_database

from app.services.payroll import calculer_its


class SimulationItsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        make_tenant(self.db, "cabinet-sim-its")

    def tearDown(self):
        self.db.close()

    def _simuler(self, **champs):
        payload = {
            "salaire_mensuel": 300000,
            "type_salaire": "Mensuel",
            "mode_calcul": "base",
            "unite_temps": "Heures",
        }
        payload.update(champs)
        reponse = client.post(f"{API}/bulletins/simuler", json=payload)
        self.assertEqual(reponse.status_code, 200, reponse.text)
        return reponse.json()

    def test_base_its_est_le_brut_imposable(self):
        """La base annoncée et la base de la ligne IBS sont le brut, pas le net."""
        donnees = self._simuler(situation_matrimoniale="Célibataire", enfants_charge=0)
        lignes = {ligne["code"]: ligne for ligne in donnees["lignes"]}

        self.assertAlmostEqual(donnees["salaire_brut"], 300000.0, places=2)
        self.assertAlmostEqual(donnees["net_imposable"], 300000.0, places=2)
        self.assertAlmostEqual(lignes["IBS"]["base_s"], 300000.0, places=2)

    def test_bareme_progressif_et_ricf(self):
        """300 000 F brut : 39 000 F d'ITS brut ; 3 parts → 22 000 F de RICF."""
        celibataire = self._simuler(situation_matrimoniale="Célibataire", enfants_charge=0)
        lignes = {ligne["code"]: ligne for ligne in celibataire["lignes"]}
        self.assertAlmostEqual(lignes["IBS"]["montant_cs"], 39000.0, places=2)
        self.assertAlmostEqual(lignes["RICF"]["montant_cs"], 0.0, places=2)

        marie = self._simuler(situation_matrimoniale="Marié", enfants_charge=2)
        lignes = {ligne["code"]: ligne for ligne in marie["lignes"]}
        self.assertAlmostEqual(lignes["IBS"]["montant_cs"], 39000.0, places=2)
        self.assertAlmostEqual(lignes["RICF"]["montant_cs"], -22000.0, places=2)

    def test_simulation_et_moteur_partagent_le_meme_calcul(self):
        """Le simulateur ne peut pas diverger du moteur : même helper pur."""
        for situation, enfants in (("Célibataire", 0), ("Marié", 2), ("Veuf", 1), ("Divorcé", 3)):
            with self.subTest(situation=situation, enfants=enfants):
                ibs, parts, ricf = calculer_its(300000.0, situation, enfants)
                lignes = {
                    ligne["code"]: ligne
                    for ligne in self._simuler(
                        situation_matrimoniale=situation, enfants_charge=enfants
                    )["lignes"]
                }
                self.assertAlmostEqual(lignes["IBS"]["montant_cs"], ibs, places=2)
                self.assertAlmostEqual(lignes["RICF"]["montant_cs"], -ricf, places=2)


if __name__ == "__main__":
    unittest.main()
