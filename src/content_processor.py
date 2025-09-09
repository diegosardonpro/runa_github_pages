# src/content_processor.py (v3.0)
import os
import json
import requests
from typing import Union
import google.generativeai as genai

# --- CONFIGURACIÓN DE IA ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ADVERTENCIA: No se encontró la GEMINI_API_KEY.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- MODELOS DE IA (centralizados para fácil actualización) ---
PRIMARY_MODEL = 'gemini-1.5-pro' # Usamos 1.5 como base estable
FALLBACK_MODEL = 'gemini-1.5-flash'

# --- PASO 1: CLASIFICACIÓN ---

def get_classification_prompt(url: str) -> str:
    """Retorna el prompt para que la IA clasifique el tipo de contenido de una URL."""
    return (
        f'''Analiza el contenido principal de la siguiente URL y clasifícalo. Responde únicamente con una de las siguientes palabras clave: "ARTICULO_TEXTO", "IMAGEN_UNICA", "GALERIA_IMAGENES", "VIDEO", "OTRO".

URL a analizar: {url}'''
    )

def classify_url_type(url: str, logger) -> str | None:
    """Usa la IA para determinar el tipo de activo en una URL."""
    logger.info(f"Clasificando tipo de activo para la URL: {url}")
    if not GEMINI_API_KEY: return 'ARTICULO_TEXTO' # Simulación si no hay API Key

    prompt = get_classification_prompt(url)
    try:
        model = genai.GenerativeModel(PRIMARY_MODEL)
        response = model.generate_content(prompt)
        asset_type = response.text.strip()
        logger.info(f"URL clasificada como: {asset_type}")
        return asset_type
    except Exception as e:
        logger.error(f"Error durante la clasificación con IA: {e}", exc_info=True)
        return 'OTRO'

# --- PASO 2: EXTRACCIÓN ESPECIALIZADA ---

def get_article_extraction_prompt(url: str) -> str:
    """Retorna el prompt para extraer metadatos de un artículo."""
    return (
        f'''Actúa como un curador de activos experto. Analiza el contenido de la siguiente URL, que ha sido clasificada como ARTICULO_TEXTO, y devuelve un único objeto JSON con la siguiente estructura. La respuesta debe ser solo el JSON, sin texto introductorio ni markdown.

URL a analizar: {url}

Estructura JSON requerida:
{{
  "titulo": "(El título principal del artículo)",
  "resumen": "(Un resumen conciso del contenido)",
  "contenido_html": "(El texto completo del artículo, formateado en párrafos HTML)",
  "tags": "(Una cadena de 5 a 7 palabras clave relevantes, separadas por comas)",
  "url_imagen_extraida": "(La URL completa de la imagen principal. Si no hay, devuelve null)"
}}
'''
    )

def extract_article_metadata(url: str, logger) -> dict | None:
    """Usa la IA para extraer metadatos de un artículo de texto."""
    logger.info(f"Extrayendo metadatos de artículo para la URL: {url}")
    if not GEMINI_API_KEY: return None

    prompt = get_article_extraction_prompt(url)
    try:
        model = genai.GenerativeModel(PRIMARY_MODEL)
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(json_text)
        logger.info("Metadatos de artículo extraídos con éxito.")
        return data
    except Exception as e:
        logger.error(f"Error en la extracción de metadatos de artículo: {e}", exc_info=True)
        return None

# --- FUNCIÓN DE UTILIDAD ---

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
        ext = '.jpg' # Default
        if content_type and 'png' in content_type: ext = '.png'
        elif content_type and 'gif' in content_type: ext = '.gif'
        elif content_type and 'webp' in content_type: ext = '.webp'

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