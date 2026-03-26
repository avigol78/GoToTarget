from fpdf import FPDF
import os

class RadarPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Radar GUI Application Documentation', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(markdown_path, output_path):
    pdf = RadarPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    if not os.path.exists(markdown_path):
        print(f"Error: {markdown_path} not found.")
        return

    with open(markdown_path, 'r') as f:
        lines = f.readlines()

    pdf.set_font("Arial", size=12)
    margin = 10
    pdf.set_left_margin(margin)
    pdf.set_right_margin(margin)
    effective_width = pdf.w - 2 * margin

    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue

        if line.startswith('# '):
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 20)
            pdf.multi_cell(effective_width, 15, line[2:], align='L')
            pdf.set_font('Arial', size=12)
        elif line.startswith('## '):
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 16)
            pdf.multi_cell(effective_width, 12, line[3:], align='L')
            pdf.set_font('Arial', size=12)
        elif line.startswith('### '):
            pdf.ln(3)
            pdf.set_font('Arial', 'B', 14)
            pdf.multi_cell(effective_width, 10, line[4:], align='L')
            pdf.set_font('Arial', size=12)
        elif line.startswith('- '):
            pdf.set_x(margin + 5)
            pdf.multi_cell(effective_width - 5, 8, chr(149) + " " + line[2:])
        elif line.startswith('> '):
            pdf.set_font('Arial', 'I', 11)
            pdf.set_text_color(100, 100, 100)
            pdf.set_x(margin + 5)
            pdf.multi_cell(effective_width - 5, 8, line[2:])
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', size=12)
        elif line.startswith('---'):
            pdf.ln(2)
            pdf.line(margin, pdf.get_y(), pdf.w - margin, pdf.get_y())
            pdf.ln(5)
        else:
            pdf.set_x(margin)
            pdf.multi_cell(effective_width, 8, line)

    pdf.output(output_path)
    print(f"PDF generated: {output_path}")

if __name__ == "__main__":
    md_file = "/home/avi/.gemini/antigravity/brain/85fb8b01-2413-4d38-a8bd-5d646cb7fdb9/radar_documentation.md"
    pdf_file = "/home/avi/Projects/Radar/Download-Center-main/Python/Sensor_cfg_TI_mmWave_App/radar_explanation.pdf"
    generate_pdf(md_file, pdf_file)
