"""Établissements : la numérotation des codes est propre à chaque société."""
import unittest

from tests.base import (
    API, SessionLocal, auth_headers, client, make_tenant, reset_database,
)


class NumerotationEtablissementsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.a = make_tenant(self.db, "cabinet-numero-a")
        self.b = make_tenant(self.db, "cabinet-numero-b")

    def tearDown(self):
        self.db.close()

    def _creer(self, tenant, nom: str, **extra) -> dict:
        r = client.post(
            f"{API}/dossiers/{tenant['dossier'].id}/etablissements",
            headers=auth_headers(tenant["user"]),
            json={"code": "ignore", "raison_sociale": nom, **extra},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        return r.json()

    def test_les_champs_dfe_sont_repris(self):
        """Le DFE saisi est relu à l'identique (régime, code activité, obligations)."""
        etab = self._creer(
            self.a, "Siège DFE",
            dfe_code_cdi="611",
            dfe_code_activite="CCE0802",
            dfe_regime_imposition="TEE",
            dfe_est_employeur=True,
            dfe_obligations_fiscales="PATENTE,TVA,TOB",
        )
        self.assertEqual(etab["dfe_code_cdi"], "611")
        self.assertEqual(etab["dfe_code_activite"], "CCE0802")
        self.assertEqual(etab["dfe_regime_imposition"], "TEE")
        self.assertTrue(etab["dfe_est_employeur"])
        self.assertEqual(etab["dfe_obligations_fiscales"], "PATENTE,TVA,TOB")

        # Lisible ensuite par la fiche établissement
        detail = client.get(
            f"{API}/etablissements/{etab['id']}", headers=auth_headers(self.a["user"]),
        ).json()
        self.assertEqual(detail["dfe_obligations_fiscales"], "PATENTE,TVA,TOB")
        self.assertEqual(detail["dfe_regime_imposition"], "TEE")

    def test_chaque_societe_a_sa_propre_sequence(self):
        """Un nouveau dossier repart à ETAB0001, même si la base en contient d'autres."""
        premier_a = self._creer(self.a, "Siège A")
        premier_b = self._creer(self.b, "Siège B")

        self.assertEqual(premier_a["code"], "ETAB0001")
        self.assertEqual(premier_b["code"], "ETAB0001")

        second_a = self._creer(self.a, "Agence A")
        self.assertEqual(second_a["code"], "ETAB0002")

        # La société B n'a pas bougé : son ETAB0001 reste le seul de sa séquence
        # (le dossier de test contient déjà un établissement au code hérité).
        codes_b = [
            etab["code"]
            for etab in client.get(
                f"{API}/dossiers/{self.b['dossier'].id}/etablissements",
                headers=auth_headers(self.b["user"]),
            ).json()
        ]
        self.assertIn("ETAB0001", codes_b)
        self.assertNotIn("ETAB0002", codes_b)

    def test_le_prochain_code_annonce_la_meme_valeur(self):
        """L'aperçu du formulaire et la création doivent s'accorder."""
        self._creer(self.a, "Siège A")
        r = client.get(
            f"{API}/dossiers/{self.a['dossier'].id}/etablissements/next-code",
            headers=auth_headers(self.a["user"]),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["code"], "ETAB0002")
        self.assertEqual(self._creer(self.a, "Agence A")["code"], "ETAB0002")


if __name__ == "__main__":
    unittest.main()
