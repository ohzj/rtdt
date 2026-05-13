---
title: Rtdt
emoji: 🚀
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.14.0
python_version: '3.13'
app_file: app.py
pinned: false
license: mit
short_description: ReadTheDamnTerms
---

# RTDT — Read The Damn Terms 🚀

## 📖 Descripción del proyecto
**RTDT (ReadTheDamnTerms)** es un analizador legal impulsado por Inteligencia Artificial diseñado para traducir Términos de Servicio (ToS) y Políticas de Privacidad complejos a un lenguaje claro, sencillo y accionable. 

**¿Por qué RTDT?** La mayoría de los usuarios aceptan términos y condiciones sin leerlos porque están redactados con jerga legal extensa e incomprensible. RTDT resuelve este problema resumiendo los documentos, identificando "Alertas Rojas" (Red Flags), datos recopilados, derechos a los que el usuario renuncia y cláusulas abusivas o trampas financieras, ayudando a las personas a saber exactamente a qué están accediendo de forma rápida.

## 🛠️ Tecnologías utilizadas
El proyecto está construido sobre un stack moderno de IA y desarrollo web:
- **[Gradio](https://gradio.app/):** Framework para la creación de la interfaz gráfica web interactiva.
- **[LangChain](https://python.langchain.com/):** Orquestación del flujo de la IA y estructuración de los agentes conversacionales.
- **[Google Gemini 2.5 Flash](https://aistudio.google.com/):** Modelo principal de LLM (Large Language Model) para el análisis jurídico, elegido por su velocidad de razonamiento y ventana de contexto.
- **[Tavily API](https://tavily.com/):** Motor de búsqueda integrado para investigar reputación de empresas, demandas o brechas de datos en tiempo real.
- **Python 3.13:** Lenguaje principal del backend.

## 🚀 Instrucciones de instalación y ejecución local

Para correr este proyecto en tu máquina local, sigue los siguientes pasos:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/ohzj/rtdt.git
   cd rtdt
   ```

2. **Crear y activar un entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En macOS/Linux:
   source venv/bin/activate
   ```

3. **Instalar las dependencias:**
   Asegúrate de instalar los requerimientos del proyecto:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar las variables de entorno:**
   Crea un archivo llamado `.env` en la raíz del proyecto basándote en la plantilla y agrega tus claves de API reales:
   ```env
   GOOGLE_API_KEY=tu_google_api_key_aqui
   TAVILY_API_KEY=tu_tavily_api_key_aqui
   ```

5. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```
   La aplicación iniciará un servidor local y estará disponible en tu navegador web en `http://localhost:7860`.

## 🌐 Link a la app desplegada
Puedes probar la aplicación en vivo desplegada en Hugging Face Spaces aquí:
👉 **[RTDT en Hugging Face Spaces](https://huggingface.co/spaces/jhzo/rtdt)**

## 📸 Capturas de pantalla de la app funcionando
*(Nota: Asegúrate de agregar una imagen real en la carpeta `assets` de tu repositorio)*

![Captura de Pantalla RTDT](https://raw.githubusercontent.com/ohzj/rtdt/master/assets/screenshot.png)
*Interfaz principal de RTDT analizando un documento legal, mostrando las métricas y habilitando el chatbot de la parte inferior.*
