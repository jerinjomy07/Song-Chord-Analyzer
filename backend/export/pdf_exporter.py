"""
Musician-Grade Lead Sheet PDF Generator matching professional chord chart standards.
Produces clean, high-contrast, compact lead sheets with yellow-highlighted section labels,
4 connected bars per line, beat-spaced multi-chord measures, and standard vertical pipe separators.
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

from backend.models.schemas import SongAnalysis, Bar


def format_bar_str(bar: Bar, empty_char: str = "—") -> str:
    """Formats a single musical measure into compact lead-sheet notation with '/' for multi-chord bars."""
    valid_chords = [c for c in bar.chords if c.display != 'N']
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
            # Bass walkdown check: same root & quality, with a slash bass (e.g. Gm -> Gm/F)
            if c.root == prev_chord.root and c.quality == prev_chord.quality and '/' in disp:
                collapsed[-1] = disp
            elif disp != collapsed[-1]:
                collapsed.append(disp)
                
    if not collapsed:
        return empty_char
    return "/".join(collapsed)


def export_to_pdf(analysis: SongAnalysis, output_path: Path) -> Path:
    """
    Generates a musician-friendly printable chord sheet matching the reference lead sheet format:
    - Title, meter, tempo, scale header
    - Yellow-highlighted section tags (Intro:, Pallavi:, CH:, Sec A:, etc.)
    - Compact 4-bar measures with zero spacing: |Bar1|Bar2|Bar3|Bar4|
    - Slash separator for multi-chord measures: |C/G|
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Standard A4 layout with clean 40pt margins
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'LeadTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.black,
        spaceAfter=3
    )

    info_style = ParagraphStyle(
        'LeadInfo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.black
    )

    sec_label_style = ParagraphStyle(
        'SecLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.black
    )

    bars_line_style = ParagraphStyle(
        'BarsLine',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.black
    )

    story = []

    # 1. Header (Title, Meter, Tempo, Scale)
    story.append(Paragraph(f"<b>{analysis.title}</b>", title_style))
    story.append(Paragraph(analysis.meter.display, info_style))
    story.append(Paragraph(f"Tempo: {analysis.tempo.bpm:.0f}", info_style))
    scale_str = analysis.key.display.replace(" Major", "").replace(" Minor", "m")
    story.append(Paragraph(f"Scale: {scale_str}", info_style))
    story.append(Spacer(1, 14))

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
            display_name = f"{raw_name.capitalize()}:"
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
                highlighted_text = f'<font backcolor="#ffff00">&nbsp;<b>{display_name}</b>&nbsp;</font>'
                cell_0 = Paragraph(highlighted_text, sec_label_style)
            else:
                cell_0 = Paragraph("", sec_label_style)

            # Col 1: Compact text line with bars: |Gm|Cm7|F/Bb|Bb|
            bars_parts = [format_bar_str(b) for b in row_bars]
            bars_line_text = f"|{ '|'.join(bars_parts) }|"
            cell_1 = Paragraph(f"<b>{bars_line_text}</b>", bars_line_style)

            table_data.append([cell_0, cell_1])

        if table_data:
            sec_table = Table(table_data, colWidths=col_widths)
            sec_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(sec_table)
            story.append(Spacer(1, 8))

    doc.build(story)
    return output_path
