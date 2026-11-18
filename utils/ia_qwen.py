import logging

from utils.llm_provider import AIUnavailable, settings

logger = logging.getLogger(__name__)

class QwenIAError(RuntimeError):
    """Error de configuración o respuesta al consultar IA a través de OpenRouter."""


DEFAULT_SYSTEM_PROMPT = (
    "Eres el asistente inteligente de RecomenRestaurant. Da respuestas útiles, "
    "cortas y en español para ayudar a dueños de restaurantes o clientes."
)


def obtener_respuesta_ia(pregunta, system_prompt=None, max_tokens=1200):
    """Consulta el modelo configurado en OpenRouter y devuelve el texto generado."""
    try:
        provider = settings()
        with provider.client() as client:
            response = client.chat.completions.create(
                model=provider.model,
                messages=[
                    {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": str(pregunta)},
                ],
                max_tokens=max(1, min(int(max_tokens), 8000)),
                temperature=0.2,
            )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise QwenIAError("El modelo no devolvió una respuesta de texto.")
        return content.strip()
    except AIUnavailable as exc:
        raise QwenIAError("El proveedor de texto no está configurado correctamente.") from exc
    except QwenIAError:
        raise
    except Exception as exc:
        logger.exception("Error al consultar OpenRouter")
        if getattr(exc, "status_code", None) == 429:
            raise QwenIAError(
                "Se alcanzó el límite del proveedor de IA. Inténtalo más tarde."
            ) from exc
        if getattr(exc, "status_code", None) in {401, 403}:
            raise QwenIAError(
                "OpenRouter rechazó la clave. Revócala si fue expuesta y configura una clave nueva en .env."
            ) from exc
        raise QwenIAError(
            "No se pudo conectar con OpenRouter. Revisa la clave, el modelo y la conexión."
        ) from exc
