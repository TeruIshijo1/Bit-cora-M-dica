import os
import sys
from typing import Optional, Dict, Any, Tuple

# Import engines
try:
    import pdf_generator
    import pdf_engine_v2
    import pdf_engine_32_01
    import pdf_engine_eed
except ImportError:
    from backend import pdf_generator
    from backend import pdf_engine_v2
    from backend import pdf_engine_32_01
    from backend import pdf_engine_eed

STATIC_PDFS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "pdfs")
os.makedirs(STATIC_PDFS_DIR, exist_ok=True)

def generate_comprobante_atencion_pdf(atencion: Any, match_found: Any, paciente: Any) -> str:
    """Genera el PDF del comprobante de atención médica con firma digital."""
    return pdf_generator.generate_pdf(atencion, match_found, paciente)

def generate_consentimiento_32_01_pdf(pt_num: str, pt_data: dict) -> Tuple[str, str]:
    """Genera el PDF oficial para el consentimiento informado 32/01."""
    pdf_filename = f"consentimiento_32_01_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    pdf_engine_32_01.generate_consentimiento_32_01(pt_data, pdf_path)
    return pdf_path, pdf_filename

def generate_nota_urgencias_pdf(
    pt_num: str, 
    pt_data: dict, 
    evolucion: Optional[int] = None, 
    target_evol: Optional[dict] = None,
    e1: Optional[dict] = None,
    e2: Optional[dict] = None,
    e3: Optional[dict] = None,
    firma_data: Optional[dict] = None
) -> Tuple[str, str]:
    """Genera el PDF oficial de Nota de Evolución de Urgencias (Formato 87/01)."""
    if evolucion is not None:
        pdf_filename = f"nota_urgencias_{pt_num}_evolucion_{evolucion}.pdf"
        pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
        pdf_engine_v2.generate_nota_urgencias(
            pt_data, target_evol, None, None, pdf_path, is_general=False, firma_data=firma_data
        )
    else:
        pdf_filename = f"nota_urgencias_{pt_num}_general.pdf"
        pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
        pdf_engine_v2.generate_nota_urgencias(
            pt_data, e1, e2, e3, pdf_path, is_general=True, firma_data=firma_data
        )
    return pdf_path, pdf_filename

def generate_consentimiento_eed_pdf(pt_num: str, pt_data: dict) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Ecocardiograma de Estrés con Dobutamina."""
    pdf_path = pdf_engine_eed.generar_pdf_eed(pt_data)
    pdf_filename = f"CI_EED_{pt_num}.pdf"
    return pdf_path, pdf_filename

def generate_consentimiento_34_01_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Estudio de Mesa Inclinada (Tilt Test)."""
    import pdf_engine_34_01
    pdf_filename = f"CI_34_01_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    pdf_engine_34_01.generate_consentimiento_34_01(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename

def generate_consentimiento_12_pdf(pt_num: str, pt_data: dict, firma_data: dict = None) -> Tuple[str, str]:
    """Genera el PDF de consentimiento informado para Revisión Ginecológica y Obstétrica (Hosp/Urg)."""
    import pdf_engine_12
    pdf_filename = f"CI_12_{pt_num}.pdf"
    pdf_path = os.path.join(STATIC_PDFS_DIR, pdf_filename)
    pdf_engine_12.generate_consentimiento_12(pt_data, pdf_path, firma_data=firma_data)
    return pdf_path, pdf_filename

