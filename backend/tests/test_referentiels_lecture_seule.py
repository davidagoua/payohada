"""Les référentiels globaux sont consultables par le cabinet, non modifiables."""
import unittest
from tests.base import API, SessionLocal, auth_headers, client, reset_database
from tests.base import make_tenant


class ReferentielsLectureSeuleTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-refs")
        self.entetes = auth_headers(self.t["user"])

    def tearDown(self):
        self.db.close()

    def test_le_cabinet_consulte_les_constantes(self):
        r = client.get(f"{API}/constantes?pays=CI", headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:200])
        self.assertGreater(len(r.json()), 0)

    def test_le_cabinet_consulte_le_plan_de_paie(self):
        r = client.get(f"{API}/plan-paie?pays=CI", headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:200])
        self.assertGreater(len(r.json()), 0)

    def test_le_cabinet_ne_peut_pas_creer_une_constante(self):
        r = client.post(
            f"{API}/constantes",
            headers=self.entetes,
            json={"code": "TEST_CAB", "description": "Test", "montant": 1,
                  "unite": "FCFA", "pays": "CI", "est_actif": True},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])

    def test_le_cabinet_ne_peut_pas_modifier_une_constante(self):
        existante = client.get(f"{API}/constantes?pays=CI", headers=self.entetes).json()[0]
        r = client.put(
            f"{API}/constantes/{existante['id']}",
            headers=self.entetes,
            json={"montant": 1},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])

    def test_le_cabinet_ne_peut_pas_creer_un_poste_de_paie(self):
        r = client.post(
            f"{API}/plan-paie",
            headers=self.entetes,
            json={"type": "B", "code": "TEST_CAB", "libelle": "Test",
                  "mode_calcul": "Manuel", "sens": "Gain", "pays": "CI"},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])


if __name__ == "__main__":
    unittest.main()
