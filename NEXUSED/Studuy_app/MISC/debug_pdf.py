import fitz  # PyMuPDF
import sys

def debug_pdf(path):
    print(f"--- Deep Dive Debugging {path} ---")
    try:
        doc = fitz.open(path)
        print(f"Page Count: {len(doc)}")
        print(f"Metadata: {doc.metadata}")
        
        for i, page in enumerate(doc):
            print(f"\n[Page {i+1}]")
            
            # 1. Text Check
            text = page.get_text()
            print(f"  Text Length: {len(text)}")
            if len(text) > 0:
                print(f"  Sample: {text[:50]}...")
            
            # 2. Image Check
            images = page.get_images(full=True)
            print(f"  Images Found: {len(images)}")
            if images:
                for img in images:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    print(f"    - Image XREF={xref}, Size={base_image['width']}x{base_image['height']}, Ext={base_image['ext']}")
            
            # 3. Font Check
            fonts = page.get_fonts()
            print(f"  Fonts Used: {len(fonts)}")
            for f in fonts:
                print(f"    - {f}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_pdf("test2.pdf")
