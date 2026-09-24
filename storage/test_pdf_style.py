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

def generate_perfect_pdf(analysis: SongAnalysis, pdf_path: Path):
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Title & Metadata styles matching the screenshot exactly
    title_style = ParagraphStyle(
        'LeadTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
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
        leading=14,
        textColor=colors.black
    )

    bar_chord_style = ParagraphStyle(
        'BarChord',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1, # Center
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
    available_width = doc.width
    label_col_width = 85
    bar_col_width = (available_width - label_col_width) / 4.0
    col_widths = [label_col_width, bar_col_width, bar_col_width, bar_col_width, bar_col_width]

    for sec in analysis.sections:
        # Convert neutral labels to musician-friendly format
        raw_name = sec.name.strip()
        if raw_name.upper().startswith("SECTION "):
            display_name = f"Sec {raw_name[8:]}:"
        elif not raw_name.endswith(":"):
            display_name = f"{raw_name.capitalize()}:"
        else:
            display_name = raw_name

        # Break bars into rows of 4
        bar_rows = []
        for i in range(0, len(sec.bars), 4):
            bar_rows.append(sec.bars[i : i + 4])

        table_data = []
        table_style_commands = [
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            # Vertical bar lines (| Bar 1 | Bar 2 | Bar 3 | Bar 4 |)
            ('LINEBEFORE', (1, 0), (1, -1), 1.2, colors.black),
            ('LINEBEFORE', (2, 0), (2, -1), 1.0, colors.black),
            ('LINEBEFORE', (3, 0), (3, -1), 1.0, colors.black),
            ('LINEBEFORE', (4, 0), (4, -1), 1.0, colors.black),
            ('LINEAFTER', (4, 0), (4, -1), 1.2, colors.black),
        ]

        for r_idx, row_bars in enumerate(bar_rows):
            row_cells = []
            # Col 0: Section label on row 0 with yellow highlight, empty string on subsequent rows
            if r_idx == 0:
                highlighted_text = f'<font backcolor="#ffff00">&nbsp;<b>{display_name}</b>&nbsp;</font>'
                row_cells.append(Paragraph(highlighted_text, sec_label_style))
            else:
                row_cells.append(Paragraph("", sec_label_style))

            # Cols 1 to 4: The 4 bars
            for bar in row_bars:
                valid_chords = [c for c in bar.chords if c.display != 'N']
                if not valid_chords:
                    bar_str = "—"
                elif len(valid_chords) == 1:
                    bar_str = valid_chords[0].display
                elif len(valid_chords) == 2:
                    bar_str = f"{valid_chords[0].display}&nbsp;&nbsp;{valid_chords[1].display}"
                else:
                    bar_str = "&nbsp;".join(c.display for c in valid_chords)

                row_cells.append(Paragraph(f"<b>{bar_str}</b>", bar_chord_style))

            # Pad if fewer than 4 bars in row
            while len(row_cells) < 5:
                row_cells.append(Paragraph("&nbsp;", bar_chord_style))

            table_data.append(row_cells)

        if table_data:
            sec_table = Table(table_data, colWidths=col_widths)
            sec_table.setStyle(TableStyle(table_style_commands))
            story.append(sec_table)
            story.append(Spacer(1, 9))

    doc.build(story)
    print(f"Generated test PDF: {pdf_path}")

if __name__ == "__main__":
    with open("storage/exports/test_analysis.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    analysis = SongAnalysis.model_validate(data)
    pdf_path = Path("storage/exports/screenshot_style_test2.pdf")
    generate_perfect_pdf(analysis, pdf_path)

    # Render page 1 to PNG
    doc_fitz = pymupdf.open(pdf_path)
    page = doc_fitz[0]
    pix = page.get_pixmap(dpi=150)
    png_path = Path("storage/exports/screenshot_style_test2_page1.png")
    pix.save(str(png_path))
    print(f"Rendered Page 1 to PNG: {png_path} ({png_path.stat().st_size} bytes)")
