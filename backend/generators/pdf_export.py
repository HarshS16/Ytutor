"""
Polished PDF exporter for Ytutor study materials.

Renders generated markdown notes, flashcards, and quizzes into a structured
ReportLab PDF with clear hierarchy, tables, bullets, headers, and footers.
"""

import html
import io
import logging
import os
import re
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

PAGE_WIDTH, PAGE_HEIGHT = A4
BRAND = colors.HexColor("#2563EB")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#D7DEE8")
SOFT_BLUE = colors.HexColor("#EFF6FF")
SOFT_SLATE = colors.HexColor("#F8FAFC")


def _register_font(name: str, path: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return True
    except Exception as exc:
        logger.debug("Could not register PDF font %s from %s: %s", name, path, exc)
        return False


FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_MONO = "Courier"

if _register_font("YtutorSans", r"C:\Windows\Fonts\arial.ttf"):
    FONT_REGULAR = "YtutorSans"
if _register_font("YtutorSansBold", r"C:\Windows\Fonts\arialbd.ttf"):
    FONT_BOLD = "YtutorSansBold"


def _clean_text(value: object) -> str:
    """Return text that built-in PDF fonts can render predictably."""
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("â€“", "-").replace("â€”", "-").replace("â€¦", "...")
    text = text.replace("ðŸ”¥", "").replace("ðŸƒ", "")
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()


def _inline_markdown(text: str) -> str:
    """Escape text and support a small markdown subset inside paragraphs."""
    escaped = html.escape(_clean_text(text))
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", rf'<font name="{FONT_MONO}">\1</font>', escaped)
    return escaped


def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontName=FONT_BOLD,
        fontSize=24,
        leading=31,
        alignment=TA_CENTER,
        textColor=INK,
        spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="CoverMeta",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=MUTED,
    ))
    styles.add(ParagraphStyle(
        name="DocSection",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=17,
        leading=22,
        textColor=BRAND,
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="H1",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=16,
        leading=21,
        textColor=INK,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="H3",
        parent=styles["Heading3"],
        fontName=FONT_BOLD,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceBefore=9,
        spaceAfter=4,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontSize=9.2,
        leading=13.5,
        textColor=INK,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="NoteBullet",
        parent=styles["Body"],
        leftIndent=14,
        firstLineIndent=-8,
        bulletIndent=0,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="NoteBulletNested",
        parent=styles["Body"],
        leftIndent=28,
        firstLineIndent=-8,
        bulletIndent=14,
        fontSize=8.8,
        leading=12.5,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["Body"],
        fontSize=8,
        leading=11,
        textColor=MUTED,
    ))
    styles.add(ParagraphStyle(
        name="CardTitle",
        parent=styles["Body"],
        fontName=FONT_BOLD,
        textColor=colors.HexColor("#1D4ED8"),
        spaceAfter=3,
    ))
    return styles


def _page_canvas(title: str):
    clean_title = _clean_text(title)

    def draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.4)
        canvas.line(doc.leftMargin, PAGE_HEIGHT - 0.48 * inch, PAGE_WIDTH - doc.rightMargin, PAGE_HEIGHT - 0.48 * inch)
        canvas.line(doc.leftMargin, 0.45 * inch, PAGE_WIDTH - doc.rightMargin, 0.45 * inch)
        canvas.setFont(FONT_REGULAR, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, 0.27 * inch, "Ytutor AI Study Export")
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 0.27 * inch, f"Page {doc.page}")
        if doc.page > 1:
            canvas.drawString(doc.leftMargin, PAGE_HEIGHT - 0.33 * inch, clean_title[:75])
        canvas.restoreState()

    return draw


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def _table_from_lines(lines: list[str], styles) -> Table | None:
    rows = []
    for line in lines:
        if _is_table_separator(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append([Paragraph(_inline_markdown(cell), styles["Small"]) for cell in cells])

    if not rows:
        return None

    col_count = max(len(row) for row in rows)
    for row in rows:
        while len(row) < col_count:
            row.append(Paragraph("", styles["Small"]))

    available_width = PAGE_WIDTH - 1.5 * inch
    col_widths = [available_width / col_count] * col_count
    table = Table(rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1 if len(rows) > 1 else 0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SOFT_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("BACKGROUND", (0, 1), (-1, -1), SOFT_SLATE),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _flush_table(story: list, table_lines: list[str], styles) -> None:
    if not table_lines:
        return
    table = _table_from_lines(table_lines, styles)
    if table:
        story.append(Spacer(1, 4))
        story.append(table)
        story.append(Spacer(1, 8))
    table_lines.clear()


def _append_markdown(story: list, markdown: str, styles) -> None:
    table_lines: list[str] = []

    for raw_line in _clean_text(markdown).split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if _is_table_row(stripped):
            table_lines.append(stripped)
            continue

        _flush_table(story, table_lines, styles)

        if not stripped:
            story.append(Spacer(1, 4))
            continue

        if stripped.startswith("# "):
            story.append(Paragraph(_inline_markdown(stripped[2:]), styles["H1"]))
        elif stripped.startswith("## "):
            text = stripped[3:]
            if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?-\d{1,2}:\d{2}(?::\d{2})?", text):
                story.append(KeepTogether([
                    Spacer(1, 6),
                    Paragraph(f"Timestamp {html.escape(text)}", styles["H2"]),
                ]))
            else:
                story.append(Paragraph(_inline_markdown(text), styles["H2"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(_inline_markdown(stripped[4:]), styles["H3"]))
        elif stripped.startswith(">"):
            story.append(Paragraph(_inline_markdown(stripped.lstrip("> ")), styles["Small"]))
        elif re.match(r"^\s{2,}[-*]\s+", line):
            text = re.sub(r"^\s*[-*]\s+", "", line)
            story.append(Paragraph(f"- {_inline_markdown(text)}", styles["NoteBulletNested"]))
        elif re.match(r"^[-*]\s+", stripped):
            text = re.sub(r"^[-*]\s+", "", stripped)
            story.append(Paragraph(f"- {_inline_markdown(text)}", styles["NoteBullet"]))
        elif re.match(r"^\d+\.\s+", stripped):
            story.append(Paragraph(_inline_markdown(stripped), styles["NoteBullet"]))
        elif re.match(r"^-{3,}$", stripped):
            story.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
        else:
            story.append(Paragraph(_inline_markdown(stripped), styles["Body"]))

    _flush_table(story, table_lines, styles)


def _append_title_page(story: list, playlist_title: str, styles, content_counts: dict) -> None:
    story.append(Spacer(1, 1.65 * inch))
    story.append(Paragraph(_inline_markdown(playlist_title), styles["CoverTitle"]))
    story.append(HRFlowable(width="45%", thickness=1.2, color=BRAND, hAlign="CENTER"))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Structured study export", styles["CoverMeta"]))
    story.append(Paragraph("Generated by Ytutor AI", styles["CoverMeta"]))
    story.append(Paragraph(
        f"Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
        styles["CoverMeta"],
    ))
    story.append(Spacer(1, 0.3 * inch))

    summary_rows = [
        [Paragraph("<b>Content</b>", styles["Small"]), Paragraph("<b>Count</b>", styles["Small"])],
        [Paragraph("Study notes", styles["Small"]), Paragraph(str(content_counts.get("notes", 0)), styles["Small"])],
        [Paragraph("Flashcards", styles["Small"]), Paragraph(str(content_counts.get("flashcards", 0)), styles["Small"])],
        [Paragraph("Quiz questions", styles["Small"]), Paragraph(str(content_counts.get("quizzes", 0)), styles["Small"])],
    ]
    table = Table(summary_rows, colWidths=[2.1 * inch, 1.0 * inch], hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SOFT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(PageBreak())


def _append_flashcards(story: list, flashcards: list[dict], styles) -> None:
    story.append(PageBreak())
    story.append(Paragraph("Flashcards", styles["DocSection"]))
    story.append(HRFlowable(width="100%", thickness=0.8, color=BRAND))
    story.append(Spacer(1, 8))

    for i, card in enumerate(flashcards, 1):
        difficulty = _clean_text(card.get("difficulty", "medium")).title()
        topic = _clean_text(card.get("topic", ""))
        q = _inline_markdown(card.get("question", ""))
        a = _inline_markdown(card.get("answer", ""))
        title = f"Q{i}. {q} <font color=\"#64748B\">[{html.escape(difficulty)}{(' - ' + html.escape(topic)) if topic else ''}]</font>"
        story.append(KeepTogether([
            Paragraph(title, styles["CardTitle"]),
            Paragraph(f"<b>Answer:</b> {a}", styles["Body"]),
            Spacer(1, 6),
        ]))


def _append_quizzes(story: list, quizzes: list[dict], styles) -> None:
    story.append(PageBreak())
    story.append(Paragraph("Quiz Questions", styles["DocSection"]))
    story.append(HRFlowable(width="100%", thickness=0.8, color=BRAND))
    story.append(Spacer(1, 8))

    for i, quiz in enumerate(quizzes, 1):
        story.append(Paragraph(f"{i}. {_inline_markdown(quiz.get('question', ''))}", styles["CardTitle"]))
        for opt in quiz.get("options") or []:
            story.append(Paragraph(f"- {_inline_markdown(opt)}", styles["NoteBullet"]))
        story.append(Paragraph(f"<b>Answer:</b> {_inline_markdown(quiz.get('correct_answer', ''))}", styles["Body"]))
        explanation = quiz.get("explanation")
        if explanation:
            story.append(Paragraph(f"<b>Explanation:</b> {_inline_markdown(explanation)}", styles["Body"]))
        story.append(Spacer(1, 8))


def generate_pdf(
    playlist_title: str,
    notes: list[dict] = None,
    flashcards: list[dict] = None,
    quizzes: list[dict] = None,
) -> bytes:
    """
    Generate a polished PDF document from playlist content.
    """
    notes = notes or []
    flashcards = flashcards or []
    quizzes = quizzes or []

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.65 * inch,
        title=_clean_text(playlist_title),
        author="Ytutor AI",
    )

    styles = _get_styles()
    story = []
    _append_title_page(
        story,
        playlist_title,
        styles,
        {"notes": len(notes), "flashcards": len(flashcards), "quizzes": len(quizzes)},
    )

    if notes:
        story.append(Paragraph("Study Notes", styles["DocSection"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=BRAND))
        story.append(Spacer(1, 8))

        for note_index, note in enumerate(notes, 1):
            note_type = _clean_text(note.get("note_type", "detailed")).title()
            if note_index > 1:
                story.append(PageBreak())
            story.append(Paragraph(f"{note_type} Notes", styles["H1"]))
            _append_markdown(story, note.get("content", ""), styles)
            story.append(Spacer(1, 12))

    if flashcards:
        _append_flashcards(story, flashcards, styles)

    if quizzes:
        _append_quizzes(story, quizzes, styles)

    doc.build(
        story,
        onFirstPage=_page_canvas(playlist_title),
        onLaterPages=_page_canvas(playlist_title),
    )
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated PDF: {len(pdf_bytes)} bytes")
    return pdf_bytes
