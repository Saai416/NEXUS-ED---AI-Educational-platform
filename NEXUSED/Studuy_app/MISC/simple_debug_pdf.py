import fitz
import os

pdf_path = r"c:\Studuy_app\static\course_materials\04fd8562_test.pdf"

print(f"Testing extraction for: {pdf_path}")

try:
    if os.path.exists(pdf_path):
        doc = fitz.open(pdf_path)
        print(f"Number of Pages: {len(doc)}")
        
        text = ""
        for i, page in enumerate(doc):
            extracted = page.get_text()
            print(f"Page {i+1} extraction length: {len(extracted)}")
            text += extracted + "\n"

        print(f"Total Extraction result length: {len(text)}")
        print("First 500 chars:")
        print(text[:500])
    else:
        print("File not found")
except Exception as e:
    print(f"Error during extraction: {e}")
