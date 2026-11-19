# -*- coding: utf-8 -*-
"""Helpers para generar el informe AV3 de SmartResto en formato APA 7."""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = "Arial"
SIZE = Pt(11)

_TABLE_COUNTER = {"n": 0}
_FIGURE_COUNTER = {"n": 0}


def _set_run(run, *, bold=False, italic=False, size=SIZE, color=None, font=FONT):
    run.font.name = font
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)
    rFonts.set(qn("w:cs"), font)


def new_document():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = SIZE
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)

    # Numeración de página en la cabecera (derecha)
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = hp.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    _set_run(run, size=Pt(10))
    return doc


def _fmt(p, *, align=None, indent_first=None, space_before=None, space_after=None, keep_with_next=False):
    if align is not None:
        p.alignment = align
    if indent_first is not None:
        p.paragraph_format.first_line_indent = Cm(indent_first)
    if space_before is not None:
        p.paragraph_format.space_before = Pt(space_before)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    if keep_with_next:
        p.paragraph_format.keep_with_next = True


def heading1(doc, text, page_break=False):
    if page_break:
        doc.add_page_break()
    p = doc.add_paragraph()
    r = p.add_run(text)
    _set_run(r, bold=True, size=Pt(13))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=Pt(12), space_after=Pt(6), keep_with_next=True)
    return p


def heading2(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    _set_run(r, bold=True, size=Pt(12))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=Pt(10), space_after=Pt(4), keep_with_next=True)
    return p


def heading3(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    _set_run(r, bold=True, italic=True, size=Pt(11))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=Pt(8), space_after=Pt(2), keep_with_next=True)
    return p


def heading4(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    _set_run(r, bold=True, size=Pt(11))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.LEFT, indent_first=0.5, space_before=Pt(6), space_after=Pt(2), keep_with_next=True)
    return p


def para(doc, text, *, indent_first=0.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold_lead=None, space_after=0):
    p = doc.add_paragraph()
    if bold_lead:
        r0 = p.add_run(bold_lead)
        _set_run(r0, bold=True)
    r = p.add_run(text)
    _set_run(r)
    _fmt(p, align=align, indent_first=indent_first, space_after=space_after)
    return p


def bullets(doc, items, *, indent=0.75):
    for it in items:
        p = doc.add_paragraph()
        r = p.add_run("•  ")
        _set_run(r)
        r2 = p.add_run(it)
        _set_run(r2)
        _fmt(p, align=WD_ALIGN_PARAGRAPH.LEFT, indent_first=0)
        p.paragraph_format.left_indent = Cm(indent)


def _shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def _cell_text(cell, text, *, bold=False, size=Pt(9.5)):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    r = p.add_run(text)
    _set_run(r, bold=bold, size=size)


def table(doc, title, headers, rows, *, note=None, col_widths=None, font_size=Pt(9.5)):
    _TABLE_COUNTER["n"] += 1
    n = _TABLE_COUNTER["n"]
    tp = doc.add_paragraph()
    tr = tp.add_run(f"Tabla {n}")
    _set_run(tr, bold=True, size=Pt(10))
    _fmt(tp, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=Pt(6), space_after=Pt(0), keep_with_next=True)
    ttl = doc.add_paragraph()
    ttlr = ttl.add_run(title)
    _set_run(ttlr, italic=True, size=Pt(10))
    _fmt(ttl, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=Pt(0), space_after=Pt(3), keep_with_next=True)

    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        _cell_text(hdr[i], h, bold=True, size=font_size)
        _shade(hdr[i], "D9E2F3")
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            _cell_text(cells[i], str(val), size=font_size)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    if note:
        np_ = doc.add_paragraph()
        nr = np_.add_run(f"Nota. {note}")
        _set_run(nr, italic=True, size=Pt(9))
        _fmt(np_, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=Pt(2), space_after=Pt(6))
    else:
        sp = doc.add_paragraph()
        _fmt(sp, space_after=Pt(4))
    return t


def figure_note(doc, caption, page_break=False):
    if page_break:
        doc.add_page_break()
    _FIGURE_COUNTER["n"] += 1
    p = doc.add_paragraph()
    r = p.add_run(f"Figura {_FIGURE_COUNTER['n']}")
    _set_run(r, bold=True, size=Pt(10))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=Pt(6), space_after=Pt(0), keep_with_next=True)
    c = doc.add_paragraph()
    cr = c.add_run(caption)
    _set_run(cr, italic=True, size=Pt(10))
    _fmt(c, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=Pt(0), space_after=Pt(8))
    return c


def page_break(doc):
    doc.add_page_break()
