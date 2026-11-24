"""Logo de l'entreprise : stocké en base, PNG/JPEG/WebP, 1 Mo au plus."""
import base64
import unittest

from tests.base import API, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


class LogoDossierTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-logo")
        self.entetes = auth_headers(self.t["user"])
        self.url = f"{API}/dossiers/{self.t['dossier'].id}"

    def tearDown(self):
        self.db.close()

    def _deposer(self, contenu, nom="logo.png", type_mime="image/png", entetes=None):
        return client.put(f"{self.url}/logo", headers=entetes or self.entetes,
                          files={"fichier": (nom, contenu, type_mime)})

    def test_depot_puis_lecture_du_logo(self):
        r = self._deposer(PNG)
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertTrue(r.json()["a_logo"])
        self.assertTrue(client.get(self.url, headers=self.entetes).json()["a_logo"])

        logo = client.get(f"{self.url}/logo", headers=self.entetes).json()
        self.assertEqual(logo["type"], "image/png")
        self.assertEqual(logo["data_url"], "data:image/png;base64," + base64.b64encode(PNG).decode())

    def test_le_format_est_lu_dans_le_contenu(self):
        # Un JPEG envoyé sous un nom .png reste un JPEG.
        self.assertEqual(self._deposer(JPEG, nom="faux.png").status_code, 200)
        self.assertEqual(client.get(f"{self.url}/logo", headers=self.entetes).json()["type"], "image/jpeg")
        self.assertEqual(self._deposer(WEBP, nom="logo.webp", type_mime="image/webp").status_code, 200)
        self.assertEqual(client.get(f"{self.url}/logo", headers=self.entetes).json()["type"], "image/webp")

    def test_svg_et_faux_fichier_refuses(self):
        self.assertEqual(self._deposer(SVG, nom="logo.svg", type_mime="image/svg+xml").status_code, 400)
        self.assertEqual(self._deposer(b"pas une image", nom="logo.png").status_code, 400)
        self.assertFalse(client.get(self.url, headers=self.entetes).json()["a_logo"])

    def test_logo_trop_lourd_refuse(self):
        r = self._deposer(PNG + b"\x00" * (1024 * 1024))
        self.assertEqual(r.status_code, 413)

    def test_retrait_du_logo(self):
        self._deposer(PNG)
        r = client.delete(f"{self.url}/logo", headers=self.entetes)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["a_logo"])
        self.assertEqual(client.get(f"{self.url}/logo", headers=self.entetes).status_code, 404)

    def test_un_autre_cabinet_ne_lit_ni_ne_modifie_le_logo(self):
        self._deposer(PNG)
        autre = auth_headers(make_tenant(self.db, "autre-cabinet")["user"])
        self.assertEqual(client.get(f"{self.url}/logo", headers=autre).status_code, 403)
        self.assertEqual(self._deposer(JPEG, entetes=autre).status_code, 403)

    def test_le_client_voit_le_logo_sans_pouvoir_le_changer(self):
        self._deposer(PNG)
        compte = make_user(self.db, "client-logo@exemple.ci", role="client", dossier_id=self.t["dossier"].id)
        entetes = auth_headers(compte)
        self.assertEqual(client.get(f"{self.url}/logo", headers=entetes).status_code, 200)
        self.assertEqual(self._deposer(JPEG, entetes=entetes).status_code, 403)

    def test_la_liste_des_dossiers_ne_charge_pas_les_images(self):
        self._deposer(PNG)
        liste = client.get(f"{API}/dossiers", headers=self.entetes).json()
        self.assertTrue(liste[0]["a_logo"])
        self.assertNotIn("logo", liste[0])


if __name__ == "__main__":
    unittest.main()


class LogoSurLeBulletinTests(unittest.TestCase):
    """Le logo de l'entreprise apparaît en tête du bulletin, au choix."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-logo-bulletin")
        from app.services.payroll import calculate_payslip
        self.bulletin = calculate_payslip(self.db, self.t["contrat"].id, 11, 2026)

    def tearDown(self):
        self.db.close()

    def _image(self, format_pil):
        from io import BytesIO
        from PIL import Image
        tampon = BytesIO()
        Image.new("RGB", (120, 40), (11, 37, 69)).save(tampon, format=format_pil)
        return tampon.getvalue()

    def _html(self, **kwargs):
        from app.services.bulletin_saari import construire_html_saari
        contrat = self.t["contrat"]
        return construire_html_saari(
            self.bulletin, contrat=contrat, salarie=contrat.salarie,
            etablissement=contrat.etablissement, dossier=self.t["dossier"], **kwargs,
        )

    def _poser_logo(self, contenu, type_image):
        self.t["dossier"].logo = contenu
        self.t["dossier"].logo_type = type_image
        self.db.commit()

    def test_logo_affiche_par_defaut_et_masquable(self):
        from app.services.bulletin_saari import AffichageBulletin
        self._poser_logo(self._image("PNG"), "image/png")
        self.assertIn('src="data:image/png;base64,', self._html())
        sans = self._html(affichage=AffichageBulletin.depuis(["raison_sociale"]))
        self.assertNotIn("data:image/png", sans)

    def test_sans_logo_rien_n_est_ajoute(self):
        self.assertNotIn('class="logo"', self._html())

    def test_le_pdf_se_genere_avec_chaque_format(self):
        from app.services.bulletin_saari import html_vers_pdf
        for format_pil, type_image in (("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")):
            with self.subTest(format=format_pil):
                self._poser_logo(self._image(format_pil), type_image)
                pdf = html_vers_pdf(self._html())
                self.assertTrue(pdf.startswith(b"%PDF-"))
                self.assertIn(b"/Image", pdf)
