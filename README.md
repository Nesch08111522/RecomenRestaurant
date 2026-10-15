# SmartResto

Aplicación web de recomendaciones y gestión de restaurantes construida con Flask.

## Crear una carta con Qwen

El panel de cada restaurante permite descargar una plantilla Excel o Word, completarla y subirla. SmartResto extrae los datos de los platos en memoria, envía esos datos a Qwen para redactar una introducción y descripciones, y muestra un borrador editable. Solo los platos aprobados por el empresario se agregan a la carta pública.

Para habilitar Qwen en desarrollo local, copia `.env.example` como `.env` y coloca tu clave en `QWEN_API_KEY`. El archivo `.env` está ignorado por Git. En el servidor de producción, configura las mismas variables en el administrador de secretos o el entorno del proceso:

- `QWEN_API_KEY`: API key de Alibaba Cloud Model Studio. También se acepta `DASHSCOPE_API_KEY`.
- `QWEN_BASE_URL`: opcional. Por defecto se usa `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, que requiere una API key de la región Singapur. Si tu clave es de otra región, usa el API Host indicado al crearla y añade `/compatible-mode/v1`.
- `QWEN_MODEL`: opcional; por defecto `qwen-plus`.

Para crear el archivo local desde PowerShell:

```powershell
Copy-Item .env.example .env
```

Después reemplaza el valor de `QWEN_API_KEY` en `.env` por tu clave real y reinicia Flask. Puedes obtener una clave en [Alibaba Cloud Model Studio](https://help.aliyun.com/en/model-studio/get-api-key); cada clave solo funciona con el endpoint de su región.

Instala las dependencias declaradas en `requirements.txt` con `pip install -r requirements.txt`. Mantén la API key únicamente en el entorno del servidor; no la incluyas en el código, las plantillas ni el navegador. Las solicitudes se facturan según la cuenta, el modelo y la región; revisa las [tarifas vigentes](https://help.aliyun.com/en/model-studio/model-pricing).

La integración usa el endpoint de chat compatible con OpenAI de [Alibaba Cloud Model Studio](https://help.aliyun.com/en/model-studio/compatibility-of-openai-with-dashscope). Consulta la [lista de modelos](https://help.aliyun.com/en/model-studio/models) y las [regiones y endpoints](https://help.aliyun.com/en/model-studio/regions/) al configurar la cuenta.
