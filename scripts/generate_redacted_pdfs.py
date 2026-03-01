"""Generate redacted PDFs from test_data T4 files.

Usage:
    cd backend
    python ../scripts/generate_redacted_pdfs.py

Outputs redacted PDFs to sample_docs/ with _redacted suffix.
"""
import sys
import os
import glob

# Add backend to path so we can import the redaction service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import fitz  # PyMuPDF

from services.redaction_service import redact_pdf_page_for_form


def redact_pdf(input_path: str, output_path: str) -> None:
    """Open a PDF, redact each page, save to output_path."""
    doc = fitz.open(input_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        form_id = redact_pdf_page_for_form(page)
        print(f"  Page {page_num + 1}: detected form type = {form_id}")
    doc.save(output_path)
    doc.close()
    print(f"  -> Saved: {output_path}")


def main():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    test_data_dir = os.path.join(project_root, "test_data")
    output_dir = os.path.join(project_root, "sample_docs")

    os.makedirs(output_dir, exist_ok=True)

    # Find all PDFs in test_data
    pdf_files = glob.glob(os.path.join(test_data_dir, "**", "*.pdf"), recursive=True)

    if not pdf_files:
        print("No PDF files found in test_data/")
        return

    print(f"Found {len(pdf_files)} PDF(s) to redact\n")

    for pdf_path in sorted(pdf_files):
        rel = os.path.relpath(pdf_path, test_data_dir)
        # e.g. customer_1/T4_2020_Thompson.pdf -> T4_2020_Thompson_redacted.pdf
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        parent_dir = os.path.basename(os.path.dirname(pdf_path))
        out_name = f"{base_name}_redacted.pdf"
        out_path = os.path.join(output_dir, out_name)

        print(f"Redacting: {rel}")
        try:
            redact_pdf(pdf_path, out_path)
        except Exception as e:
            print(f"  ERROR: {e}")
        print()

    print("Done! Redacted PDFs are in sample_docs/")


if __name__ == "__main__":
    main()
