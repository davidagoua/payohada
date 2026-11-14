"""Cabinet de type « entreprise » : une société qui gère elle-même sa paie.

C'est un cabinet (mêmes droits de paie) limité à une seule société, créée
avec le compte par l'administrateur plateforme. Ses membres arrivent
directement sur l'établissement.
"""
import unittest

from tests.base import (
    API, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database,
)
from app.models import models as M

MDP = "MotDePasse!2026"
EMAIL = "direction@entreprise-test.ci"


class CabinetEntrepriseTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.admin = make_user(self.db, "plateforme@payohada.ci", role="cabinet", is_admin=True)

    def tearDown(self):
        self.db.close()

    def _creer(self, type_cabinet="entreprise", email=EMAIL, nom="Boulangerie Kouassi"):
        return client.post(
            f"{API}/platform/cabinets",
            headers=auth_headers(self.admin),
            json={
                "cabinet_nom": nom,
                "type_cabinet": type_cabinet,
                "administrateur": {
                    "prenom": "Awa", "nom": "Kouassi", "email": email, "password": MDP,
                },
            },
        )

    def _compte(self, email=EMAIL):
        self.db.expire_all()
        return self.db.query(M.Utilisateur).filter(M.Utilisateur.email == email).first()

    def _societe(self, proprietaire):
        dossiers = self.db.query(M.Dossier).filter(M.Dossier.utilisateur_id == proprietaire.id).all()
        self.assertEqual(len(dossiers), 1)
        etabs = self.db.query(M.Etablissement).filter(M.Etablissement.dossier_id == dossiers[0].id).all()
        self.assertEqual(len(etabs), 1)
        return dossiers[0], etabs[0]

    # ─── Création ──────────────────────────────────────────

    def test_la_creation_ajoute_un_dossier_et_un_etablissement_au_nom_du_cabinet(self):
        r = self._creer()
        self.assertEqual(r.status_code, 201, r.text[:500])
        self.assertEqual(r.json()["type_cabinet"], "entreprise")
        self.assertEqual(r.json()["dossiers"], 1)

        proprietaire = self._compte()
        self.assertEqual(proprietaire.role, "cabinet")
        self.assertEqual(proprietaire.type_cabinet, "entreprise")
        dossier, etab = self._societe(proprietaire)
        self.assertEqual(dossier.nom_dossier, "Boulangerie Kouassi")
        self.assertEqual(etab.raison_sociale, "Boulangerie Kouassi")
        self.assertTrue(etab.etablissement_principal)

    def test_un_nom_long_est_tronque_pour_le_dossier_seulement(self):
        nom = "Société Ivoirienne de Transformation et de Distribution Alimentaire"
        self.assertEqual(self._creer(nom=nom).status_code, 201)
        dossier, etab = self._societe(self._compte())
        self.assertEqual(dossier.nom_dossier, nom[:50])
        self.assertEqual(etab.raison_sociale, nom)

    def test_deux_entreprises_ont_des_codes_de_dossier_distincts(self):
        self.assertEqual(self._creer().status_code, 201)
        self.assertEqual(self._creer(email="rh@autre-entreprise.ci", nom="Autre").status_code, 201)
        codes = [d.code for d in self.db.query(M.Dossier).all()]
        self.assertEqual(len(codes), len(set(codes)))

    def test_un_cabinet_classique_ne_recoit_pas_de_societe(self):
        r = self._creer(type_cabinet="cabinet")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["type_cabinet"], "cabinet")
        self.assertEqual(self.db.query(M.Dossier).count(), 0)

    def test_type_inconnu_refuse(self):
        self.assertEqual(self._creer(type_cabinet="banque").status_code, 422)
        self.assertIsNone(self._compte())

    # ─── Profil et page d'accueil ──────────────────────────

    def test_le_profil_donne_le_type_et_l_etablissement_d_accueil(self):
        self._creer()
        proprietaire = self._compte()
        dossier, etab = self._societe(proprietaire)

        connexion = client.post(f"{API}/auth/login", json={"email": EMAIL, "password": MDP})
        self.assertEqual(connexion.status_code, 200, connexion.text[:300])
        profil = connexion.json()["user"]
        self.assertEqual(profil["type_cabinet"], "entreprise")
        self.assertEqual(profil["accueil_dossier_id"], dossier.id)
        self.assertEqual(profil["accueil_etablissement_id"], etab.id)

        moi = client.get(f"{API}/auth/me", headers=auth_headers(proprietaire)).json()
        self.assertEqual(moi["type_cabinet"], "entreprise")
        self.assertEqual(moi["accueil_etablissement_id"], etab.id)

    def test_un_membre_herite_du_type_et_de_l_accueil(self):
        self._creer()
        proprietaire = self._compte()
        dossier, etab = self._societe(proprietaire)
        membre = make_user(self.db, "paie@entreprise-test.ci", role="gestionnaire_paie")
        membre.cabinet_owner_id = proprietaire.id
        self.db.commit()

        moi = client.get(f"{API}/auth/me", headers=auth_headers(membre)).json()
        self.assertEqual(moi["type_cabinet"], "entreprise")
        self.assertEqual(moi["accueil_dossier_id"], dossier.id)
        self.assertEqual(moi["accueil_etablissement_id"], etab.id)
        r = client.post(
            f"{API}/dossiers", headers=auth_headers(membre),
            json={"code": "AUTRE1", "nom_dossier": "Autre société"},
        )
        self.assertEqual(r.status_code, 403)

    def test_un_cabinet_classique_n_a_pas_d_accueil(self):
        tenant = make_tenant(self.db)
        moi = client.get(f"{API}/auth/me", headers=auth_headers(tenant["user"])).json()
        self.assertEqual(moi["type_cabinet"], "cabinet")
        self.assertIsNone(moi["accueil_dossier_id"])

    def test_hors_cabinet_le_type_est_vide(self):
        client_compte = make_user(self.db, "client@exemple.ci", role="client")
        moi = client.get(f"{API}/auth/me", headers=auth_headers(client_compte)).json()
        self.assertIsNone(moi["type_cabinet"])
        moi_admin = client.get(f"{API}/auth/me", headers=auth_headers(self.admin)).json()
        self.assertIsNone(moi_admin["type_cabinet"])

    # ─── Une seule société ─────────────────────────────────

    def test_pas_de_second_dossier_ni_de_suppression(self):
        self._creer()
        proprietaire = self._compte()
        dossier, _ = self._societe(proprietaire)
        entetes = auth_headers(proprietaire)

        r = client.post(f"{API}/dossiers", headers=entetes,
                        json={"code": "AUTRE1", "nom_dossier": "Autre société"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(client.delete(f"{API}/dossiers/{dossier.id}", headers=entetes).status_code, 403)
        self._societe(proprietaire)

    def test_un_cabinet_classique_cree_toujours_des_dossiers(self):
        tenant = make_tenant(self.db)
        r = client.post(f"{API}/dossiers", headers=auth_headers(tenant["user"]),
                        json={"code": "NOUV1", "nom_dossier": "Nouvelle société"})
        self.assertEqual(r.status_code, 200, r.text[:300])

    # ─── Paie de sa société, et d'elle seule ──────────────

    def test_l_entreprise_gere_sa_societe_et_ajoute_des_etablissements(self):
        self._creer()
        proprietaire = self._compte()
        dossier, etab = self._societe(proprietaire)
        entetes = auth_headers(proprietaire)

        self.assertEqual(client.get(f"{API}/dossiers/{dossier.id}", headers=entetes).status_code, 200)
        self.assertEqual(client.get(f"{API}/etablissements/{etab.id}", headers=entetes).status_code, 200)
        r = client.post(f"{API}/dossiers/{dossier.id}/etablissements", headers=entetes,
                        json={"code": "X", "raison_sociale": "Agence de Bouaké"})
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["code"], "ETAB0002")
        liste = client.get(f"{API}/dossiers", headers=entetes).json()
        self.assertEqual([d["id"] for d in liste], [dossier.id])

    def test_l_entreprise_ne_voit_pas_les_autres_societes(self):
        self._creer()
        entetes = auth_headers(self._compte())
        autre = make_tenant(self.db, "autre-cabinet")
        self.assertEqual(
            client.get(f"{API}/dossiers/{autre['dossier'].id}", headers=entetes).status_code, 403
        )
        self.assertEqual(
            client.get(f"{API}/etablissements/{autre['etablissement'].id}", headers=entetes).status_code,
            403,
        )


if __name__ == "__main__":
    unittest.main()
