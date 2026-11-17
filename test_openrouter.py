
from dotenv import load_dotenv

load_dotenv(override=True)

from views.ai_routes import _openrouter_json

try:
    result = _openrouter_json([
        {
            "role": "user",
            "content": 'Responde únicamente este JSON: {"ok": true}'
        }
    ])

    print("\nCONEXIÓN EXITOSA")
    print("RESPUESTA:", result)

except Exception as e:
    print("\nERROR DE OPENROUTER")
    print("TIPO:", type(e).__name__)
    print("DETALLE:", str(e))
