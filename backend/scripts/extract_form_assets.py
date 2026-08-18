"""
Extractor Automatizado de Assets para Formatos Hospitalarios (Hospital Escandón)
================================================================================
Uso:
    python extract_form_assets.py "ruta/al/formato_muestra.pdf" [directorio_salida]

Este script procesa un PDF oficial aprobado por Calidad y genera automáticamente:
1. header_completo_oficial.png (600 DPI con marca de agua, cruz y logos institucionales).
2. pie_hes_sin_disenador.png (600 DPI con datos oficiales y eliminación de marcas externas).
3. lateral_hes_oficial_bold.png (600 DPI con engrosamiento y contraste para impresión nítida).
"""

import sys
import os
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFilter


def extract_assets(pdf_path: str, output_dir: str = None):
    if not os.path.exists(pdf_path):
        print(f"[ERROR] No se encontro el archivo: {pdf_path}")
        return False

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(pdf_path), 'Encabezado, pie, lateral')

    os.makedirs(output_dir, exist_ok=True)
    print(f"\n[INFO] Procesando plantilla: {pdf_path}")
    print(f"[INFO] Destino de assets: {output_dir}\n")

    doc = fitz.open(pdf_path)
    page = doc[0]  # Pagina 1 (Letter 612 x 792 pt)

    # ─────────────────────────────────────────────────────────────
    # 1. ENCABEZADO OFICIAL (y: 0 a 90 pt)
    # ─────────────────────────────────────────────────────────────
    rect_head = fitz.Rect(0, 0, 612, 90)
    pix_head = page.get_pixmap(clip=rect_head, dpi=600, alpha=True)
    head_path = os.path.join(output_dir, 'header_completo_oficial.png')
    pix_head.save(head_path)
    print(f"[OK] Encabezado 600 DPI generado: {os.path.basename(head_path)} ({pix_head.width}x{pix_head.height} px)")

    # ─────────────────────────────────────────────────────────────
    # 2. PIE INSTITUCIONAL LIMPIO (y: 742 a 792 pt)
    # ─────────────────────────────────────────────────────────────
    rect_foot = fitz.Rect(0, 742, 612, 792)
    pix_foot = page.get_pixmap(clip=rect_foot, dpi=600, alpha=True)
    foot_img = Image.frombytes("RGBA", [pix_foot.width, pix_foot.height], pix_foot.samples)

    # Limpieza de marca del disenador y texto de pagina estatico
    clean_foot = foot_img.copy()
    draw = ImageDraw.Draw(clean_foot)

    # Borrar marca del disenador (esquina inferior derecha debajo de la barra azul)
    cutoff_x = int(555.0 / 612.0 * clean_foot.width)
    cutoff_y = int(8.0 / 50.0 * clean_foot.height)
    draw.rectangle([(cutoff_x, cutoff_y), (clean_foot.width, clean_foot.height)], fill=(255, 255, 255, 0))

    # Borrar texto de pagina estatico "Pagina 1 de X" para usar numeracion dinamica
    p_x0 = int(495.0 / 612.0 * clean_foot.width)
    p_x1 = int(555.0 / 612.0 * clean_foot.width)
    p_y0 = int(8.0 / 50.0 * clean_foot.height)
    p_y1 = int(25.0 / 50.0 * clean_foot.height)
    draw.rectangle([(p_x0, p_y0), (p_x1, p_y1)], fill=(255, 255, 255, 0))

    foot_path = os.path.join(output_dir, 'pie_hes_sin_disenador.png')
    clean_foot.save(foot_path)
    print(f"[OK] Pie institucional limpio generado: {os.path.basename(foot_path)} ({clean_foot.size[0]}x{clean_foot.size[1]} px)")

    # ─────────────────────────────────────────────────────────────
    # 3. LATERAL FUNDACION ENGROSADO (x: 574..604, y: 110..685)
    # ─────────────────────────────────────────────────────────────
    rect_lat = fitz.Rect(574, 110, 604, 685)
    pix_lat = page.get_pixmap(clip=rect_lat, dpi=600, alpha=True)
    lat_img = Image.frombytes("RGBA", [pix_lat.width, pix_lat.height], pix_lat.samples)

    # Aplicar dilatacion y contraste tipografico
    r, g, b, a = lat_img.split()
    a_bold = a.filter(ImageFilter.MaxFilter(3))
    solid_grey = Image.new('RGB', lat_img.size, (90, 95, 105)) # Gris institucional solido
    bold_lat = Image.merge('RGBA', (solid_grey.split()[0], solid_grey.split()[1], solid_grey.split()[2], a_bold))

    lat_path = os.path.join(output_dir, 'lateral_hes_oficial_bold.png')
    bold_lat.save(lat_path)
    print(f"[OK] Lateral engrosado de alta definicion generado: {os.path.basename(lat_path)} ({bold_lat.size[0]}x{bold_lat.size[1]} px)")

    # Tambien guardamos el logo suelto de referencia
    rect_logo = fitz.Rect(380, 15, 602, 69)
    pix_logo = page.get_pixmap(clip=rect_logo, dpi=600, alpha=True)
    logo_path = os.path.join(output_dir, 'logo_hes_oficial.png')
    pix_logo.save(logo_path)
    print(f"[OK] Logotipo institucional generado: {os.path.basename(logo_path)} ({pix_logo.width}x{pix_logo.height} px)")

    print(f"\n[EXITO] Todos los assets oficiales estan listos para su uso en el motor de PDFs.\n")
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # Por defecto usa la plantilla oficial disponible
        pdf_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Formatos VERTICAL', '87_01_NOTA DE EVOLUCION DE URGENCIAS.pdf'))
        out_dir = None

    extract_assets(pdf_file, out_dir)
