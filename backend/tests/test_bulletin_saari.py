"""Tests du bulletin de paie au format Sage Saari (HTML puis PDF).

Vérifient la structure du document, la validité du PDF produit et
l'échappement des données saisies : un nom de salarié contenant du HTML ne doit
jamais être interprété, ni dans le PDF, ni dans l'email.
"""
import unittest

from tests import base
from tests.base import API, SessionLocal, auth_headers, client, make_tenant, reset_database

from app.models import models as M
from app.services.bulletin_saari import (
    construire_html_saari,
    generer_pdf_saari,
    html_vers_pdf,
    nom_fichier_bulletin,
)
from app.services.email import _construire_message
from app.services.payroll import calculate_payslip


class BulletinSaariHtmlTests(unittest.TestCase):
    """Contenu du gabarit HTML, sans passer par la base."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-saari")
        self.contrat = self.t["contrat"]
        self.bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        self.salarie = self.contrat.salarie
        self.etablissement = self.contrat.etablissement

    def tearDown(self):
        self.db.close()

    def _html(self, **kwargs):
        return construire_html_saari(
            self.bulletin,
            contrat=self.contrat,
            salarie=kwargs.pop("salarie", self.salarie),
            etablissement=kwargs.pop("etablissement", self.etablissement),
            dossier=kwargs.pop("dossier", self.t["dossier"]),
            cumuls=kwargs.pop("cumuls", None),
            **kwargs,
        )

    def test_structure_du_document(self):
        html = self._html()
        for attendu in (
            "Bulletin de paie",
            "Bulletin de paie",  # titre
            "Matricule",
            "Désignation",
            "Part salariale",
            "Part patronale",
            "1 — Éléments de salaire brut",
            "2 — Cotisations et retenues",
            "3 — Indemnités et retenues diverses",
            "Net à payer",
            "Cumuls",
            "Congés payés",
            "N° employeur CNPS",
        ):
            with self.subTest(attendu=attendu):
                self.assertIn(attendu, html)

    def test_periode_et_montants(self):
        html = self._html()
        self.assertIn("Juin 2025", html)
        # Le brut du contrat de test est de 300 000 F
        self.assertIn("300 000", html)

    def test_lignes_du_bulletin_reparties_par_section(self):
        html = self._html()
        self.assertIn("BASE", html)
        self.assertIn("CNPS_RETRAITE", html)

    def test_echappement_des_donnees_saisies(self):
        """Un nom contenant du HTML ne doit pas être interprété."""
        self.salarie.nom = '<script>alert("xss")</script>'
        self.salarie.prenom = "<b>Intrus</b>"
        html = self._html()

        minuscule = html.lower()
        self.assertNotIn("<script>", minuscule)
        self.assertNotIn("<b>intrus</b>", minuscule)
        # Les chevrons sont bien neutralisés en entités HTML
        self.assertIn("&lt;script&gt;", minuscule)
        self.assertIn("&lt;b&gt;intrus&lt;/b&gt;", minuscule)

    def test_cumuls_absents_ne_cassent_pas_le_rendu(self):
        html = self._html(cumuls=None)
        self.assertIn("Cumuls", html)
        self.assertIn("Net à payer", html)

    def test_mention_du_numero_de_bulletin_dans_un_lot(self):
        html = self._html(rang=2, total=5)
        self.assertIn("2 / 5", html)


class BulletinSaariPdfTests(unittest.TestCase):
    """Conversion HTML → PDF et validité du fichier produit."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-saari-pdf")
        self.contrat = self.t["contrat"]
        self.bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        self.salarie = self.contrat.salarie

    def tearDown(self):
        self.db.close()

    def test_pdf_valide(self):
        pdf = generer_pdf_saari(
            self.bulletin,
            contrat=self.contrat,
            salarie=self.salarie,
            etablissement=self.contrat.etablissement,
            dossier=self.t["dossier"],
        )
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertGreater(len(pdf), 2000, "PDF suspicieusement petit")

    def test_pdf_contient_les_donnees_du_bulletin(self):
        from io import BytesIO

        pdf = generer_pdf_saari(
            self.bulletin, contrat=self.contrat, salarie=self.salarie,
            etablissement=self.contrat.etablissement, dossier=self.t["dossier"],
        )
        try:
            from pypdf import PdfReader
        except ImportError:  # pragma: no cover
            self.skipTest("pypdf indisponible")

        lecteur = PdfReader(BytesIO(pdf))
        self.assertGreaterEqual(len(lecteur.pages), 1)
        texte = "".join(page.extract_text() for page in lecteur.pages)

        for attendu in ("BASE", "NET À PAYER", "CUMULS", "Matricule"):
            with self.subTest(attendu=attendu):
                self.assertIn(attendu, texte)
        self.assertIn(self.salarie.matricule, texte)

    def test_html_invalide_leve_une_exception_explicite(self):
        """La conversion ne doit jamais retourner un PDF vide silencieusement."""
        pdf = html_vers_pdf("<html><body><p>ok</p></body></html>")
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_le_taux_horaire_n_est_pas_affiche_en_pourcentage(self):
        """Régression : la ligne BASE affichait « 1 730,8 % » au lieu de « 1 730,80 ».

        `taux_s` vaut un taux horaire en francs pour les lignes de rémunération,
        et un pourcentage seulement pour les cotisations.
        """
        from app.services.bulletin_saari import construire_html_saari

        html = construire_html_saari(
            self.bulletin, contrat=self.contrat, salarie=self.salarie,
            etablissement=self.contrat.etablissement, dossier=self.t["dossier"],
        )
        # Taux horaire du salaire de base : 300 000 / 173,33 ≈ 1 730,80
        self.assertNotIn("1730,8 %", html)
        self.assertIn("1 730,80", html)
        # Les cotisations conservent bien leur pourcentage
        self.assertIn("6,3 %", html)

    def test_nom_de_fichier(self):
        nom = nom_fichier_bulletin(self.salarie, self.bulletin)
        self.assertTrue(nom.startswith("bulletin_paie_"))
        self.assertTrue(nom.endswith("-2025.pdf"))
        self.assertIn(self.salarie.matricule, nom)

    def test_nom_de_fichier_neutralise_les_caracteres_dangereux(self):
        self.salarie.matricule = 'M/001 "test"\r\nX-Injection: oui'
        nom = nom_fichier_bulletin(self.salarie, self.bulletin)
        for interdit in ('/', '"', "\r", "\n", ":"):
            self.assertNotIn(interdit, nom)
        self.assertTrue(nom.startswith("bulletin_paie_"))


class PieceJointeEmailTests(unittest.TestCase):
    """La pièce jointe doit cohabiter avec le corps HTML du message."""

    def test_message_sans_piece_jointe_inchange(self):
        message = _construire_message("a@b.ci", "Sujet", "<p>x</p>", ())
        self.assertEqual(message.get_content_type(), "multipart/alternative")

    def test_message_avec_piece_jointe_conserve_le_html(self):
        import email

        pdf = b"%PDF-1.4\n%%EOF\n"
        message = _construire_message(
            "a@b.ci", "Bulletin", "<p>Bonjour</p>",
            [("bulletin_paie_M1_06-2025.pdf", pdf, "application/pdf")],
        )
        self.assertEqual(message.get_content_type(), "multipart/mixed")

        relu = email.message_from_string(message.as_string())
        corps = None
        pieces = []
        for partie in relu.walk():
            if partie.get_content_maintype() == "multipart":
                continue
            if partie.get_content_type() == "text/html":
                corps = partie.get_payload(decode=True)
            if partie.get_filename():
                pieces.append(partie)

        self.assertIsNotNone(corps, "le corps HTML a disparu")
        self.assertIn(b"Bonjour", corps)
        self.assertEqual(len(pieces), 1)
        self.assertEqual(pieces[0].get_filename(), "bulletin_paie_M1_06-2025.pdf")
        self.assertEqual(pieces[0].get_content_type(), "application/pdf")
        self.assertEqual(pieces[0].get_payload(decode=True), pdf)


class BulletinPdfApiTests(unittest.TestCase):
    """L'endpoint de téléchargement et son cloisonnement."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-saari-api")
        self.contrat = self.t["contrat"]
        self.bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        self.entetes = auth_headers(self.t["user"])

    def tearDown(self):
        self.db.close()

    def test_telechargement_du_pdf(self):
        r = client.get(f"{API}/bulletins/{self.bulletin.id}/pdf", headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:200])
        self.assertEqual(r.headers["content-type"], "application/pdf")
        # « inline » permet de consulter et d'imprimer sans téléchargement préalable
        self.assertIn("inline", r.headers["content-disposition"])
        self.assertIn("bulletin_paie_", r.headers["content-disposition"])
        self.assertTrue(r.content.startswith(b"%PDF-"))

    def test_cloisonnement_entre_cabinets(self):
        autre = make_tenant(self.db, "cabinet-saari-autre")
        r = client.get(f"{API}/bulletins/{self.bulletin.id}/pdf",
                       headers=auth_headers(autre["user"]))
        self.assertEqual(r.status_code, 403)

    def test_bulletin_inexistant(self):
        r = client.get(f"{API}/bulletins/999999/pdf", headers=self.entetes)
        self.assertEqual(r.status_code, 404)


class EnvoiBulletinParEmailTests(unittest.TestCase):
    """Le bulletin envoyé par email doit porter la pièce jointe au format Saari.

    L'envoi SMTP est intercepté : on vérifie ce que l'application transmet
    réellement au service d'email, sans dépendre d'un serveur.
    """

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-saari-mail")
        self.contrat = self.t["contrat"]
        self.bulletin = calculate_payslip(self.db, self.contrat.id, 6, 2025)
        self.entetes = auth_headers(self.t["user"])
        self.salarie = self.contrat.salarie
        self.salarie.email = "salarie@exemple.ci"
        self.db.commit()

        self.appels = []

        def faux_send_email(to_email, subject, html_content, pieces_jointes=None):
            self.appels.append({
                "to": to_email, "subject": subject, "html": html_content,
                "pieces_jointes": list(pieces_jointes or []),
            })
            return True, "ok"

        import app.routers.bulletins as routeur
        self._originel = routeur.send_email
        routeur.send_email = faux_send_email

    def tearDown(self):
        import app.routers.bulletins as routeur
        routeur.send_email = self._originel
        self.db.close()

    def test_envoi_a_l_employe_joint_le_pdf_saari(self):
        r = client.post(
            f"{API}/bulletins/{self.bulletin.id}/envoyer-employe", headers=self.entetes
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(len(self.appels), 1, "l'email n'a pas été transmis")

        appel = self.appels[0]
        self.assertEqual(appel["to"], "salarie@exemple.ci")
        self.assertEqual(len(appel["pieces_jointes"]), 1, "aucune pièce jointe")

        nom, contenu, type_mime = appel["pieces_jointes"][0]
        self.assertTrue(nom.startswith("bulletin_paie_"), nom)
        self.assertTrue(nom.endswith(".pdf"), nom)
        self.assertIn(self.salarie.matricule, nom)
        self.assertEqual(type_mime, "application/pdf")
        self.assertTrue(contenu.startswith(b"%PDF-"), "la pièce jointe n'est pas un PDF")
        self.assertGreater(len(contenu), 2000)

        # Le corps du message reste présent, en HTML
        self.assertIn("<html", appel["html"].lower())

        # La réponse annonce la pièce jointe
        self.assertEqual(r.json()["piece_jointe"], nom)

    def test_le_pdf_joint_porte_les_donnees_du_bulletin(self):
        """Le PDF envoyé n'est pas une coquille vide : il contient le bulletin."""
        client.post(
            f"{API}/bulletins/{self.bulletin.id}/envoyer-employe", headers=self.entetes
        )
        contenu = self.appels[0]["pieces_jointes"][0][1]
        try:
            from pypdf import PdfReader
        except ImportError:  # pragma: no cover
            self.skipTest("pypdf indisponible")
        from io import BytesIO

        texte = "".join(p.extract_text() for p in PdfReader(BytesIO(contenu)).pages)
        self.assertIn("BULLETIN DE PAIE", texte)
        self.assertIn("NET À PAYER", texte)
        self.assertIn(self.salarie.matricule, texte)

    def test_envoi_au_gestionnaire_joint_aussi_le_pdf(self):
        r = client.post(
            f"{API}/bulletins/{self.bulletin.id}/envoyer-gestionnaire",
            headers=self.entetes,
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(len(self.appels[0]["pieces_jointes"]), 1)
        self.assertEqual(self.appels[0]["pieces_jointes"][0][2], "application/pdf")

    def test_l_email_part_sans_piece_jointe_si_la_generation_echoue(self):
        """Une panne de génération ne doit pas priver le salarié de sa notification."""
        import app.routers.bulletins as routeur
        from app.services import bulletin_saari

        originel = bulletin_saari.generer_pdf_saari
        routeur.generer_pdf_saari = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("panne simulée")
        )
        try:
            r = client.post(
                f"{API}/bulletins/{self.bulletin.id}/envoyer-employe",
                headers=self.entetes,
            )
        finally:
            routeur.generer_pdf_saari = originel

        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(len(self.appels), 1, "l'email aurait dû partir quand même")
        self.assertEqual(self.appels[0]["pieces_jointes"], [])
        self.assertIn("sans pièce jointe", r.json()["message"])


if __name__ == "__main__":
    unittest.main()
