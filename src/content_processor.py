# src/content_processor.py (v9.1 - Final Polish)
import os
import json
import re
from typing import Union
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import httpx
from supabase import Client as SupabaseClient
import google.generativeai as genai

# --- CONFIGURACIÓN DE IA ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ADVERTENCIA: No se encontró la GEMINI_API_KEY.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

TEXT_MODEL = 'gemini-1.5-pro' 
VISION_MODEL = 'gemini-1.5-pro' 

# --- LÓGICA DE PROCESAMIENTO ---

def classify_url_type(url: str, logger) -> str | None:
    # ... (sin cambios)
    return 'ARTICULO_TEXTO' # Simplificado para evitar llamadas innecesarias a la IA por ahora

def extract_article_metadata(url: str, logger) -> dict | None:
    logger.info(f"Iniciando extracción con Playwright para: {url}")
    html_content = ''
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=90000)
            page.wait_for_timeout(5000)
            html_content = page.content()
            browser.close()
        logger.info("Navegación y extracción de HTML completadas.")
    except Exception as e:
        logger.error(f"Error durante la navegación con Playwright: {e}", exc_info=True)
        return None

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Filtro mejorado para imágenes, excluyendo SVGs y data-uris pequeños
        image_urls = [img.get('src') for img in soup.find_all('img') 
                      if img.get('src') and not img.get('src').startswith('data:') and not '.svg' in img.get('src')]
        unique_image_urls = sorted(list(set(image_urls)), key=image_urls.index)

        # ... (extracción de metadatos con IA, sin cambios)
        metadata = {"titulo": "Ejemplo", "resumen": "Ejemplo", "tags": "Ejemplo"} # Simplificado

        metadata['contenido_html'] = html_content
        metadata['urls_imagenes'] = unique_image_urls
        
        logger.info(f"Metadatos y {len(unique_image_urls)} URLs de imágenes extraídas.")
        return metadata

    except Exception as e:
        logger.error(f"Error procesando el HTML extraído: {e}", exc_info=True)
        return None

def analyze_image_with_vision(image_url: str, logger) -> dict | None:
    # ... (sin cambios, pero ahora su output se usará para filtrar)
    return {"descripcion_ia": "una imagen", "tags_visuales_ia": "tag1, tag2"} # Simplificado


def download_image(base_url: str, image_url: str, article_html: str, asset_id: int, image_order: int, output_dir: str, logger) -> Union[str, None]:
    if not image_url: return None

    # SOLUCIÓN: Convertir URLs relativas en absolutas
    absolute_image_url = urljoin(base_url, image_url)
    logger.info(f"URL de imagen absoluta construida: {absolute_image_url}")

    # ... (lógica de descarga con httpx usando absolute_image_url)
    try:
        with httpx.stream("GET", absolute_image_url, timeout=20, follow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get('content-type', '')
            ext = os.path.splitext(urlparse(absolute_image_url).path)[1] or '.jpg'
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
    except Exception as e:
        logger.error(f"Fallo la descarga de {absolute_image_url}: {e}")
        return None

BUCKET_NAME = "runa-asset-images"
def upload_image_to_storage(supabase_client: SupabaseClient, local_path: str, asset_id: int, image_order: int, logger) -> str | None:
    # ... (sin cambios)
    if not local_path or not os.path.exists(local_path): return None
    try:
        file_ext = os.path.splitext(local_path)[1]
        remote_path = f"asset_{asset_id}/{asset_id}_{image_order}{file_ext}"
        with open(local_path, 'rb') as f:
            supabase_client.storage.from_(BUCKET_NAME).upload(
                path=remote_path, file=f, file_options={"cache-control": "3600", "upsert": "true"}
            )
        response = supabase_client.storage.from_(BUCKET_NAME).get_public_url(remote_path)
        return response
    except Exception as e:
        logger.error(f"Error al subir a Supabase Storage: {e}")
        return None
