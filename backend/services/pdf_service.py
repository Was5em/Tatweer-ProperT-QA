import os
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

# Ensure the local reports output folder exists
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)
    print(f"Created PDF reports output directory at: {REPORTS_DIR}")

def generate_pdf_report(data: dict, filename: str) -> str:
    """
    Renders HTML Jinja2 template and compiles it into a PDF file using xhtml2pdf.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("report_template.html")
    
    # Render HTML content with audit parameters
    html_content = template.render(**data)
    
    pdf_path = os.path.join(REPORTS_DIR, filename)
    
    # Write to local PDF file
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
        
    if pisa_status.err:
        raise Exception(f"xhtml2pdf error compiling report PDF: code {pisa_status.err}")
        
    return pdf_path
