# -*- coding: utf-8 -*-
"""Portada, índice y resumen ejecutivo."""
from report_lib import (
    para, heading1, heading2, bullets, page_break,
    WD_ALIGN_PARAGRAPH, _set_run, _fmt, Pt,
)


def build(doc):
    # ---------------- PORTADA ----------------
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("UNIVERSIDAD TECNOLÓGICA DEL PERÚ")
    _set_run(r, bold=True, size=Pt(14))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = doc.add_paragraph()
    r = p.add_run("Facultad de Ingeniería — Ingeniería de Sistemas")
    _set_run(r, size=Pt(12))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("SMARTRESTO")
    _set_run(r, bold=True, size=Pt(28))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = doc.add_paragraph()
    r = p.add_run("Plataforma inteligente de descubrimiento, recomendación y comercialización gastronómica")
    _set_run(r, italic=True, size=Pt(13))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("AVANCE DE PROYECTO FINAL 3 (AV3)")
    _set_run(r, bold=True, size=Pt(16))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = doc.add_paragraph()
    r = p.add_run("Curso: Innovación y Transformación Digital")
    _set_run(r, size=Pt(12))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = doc.add_paragraph()
    r = p.add_run("Ciclo: VIII — Sección: 40802 — 2026-1 — Sede Trujillo")
    _set_run(r, size=Pt(12))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("Integrantes")
    _set_run(r, bold=True, size=Pt(12))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    for nombre in [
        "Cabanillas Llontop, Diego Rodrigo — U23217091",
        "Lujan Zavaleta, Wilmer Enrique — U2327306",
        "Paredes Azabache, Miguel Alejandro — U2320068",
        "Sandoval Chacón, Nancy Elizabeth — U23219525",
    ]:
        p = doc.add_paragraph()
        r = p.add_run(nombre)
        _set_run(r, size=Pt(12))
        _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("Docente: Blancas Nuñez, Mitchell Paulo")
    _set_run(r, size=Pt(12))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = doc.add_paragraph()
    r = p.add_run("Noviembre de 2026")
    _set_run(r, size=Pt(12))
    _fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    page_break(doc)

    # ---------------- ÍNDICE ----------------
    heading1(doc, "Índice de contenidos")
    idx = [
        ("Resumen ejecutivo", ""),
        ("1. Modificación del contenido del Avance 2: evolución de SmartResto", ""),
        ("2. Arquitectura general y estructura central (Fase 1)", ""),
        ("3. Selección de tecnologías de transformación digital", ""),
        ("4. Justificación técnica de las tecnologías", ""),
        ("5. Auditoría funcional por fases y módulos (Fases 2 a 6)", ""),
        ("6. Auditoría de inteligencia artificial y algoritmos", ""),
        ("7. Plan de trabajo del proyecto", ""),
        ("8. Desarrollo preliminar y evidencia del avance", ""),
        ("9. Impacto esperado de la solución", ""),
        ("10. Conclusiones parciales y próximos pasos", ""),
        ("Referencias", ""),
        ("Anexos", ""),
    ]
    for t, _ in idx:
        p = doc.add_paragraph()
        r = p.add_run(t)
        _set_run(r, size=Pt(11))
        _fmt(p, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(2))
    page_break(doc)

    # ---------------- RESUMEN EJECUTIVO ----------------
    heading1(doc, "Resumen ejecutivo")
    para(doc,
         "SmartResto nació como una propuesta para reducir la fricción de descubrimiento y decisión "
         "gastronómica de los estudiantes universitarios de Trujillo, ciudad caracterizada por una alta "
         "densidad culinaria y una oferta dispersa en directorios genéricos. El Avance de Proyecto Final 2 "
         "(APF2) delimitó un producto mínimo viable centrado en el perfil del comensal, filtros contextuales "
         "por presupuesto, distrito, modalidad y restricciones alimentarias, y un mecanismo de recomendación "
         "basado en reglas deterministas. Aquella entrega dejó expresamente fuera del alcance los pedidos, "
         "los pagos, las reservas, la interacción por voz y la personalización avanzada.")
    para(doc,
         "El presente avance documenta la transformación de esa propuesta en un ecosistema integrado. La "
         "aplicación se construyó sobre Flask y PostgreSQL gestionado por Supabase, con un esquema relacional "
         "para las entidades canónicas y un almacén de documentos JSONB para las colecciones dinámicas de la "
         "plataforma. El sistema incorpora tres roles operativos —comensal, empresario y administrador— y un "
         "conjunto de módulos que superan el alcance original: catálogo gastronómico con registro inteligente, "
         "radar de descubrimiento automático de negocios, páginas empresariales, marketplace con carrito y "
         "pedidos, recomendación híbrida explicable, inteligencia de negocio y asistencia mediante inteligencia "
         "artificial generativa.")
    para(doc,
         "Este informe audita el código real del repositorio y clasifica cada funcionalidad según su estado: "
         "implementada y probada, implementada con validación externa pendiente, implementación parcial o "
         "perteneciente al roadmap. Se identifican las tecnologías que intervienen en cada capa, su "
         "justificación técnica y sus límites, y se construye la matriz comparativa entre el APF2 y el estado "
         "actual. La evidencia se apoya en la estructura del repositorio, los blueprints y endpoints registrados, "
         "el esquema de base de datos, los modelos de dominio, los archivos de prueba y la ejecución local de la "
         "aplicación.")
    para(doc,
         "El resultado es un sistema que conserva la decisión central del APF2 —la recomendación debe ser "
         "determinista y explicable, sin delegar datos críticos a la inteligencia artificial— y que la extiende "
         "con integraciones de proveedores externos, autenticación y autorización por roles, auditoría y "
         "mecanismos de trazabilidad. Se mantienen, no obstante, limitaciones que el documento declara de "
         "forma expresa: la ausencia de un modelo de aprendizaje automático entrenado con datos propios, la "
         "dependencia de servicios externos cuyos límites y costos deben validarse, y la falta de un piloto con "
         "usuarios reales que permita medir el impacto propuesto.")
    page_break(doc)
