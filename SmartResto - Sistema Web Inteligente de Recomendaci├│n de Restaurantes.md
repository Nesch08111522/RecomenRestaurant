# SmartResto - Sistema Web Inteligente de Recomendación de Restaurantes

Sistema web profesional desarrollado con **Python** y **Flask** siguiendo el patrón **MVT**. Este proyecto combina tres paradigmas de programación para ofrecer una experiencia de recomendación personalizada y escalable.

## 🚀 Paradigmas Implementados

1.  **Imperativo / Orientado a Objetos**: Capa de modelos (`models/`) con herencia y métodos CRUD, gestión de sesiones y controladores.
2.  **Funcional**: Motor de procesamiento en `utils/functional.py` utilizando funciones puras, `map`, `filter`, `reduce` y lambdas para cálculos de scores y filtrado.
3.  **Lógico**: Motor de inferencia en `logic/recommender.py` utilizando **pyDatalog** para aplicar reglas de exclusión (restricciones alimenticias) y justificaciones inteligentes.

## 🎨 Características Premium

-   **Interfaz Estilo Airbnb**: Diseño limpio, responsive y enfocado en la usabilidad.
-   **Mapa Interactivo**: Integración con **Leaflet** y **OpenStreetMap** sincronizado con los resultados.
-   **Personalización Total**: Configuración centralizada en `config.py` para cambiar ciudad, colores, moneda y más.
-   **Búsqueda en Tiempo Real**: Filtrado AJAX dinámico sin recarga de página.

## 🛠️ Instalación y Ejecución

1.  Instalar dependencias:
    ```bash
    pip install -r requirements.txt
    ```
2.  Ejecutar la aplicación:
    ```bash
    python app.py
    ```
3.  Acceder a: `http://localhost:5000`

## 📂 Estructura del Proyecto

-   `models/`: Persistencia de datos en JSON.
-   `views/`: Blueprints de Flask para rutas y lógica de vista.
-   `logic/`: Reglas lógicas con pyDatalog.
-   `utils/`: Funciones geográficas y procesamiento funcional.
-   `static/`: Assets (CSS, JS, Imágenes).
-   `templates/`: Plantillas Jinja2.

---
Desarrollado con principios SOLID, DRY y KISS.
