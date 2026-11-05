"""Boîte à outils de mise en page du manuel d'utilisation payohada.

Le module centralise les styles et les briques réutilisables (titres, encadrés,
tableaux, captures) afin que les trois parties du manuel restent homogènes.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ── Palette de la charte payohada ──────────────────────────────────────────
NAVY_HEX = "01173A"
NAVY = RGBColor(0x01, 0x17, 0x3A)
GREEN_HEX = "177B36"
GREEN = RGBColor(0x17, 0x7B, 0x36)
GREEN_BRIGHT_HEX = "20973D"
SLATE = RGBColor(0x47, 0x55, 0x69)
SLATE_LIGHT = RGBColor(0x64, 0x74, 0x8B)
DARK = RGBColor(0x0F, 0x17, 0x2A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER_HEX = "D9E2EA"
ZEBRA_HEX = "F6F8FB"
INFO_FILL = "EEF3F8"
SUCCESS_FILL = "EDF6EF"
WARNING_FILL = "FDF6E8"
DANGER_FILL = "FBEEEE"


# ── Utilitaires XML ────────────────────────────────────────────────────────
def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _cell_borders(cell, color=BORDER_HEX, size=4) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tc_pr.append(borders)


def _table_borders(table, color=BORDER_HEX, size=4) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl_pr.append(borders)


def _table_layout_fixed(table) -> None:
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)


def _table_cell_margins(table, top=80, bottom=80, left=110, right=110) -> None:
    tbl_pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tbl_pr.append(mar)


def _row_no_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    tr_pr.append(cant)


def _paragraph_bottom_border(paragraph, color=GREEN_HEX, size=12, space=6) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def _add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


# ── Mise en page générale ──────────────────────────────────────────────────
def setup_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(1.9)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(0.9)
    section.footer_distance = Cm(0.8)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = DARK
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.12

    h1 = styles["Heading 1"]
    h1.font.name = "Calibri"
    h1.font.size = Pt(21)
    h1.font.bold = True
    h1.font.color.rgb = NAVY
    h1.paragraph_format.space_before = Pt(0)
    h1.paragraph_format.space_after = Pt(8)
    h1.paragraph_format.keep_with_next = True

    h2 = styles["Heading 2"]
    h2.font.name = "Calibri"
    h2.font.size = Pt(14)
    h2.font.bold = True
    h2.font.color.rgb = NAVY
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(5)
    h2.paragraph_format.keep_with_next = True

    h3 = styles["Heading 3"]
    h3.font.name = "Calibri"
    h3.font.size = Pt(11.5)
    h3.font.bold = True
    h3.font.color.rgb = GREEN
    h3.paragraph_format.space_before = Pt(10)
    h3.paragraph_format.space_after = Pt(3)
    h3.paragraph_format.keep_with_next = True

    quote = styles["Quote"]
    quote.font.name = "Calibri"
    quote.font.size = Pt(10)
    quote.font.italic = True
    quote.font.color.rgb = SLATE

    for name in ("List Bullet", "List Number"):
        style = styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(10.5)
        style.font.color.rgb = DARK
        style.paragraph_format.space_after = Pt(3)

    _setup_header_footer(doc)
    return doc


def _setup_header_footer(doc: Document) -> None:
    section = doc.sections[0]
    section.different_first_page_header_footer = True

    header = section.header
    paragraph = header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Manuel d'utilisation · payohada")
    run.font.name = "Calibri"
    run.font.size = Pt(8)
    run.font.color.rgb = SLATE_LIGHT
    _paragraph_bottom_border(paragraph, color=BORDER_HEX, size=6, space=2)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.paragraph_format.tab_stops.add_tab_stop(Cm(17), WD_TAB_ALIGNMENT.RIGHT)
    left = fp.add_run("payohada — La paie conforme pour l'Afrique de l'Ouest")
    left.font.name = "Calibri"
    left.font.size = Pt(7.5)
    left.font.color.rgb = SLATE_LIGHT
    fp.add_run("\t")
    page_run = fp.add_run("Page ")
    page_run.font.name = "Calibri"
    page_run.font.size = Pt(8)
    page_run.font.color.rgb = SLATE
    _add_field(fp, "PAGE")
    of_run = fp.add_run(" / ")
    of_run.font.size = Pt(8)
    of_run.font.color.rgb = SLATE
    _add_field(fp, "NUMPAGES")


# ── Briques de contenu ─────────────────────────────────────────────────────
def add_spacer(doc: Document, points: float = 8) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.line_spacing = Pt(points)


def add_page_break(doc: Document) -> None:
    doc.add_page_break()


def add_rich(paragraph, text: str, size: float | None = None, color: RGBColor | None = None,
              bold: bool = False, italic: bool = False) -> None:
    """Ajoute du texte en interprétant **gras**."""
    for part in re.split(r"(\*\*[^*]+\*\*)", text):
        if not part:
            continue
        is_bold = part.startswith("**") and part.endswith("**")
        content = part[2:-2] if is_bold else part
        run = paragraph.add_run(content)
        run.bold = bold or is_bold
        run.italic = italic
        if size:
            run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color


def add_heading(doc: Document, text: str, level: int = 2, page_break: bool = False) -> None:
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    if page_break:
        paragraph.paragraph_format.page_break_before = True
    add_rich(paragraph, text)
    if level == 1:
        _paragraph_bottom_border(paragraph, color=GREEN_HEX, size=14, space=6)


def add_title_label(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(2)
    run = paragraph.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(9)
    run.font.color.rgb = GREEN


def add_para(doc: Document, text: str, space_after: float = 5, size: float | None = None,
             color: RGBColor | None = None, italic: bool = False,
             align: WD_ALIGN_PARAGRAPH | None = None) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        paragraph.alignment = align
    add_rich(paragraph, text, size=size, color=color, italic=italic)


def add_lead(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(10)
    add_rich(paragraph, text, size=11.5, color=SLATE)


def add_bullets(doc: Document, items: list[str], size: float = 10.5, style: str = "List Bullet") -> None:
    for item in items:
        paragraph = doc.add_paragraph(style=style)
        paragraph.paragraph_format.space_after = Pt(3)
        add_rich(paragraph, item, size=size)


def add_steps(doc: Document, items: list[str]) -> None:
    for index, item in enumerate(items, start=1):
        paragraph = doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.left_indent = Cm(0.7)
        fmt.first_line_indent = Cm(-0.7)
        fmt.space_after = Pt(4)
        number = paragraph.add_run(f"{index}.  ")
        number.bold = True
        number.font.color.rgb = GREEN
        add_rich(paragraph, item)


def add_table(doc: Document, headers: list[str], rows: list[list[str]],
              widths: list[float] | None = None, font_size: float = 9,
              header_fill: str = NAVY_HEX, zebra: bool = True,
              first_col_bold: bool = False, align_center: bool = False) -> None:
    column_count = len(headers)
    table = doc.add_table(rows=1, cols=column_count)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _table_layout_fixed(table)
    _table_borders(table)
    _table_cell_margins(table)

    if widths is None:
        widths = [17 / column_count] * column_count
    scale = 17.0 / sum(widths)
    widths = [width * scale for width in widths]

    header_row = table.rows[0]
    _row_no_split(header_row)
    # L'en-tête se répète en haut de chaque page si le tableau se poursuit.
    tr_pr = header_row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        cell.width = Cm(widths[index])
        _shade(cell, header_fill)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.keep_with_next = True
        if align_center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(header)
        run.bold = True
        run.font.size = Pt(font_size)
        run.font.color.rgb = WHITE

    for row_index, row in enumerate(rows):
        table_row = table.add_row()
        _row_no_split(table_row)
        for col_index, value in enumerate(row):
            cell = table_row.cells[col_index]
            cell.width = Cm(widths[col_index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if zebra and row_index % 2 == 1:
                _shade(cell, ZEBRA_HEX)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            if align_center:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_rich(paragraph, value, size=font_size)
            if first_col_bold and col_index == 0:
                for run in paragraph.runs:
                    run.bold = True

    add_spacer(doc, 6)


def add_callout(doc: Document, kind: str, label: str, text: str) -> None:
    fills = {"info": INFO_FILL, "success": SUCCESS_FILL, "warning": WARNING_FILL, "danger": DANGER_FILL}
    accents = {"info": NAVY_HEX, "success": GREEN_HEX, "warning": "B7791F", "danger": "B91C1C"}
    fill = fills.get(kind, INFO_FILL)
    accent = accents.get(kind, NAVY_HEX)

    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _table_layout_fixed(table)
    _table_cell_margins(table, top=110, bottom=110, left=150, right=150)
    cell = table.rows[0].cells[0]
    cell.width = Cm(17)
    _shade(cell, fill)
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge, val in (("top", "nil"), ("left", "single"), ("bottom", "nil"), ("right", "nil")):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val)
        if val == "single":
            el.set(qn("w:sz"), "24")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), accent)
        borders.append(el)
    tc_pr.append(borders)

    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(f"{label} — ")
    run.bold = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = NAVY
    add_rich(paragraph, text, size=9.5)
    add_spacer(doc, 6)


def add_figure(doc: Document, path: str | Path, caption: str,
               width_cm: float = 15.8) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(2)
    run = paragraph.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    caption_paragraph = doc.add_paragraph()
    caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_paragraph.paragraph_format.space_after = Pt(10)
    caption_run = caption_paragraph.add_run(caption)
    caption_run.italic = True
    caption_run.font.size = Pt(8.5)
    caption_run.font.color.rgb = SLATE_LIGHT


def add_part_divider(doc: Document, roman: str, title: str, lead: str,
                     chapters: list[str]) -> None:
    add_page_break(doc)
    add_spacer(doc, 60)
    add_title_label(doc, f"Partie {roman}")
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.size = Pt(30)
    run.font.color.rgb = NAVY
    rule = doc.add_paragraph()
    rule.paragraph_format.space_after = Pt(14)
    _paragraph_bottom_border(rule, color=GREEN_HEX, size=18, space=2)
    add_lead(doc, lead)
    add_para(doc, "**Au programme de cette partie :**", size=10.5)
    add_bullets(doc, chapters)


def add_cover(doc: Document, logo_path: str | Path) -> None:
    add_spacer(doc, 46)
    logo_paragraph = doc.add_paragraph()
    logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo_paragraph.add_run().add_picture(str(logo_path), width=Cm(7.4))

    add_spacer(doc, 34)
    label = doc.add_paragraph()
    label.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = label.add_run("GUIDE PRATIQUE PAR RÔLE")
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = GREEN
    run.font.name = "Calibri"

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(4)
    title.paragraph_format.space_after = Pt(2)
    run = title.add_run("Manuel d'utilisation")
    run.bold = True
    run.font.size = Pt(34)
    run.font.color.rgb = NAVY

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Cabinet comptable · Entreprise · Salarié")
    run.font.size = Pt(13)
    run.font.color.rgb = SLATE

    rule = doc.add_paragraph()
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rule.paragraph_format.space_before = Pt(14)
    rule.paragraph_format.space_after = Pt(20)
    _paragraph_bottom_border(rule, color=GREEN_HEX, size=18, space=2)

    roles = doc.add_table(rows=1, cols=3)
    roles.alignment = WD_TABLE_ALIGNMENT.CENTER
    roles.autofit = False
    _table_layout_fixed(roles)
    _table_cell_margins(roles, top=90, bottom=90, left=60, right=60)
    labels = ["Cabinet", "Entreprise", "Salarié"]
    for index, text in enumerate(labels):
        cell = roles.rows[0].cells[index]
        cell.width = Cm(5.5)
        _shade(cell, ZEBRA_HEX)
        _cell_borders(cell, color=BORDER_HEX, size=4)
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = NAVY

    add_spacer(doc, 40)
    info = doc.add_table(rows=3, cols=2)
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    info.autofit = False
    _table_layout_fixed(info)
    rows = [
        ("Version", "1.3"),
        ("Édition", "Novembre 2026"),
        ("Portée", "Utilisateurs de la plateforme payohada"),
    ]
    for row_index, (key, value) in enumerate(rows):
        key_cell, value_cell = info.rows[row_index].cells
        key_cell.width, value_cell.width = Cm(4.5), Cm(9.5)
        for cell in (key_cell, value_cell):
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(1)
        run = key_cell.paragraphs[0].add_run(key)
        run.bold = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = SLATE
        run = value_cell.paragraphs[0].add_run(value)
        run.font.size = Pt(8.5)
        run.font.color.rgb = NAVY

    footer_note = doc.add_paragraph()
    footer_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_note.paragraph_format.space_before = Pt(24)
    run = footer_note.add_run("Document destiné aux utilisateurs — usage interne")
    run.font.size = Pt(8)
    run.italic = True
    run.font.color.rgb = SLATE_LIGHT
