from fpdf import FPDF
import os
import re

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")


def generate_pdf(title: str, sections: list[tuple[str, str]]) -> bytes:
    pdf = FPDF()
    pdf.add_font("DejaVu", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))
    pdf.add_font("DejaVu", "I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf"))
    pdf.add_page()

    # Document Title
    pdf.set_font("DejaVu", "B", 16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(4)

    fig_counter = 1
    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")

    for section_name, text in sections:
        pdf.set_font("DejaVu", "B", 13)
        pdf.multi_cell(0, 8, section_name)
        pdf.ln(2)

        lines = text.split("\n")
        paragraph_buf = []

        for line in lines:
            img_match = image_pattern.search(line)
            if img_match:
                # Output accumulated text before the image
                if paragraph_buf:
                    pdf.set_font("DejaVu", "", 11)
                    pdf.multi_cell(0, 6, "\n".join(paragraph_buf))
                    pdf.ln(2)
                    paragraph_buf = []

                caption = img_match.group(1)
                img_path = img_match.group(2)

                if os.path.exists(img_path):
                    try:
                        pdf.ln(2)
                        # Render image centered (width 130mm)
                        pdf.image(img_path, x=40, w=130)
                        pdf.ln(2)
                        pdf.set_font("DejaVu", "I", 9)
                        pdf.multi_cell(0, 5, f"Figure {fig_counter}: {caption}", align="C")
                        pdf.ln(4)
                        fig_counter += 1
                    except Exception as e:
                        print(f"Error inserting image {img_path} into PDF: {e}")
            else:
                paragraph_buf.append(line)

        # Output remaining paragraph text
        if paragraph_buf:
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 6, "\n".join(paragraph_buf))
            pdf.ln(4)

    return bytes(pdf.output())
