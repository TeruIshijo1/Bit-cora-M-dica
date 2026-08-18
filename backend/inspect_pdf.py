import os
import pypdf

pdf_path = r'd:\Escritorio\Bitacora_HES\Formatos VERTICAL\87_01_NOTA DE EVOLUCION DE URGENCIAS.pdf'

try:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"=== PAGE {i+1} ===")
            print(f"Size: {page.width} x {page.height}")
            print(f"Images: {len(page.images)}")
            for img in page.images:
                print(f"  Img: x0={img['x0']:.1f}, top={img['top']:.1f}, x1={img['x1']:.1f}, bottom={img['bottom']:.1f}, w={img['width']:.1f}, h={img['height']:.1f}")
            print(f"Total words: {len(page.extract_words())}")
            for w in page.extract_words()[:20]:
                print(f"  Word: '{w['text']}' @ ({w['x0']:.1f}, {w['top']:.1f}) font={w.get('fontname')} size={w.get('size')}")
except Exception as e:
    print("pdfplumber error/not installed:", e)
