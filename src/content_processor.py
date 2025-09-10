# src/content_processor.py (v3.4 - Playwright)
import os
import json
import re
from typing import Union

# Herramientas de Navegación y Parseo
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import httpx

# Cliente de IA
import google.generativeai as genai

# --- CONFIGURACIÓN DE IA ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ADVERTENCIA: No se encontró la GEMINI_API_KEY.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- MODELOS DE IA ---
TEXT_MODEL = 'gemini-1.5-pro' 
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

# --- EXTRACCIÓN DE ARTÍCULOS (v3.0 con Playwright) ---
def get_article_extraction_prompt_from_html() -> str:
    return (
        f'''Actúa como curador experto. Analiza el siguiente contenido HTML de un artículo y devuelve un JSON. La respuesta debe ser solo el JSON, sin markdown.
Estructura JSON requerida:
{{
  "titulo": "(Título del artículo)",
  "resumen": "(Resumen conciso del contenido)",
  "tags": "(Cadena de 5-7 palabras clave separadas por comas)"
}}
'''
    )

def extract_article_metadata(url: str, logger) -> dict | None:
    logger.info(f"Iniciando extracción con Playwright para: {url}")
    html_content = ''
    try:
        with sync_playwright() as p:
            logger.info("Playwright: Lanzando navegador Chromium...")
            browser = p.chromium.launch(headless=True)
            logger.info("Playwright: Navegador lanzado. Creando nueva página...")
            page = browser.new_page()
            logger.info(f"Playwright: Navegando a la URL: {url}...")
            page.goto(url, wait_until='domcontentloaded', timeout=90000)
            logger.info("Playwright: Navegación inicial completada. Esperando 5s adicionales para renderizado...")
            page.wait_for_timeout(5000)
            logger.info("Playwright: Espera adicional completada. Extrayendo contenido HTML...")
            html_content = page.content()
            logger.info("Playwright: Contenido HTML extraído. Cerrando navegador...")
            browser.close()
        logger.info("Navegación y extracción de HTML completadas con éxito.")
    except Exception as e:
        logger.error(f"Error durante la navegación con Playwright: {e}", exc_info=True)
        return None

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        image_urls = [img.get('src') for img in soup.find_all('img', width=lambda w: not w or int(w) > 100) if img.get('src')]
        unique_image_urls = sorted(list(set(image_urls)), key=image_urls.index)

        model = genai.GenerativeModel(TEXT_MODEL)
        prompt = [get_article_extraction_prompt_from_html(), html_content]
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        metadata = json.loads(json_text)

        metadata['contenido_html'] = html_content
        metadata['urls_imagenes'] = unique_image_urls
        
        logger.info(f"Metadatos y {len(unique_image_urls)} URLs de imágenes extraídas con éxito.")
        return metadata

    except Exception as e:
        logger.error(f"Error procesando el HTML extraído: {e}", exc_info=True)
        return None

# --- ANÁLISIS DE VISIÓN ---
def get_image_analysis_prompt() -> str:
    return (
        """Analiza esta imagen y devuelve un objeto JSON con dos claves: 'tags_visuales_ia' (una cadena de 5-7 palabras clave que describan visualmente la imagen) y 'descripcion_ia' (una frase concisa que describa la escena). La respuesta debe ser solo el JSON, sin markdown."""
    )

def analyze_image_with_vision(image_url: str, logger) -> dict | None:
    logger.info(f"Analizando con IA de Visión la imagen: {image_url[:100]}...")
    if not GEMINI_API_KEY: return None
    try:
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

# --- FUNCIÓN DE DESCARGA DE IMAGEN ---
def download_image(image_url: str, article_html: str, asset_id: int, image_order: int, output_dir: str, logger) -> Union[str, None]:
    if not image_url: return None
    BROWSER_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
        'Referer': 'https://es.mongabay.com/'
    }

    def _attempt_download(url_to_try: str, attempt_name: str):
        if not url_to_try: return None
        logger.info(f"[Intento {attempt_name}] Intentando descarga de: {url_to_try}")
        try:
            with httpx.stream("GET", url_to_try, headers=BROWSER_HEADERS, timeout=20, follow_redirects=True) as response:
                response.raise_for_status()
                content_type = response.headers.get('content-type', '')
                ext = '.jpg'
                if 'png' in content_type: ext = '.png'
                elif 'gif' in content_type: ext = '.gif'
                elif 'webp' in content_type: ext = '.webp'
                filename = f"{asset_id}_{image_order}{ext}"
                os.makedirs(output_dir, exist_ok=True)
                local_path = os.path.join(output_dir, filename)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
                logger.info(f"¡ÉXITO! Imagen guardada en: {local_path}")
                return local_path
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"[Intento {attempt_name}] URL no encontrada (404): {url_to_try}")
            else:
                logger.error(f"[Intento {attempt_name}] Error HTTP: {e}")
            return None
        except Exception as e:
            logger.error(f"[Intento {attempt_name}] Error genérico: {e}")
            return None

    local_path = _attempt_download(image_url, "Directo con Headers")
    if local_path: return local_path

    cleaned_url = re.sub(r'(-\d+x\d+|-scaled|-e\d+)(?=\.\w+($|\?))', '', image_url)
    if cleaned_url != image_url:
        local_path = _attempt_download(cleaned_url, "URL Limpia con Headers")
        if local_path: return local_path
    
    if article_html:
        try:
            soup = BeautifulSoup(article_html, 'html.parser')
            img_tag = soup.find('img', src=lambda s: s and image_url in s)
            if img_tag and img_tag.parent and img_tag.parent.name == 'a':
                parent_link = img_tag.parent.get('href')
                if parent_link and parent_link != '#':
                    logger.info(f"Se encontró un enlace padre: {parent_link}")
                    local_path = _attempt_download(parent_link, "Análisis HTML con Headers")
                    if local_path: return local_path
            else:
                logger.warning("No se encontró una etiqueta <a> padre para la imagen.")
        except Exception as e:
            logger.error(f"Error durante el parseo de HTML: {e}")
    else:
        logger.warning("No se proporcionó HTML para el análisis avanzado.")

    logger.error(f"Todos los intentos de descarga para {image_url} fallaron.")
    return None