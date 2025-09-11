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

        # --- INICIO CAPA 1: FILTRADO ESTRUCTURAL (DOM) ---
        logger.info("Capa 1: Iniciando filtrado estructural para encontrar el cuerpo del artículo.")
        article_body = soup.find('article') or \
                       soup.find('main') or \
                       soup.find(['div', 'section'], class_=re.compile(r'content|post|body|article', re.I))

        if not article_body:
            logger.warning("Capa 1: No se encontró un contenedor de artículo claro. Usando <body> como último recurso.")
            article_body = soup.body
        else:
            logger.info(f"Capa 1: Contenedor de artículo encontrado: <{article_body.name}>.")
        
        image_tags = article_body.find_all('img') if article_body else []
        logger.info(f"Capa 1: Se encontraron {len(image_tags)} etiquetas <img> dentro del contenedor.")
        # --- FIN CAPA 1 ---

        # --- INICIO CAPA 2: FILTRADO HEURÍSTICO (ATRIBUTOS) ---
        logger.info("Capa 2: Iniciando filtrado heurístico de atributos de imagen.")
        urls_potenciales = []
        for img in image_tags:
            src = img.get('src')
            if not src or src.startswith('data:') or '.svg' in src:
                continue

            if any(keyword in src.lower() for keyword in ['logo', 'icon', 'avatar', 'banner', 'badge']):
                logger.info(f"Capa 2: Descartada por palabra clave en URL: {src}")
                continue
            
            try:
                width = int(img.get('width', 0))
                height = int(img.get('height', 0))
                if (width > 0 and width < 250) or (height > 0 and height < 250):
                    logger.info(f"Capa 2: Descartada por dimensiones explícitas pequeñas ({width}x{height}): {src}")
                    continue
            except (ValueError, TypeError):
                pass

            urls_potenciales.append(src)

        unique_image_urls = sorted(list(set(urls_potenciales)), key=urls_potenciales.index)
        logger.info(f"Capa 2: Filtrado heurístico completado. Quedan {len(unique_image_urls)} imágenes potenciales.")
        # --- FIN CAPA 2 ---

        # ... (extracción de metadatos con IA, sin cambios)
        metadata = {"titulo": "Ejemplo", "resumen": "Ejemplo", "tags": "Ejemplo"} # Simplificado

        metadata['contenido_html'] = html_content
        metadata['urls_imagenes'] = unique_image_urls
        
        logger.info(f"Metadatos y {len(unique_image_urls)} URLs de imágenes extraídas.")
        return metadata

    except Exception as e:
        logger.error(f"Error procesando el HTML extraído: {e}", exc_info=True)
        return None

def analyze_image_with_vision(image_url: str, logger) -> str | None:
    logger.info(f"Capa 3: Analizando imagen con IA de visión: {image_url}")
    try:
        if not image_url.startswith(('http://', 'https://')):
             logger.warning(f"URL de imagen inválida o relativa, se omite: {image_url}")
             return None

        model = genai.GenerativeModel(VISION_MODEL)
        
        system_prompt = "Eres un experto analista de contenido visual para un medio periodístico. Tu tarea es analizar una imagen y clasificar su propósito dentro de un artículo. Responde únicamente con un objeto JSON válido sin formato adicional."
        user_prompt = f'''Analiza la imagen. Clasifícala según uno de los siguientes tipos: "fotografia_principal", "grafico_o_diagrama", "captura_de_pantalla", "logo_o_banner", "irrelevante". Determina si es relevante para el contenido principal de un artículo. La descripción debe ser concisa (máximo 15 palabras).

Formato de respuesta JSON requerido:
{{
  "tipo": "uno de los tipos válidos",
  "es_relevante": true/false,
  "descripcion_ia": "Una descripción concisa de la imagen."
}}'''

        with httpx.Client(follow_redirects=True) as client:
            response = client.get(image_url, timeout=30.0)
            response.raise_for_status()
            image_bytes = response.content
        
        image_part = { "mime_type": response.headers['content-type'], "data": image_bytes }

        # El prompt final debe ser una lista de partes
        final_prompt = [system_prompt, user_prompt, image_part]
        
        response = model.generate_content(final_prompt)
        
        json_response_text = response.text.strip().replace('```json', '').replace('```', '')
        logger.info(f"Capa 3: Respuesta JSON de la IA: {json_response_text}")
        
        # Validar que la respuesta es un JSON válido antes de devolverla
        json.loads(json_response_text)
        return json_response_text

    except httpx.RequestError as e:
        logger.error(f"Capa 3: Error de red al descargar la imagen {image_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Capa 3: Error en el análisis de visión para {image_url}: {e}", exc_info=True)
        return None


def download_image(base_url: str, image_url: str, article_html: str, asset_id: int, image_order: int, output_dir: str, logger) -> Union[str, None]:
    if not image_url: return None

    absolute_image_url = urljoin(base_url, image_url)
    logger.info(f"URL de imagen absoluta construida: {absolute_image_url}")

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