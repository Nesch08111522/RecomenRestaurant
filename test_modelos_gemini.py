import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("Falta GEMINI_API_KEY en el archivo .env")

client = genai.Client(api_key=api_key)

modelos = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
]

print("\n=== PRUEBA DE MODELOS GEMINI ===\n")

for modelo in modelos:
    print(f"Probando: {modelo}")

    try:
        respuesta = client.models.generate_content(
            model=modelo, contents="Responde únicamente: GEMINI FUNCIONA"
        )

        print(f"✅ FUNCIONA: {modelo}")
        print(f"Respuesta: {respuesta.text}")

        print("\nMODELO RECOMENDADO PARA CONFIGURAR:")
        print(f"GEMINI_MODEL={modelo}")
        break

    except Exception as error:
        print(f"❌ ERROR: {modelo}")
        print(f"Tipo: {type(error).__name__}")

        codigo = getattr(error, "code", None)

        if codigo is not None:
            print(f"Código: {codigo}")

        print("-" * 45)

else:
    print(
        "\nNinguno de los modelos probados respondió correctamente. "
        "Revisa los errores y los límites de tu cuenta."
    )
