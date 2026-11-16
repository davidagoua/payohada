# -*- coding: utf-8 -*-
"""Description stack technique Payohada — version non technique (avantages uniquement)."""

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

DARK = RGBColor(0x1A, 0x1A, 0x1A)
GRAY = RGBColor(0x59, 0x59, 0x59)
BLACK = RGBColor(0x00, 0x00, 0x00)


def set_run_font(run, name="Calibri", size=11, bold=False, italic=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)


def add_bottom_border(paragraph, color="BFBFBF", size=6):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "5")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    ppr.append(pbdr)


def shade_cell(cell, fill="E7E6E6"):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def set_cell_margins(table, top=55, bottom=55, left=105, right=105):
    tblpr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for tag, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.append(mar)


def add_field(paragraph, instruction):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(placeholder)
    run._r.append(fld_end)
    return run


doc = Document()

section = doc.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.top_margin = Cm(2.0)
section.bottom_margin = Cm(1.8)
section.left_margin = Cm(2.2)
section.right_margin = Cm(2.2)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)
normal.font.color.rgb = BLACK
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.15
rpr = normal.element.get_or_add_rPr()
lang = OxmlElement("w:lang")
lang.set(qn("w:val"), "fr-FR")
rpr.append(lang)

h1 = styles["Heading 1"]
h1.font.name = "Calibri"
h1.font.size = Pt(14)
h1.font.bold = True
h1.font.italic = False
h1.font.color.rgb = DARK
h1.paragraph_format.space_before = Pt(16)
h1.paragraph_format.space_after = Pt(6)
h1.paragraph_format.keep_with_next = True

st = styles["List Bullet"]
st.font.name = "Calibri"
st.font.size = Pt(11)
st.paragraph_format.space_after = Pt(4)
st.paragraph_format.line_spacing = 1.15

core = doc.core_properties
core.title = "Description stack technique Payohada"
core.subject = "Technologies, sauvegarde et sécurité de la plateforme Payohada"
core.author = "Payohada"
core.language = "fr-FR"
core.category = "Documentation"


def para(text="", size=11, bold=False, italic=False, color=None, space_after=6,
         space_before=0, keep_next=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = 1.15
    pf.keep_with_next = keep_next
    if text:
        run = p.add_run(text)
        set_run_font(run, size=size, bold=bold, italic=italic, color=color)
    return p


def heading(text):
    p = doc.add_paragraph(style="Heading 1")
    run = p.add_run(text)
    set_run_font(run, size=14, bold=True, color=DARK)
    add_bottom_border(p)
    return p


def bullet(lead, rest=""):
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(lead)
    set_run_font(r, size=11, bold=True)
    r = p.add_run(rest)
    set_run_font(r, size=11)
    return p


def add_table(headers, rows, widths, font_size=10):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_cell_margins(table)

    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.width = Cm(widths[i])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shade_cell(cell)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(header)
        set_run_font(run, size=font_size, bold=True)

    trpr = table.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    trpr.append(tbl_header)

    for row_data in rows:
        row = table.add_row()
        trpr = row._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
        for i, value in enumerate(row_data):
            cell = row.cells[i]
            cell.width = Cm(widths[i])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(value)
            set_run_font(run, size=font_size)
    return table


def spacer(size=3):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run()
    set_run_font(run, size=size)
    return p


footer = section.footer
footer.is_linked_to_previous = False
fp = footer.paragraphs[0]
fp.paragraph_format.tab_stops.add_tab_stop(Cm(16.6), WD_TAB_ALIGNMENT.RIGHT)
r = fp.add_run("Payohada — Description stack technique")
set_run_font(r, size=8, color=GRAY)
fp.add_run("\t")
r = fp.add_run("Page ")
set_run_font(r, size=8, color=GRAY)
add_field(fp, " PAGE ")
r = fp.add_run(" / ")
set_run_font(r, size=8, color=GRAY)
add_field(fp, " NUMPAGES ")
for run in fp.runs:
    if run.font.size is None:
        set_run_font(run, size=8, color=GRAY)

# --------------------------------------------------------------------------
# En-tête
# --------------------------------------------------------------------------
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(2)
r = p.add_run("Description stack technique Payohada")
set_run_font(r, size=22, bold=True, color=DARK)

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(12)
r = p.add_run("Technologies, sauvegarde des données et sécurité — octobre 2026")
set_run_font(r, size=10, color=GRAY)
add_bottom_border(p, color="808080", size=8)

# --------------------------------------------------------------------------
# 1. Présentation
# --------------------------------------------------------------------------
heading("1. Une application simple à utiliser")
para(
    "Payohada est une application en ligne de gestion de la paie et des ressources humaines, "
    "destinée aux cabinets comptables, aux entreprises et à leurs salariés. Elle fonctionne "
    "directement dans le navigateur : aucune installation n'est nécessaire, et chacun accède "
    "uniquement à son espace et à ses dossiers."
)
para(
    "Derrière cette simplicité, la plateforme s'appuie sur des technologies reconnues et "
    "éprouvées, choisies pour trois raisons : la rapidité au quotidien, la fiabilité des "
    "données de paie et la sécurité des informations personnelles."
)

# --------------------------------------------------------------------------
# 2. Technologies et avantages
# --------------------------------------------------------------------------
heading("2. Les technologies et ce qu'elles vous apportent")
para(
    "Chaque brique de la plateforme a été retenue pour un bénéfice concret. Les noms techniques "
    "figurent ci-dessous, mais c'est la dernière colonne qui compte pour vous."
)
add_table(
    ["Technologie", "Son rôle", "Vos bénéfices"],
    [
        ["Vue.js / Nuxt.js", "L'interface utilisateur",
         "Application fluide, proche d'un logiciel installé. Un simple navigateur suffit. "
         "Écrans clairs et cohérents, moins d'erreurs de saisie."],
        ["FastAPI", "Le traitement des opérations",
         "Les informations sont vérifiées avant d'être enregistrées : moins d'erreurs. "
         "Les évolutions sont rapides et sans interruption de service."],
        ["Go", "Le moteur de calcul",
         "Bulletins calculés en quelques secondes, même en période de pointe. "
         "Un même bulletin recalculé donne toujours le même résultat. Coûts d'hébergement maîtrisés."],
        ["PostgreSQL", "Le stockage des données",
         "Données fiables, sans perte ni doublon. Chaque client est isolé des autres. "
         "Historique complet et éditions rapides."],
        ["Redis", "L'accélération de l'application",
         "Réactivité conservée même en forte affluence. Absorption des pics de fin de mois. "
         "Freinage des tentatives de connexion abusives."],
    ],
    widths=[3.4, 4.2, 9.2],
)

# --------------------------------------------------------------------------
# 3. Sauvegarde
# --------------------------------------------------------------------------
doc.add_page_break()
heading("3. La sauvegarde des données")
para(
    "Vos données sont copiées automatiquement à deux rythmes, sur deux emplacements différents. "
    "Une copie reste toujours disponible même en cas d'incident sur le serveur principal."
)
add_table(
    ["Type de copie", "Rythme", "Contenu", "Emplacement", "Conservation"],
    [
        ["Quotidienne", "Chaque nuit",
         "Les modifications de la journée",
         "Serveur principal + copie sécurisée chez Amazon (AWS)", "30 jours"],
        ["Hebdomadaire", "Chaque semaine",
         "L'ensemble des données",
         "Amazon (AWS), dans une autre région géographique", "12 semaines"],
    ],
    widths=[2.8, 2.8, 4.4, 5.6, 2.4],
    font_size=9.5,
)
spacer()
bullet("Copies chiffrées, ", "illisibles sans la clé de déchiffrement.")
bullet("Copies protégées, ", "conservées dans un espace dédié où elles ne peuvent être ni supprimées ni altérées.")
bullet("Contrôle et restauration, ", "chaque copie est vérifiée, une alerte signale les échecs et une restauration est testée régulièrement.")

# --------------------------------------------------------------------------
# 4. Sécurité
# --------------------------------------------------------------------------
heading("4. La sécurité")
para(
    "La sécurité combine plusieurs protections indépendantes : l'accès des utilisateurs, le "
    "contrôle du code et des mises à jour, et la surveillance continue de la plateforme."
)
add_table(
    ["Protection", "Solution", "Ce que cela garantit"],
    [
        ["Connexion", "Supabase",
         "Connexion sécurisée, mots de passe protégés, double authentification possible."],
        ["Droits d'accès", "Gestion des rôles",
         "Chaque utilisateur ne voit que ce qui le concerne : son cabinet, son entreprise ou ses bulletins."],
        ["Tests de sécurité", "OWASP ZAP",
         "L'application est testée contre les attaques les plus courantes avant chaque mise à jour."],
        ["Mises à jour", "Chaîne DevSecOps",
         "Chaque version est contrôlée automatiquement avant sa mise en ligne."],
        ["Journal des accès", "ELK",
         "Connexions et actions sensibles sont enregistrées et consultables en cas de besoin."],
        ["Surveillance", "Wazuh",
         "Les serveurs et le réseau sont surveillés en continu ; toute anomalie déclenche une alerte."],
        ["Alertes", "SIEM",
         "Les signaux suspects sont regroupés et traités rapidement par l'équipe technique."],
    ],
    widths=[3.4, 3.6, 9.8],
    font_size=9.5,
)
spacer()
para(
    "En résumé : une application rapide et simple à utiliser, des données de paie fiables et "
    "sauvegardées, des accès strictement contrôlés et une plateforme surveillée en permanence.",
    space_after=2,
)

doc.save("/Users/macbookpro/devspace/logiciel_paie/docs/Description_stack_technique_Payohada.docx")
print("DOCX généré")
