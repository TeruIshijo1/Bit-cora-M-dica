"""Single catalogue used by the EHR and permission editor (no ERP connection)."""


def clinical_format_groups(pt_num="{pt_num}"):
    groups = [
            {
                "area": "Expediente Integral",
                "icono": "FiLayers",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-EXPEDIENTE-COMPLETO",
                        "nombre": "Expediente Clínico Completo (Compilado NOM-004)",
                        "subtitulo": "Documento maestro integral con carátula foliada, notas de evolución, consentimientos, recetas y paraclínicos",
                        "tipo": "Compilado",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-expediente-completo",
                        "paginas": "Integral",
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Urgencias",
                "icono": "FiAlertCircle",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-87/01",
                        "nombre": "Nota de Evolución de Urgencias",
                        "subtitulo": "Documento general con hasta 3 notas consecutivas y firmas normadas",
                        "tipo": "Evolución",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-nota-urgencias",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-01/01",
                        "nombre": "Historia Clínica de Admisión Urgencias",
                        "subtitulo": "Interrogatorio, antecedentes, examen físico inicial y motivo de urgencia",
                        "tipo": "Admisión",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-12/01",
                        "nombre": "Hoja de Clasificación Triage",
                        "subtitulo": "Evaluación rápida de gravedad, signos vitales y asignación de prioridad (Código)",
                        "tipo": "Triage",
                        "activo": False,
                          "paginas": 1,
                          "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-43",
                        "nombre": "Orden de Intubación Endotraqueal / Soporte Ventilatorio",
                        "subtitulo": "Consentimiento informado y orden médica para intubación orotraqueal y ventilación mecánica",
                        "tipo": "Procedimiento",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-43",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Hospitalización",
                "icono": "FiHome",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-24",
                        "nombre": "Nota de Evolución de Hospitalización",
                        "subtitulo": "Seguimiento médico integral continuo en piso / hospitalización",
                        "tipo": "Evolución",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-nota-hospitalizacion",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-88/01",
                        "nombre": "Nota de Ingreso Hospitalario",
                        "subtitulo": "Registro de pase a piso, indicaciones iniciales y plan de hospitalización",
                        "tipo": "Ingreso",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-89/01",
                        "nombre": "Nota de Evolución en Piso",
                        "subtitulo": "Pase de visita matutino y vespertino por médico adscrito",
                        "tipo": "Evolución",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-95/01",
                        "nombre": "Resumen Clínico de Egreso / Alta",
                        "subtitulo": "Epicrisis, diagnóstico de egreso, tratamiento ambulatorio y citas",
                        "tipo": "Alta",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Cirugía y Quirófano",
                "icono": "FiScissors",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-07",
                        "nombre": "Consentimiento Informado para Procedimientos Quirúrgicos",
                        "subtitulo": "Consentimiento informado oficial para procedimientos quirúrgicos, riesgos y alternativas",
                        "tipo": "Legal y Quirúrgico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-07",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-02",
                        "nombre": "Consentimiento Informado para Tratamiento Quirúrgico / Disentimiento",
                        "subtitulo": "Autorización médica y quirúrgica con registro de tratamientos, anestesia y disentimiento",
                        "tipo": "Legal",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-02",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-40/01",
                        "nombre": "Consentimiento Informado Quirúrgico",
                        "subtitulo": "Autorización de procedimiento con firma de paciente, testigo y cirujano",
                        "tipo": "Legal",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-42/01",
                        "nombre": "Nota Preoperatoria",
                        "subtitulo": "Diagnóstico prequirúrgico, plan operatorio y riesgo anestésico",
                        "tipo": "Quirúrgico",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-45/01",
                        "nombre": "Reporte Quirúrgico y Postoperatorio",
                        "subtitulo": "Descripción de la técnica, hallazgos, sangrado y cuenta de gasas",
                        "tipo": "Quirúrgico",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Consulta Externa e Interconsultas",
                "icono": "FiUsers",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-02/01",
                        "nombre": "Historia Clínica de Consulta Externa",
                        "subtitulo": "Expediente ambulatorio por especialidad médica",
                        "tipo": "Consulta",
                        "activo": False,
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-55/01",
                        "nombre": "Nota de Interconsulta Especializada",
                        "subtitulo": "Solicitud y respuesta de valoración por médico especialista",
                        "tipo": "Interconsulta",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            },
            {
                "area": "Servicios Auxiliares y Diagnóstico",
                "icono": "FiActivity",
                "formatos": [
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-70/01",
                        "nombre": "Solicitud de Exámenes de Laboratorio",
                        "subtitulo": "Orden electrónica de análisis clínicos y pruebas especiales",
                        "tipo": "Laboratorio",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-72/01",
                        "nombre": "Solicitud de Gabinete e Imagenología",
                        "subtitulo": "Orden de estudios radiológicos, ultrasonidos y tomografías",
                        "tipo": "Imagen",
                        "activo": False,
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-32/01",
                        "nombre": "Consentimiento Informado para Ecocardiograma Transesofágico",
                        "subtitulo": "Autorización para realización de estudio bajo sedación con apoyo de anestesiólogo cardiovascular",
                        "tipo": "Legal",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-32-01",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-EED",
                        "nombre": "Ecocardiograma de Estrés con Dobutamina",
                        "subtitulo": "Consentimiento informado y hoja de monitoreo hemodinámico",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-eed",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-25",
                        "nombre": "Consentimiento Informado para Revisión Ginecológica, Obstétrica y Consulta Externa",
                        "subtitulo": "Autorización para revisión ginecológica u obstétrica, estudios y procedimientos en consulta externa",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-25",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-34",
                        "nombre": "Consentimiento Informado para Estudio de Mesa Inclinada (Tilt Test)",
                        "subtitulo": "Consentimiento informado y hoja de monitoreo hemodinámico protocolo INICICH",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-34-01",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-12",
                        "nombre": "Consentimiento Revisión Gineco y Obstetricia (Hosp. / Urg.)",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-12 • Consentimiento Informado Hospitalización y Urgencias",
                        "area": "Ginecología y Obstetricia / Urgencias",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-12",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-04",
                        "nombre": "Consentimiento Colocación de Catéter Venoso Central",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-04 • Consentimiento Informado Procedimientos y Cirugía",
                        "area": "Procedimientos / Cirugía",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-04",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-15",
                        "nombre": "Consentimiento Informado para Cesárea / Disentimiento",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-15 • Consentimiento o Negativa Informada",
                        "area": "Ginecología y Obstetricia",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-15",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-08",
                        "nombre": "Consentimiento Diagnóstico en Admisión Continua",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-08 • Tratamiento y procedimientos diagnósticos en admisión continua",
                        "area": "Admisión Continua / Urgencias",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-08",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-11",
                        "nombre": "Consentimiento de No Reanimación (Voluntad Anticipada)",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-11 • Voluntad anticipada y limitación del esfuerzo terapéutico",
                        "area": "Medicina Interna / Urgencias / UCI",
                        "tipo": "Legal y Bioético",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-11",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-19",
                        "nombre": "Consentimiento Informado para Histerectomía",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-19 • Autorización o negativa para intervención quirúrgica de histerectomía",
                        "area": "Ginecología y Obstetricia",
                        "tipo": "Quirúrgico y Legal",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-19",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-15",
                        "nombre": "Egreso Voluntario",
                        "subtitulo": "HE-DIRMED-SINPRO-PLT-15 • Documento formal de alta voluntaria contra opinión médica",
                        "area": "Hospitalización y Urgencias",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-egreso-voluntario-15",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-06",
                        "nombre": "Consentimiento para Autorizar Procedimiento Anestésico",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-06 • Evaluación anestesiológica, riesgos y autorización del acto anestésico",
                        "area": "Anestesiología y Quirófano",
                        "tipo": "Legal y Anestésico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-06",
                        "paginas": 1,
                        "norma": "NOM-004-SSA3-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-CONSUL-PLT-09",
                        "nombre": "Consentimiento Informado para Transfusión de Hemocomponentes",
                        "subtitulo": "HE-DIRMED-CONSUL-PLT-09 • Autorización de transfusión de hemoderivados, riesgos, alternativas y verificación",
                        "area": "Medicina Transfusional / Hospitalización / Urgencias / Quirófano",
                        "tipo": "Legal y Clínico",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-consentimiento-09",
                        "paginas": 1,
                        "firmas_especiales_requeridas": ["BANCO_SANGRE"],
                        "norma": "NOM-004-SSA3-2012 / NOM-253-SSA1-2012"
                    },
                    {
                        "codigo": "HE-DIRMED-SINPRO-PLT-16",
                        "nombre": "Egreso y Resumen Clínico",
                        "subtitulo": "HE-DIRMED-SINPRO-PLT-16 • Resumen clínico de estancia hospitalaria, diagnóstico final, manejo y alta",
                        "area": "Hospitalización / Medicina Interna / Cirugía",
                        "tipo": "Clínico y Legal",
                        "activo": True,
                        "url_pdf": f"/ehr/paciente/{pt_num}/pdf-egreso-resumen-16",
                        "paginas": 2,
                        "norma": "NOM-004-SSA3-2012"
                    }
                ]
            }
        ]
    return [dict(group, formatos=[f for f in group["formatos"] if f.get("activo")]) for group in groups if any(f.get("activo") for f in group["formatos"])]


def clinical_formats():
    result = []
    for group in clinical_format_groups():
        for item in group["formatos"]:
            formatted = dict(item, area=group["area"])
            roles = formatted.get("firmas_especiales_requeridas") or []
            if roles:
                formatted["firmas_especiales_requeridas_labels"] = [
                    {"id": role, "label": special_signature_role_label(role)} for role in roles
                ]
            result.append(formatted)
    return result


def canonical_format_code(code):
    from vertical_signer import resolve_vertical_controller_and_pk
    try:
        controller, _ = resolve_vertical_controller_and_pk(str(code))
        return controller or str(code).strip().upper()
    except (ValueError, KeyError):
        return str(code).strip().upper()


def special_signature_requirements(code):
    """Return explicitly declared nonstandard signer roles for one format."""
    target = canonical_format_code(code)
    for item in clinical_formats():
        if canonical_format_code(item.get("codigo")) == target:
            roles = item.get("firmas_especiales_requeridas") or []
            return list(dict.fromkeys(str(role).strip().upper() for role in roles if str(role).strip()))
    return []


def normalize_signature_role(value):
    """Map area/role labels to the stable uppercase identifier used by signatures."""
    import re
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")


def signature_role_for_account_role(role):
    return normalize_signature_role(role)


def special_signature_role_label(role, role_catalog=None):
    role_key = normalize_signature_role(role)
    roles = role_catalog
    if roles is None:
        try:
            from access_control import CATALOG
            roles = CATALOG.get("roles", [])
        except ImportError:
            roles = []
    match = next((item for item in roles if normalize_signature_role(item.get("id")) == role_key), None)
    if match:
        return match.get("label") or str(role).replace("_", " ").title()
    if role_key == "BANCO_SANGRE":
        return "Banco de Sangre"
    return role_key.replace("_", " ").title()


def format_for_route(path):
    tail = path.rsplit("/", 1)[-1]
    for item in clinical_formats():
        suffix = item.get("url_pdf", "").rsplit("/", 1)[-1]
        if suffix and tail in {suffix, suffix.removeprefix("pdf-")}:
            return item["codigo"]
    aliases = {"consentimiento-15-ev": "HE-DIRMED-SINPRO-PLT-15", "evoluciones-hospitalizacion": "HE-DIRMED-CONSUL-PLT-24"}
    return aliases.get(tail)
