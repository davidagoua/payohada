"""Génère le manuel d'utilisation payohada (DOCX) prêt à être exporté en PDF.

Utilisation :
    python docs/manuel/build_manuel_utilisation.py

Le script produit docs/manuel-utilisation-payohada.docx. L'export PDF est
réalisé ensuite avec LibreOffice Kit (voir office-export-pdf).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from docx import Document  # noqa: E402

import content_part1  # noqa: E402
import content_part2  # noqa: E402
import content_part3  # noqa: E402
import manuel_kit as k  # noqa: E402

ROOT = HERE.parent.parent
LOGO = ROOT / "frontend" / "public" / "payohada-logo.png"
OUTPUT = ROOT / "docs" / "manuel-utilisation-payohada.docx"


def add_sommaire(doc: Document) -> None:
    doc.add_page_break()
    k.add_heading(doc, "Sommaire", level=1)
    k.add_lead(
        doc,
        "Ce manuel est organisé en trois parties. Chaque chapitre démarre sur une "
        "nouvelle page ; les renvois indiquent le numéro de section à consulter.",
    )
    k.add_table(
        doc,
        ["Chapitre", "Contenu", "Rôles concernés"],
        [
            ["**1. Introduction**", "Objet du manuel, espaces de travail, conventions de lecture.", "Tous"],
            ["**2. Premiers pas**", "Connexion, inscription cabinet, mot de passe, navigation.", "Tous"],
            ["**3. Guide Cabinet**", "Dossiers, établissements, salariés, contrats, import Excel/CSV, cycle de paie, bulletins, éditions, simulation, réclamations, administration du cabinet.", "Cabinet"],
            ["**4. Guide Entreprise**", "Saisie et transmission des variables, bulletins, personnel, demandes, réclamations.", "Entreprise"],
            ["**5. Guide Salarié**", "Bulletins, congés, acomptes, réclamations, mot de passe.", "Salarié"],
            ["**6. Sécurité et confidentialité**", "Comptes, rôles, données personnelles, poste de travail, incidents.", "Tous"],
            ["**7. Questions fréquentes**", "Réponses aux situations les plus courantes.", "Tous"],
            ["**8. Matrice des rôles**", "Droits par action et par rôle.", "Tous"],
            ["**9. Glossaire**", "Vocabulaire de la paie et de la plateforme.", "Tous"],
            ["**10. Annexes**", "Calendrier type, checklist, statuts, support.", "Tous"],
        ],
        widths=[5.4, 9.2, 2.4],
        font_size=8.8,
    )

    k.add_heading(doc, "Les espaces en un coup d'œil", level=2)
    k.add_table(
        doc,
        ["Espace", "Compte", "Page d'accueil", "Mission"],
        [
            ["Cabinet", "cabinet, gestionnaire_paie", "/dossiers", "Produire la paie des entreprises clientes."],
            ["Entreprise", "client", "/client", "Préparer les variables et suivre les bulletins."],
            ["Salarié", "salarie", "/salaries/bulletins", "Consulter ses bulletins et ses demandes."],
        ],
        widths=[3.0, 4.0, 4.2, 5.8],
        font_size=8.8,
    )


def validate(path: Path) -> None:
    document = Document(path)
    headings = [p.text for p in document.paragraphs if p.style.name.startswith("Heading")]
    tables = len(document.tables)
    images = len(document.inline_shapes)
    words = sum(len(p.text.split()) for p in document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                words += len(cell.text.split())
    print(f"DOCX : {path}")
    print(f"  titres   : {len(headings)}")
    print(f"  tableaux : {tables}")
    print(f"  images   : {images}")
    print(f"  mots     : {words}")
    assert len(headings) >= 60, "trop peu de titres"
    assert tables >= 30, "trop peu de tableaux"
    assert images == 10, f"images attendues : 10, trouvées : {images}"
    if len(headings) < 80:
        print("  (avertissement : nombre de titres plus faible que prévu)")


def main() -> None:
    if not LOGO.exists():
        raise SystemExit(f"Logo introuvable : {LOGO}")

    doc = k.setup_document()

    props = doc.core_properties
    props.title = "Manuel d'utilisation payohada — guide par rôle"
    props.subject = "Utilisation de la plateforme de paie payohada"
    props.author = "payohada"
    props.keywords = "paie, manuel, cabinet, entreprise, salarié, administration, OHADA"
    props.comments = "Guide pratique par rôle — version 1.2 (sans l'administration plateforme)"

    k.add_cover(doc, LOGO)
    add_sommaire(doc)
    content_part1.render(doc)
    content_part2.render(doc)
    content_part3.render(doc)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    validate(OUTPUT)


if __name__ == "__main__":
    main()
