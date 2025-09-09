# src/content_processor.py
import os
import json
import requests
from typing import Union
import google.generativeai as genai

# --- CONFIGURACIÓN DE IA --- 
# v2.1 - Se elimina BeautifulSoup y se delega toda la extracción a la IA.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ADVERTENCIA: No se encontró la GEMINI_API_KEY. La funcionalidad de IA estará desactivada.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

def get_url_processing_prompt(url: str) -> str:
    """
    Retorna el prompt específico para que la IA extraiga y procese el contenido de una URL.
    """
    prompt = (
        f'''Actúa como un curador de activos digitales experto para el proyecto Runa. Tu tarea es analizar el contenido de la siguiente URL y devolver un único objeto JSON. La respuesta debe ser solo el JSON, sin texto introductorio, explicaciones, ni markdown.

URL a analizar: {url}

La estructura del JSON debe ser la siguiente:
{{
  "titulo": "(El título principal del artículo)",
  "resumen": "(Un resumen conciso y bien redactado del contenido en un solo párrafo)",
  "contenido_html": "(El texto completo del artículo, formateado en párrafos HTML. Cada párrafo debe estar envuelto en etiquetas <p>)",
  "tags": "(Una cadena de 5 a 7 palabras clave relevantes, separadas por comas)",
  "url_imagen_original": "(La URL completa y directa de la imagen principal o de portada del artículo. Si no hay una, devuelve null)"
}}
'''
    )
    return prompt

def process_url_with_ai(url: str, logger) -> Union[dict, None]:
    """
    Usa el modelo Gemini para realizar el scraping y enriquecimiento de una URL en un solo paso.
    Implementa una lógica de modelo primario/respaldo según la directiva.
    """
    # Directiva del usuario: usar modelos 2.5
    primary_model_name = 'gemini-2.5-pro'
    fallback_model_name = 'gemini-2.5-flash'
    
    full_prompt = get_url_processing_prompt(url)

    try:
        logger.info(f"Contactando a la API de Gemini con el modelo prioritario: {primary_model_name}...")
        model = genai.GenerativeModel(primary_model_name)
        response = model.generate_content(full_prompt)
    except Exception as e:
        logger.error(f"El modelo '{primary_model_name}' falló. Error: {e}")
        logger.info(f"Reintentando automáticamente con el modelo de respaldo: {fallback_model_name}...")
        try:
            model = genai.GenerativeModel(fallback_model_name)
            response = model.generate_content(full_prompt)
        except Exception as final_e:
            logger.error(f"El modelo de respaldo '{fallback_model_name}' también falló. Error: {final_e}")
            return None

    try:
        # Limpieza robusta para asegurar que el string sea parseable
        json_response_text = response.text.strip()
        # Eliminar el markdown code block si existe
        if json_response_text.startswith("```json"):
            json_response_text = json_response_text[7:-3].strip()
        
        logger.info("Respuesta de la IA recibida. Parseando JSON...")
        data = json.loads(json_response_text)
        logger.info("JSON del activo parseado con éxito.")
        return data
    except Exception as e:
        logger.error(f"Error al parsear la respuesta JSON de la IA: {e}")
        logger.error(f"Respuesta recibida del modelo que causó el error: {response.text}")
        return None

def download_image(image_url: str, asset_id: int, output_dir: str, logger) -> Union[str, None]:
    """Descarga una imagen desde una URL y la guarda localmente."""
    if not image_url:
        logger.warning("No se proporcionó URL de imagen para descargar.")
        return None
    logger.info(f"Iniciando descarga de imagen: {image_url}")
    try:
        response = requests.get(image_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        content_type = response.headers.get('content-type')
        if content_type and 'png' in content_type:
            ext = '.png'
        elif content_type and 'gif' in content_type:
            ext = '.gif'
        elif content_type and 'webp' in content_type:
            ext = '.webp'
        else:
            ext = '.jpg'

        os.makedirs(output_dir, exist_ok=True)
        local_path = os.path.join(output_dir, f"{asset_id}{ext}")
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Imagen guardada exitosamente en: {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Error al descargar la imagen {image_url}: {e}", exc_info=True)
        return None
