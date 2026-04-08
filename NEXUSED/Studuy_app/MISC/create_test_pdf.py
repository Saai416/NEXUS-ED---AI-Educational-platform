import fitz

def create_valid_pdf(filename="verify_upload_test.pdf"):
    doc = fitz.open()
    page = doc.new_page()
    text = "This is a valid test PDF for the Study App. If you can read this, the upload works!"
    page.insert_text((50, 50), text, fontsize=12)
    doc.save(filename)
    print(f"Created {filename}")

if __name__ == "__main__":
    create_valid_pdf()
