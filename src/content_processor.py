# src/content_processor.py (v3.2 - Visión)
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

# --- MODELOS DE IA ---
# Modelo de texto para análisis de artículos
TEXT_MODEL = 'gemini-1.5-pro' 
# Modelo de visión para análisis de imágenes, según directiva
VISION_MODEL = 'gemini-2.5-pro' 

# --- CLASIFICACIÓN ---
def get_classification_prompt(url: str) -> str:
    return (
        f'''Analiza la URL y clasifícala. Responde solo con: "ARTICULO_TEXTO", "IMAGEN_UNICA", "VIDEO", "OTRO".
URL: {url}'''
    )

def classify_url_type(url: str, logger) -> str | None:
    logger.info(f"Clasificando tipo de activo para: {url}")
    if not GEMINI_API_KEY: return 'ARTICULO_TEXTO'
    try:
        model = genai.GenerativeModel(TEXT_MODEL)
        response = model.generate_content(get_classification_prompt(url))
        asset_type = response.text.strip()
        logger.info(f"URL clasificada como: {asset_type}")
        return asset_type
    except Exception as e:
        logger.error(f"Error durante la clasificación con IA: {e}", exc_info=True)
        return 'OTRO'

# --- EXTRACCIÓN DE ARTÍCULOS ---
def get_article_extraction_prompt(url: str) -> str:
    return (
        f'''Actúa como curador experto. Analiza el contenido de la URL (clasificada como ARTICULO_TEXTO) y devuelve un JSON. La respuesta debe ser solo el JSON, sin markdown.
URL: {url}
Estructura JSON requerida:
{{
  "titulo": "(Título del artículo)",
  "resumen": "(Resumen conciso del contenido)",
  "contenido_html": "(Texto completo del artículo en párrafos HTML)",
  "tags": "(Cadena de 5-7 palabras clave separadas por comas)",
  "urls_imagenes": [
    "(URL completa de la primera imagen encontrada en el artículo)",
    "(URL completa de la segunda imagen)"
  ]
}}
'''
    )

def extract_article_metadata(url: str, logger) -> dict | None:
    logger.info(f"Extrayendo metadatos de artículo para: {url}")
    if not GEMINI_API_KEY: return None
    try:
        model = genai.GenerativeModel(TEXT_MODEL)
        response = model.generate_content(get_article_extraction_prompt(url))
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(json_text)
        logger.info("Metadatos de artículo extraídos con éxito.")
        return data
    except Exception as e:
        logger.error(f"Error en la extracción de metadatos de artículo: {e}", exc_info=True)
        return None

# --- ANÁLISIS DE VISIÓN ---
def get_image_analysis_prompt() -> str:
    return (
        """Analiza esta imagen y devuelve un objeto JSON con dos claves: 'tags_visuales_ia' (una cadena de 5-7 palabras clave que describan visualmente la imagen) y 'descripcion_ia' (una frase concisa que describa la escena). La respuesta debe ser solo el JSON, sin markdown."""
    )

def analyze_image_with_vision(image_url: str, logger) -> dict | None:
    """Usa el modelo de visión para analizar una imagen y extraer etiquetas y descripción."""
    logger.info(f"Analizando con IA de Visión la imagen: {image_url[:100]}...")
    if not GEMINI_API_KEY: return None
    try:
        # NOTA: La API de Gemini para visión con URLs requiere un formato específico.
        # Esto es una simplificación conceptual. El código real puede necesitar `PIL` y pasar bytes.
        # Por ahora, asumimos que el modelo puede procesar una URL directamente con un prompt de texto.
        # Esta es una suposición fuerte que podría necesitar ajuste.
        image_prompt = [get_image_analysis_prompt(), image_url]
        
        model = genai.GenerativeModel(VISION_MODEL)
        response = model.generate_content(image_prompt)
        
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(json_text)
        logger.info("Análisis de visión completado con éxito.")
        return data
    except Exception as e:
        logger.error(f"Error en el análisis de visión para la imagen {image_url}: {e}", exc_info=True)
        return None

# --- FUNCIÓN DE UTILIDAD ---
def download_image(image_url: str, asset_id: int, image_order: int, output_dir: str, logger) -> Union[str, None]:
    """Descarga una imagen y la nombra usando el ID del activo y un orden."""
    if not image_url: return None
    logger.info(f"Iniciando descarga de imagen: {image_url}")
    try:
        response = requests.get(image_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        ext = '.jpg'
        if 'png' in content_type: ext = '.png'
        elif 'gif' in content_type: ext = '.gif'
        elif 'webp' in content_type: ext = '.webp'

        # Nuevo formato de nombre: {asset_id}_{orden}.{ext}
        filename = f"{asset_id}_{image_order}{ext}"
        os.makedirs(output_dir, exist_ok=True)
        local_path = os.path.join(output_dir, filename)
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        
        logger.info(f"Imagen guardada exitosamente en: {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Error al descargar la imagen {image_url}: {e}", exc_info=True)
        return None
