import os
import logging

try:
    from openai import OpenAI
except ImportError:  # The rest of the web app remains available until requirements are installed.
    OpenAI = None

logger = logging.getLogger(__name__)

class QwenIAError(RuntimeError):
    """Error de configuración o respuesta al consultar Qwen a través de Groq."""


DEFAULT_SYSTEM_PROMPT = (
    "Eres el asistente inteligente de RecomenRestaurant. Da respuestas útiles, "
    "cortas y en español para ayudar a dueños de restaurantes o clientes."
)


def obtener_respuesta_ia(pregunta, system_prompt=None, max_tokens=1200):
    """Consulta el modelo Qwen servido por Groq y devuelve el texto generado."""
    if OpenAI is None:
        raise QwenIAError(
            "Falta el SDK de OpenAI. Instala las dependencias del proyecto con pip install -r requirements.txt."
        )

    api_key = (os.getenv("QWEN_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
    if not api_key or api_key in {"pon_aqui_tu_clave_nueva", "coloca_aqui_tu_api_key"}:
        raise QwenIAError(
            "Qwen/Groq no está configurado. Agrega una clave nueva en QWEN_API_KEY dentro de .env."
        )

    base_url = (os.getenv("QWEN_BASE_URL") or "https://api.groq.com/openai/v1").strip().rstrip("/")
    model = (os.getenv("QWEN_MODEL") or "qwen/qwen3.8-27b").strip()
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=45)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": str(pregunta)},
            ],
            max_tokens=max(1, min(int(max_tokens), 8000)),
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise QwenIAError("Qwen no devolvió una respuesta de texto.")
        return content.strip()
    except QwenIAError:
        raise
    except Exception as exc:
        logger.exception("Error al consultar Qwen/Groq")
        if getattr(exc, "status_code", None) == 429:
            raise QwenIAError(
                "Se alcanzó el límite gratuito de Groq. Inténtalo más tarde."
            ) from exc
        if getattr(exc, "status_code", None) in {401, 403}:
            raise QwenIAError(
                "Groq rechazó la clave. Revócala si fue expuesta y configura una clave nueva en .env."
            ) from exc
        raise QwenIAError(
            "No se pudo conectar con Qwen/Groq. Revisa la clave, el modelo y la conexión."
        ) from exc


def obtener_recomendacion_ia(pregunta):
    """Responde al chatbot sin interrumpir las vistas si el servicio falla."""
    try:
        return obtener_respuesta_ia(pregunta)
    except QwenIAError:
        return "Lo siento, hubo un problema al procesar tu solicitud con la IA."
