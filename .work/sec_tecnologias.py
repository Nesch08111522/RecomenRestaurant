# -*- coding: utf-8 -*-
"""Secciones 3 y 4: selección y justificación de tecnologías."""
from report_lib import (
    para, heading1, heading2, heading3, table, page_break,
)


def build(doc):
    heading1(doc, "3. Selección de tecnologías de transformación digital", page_break=True)
    para(doc,
         "La selección tecnológica de SmartResto se construyó alrededor de una restricción central heredada del "
         "APF2: la recomendación y los datos críticos del comensal —presupuesto, alérgenos y disponibilidad— deben "
         "procesarse con reglas deterministas, mientras la inteligencia artificial generativa actúa como asistencia "
         "que propone y no certifica. A partir de esa restricción se eligieron tecnologías de madurez probada para "
         "cada capa, priorizando la simplicidad de despliegue y la trazabilidad de las decisiones. La Tabla 7 "
         "presenta el inventario completo, conectando cada tecnología con el módulo y la necesidad que resuelve.")
    table(doc,
          "Inventario tecnológico de SmartResto",
          ["Tecnología", "Capa", "Módulos que la utilizan", "Necesidad que resuelve"],
          [
              ["Python 3.12", "Lenguaje", "Todo el backend", "Lenguaje de propósito general con ecosistema para web, datos e IA"],
              ["Flask 3.0", "Framework", "app.py y los 22 blueprints", "Servidor web, enrutamiento, sesiones y plantillas"],
              ["Jinja2", "Plantillas", "templates/", "Renderizado de vistas por rol"],
              ["Flask-Login / sesión", "Seguridad", "utils/security.py, views/auth.py", "Gestión de sesión e identidad del usuario"],
              ["Flask-WTF (CSRF)", "Seguridad", "Todo formulario y API JSON", "Protección contra falsificación de peticiones"],
              ["Werkzeug", "Seguridad", "scripts/create_user.py, auth", "Resumen de contraseñas (hash seguro)"],
              ["PostgreSQL (Supabase)", "Persistencia", "database/", "Almacenamiento relacional y de documentos JSONB"],
              ["psycopg 3", "Acceso a datos", "database/connection.py, repository.py", "Conexión y consultas a PostgreSQL"],
              ["OpenRouter (API)", "IA", "utils/llm_provider.py, ai_routes, admin_ai_routes", "Acceso unificado a modelos generativos compatibles con OpenAI"],
              ["GPT-4o-mini (OpenAI)", "IA", "Búsqueda, chat, copiloto, análisis", "Interpretación de lenguaje natural y análisis de texto"],
              ["Gemini (google-genai)", "IA", "utils/gemini_menu.py, catálogo", "Extracción de cartas e imágenes"],
              ["geopy / Nominatim", "Geografía", "utils/geo.py", "Geocodificación inversa de coordenadas"],
              ["haversine", "Geografía", "utils/geo.py, recomendación", "Cálculo de distancia entre coordenadas"],
              ["pyDatalog", "Lógica", "logic/phase7_recommender.py", "Reglas lógicas declarativas para recomendación"],
              ["pandas / openpyxl", "Datos", "utils/catalog_workbook.py", "Importación de catálogo desde Excel"],
              ["python-docx", "Datos", "utils/menu_documents.py", "Extracción de cartas desde Word"],
              ["Pillow", "Imágenes", "catálogo, sitios", "Validación y normalización de imágenes"],
              ["qrcode", "Catálogo", "views/catalog.py", "Generación de códigos QR por mesa"],
              ["Leaflet 1.9.4", "Frontend", "templates/base.html, js/map.js", "Mapas interactivos y marcadores"],
              ["Chart.js", "Frontend", "paneles de analítica", "Gráficos de indicadores"],
              ["model-viewer", "Frontend", "experiencias 3D", "Visualización de modelos GLB y realidad aumentada"],
              ["Resend / Twilio", "Integración", "utils/password_codes.py", "Envío de códigos de recuperación por correo y SMS"],
              ["Open-Meteo", "Integración", "utils/weather.py", "Datos meteorológicos para el contexto"],
              ["cryptography / python-dotenv", "Infraestructura", "config.py", "Cifrado y carga de variables de entorno"],
          ],
          note="El proveedor de IA configurado es OpenRouter; Gemini se conserva para la extracción histórica de cartas y la generación de imágenes.")

    heading2(doc, "3.1. Tecnologías evaluadas y no incorporadas")
    para(doc,
         "El proceso de selección evaluó alternativas que finalmente no se incorporaron al alcance actual. FastAPI "
         "y Node.js se consideraron para el backend y se descartaron a favor de Flask por la reutilización del "
         "prototipo previo y la simplicidad del monolito modular. PostGIS se omitió porque los cálculos de "
         "distancia requeridos se resuelven con Haversine sobre coordenadas y no justifican la extensión "
         "geoespacial. Docker, la integración continua y el despliegue continuo quedan como trabajo pendiente, al "
         "igual que IoT y Blockchain, que el APF2 descartó para el producto mínimo y que no aportan valor "
         "verificable a las fases actuales.")

    heading1(doc, "4. Justificación técnica de las tecnologías", page_break=True)
    para(doc,
         "Cada tecnología del inventario responde a una necesidad concreta de la arquitectura y se justifica por "
         "sus ventajas, sus límites y la alternativa que desplaza. La Tabla 8 sintetiza la justificación y se "
         "complementa con la argumentación de los párrafos siguientes.")
    table(doc,
          "Justificación técnica, ventajas, limitaciones y alternativas",
          ["Tecnología", "Ventajas", "Limitaciones", "Alternativa descartada"],
          [
              ["Python", "Productividad, ecosistema maduro para datos e IA, legibilidad", "Menor rendimiento frente a lenguajes compilados", "Node.js/TypeScript"],
              ["Flask", "Ligero, explícito, fácil de auditar y probar; patrón de fábrica", "Requiere ensamblar componentes que otros frameworks traen por defecto", "FastAPI, Django"],
              ["PostgreSQL/Supabase", "ACID, JSONB, RLS, índices; gestión administrada", "Dependencia del proveedor; costos al superar el plan gratuito", "MongoDB, MySQL"],
              ["OpenRouter", "Un solo punto para varios modelos; API compatible con OpenAI", "Latencia y costo variables; depende del proveedor", "Groq, llamadas directas a OpenAI"],
              ["GPT-4o-mini", "Bajo costo, multimodal, adecuado para asistencia", "No debe certificar datos críticos; puede alucinar", "Modelos locales"],
              ["Gemini", "Extracción de cartas y generación de imagen", "Requiere clave independiente; límites por uso", "Qwen vía Groq"],
              ["Haversine/Nominatim", "Cálculo local determinista; geocodificación sin PostGIS", "Distancia en línea recta, no ruta real; límite de Nominatim", "PostGIS, Google Maps"],
              ["pyDatalog", "Reglas declarativas explicables y auditable", "No escala a grandes volúmenes; sintaxis propia", "Motor de reglas propio"],
              ["pandas/openpyxl/python-docx", "Importación de documentos ofimáticos", "Depende del formato de entrada", "Carga manual"],
              ["Leaflet", "Libre, ligero, sin clave obligatoria", "Tiles y geocodificación dependen de proveedores", "Google Maps, MapLibre"],
              ["model-viewer", "GLB y AR en navegador sin desarrollo nativo", "Requiere WebGL/WebXR y acceso al CDN", "Three.js a medida"],
          ],
          note="La elección prioriza explicabilidad, simplicidad operativa y control sobre los datos críticos.")

    heading2(doc, "4.1. Por qué Flask sobre las alternativas de backend")
    para(doc,
         "Flask se seleccionó porque ofrece un núcleo mínimo y explícito que permite registrar blueprints por "
         "dominio sin imponer una estructura, lo que favorece el monolito modular descrito en la sección 2 "
         "(Pallets, s. f.). La existencia de un prototipo previo en Flask redujo el costo de migración y el patrón "
         "de fábrica de create_app facilitó la separación entre configuración, validación de arranque y registro "
         "de rutas. Frente a FastAPI, que aporta validación asíncrona y tipado, se priorizó la simplicidad y la "
         "madurez del ecosistema de plantillas y extensiones; la carga asíncrona no era un requisito para el "
         "volumen esperado del proyecto académico.")
    heading2(doc, "4.2. Por qué PostgreSQL y Supabase")
    para(doc,
         "PostgreSQL permite combinar tablas relacionales con documentos JSONB en una misma base, lo que resuelve "
         "la doble necesidad del sistema: entidades con integridad referencial (usuarios, negocios, platos) y "
         "colecciones flexibles que evolucionan con los módulos (The PostgreSQL Global Development Group, s. f.). "
         "La seguridad a nivel de fila y la revocación de permisos a los roles del navegador mantienen los "
         "documentos privados, y Supabase añade la administración del motor sin gestionar la infraestructura "
         "(Supabase, s. f.). La ausencia de PostGIS es una decisión deliberada: la distancia por Haversine sobre "
         "coordenadas normalizadas cubre el radio máximo de diez kilómetros sin extender el esquema.")
    heading2(doc, "4.3. Por qué OpenRouter y los modelos elegidos")
    para(doc,
         "OpenRouter centraliza el acceso a modelos generativos mediante una interfaz compatible con OpenAI, lo "
         "que evita acoplar el código a un único proveedor y permite cambiar el modelo cambiando una variable de "
         "entorno (OpenRouter, s. f.). El modelo configurado para texto y visión es openai/gpt-4o-mini, elegido por "
         "su relación costo-capacidad para tareas de interpretación y análisis asistido (OpenAI, s. f.). Gemini "
         "se reserva para la extracción de cartas y la generación editorial de imágenes, tareas que requieren "
         "capacidad multimodal específica (Google, s. f.). La decisión de no delegar datos críticos a la IA se "
         "materializa en que las respuestas generativas pasan por validaciones deterministas antes de publicarse.")
    heading2(doc, "4.4. Por qué reglas deterministas y pyDatalog")
    para(doc,
         "El recomendador utiliza señales persistidas y reglas explícitas en lugar de un modelo estadístico "
         "entrenado, porque el volumen de interacciones disponible no justifica el entrenamiento y porque la "
         "explicabilidad de cada resultado es un requisito del producto. pyDatalog aporta una sintaxis declarativa "
         "para expresar las reglas de la fase siete y auditar el razonamiento (pyDatalog, s. f.). El recomendador "
         "híbrido complementa estas reglas con puntuación de contenido, contexto y una señal colaborativa que "
         "solo se activa cuando existen suficientes favoritos y reseñas, evitando falsos patrones de arranque en "
         "frío.")
    heading2(doc, "4.5. Por qué Leaflet y los proveedores geográficos")
    para(doc,
         "Leaflet se eligió por ser una biblioteca libre y ligera que no exige clave de acceso para el mapa base, "
         "reduciendo la dependencia de servicios de pago (Leaflet, s. f.). La geocodificación inversa usa "
         "Nominatim con caché y sin ejecutarse en cada búsqueda, y la distancia se calcula con Haversine de forma "
         "determinista. Esta combinación mantiene el cálculo de proximidad dentro del control de la aplicación y "
         "limita las llamadas externas; la obtención de rutas reales y tiempos de viaje sigue dependiendo de "
         "proveedores externos y queda como trabajo pendiente.")
    heading2(doc, "4.6. Por qué la importación ofimática y los visores")
    para(doc,
         "La importación de cartas desde Excel y Word se apoya en pandas, openpyxl y python-docx, que normalizan "
         "los documentos del empresario a estructuras de catálogo antes de la prevalidación (pandas development "
         "team, s. f.). El visor model-viewer permite cargar modelos GLB autocontenidos y activar realidad "
         "aumentada sin desarrollar un motor propio, y delega al negocio la responsabilidad de aportar modelos que "
         "representen sus platos (Google, s. f.). La generación de códigos QR se resuelve con la biblioteca "
         "qrcode, que produce el identificador por mesa que enlaza con la sesión de atención.")
    page_break(doc)
