import pymupdf
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
import json
from backend.models.schemas import SongAnalysis

def format_bar_str(bar):
    valid_chords = [c for c in bar.chords if c.display != 'N']
    if not valid_chords:
        return "—"
    
    # Deduplicate consecutive identical chords and handle bass walkdowns
    collapsed = []
    for i, c in enumerate(valid_chords):
        disp = c.display
        if not collapsed:
            collapsed.append(disp)
        else:
            prev_chord = valid_chords[i-1]
            # Bass walkdown check: same root & quality, with a slash bass
            if c.root == prev_chord.root and c.quality == prev_chord.quality and '/' in disp:
                collapsed[-1] = disp
            elif disp != collapsed[-1]:
                collapsed.append(disp)
                
    if not collapsed:
        return "—"
    return "/".join(collapsed)

def generate_tight_pdf(analysis: SongAnalysis, pdf_path: Path):
    doc = SimpleDocTemplate(
        str(pdf_path),
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

    # 2. Sections
    label_width = 80
    bars_width = doc.width - label_width
    col_widths = [label_width, bars_width]

    for sec in analysis.sections:
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
    print(f"Generated tight PDF: {pdf_path}")

if __name__ == "__main__":
    with open("storage/exports/test_analysis.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    analysis = SongAnalysis.model_validate(data)
    pdf_path = Path("storage/exports/tight_style_v3.pdf")
    generate_tight_pdf(analysis, pdf_path)

    # Render page 1 to PNG
    doc_fitz = pymupdf.open(pdf_path)
    page = doc_fitz[0]
    pix = page.get_pixmap(dpi=150)
    png_path = Path("storage/exports/tight_style_v3_page1.png")
    pix.save(str(png_path))
    print(f"Rendered Page 1 to PNG: {png_path} ({png_path.stat().st_size} bytes)")
