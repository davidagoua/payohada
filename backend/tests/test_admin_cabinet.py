"""Administration du cabinet : membres, rôles et portée.

L'administration appartient au propriétaire du cabinet (rôle `cabinet`), avec
un relais possible pour les membres promus co-administrateurs. Ces tests
verrouillent la portée (un cabinet ne voit pas les membres d'un autre), les
garde-fous (propriétaire non modifiable) et l'effet réel des rôles sur l'accès
aux sociétés.
"""
import unittest

from tests.base import (
    API, SessionLocal, auth_headers, client, make_dossier, make_etablissement,
    make_tenant, make_user, reset_database,
)

from app.models import models as M


class AdministrationCabinetTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-admin")
        self.proprietaire = self.t["user"]
        self.entetes = auth_headers(self.proprietaire)

        # Une seconde société du même cabinet, pour vérifier l'élargissement.
        self.seconde_societe = make_dossier(
            self.db, self.proprietaire, code="DOS2", nom="Seconde société",
        )
        make_etablissement(self.db, self.seconde_societe, code="ET2")
        self.db.commit()

    def tearDown(self):
        self.db.close()

    # ── helpers ──────────────────────────────────────────────────────────

    def _creer_membre(self, email="membre@cabinet.ci", role="gestionnaire_paie",
                      password=None, entetes=None):
        corps = {
            "email": email,
            "nom": "Yao",
            "prenom": "Adjoua",
            "role": role,
        }
        if password:
            corps["password"] = password
        return client.post(
            f"{API}/admin/utilisateurs",
            headers=entetes or self.entetes,
            json=corps,
        )

    def _compte(self, email="membre@cabinet.ci"):
        return (
            self.db.query(M.Utilisateur)
            .filter(M.Utilisateur.email == email)
            .first()
        )

    def _liste(self, entetes=None):
        return client.get(f"{API}/admin/utilisateurs", headers=entetes or self.entetes)

    # ── accès à l'administration ─────────────────────────────────────────

    def test_le_proprietaire_voit_son_administration(self):
        r = self._liste()
        self.assertEqual(r.status_code, 200, r.text[:300])
        membres = r.json()
        self.assertEqual(len(membres), 1)
        self.assertEqual(membres[0]["id"], self.proprietaire.id)
        self.assertTrue(membres[0]["est_proprietaire"])
        self.assertEqual(membres[0]["nombre_societes"], 2)

    def test_un_gestionnaire_ne_peut_pas_administrer(self):
        self._creer_membre()
        membre = self._compte()
        self.assertEqual(
            self._liste(auth_headers(membre)).status_code,
            403,
        )

    def test_un_client_ne_peut_pas_administrer(self):
        client_user = make_user(
            self.db, "client-admin@exemple.ci", role="client",
            dossier_id=self.t["dossier"].id,
        )
        self.db.commit()
        self.assertEqual(
            self._liste(auth_headers(client_user)).status_code,
            403,
        )

    def test_isolation_entre_cabinets(self):
        self._creer_membre()
        autre = make_tenant(self.db, "cabinet-voisin")

        membres = self._liste(auth_headers(autre["user"])).json()
        emails = {m["email"] for m in membres}
        self.assertNotIn("membre@cabinet.ci", emails)
        self.assertNotIn(self.proprietaire.email, emails)

        # Il ne peut pas modifier un membre d'un autre cabinet.
        cible = self._compte()
        r = client.put(
            f"{API}/admin/utilisateurs/{cible.id}",
            headers=auth_headers(autre["user"]),
            json={"is_active": False},
        )
        self.assertEqual(r.status_code, 404, r.text[:200])

    # ── création ─────────────────────────────────────────────────────────

    def test_creation_d_un_membre_du_cabinet(self):
        r = self._creer_membre(password="MotDePasse!2026")
        self.assertEqual(r.status_code, 201, r.text[:300])
        corps = r.json()
        self.assertEqual(corps["role"], "gestionnaire_paie")
        self.assertEqual(corps["cabinet_owner_id"], self.proprietaire.id)
        self.assertFalse(corps["est_proprietaire"])
        self.assertEqual(corps["nombre_societes"], 0)
        self.assertIsNone(corps["mot_de_passe_initial"])

        # Le compte peut se connecter, et voit l'administration ? Non : rôle gestionnaire.
        connexion = client.post(
            f"{API}/auth/login",
            json={"email": "membre@cabinet.ci", "password": "MotDePasse!2026"},
        )
        self.assertEqual(connexion.status_code, 200, connexion.text[:200])

    def test_creation_refusee_si_email_existant(self):
        self._creer_membre()
        r = self._creer_membre()
        self.assertEqual(r.status_code, 400, r.text[:200])

    def test_creation_reservee_au_cabinet(self):
        self._creer_membre()
        membre = self._compte()
        r = self._creer_membre(
            email="autre@cabinet.ci", entetes=auth_headers(membre),
        )
        self.assertEqual(r.status_code, 403, r.text[:200])

    # ── rôles et portée ──────────────────────────────────────────────────

    def test_promotion_en_coadministrateur_ouvre_les_societes(self):
        self._creer_membre(password="MotDePasse!2026")
        membre = self._compte()
        entetes_membre = auth_headers(membre)

        # Gestionnaire sans affectation : aucune société visible.
        self.assertEqual(
            client.get(f"{API}/dossiers", headers=entetes_membre).json(),
            [],
        )

        r = client.put(
            f"{API}/admin/utilisateurs/{membre.id}",
            headers=self.entetes,
            json={"role": "cabinet"},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["role"], "cabinet")

        # Co-administrateur : toutes les sociétés du propriétaire.
        dossiers = client.get(f"{API}/dossiers", headers=entetes_membre).json()
        self.assertEqual(
            {d["id"] for d in dossiers},
            {self.t["dossier"].id, self.seconde_societe.id},
        )
        # Et il accède à l'administration du cabinet.
        self.assertEqual(
            self._liste(entetes_membre).status_code,
            200,
        )

    def test_retrogradation_retire_l_acces_aux_societes_non_affectees(self):
        self._creer_membre()
        membre = self._compte()
        client.put(
            f"{API}/admin/utilisateurs/{membre.id}",
            headers=self.entetes,
            json={"role": "cabinet"},
        )
        r = client.put(
            f"{API}/admin/utilisateurs/{membre.id}",
            headers=self.entetes,
            json={"role": "gestionnaire_paie"},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(
            client.get(f"{API}/dossiers", headers=auth_headers(membre)).json(),
            [],
        )

    # ── garde-fous ───────────────────────────────────────────────────────

    def test_le_proprietaire_ne_peut_pas_modifier_son_propre_compte(self):
        r = client.put(
            f"{API}/admin/utilisateurs/{self.proprietaire.id}",
            headers=self.entetes,
            json={"role": "gestionnaire_paie"},
        )
        self.assertEqual(r.status_code, 400, r.text[:200])

    def test_le_proprietaire_ne_peut_pas_etre_desactive(self):
        # Promu co-administrateur, il tente de désactiver le propriétaire.
        self._creer_membre()
        membre = self._compte()
        client.put(
            f"{API}/admin/utilisateurs/{membre.id}",
            headers=self.entetes,
            json={"role": "cabinet"},
        )
        r = client.put(
            f"{API}/admin/utilisateurs/{self.proprietaire.id}",
            headers=auth_headers(membre),
            json={"is_active": False},
        )
        self.assertEqual(r.status_code, 400, r.text[:200])

    def test_desactivation_empeche_la_connexion(self):
        self._creer_membre(password="MotDePasse!2026")
        membre = self._compte()
        r = client.put(
            f"{API}/admin/utilisateurs/{membre.id}",
            headers=self.entetes,
            json={"is_active": False},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        connexion = client.post(
            f"{API}/auth/login",
            json={"email": "membre@cabinet.ci", "password": "MotDePasse!2026"},
        )
        self.assertNotEqual(connexion.status_code, 200, connexion.text[:200])

    # ── administrateur plateforme ────────────────────────────────────────

    def test_l_administrateur_plateforme_n_administre_pas_les_membres(self):
        """Il gère les cabinets depuis /platform, pas leurs comptes internes."""
        self._creer_membre()
        admin = make_user(self.db, "admin@plateforme.ci", role="cabinet", is_admin=True)
        self.db.commit()

        self.assertEqual(self._liste(auth_headers(admin)).status_code, 403)
        cible = self._compte()
        r = client.put(
            f"{API}/admin/utilisateurs/{cible.id}",
            headers=auth_headers(admin),
            json={"is_active": False},
        )
        self.assertEqual(r.status_code, 403, r.text[:300])
        self.db.refresh(cible)
        self.assertTrue(cible.is_active)

if __name__ == "__main__":
    unittest.main()
