# -*- coding: utf-8 -*-
"""Sección 1: Modificación del contenido del Avance 2 (evolución APF2 -> AV3)."""
from report_lib import (
    para, heading1, heading2, heading3, heading4, bullets, table, page_break,
)


def build(doc):
    heading1(doc, "1. Modificación del contenido del Avance 2", page_break=True)

    heading2(doc, "1.1. Problema original y objetivo del APF2")
    para(doc,
         "El APF2 definió SmartResto como un sistema web de recomendación inteligente orientado a estudiantes "
         "universitarios de Trujillo. El problema identificado era la sobrecarga de información —denominada "
         "infoxicación— que enfrenta el estudiante al decidir dónde comer: canales de difusión tradicionales y "
         "directorios masivos no filtran la oferta según las restricciones reales de tiempo, dinero y salud del "
         "segmento. La investigación preliminar del equipo reportó que el 69,6 % de los usuarios recurre a "
         "plataformas genéricas no contextualizadas y que el 47,8 % invierte entre cinco y diez minutos por "
         "búsqueda manual. Estos porcentajes proceden del material de origen y su interpretación quedó "
         "restringida por la ausencia de una ficha metodológica que documentara muestra, población, fechas, "
         "cuestionario y estrategia de selección.")
    para(doc,
         "El ámbito de innovación se acotó al proceso de descubrimiento y decisión —desde que el estudiante "
         "siente la necesidad de comer hasta que elige un restaurante y un plato— y no a la cocina ni al servicio "
         "presencial. La pregunta de diseño vigente fue cómo ayudar a los estudiantes de Trujillo a encontrar y "
         "comparar opciones compatibles con sus criterios, explicando qué datos están confirmados y cuáles son "
         "desconocidos, y facilitar a los negocios la publicación responsable de su oferta.")

    heading2(doc, "1.2. Alcance del producto mínimo viable en el APF2")
    para(doc,
         "El MVP propuesto en el APF2 incluía, para el estudiante, el registro y perfil mínimo, las preferencias "
         "editables, los filtros contextuales, el catálogo, la ficha de negocio, los motivos de recomendación y "
         "los favoritos. Para el negocio contemplaba el registro guiado, el alta y edición de local y platos, los "
         "ingredientes declarados, el precio, la modalidad y el estado de actualización. Para el administrador "
         "preveía la revisión básica de publicaciones, los estados, los permisos, los reportes y el registro de "
         "cambios. Se excluyeron de forma expresa los pagos, los pedidos, las reservas, la voz, la realidad "
         "aumentada web, la nutrición automatizada, el inventario predictivo, el copiloto de inteligencia "
         "artificial y la analítica avanzada.")
    para(doc,
         "La recomendación debía comenzar con reglas deterministas y explicables. La inteligencia artificial "
         "generativa, el filtrado colaborativo, la predicción, la voz y la realidad aumentada no debían controlar "
         "disponibilidad, precios, ingredientes ni alérgenos; se consideraron evoluciones condicionadas. Esta "
         "decisión se conserva en la implementación actual y constituye el eje que guía la separación entre "
         "reglas de negocio y asistencia generativa en todo el sistema.")

    heading2(doc, "1.3. Evolución del alcance hacia el ecosistema actual")
    para(doc,
         "La implementación posterior transformó la propuesta en un ecosistema que incorpora gestión comercial, "
         "automatización empresarial, códigos QR, pedidos, producción, inventario, fidelización, experiencias "
         "tridimensionales, analítica y funcionalidades inteligentes. El cambio debe entenderse como una "
         "evolución del alcance y no como si todos los módulos hubieran formado parte del MVP original. La "
         "Tabla 1 resume la comparación entre el alcance declarado en el APF2 y el estado verificado en el "
         "código del repositorio.")
    table(doc,
          "Comparación entre el APF2 y el estado actual de SmartResto",
          ["Dimensión", "APF2 (propuesta)", "AV3 (estado verificado)"],
          [
              ["Problema", "Infoxicación y búsqueda dispersa del estudiante universitario",
               "Se mantiene como problema de partida; se amplía a la gestión integral del negocio gastronómico"],
              ["Usuario principal", "Estudiante universitario",
               "Tres roles operativos: comensal, empresario y administrador"],
              ["Negocio", "Proveedor de oferta con panel básico",
               "Empresario con catálogo, mercado, cocina, salón, sitio de marca y analítica"],
              ["Administrador", "Rol operativo sin panel demostrado",
               "Panel con moderación, usuarios, radar de descubrimiento y BI"],
              ["Arquitectura", "Monolito modular propuesto; PostGIS por verificar",
               "Monolito modular Flask con 22 blueprints; PostgreSQL sin PostGIS, cálculos con Haversine"],
              ["Persistencia", "Relacional + PostGIS (alternativa)",
               "Tablas relacionales + almacén JSONB (app_records) con RLS"],
              ["Recomendación", "Reglas deterministas y explicables",
               "Recomendador híbrido determinista: contenido + contexto + colaborativo condicional"],
              ["IA", "Qwen/Gemini vía Groq/Google AI Studio (por verificar)",
               "OpenRouter (GPT-4o-mini) + Gemini; IA generativa asistida, sin certificar datos críticos"],
              ["Pedidos y pagos", "Fuera del MVP",
               "Marketplace con carrito, pedidos y pago simulado"],
              ["Reservas", "Fuera del MVP",
               "Reservas con capacidad compartida y protección transaccional"],
              ["Voz", "Fuera del MVP",
               "Registro de productos por voz en el catálogo"],
              ["3D/AR", "Fuera del MVP (Web-AR)",
               "Carga de modelos GLB y visor model-viewer"],
              ["Despliegue", "Render, Supabase, Vercel/Netlify, Docker (alternativas)",
               "Supabase (base de datos) y servidor Flask local; sin Docker ni CI/CD verificado"],
          ],
          note="La columna AV3 refleja lo comprobado en el código, las rutas y el esquema de base de datos, no una aspiración del roadmap.")

    heading2(doc, "1.4. Observaciones metodológicas del APF2 y su resolución")
    para(doc,
         "La auditoría de la documentación previa identificó cinco observaciones que debían resolverse para "
         "evitar contradicciones entre el APF2 y el AV3. A continuación se describe el tratamiento de cada una.")
    heading3(doc, "1.4.1. Encuestas y ficha técnica")
    para(doc,
         "El APF2 mostró gráficos con quinientas respuestas, pero reconoció la ausencia de ficha técnica de la "
         "investigación. El presente avance no reproduce esos porcentajes como resultados validados: los conserva "
         "únicamente como indicadores comunicados por el equipo y pendientes de documentar muestra, población, "
         "fechas, cuestionario y método de selección. La validación del problema queda condicionada a la "
         "recuperación de esa ficha o a la ejecución de un nuevo instrumento con registro metodológico.")
    heading3(doc, "1.4.2. Entrevistas a empresarios")
    para(doc,
         "El anexo L contenía cuatro referencias a entrevistas sin identificar participantes, fechas, consentimiento, "
         "transcripciones ni hallazgos utilizados. La implementación actual se sustenta en requisitos derivados del "
         "problema y del análisis del equipo; las necesidades empresariales específicas que se asumen para los "
         "módulos de negocio deben confirmarse con entrevistas estructuradas y documentadas.")
    heading3(doc, "1.4.3. Estado del prototipo")
    para(doc,
         "El APF2 describió por una parte un prototipo navegable en Flask y por otra la ausencia de una "
         "aplicación funcional, con pantallas conceptuales. La reconciliación es la siguiente: en el APF2 se "
         "presentaron wireframes estáticos y una arquitectura lógica; la aplicación ejecutable se construyó con "
         "posterioridad y es el objeto de este informe. Ninguna captura de este documento corresponde a mockups: "
         "las rutas, plantillas y endpoints referidos existen en el repositorio y fueron ejecutados localmente.")
    heading3(doc, "1.4.4. Metodología")
    para(doc,
         "El APF2 propuso Design Thinking para la comprensión del contexto y Extreme Programming (XP) para el "
         "desarrollo iterativo, y evaluó LeSS como marco de escalamiento. Se distingue lo analizado de lo "
         "efectivamente aplicado: el desarrollo siguió iteraciones con historias de usuario y pruebas "
         "automatizadas compatibles con XP, mientras que LeSS permanece como evaluación documental sin "
         "aplicación operativa, dado que el equipo no requiere escalamiento multiequipo.")
    heading3(doc, "1.4.5. Tecnologías y costos")
    para(doc,
         "El APF2 planteó Cloud, inteligencia artificial y ciberseguridad como tecnologías pertinentes, descartó "
         "Blockchain e IoT para el MVP y mencionó Render, Supabase, Vercel, Docker y proveedores de IA como "
         "alternativas por verificar. La selección definitiva se documenta en las secciones 3 y 4: Flask como "
         "framework, Supabase/PostgreSQL como único almacenamiento, OpenRouter y Gemini como proveedores de "
         "IA, y bibliotecas deterministas para geolocalización y recomendación. El costo no se asume como cero: "
         "los límites gratuitos y las tarifas por uso de los proveedores deben validarse antes de producción.")

    heading2(doc, "1.5. Matriz comparativa de tecnologías APF2 frente a AV3")
    table(doc,
          "Decisiones tecnológicas: propuesta del APF2 y selección implementada",
          ["Capa", "Propuesta APF2", "Selección implementada", "Motivo del cambio"],
          [
              ["Backend", "FastAPI o Node.js", "Flask 3.0 (Python 3.12)", "Simplicidad del monolito modular y reutilización del prototipo previo"],
              ["Frontend", "Interfaz por rol", "Jinja2 + Leaflet + Chart.js + model-viewer", "Renderizado de servidor coherente con el stack Flask"],
              ["Base de datos", "PostgreSQL/PostGIS", "PostgreSQL (Supabase) sin PostGIS", "Los cálculos de distancia usan Haversine; PostGIS se omite por no requerirse"],
              ["IA de menús", "Qwen/Gemini vía Groq o Google AI Studio", "OpenRouter (GPT-4o-mini) y Gemini", "OpenRouter concentra proveedores compatibles con OpenAI; Gemini se reserva para extracción y generación de imagen"],
              ["Recomendación", "Reglas deterministas", "Recomendador híbrido determinista (Python)", "Se conserva la decisión de explicabilidad; se añade señal colaborativa condicional"],
              ["Despliegue", "Render/Vercel/Docker", "Servidor Flask local; Supabase para datos", "El despliegue productivo y la contenedorización quedan como trabajo pendiente"],
          ],
          note="La columna de cambio justifica por qué la decisión final difiere de las alternativas analizadas; no se descartan las alternativas para fases posteriores.")
    page_break(doc)
