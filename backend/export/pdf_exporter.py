"""
Musician-Grade Lead Sheet PDF Generator matching professional chord chart standards.
Produces clean, high-contrast, compact lead sheets with yellow-highlighted section labels,
adaptive one-page fitting, and standard vertical pipe separators.
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from xml.sax.saxutils import escape

from backend.models.schemas import SongAnalysis, Bar


# Adaptive layout scaling profiles ordered from most spacious to most compact
PROFILES = [
    # Level 0: Standard spacious (Short songs e.g. Kaattu Thottappol)
    {
        "margin": 36,
        "title_sz": 18,
        "title_lead": 22,
        "info_sz": 10,
        "info_lead": 14,
        "sec_sz": 11,
        "sec_lead": 15,
        "chord_sz": 13.5,
        "chord_lead": 17,
        "sec_gap": 8,
        "pad": 2.0,
        "chord_sep": "  ",
        "header_gap": 10,
    },
    # Level 1: Medium compact (30-50 bars)
    {
        "margin": 32,
        "title_sz": 17,
        "title_lead": 20,
        "info_sz": 9.5,
        "info_lead": 13,
        "sec_sz": 10.5,
        "sec_lead": 14,
        "chord_sz": 12,
        "chord_lead": 15,
        "sec_gap": 6,
        "pad": 1.5,
        "chord_sep": "  ",
        "header_gap": 8,
    },
    # Level 2: High density (60-90 bars e.g. Bekhayali / Radhimaa)
    {
        "margin": 28,
        "title_sz": 16,
        "title_lead": 19,
        "info_sz": 9.0,
        "info_lead": 12,
        "sec_sz": 10.0,
        "sec_lead": 13,
        "chord_sz": 11,
        "chord_lead": 13.5,
        "sec_gap": 4.5,
        "pad": 1.2,
        "chord_sep": "  ",
        "header_gap": 6,
    },
    # Level 3: Extra compact (90-120 bars)
    {
        "margin": 25,
        "title_sz": 15,
        "title_lead": 17,
        "info_sz": 8.5,
        "info_lead": 11,
        "sec_sz": 9.5,
        "sec_lead": 12,
        "chord_sz": 10,
        "chord_lead": 12.5,
        "sec_gap": 3.5,
        "pad": 1.0,
        "chord_sep": "  ",
        "header_gap": 5,
    },
    # Level 4: Maximum single-page compression (Safe readability floor ~9 pt)
    {
        "margin": 24,
        "title_sz": 14,
        "title_lead": 16,
        "info_sz": 8.0,
        "info_lead": 10.5,
        "sec_sz": 9.0,
        "sec_lead": 11,
        "chord_sz": 9.0,
        "chord_lead": 11.2,
        "sec_gap": 2.5,
        "pad": 0.8,
        "chord_sep": " ",
        "header_gap": 4,
    },
]


def estimate_pdf_height(analysis: SongAnalysis, p: dict) -> float:
    """Calculates total document vertical height in points for a candidate profile."""
    # Header: title leading + metadata leading + divider gap + header gap
    h = p["title_lead"] + 3 + p["info_lead"] + p["header_gap"]
    for sec in analysis.sections:
        num_rows = (len(sec.bars) + 3) // 4
        if num_rows == 0:
            continue
        row_h = p["chord_lead"] + (2 * p["pad"])
        h += (num_rows * row_h) + p["sec_gap"]
    return h


def format_bar_str(bar: Bar, empty_char: str = "N", chord_sep: str = "  ") -> str:
    """Formats a single musical measure into compact lead-sheet notation with spaces for multi-chord bars."""
    valid_chords = [c for c in bar.chords if c.display != 'N' and c.display.strip()]
    if not valid_chords:
        return empty_char
    
    # Deduplicate consecutive identical chords and handle bass walkdowns
    collapsed = []
    for i, c in enumerate(valid_chords):
        disp = c.display
        if not collapsed:
            collapsed.append(disp)
        else:
            prev_chord = valid_chords[i - 1]
            # Refine unslashed chord if immediately followed by same harmony with slash bass (e.g. Gm -> Gm/F)
            if c.root == prev_chord.root and c.quality == prev_chord.quality and '/' not in prev_chord.display and '/' in disp:
                collapsed[-1] = disp
            elif disp != collapsed[-1]:
                collapsed.append(disp)
                
    if not collapsed:
        return empty_char
    return chord_sep.join(collapsed)


def export_to_pdf(analysis: SongAnalysis, output_path: Path) -> Path:
    """
    Generates a musician-friendly printable chord sheet matching the reference lead sheet format:
    - Adaptive fit-to-page algorithm: always attempts to fit the complete chart onto ONE A4 PAGE.
    - Dynamically reduces vertical spacing, margins, and chord font size in priority order.
    - Yellow-highlighted section tags (Intro:, Pallavi:, CH:, Sec A:, etc.).
    - Compact 4-bar measures with zero spacing: |Bar1|Bar2|Bar3|Bar4|.
    - Slash chords preserved intact.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Measurement-based adaptive fitting: select the most comfortable profile that fits on one page
    selected_p = PROFILES[-1]
    for p in PROFILES:
        usable_h = 841.89 - (2 * p["margin"])
        req_h = estimate_pdf_height(analysis, p)
        if req_h <= usable_h:
            selected_p = p
            break

    # Standard A4 layout with adaptive margins
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=selected_p["margin"],
        rightMargin=selected_p["margin"],
        topMargin=selected_p["margin"],
        bottomMargin=selected_p["margin"]
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'LeadTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=selected_p["title_sz"],
        leading=selected_p["title_lead"],
        textColor=colors.black,
        spaceAfter=2
    )

    info_style = ParagraphStyle(
        'LeadInfo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=selected_p["info_sz"],
        leading=selected_p["info_lead"],
        textColor=colors.black
    )

    sec_label_style = ParagraphStyle(
        'SecLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=selected_p["sec_sz"],
        leading=selected_p["sec_lead"],
        textColor=colors.black
    )

    bars_line_style = ParagraphStyle(
        'BarsLine',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=selected_p["chord_sz"],
        leading=selected_p["chord_lead"],
        textColor=colors.black
    )

    story = []

    # 1. Header (Title, Meter, Tempo, Scale)
    story.append(Paragraph(f"<b>{escape(str(analysis.title))}</b>", title_style))
    meta_line = f"Key: {escape(str(analysis.key.display))} &nbsp; &nbsp; &nbsp; &nbsp; Tempo: {analysis.tempo.bpm:.0f} BPM &nbsp; &nbsp; &nbsp; &nbsp; Time: {escape(str(analysis.meter.display))}"
    story.append(Paragraph(meta_line, info_style))
    story.append(Spacer(1, selected_p["header_gap"]))

    # 2. Sections (2-column layout: Col 0 = Section Label, Col 1 = Compact Bar Line)
    label_width = 80
    bars_width = doc.width - label_width
    col_widths = [label_width, bars_width]

    for sec in analysis.sections:
        # Convert neutral labels to musician-friendly format
        raw_name = sec.name.strip()
        if raw_name.upper().startswith("SECTION "):
            remainder = raw_name[8:].strip()
            if "(Repeat)" in remainder:
                letter = remainder.replace("(Repeat)", "").strip()
                display_name = f"Sec {letter} (Rep):"
            else:
                display_name = f"Sec {remainder}:"
        elif raw_name.upper() == "INTRO":
            display_name = "Intro:"
        elif raw_name.upper() == "OUTRO":
            display_name = "Outro:"
        elif raw_name.upper() in ["CHORUS", "CH"]:
            display_name = "CH:"
        elif not raw_name.endswith(":"):
            display_name = f"{raw_name[:1].upper()}{raw_name[1:]}:"
        else:
            display_name = raw_name

        # Break bars into rows of 4
        bar_rows = []
        for i in range(0, len(sec.bars), 4):
            bar_rows.append(sec.bars[i : i + 4])

        table_data = []

        for r_idx, row_bars in enumerate(bar_rows):
            # Col 0: Section label on row 0 with yellow highlight, blank on subsequent rows
            if r_idx == 0:
                highlighted_text = f'<font backcolor="#ffff00">&nbsp;<b>{escape(str(display_name))}</b>&nbsp;</font>'
                cell_0 = Paragraph(highlighted_text, sec_label_style)
            else:
                cell_0 = Paragraph("", sec_label_style)

            # Col 1: Compact text line with bars: |Gm|Cm7|F/Bb|Bb|
            bars_parts = [format_bar_str(b, chord_sep=selected_p["chord_sep"]) for b in row_bars]
            bars_line_text = f"|{ '|'.join(bars_parts) }|"
            cell_1 = Paragraph(f"<b>{escape(str(bars_line_text))}</b>", bars_line_style)

            table_data.append([cell_0, cell_1])

        if table_data:
            sec_table = Table(table_data, colWidths=col_widths)
            sec_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), selected_p["pad"]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), selected_p["pad"]),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(sec_table)
            story.append(Spacer(1, selected_p["sec_gap"]))

    doc.build(story)
    return output_path
