# src/content_processor.py (v3.8.5 - Stable Syntax)
import os
import json
import re
import time
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
BUCKET_NAME = "runa-asset-images"

# --- LÓGICA DE PROCESAMIENTO ---

def extract_article_metadata(url: str, logger) -> dict | None:
    logger.info(f"Iniciando extracción con Playwright para: {url}")
    html_content = ''
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=90000)
            
            logger.info("Iniciando desplazamiento para forzar carga de contenido dinámico...")
            scroll_height = page.evaluate("document.body.scrollHeight")
            for i in range(0, scroll_height, 500):
                page.evaluate(f"window.scrollTo(0, {i})")
                time.sleep(0.2)
            page.wait_for_timeout(5000)

            html_content = page.content()
            browser.close()
        logger.info("Navegación y extracción de HTML completadas.")
    except Exception as e:
        logger.error(f"Error durante la navegación con Playwright: {e}", exc_info=True)
        return None

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        final_image_candidates = []

        # Fase A: Captura Prioritaria (og:image)
        logger.info("Fase A: Buscando imagen prioritaria (og:image)...")
        og_tag = soup.find('meta', property='og:image')
        if og_tag and og_tag.get('content'):
            og_image_url = og_tag['content']
            logger.info(f"Imagen prioritaria encontrada: {og_image_url}")
            final_image_candidates.append(og_image_url)
        else:
            logger.info("No se encontró imagen prioritaria (og:image).")

        # Fase B: Captura de Contenido Extensiva
        logger.info("Fase B: Iniciando escaneo de imágenes en el cuerpo del contenido...")
        
        # Capa 1: Filtrado Estructural Inteligente
        logger.info("Capa 1: Iniciando filtrado estructural inteligente...")
        best_container = None
        max_text_len = 0
        candidate_selectors = ['article', 'main', 'div[class*="post"]', 'div[class*="content"]', 'div[class*="body"]', 'div[id*="post"]', 'div[id*="content"]', 'div[id*="body"]']
        for selector in candidate_selectors:
            for container in soup.select(selector):
                text_len = len(container.get_text(strip=True))
                if text_len > max_text_len:
                    max_text_len = text_len
                    best_container = container
        
        article_body = best_container or soup.body

        content_images = []
        # Capa 2: Filtrado Heurístico de <img>
        image_tags = article_body.find_all('img')
        logger.info(f"Capa 2: Encontradas {len(image_tags)} etiquetas <img>.")
        for img in image_tags:
            src = img.get('data-src') or img.get('src')
            if not src or src.startswith('data:') or '.svg' in src: continue
            if any(keyword in src.lower() for keyword in ['logo', 'icon', 'avatar', 'banner', 'badge']): continue
            content_images.append(src)
        
        # Capa 2.1: Búsqueda en CSS (background-image)
        logger.info("Capa 2.1: Buscando imágenes en atributos 'style'...")
        background_tags = article_body.select('[style*="background-image"]')
        for tag in background_tags:
            style = tag.get('style', '')
            try:
                url_part = style.split('url(')[1].split(')')[0]
                bg_img_url = url_part.replace('"', '').replace("'", "").strip()
                if bg_img_url and not bg_img_url.startswith('data:'):
                    content_images.append(bg_img_url)
            except IndexError:
                continue

        # Capa 2.2: Búsqueda en JSON
        logger.info("Capa 2.2: Buscando imágenes en bloques de datos JSON...")
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                try:
                    # Regex simplificado para máxima estabilidad
                    found_urls = re.findall(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)', script.string)
                    if found_urls:
                        content_images.extend(found_urls)
                except Exception: continue

        # Fase C: Combinación y Deduplicación
        logger.info("Fase C: Combinando y depurando listas de imágenes...")
        for img_url in content_images:
            if img_url not in final_image_candidates:
                final_image_candidates.append(img_url)

        unique_images = []
        seen_image_paths = set()
        for img_url in final_image_candidates:
            try:
                url_path = urlparse(img_url).path
                if url_path not in seen_image_paths:
                    seen_image_paths.add(url_path)
                    unique_images.append(img_url)
            except Exception as e:
                logger.warning(f"No se pudo parsear la URL '{img_url}'. Error: {e}. Se omite.")
        
        # Fase D: Absolutización de URLs
        unique_image_urls = [urljoin(url, img_url) for img_url in unique_images]
        logger.info(f"Proceso de extracción finalizado. Se encontraron {len(unique_image_urls)} candidatas de imagen únicas.")

        metadata = {"titulo": "Ejemplo", "resumen": "Ejemplo", "tags": "Ejemplo"}
        metadata['contenido_html'] = html_content
        metadata['urls_imagenes'] = unique_image_urls
        
        return metadata

    except Exception as e:
        logger.error(f"Error procesando el HTML extraído: {e}", exc_info=True)
        return None

def analyze_image_with_vision(image_url: str, logger) -> str | None:
    logger.info(f"Capa 3: Analizando imagen con IA de visión: {image_url}")
    try:
        if not image_url.startswith(('http://', 'https://')):
             logger.warning(f"URL de imagen inválida, se omite: {image_url}")
             return None

        model = genai.GenerativeModel(VISION_MODEL)
        system_prompt = "Eres un experto analista de contenido visual para un medio periodístico. Tu tarea es analizar una imagen y clasificar su propósito dentro de un artículo. Responde únicamente con un objeto JSON válido sin formato adicional."
        user_prompt = f'''Analiza la imagen. Clasifícala según uno de los siguientes tipos: "fotografia_principal", "grafico_o_diagrama", "captura_de_pantalla", "logo_o_banner", "irrelevante". Determina si es relevante para el contenido principal. La descripción debe ser concisa (máximo 15 palabras).

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
        final_prompt = [system_prompt, user_prompt, image_part]
        response = model.generate_content(final_prompt)
        json_response_text = response.text.strip().replace('```json', '').replace('```', '')
        json.loads(json_response_text)
        return json_response_text

    except Exception as e:
        logger.error(f"Capa 3: Error en el análisis de visión para {image_url}: {e}", exc_info=True)
        return None

def download_image(base_url: str, image_url: str, asset_id: int, image_order: int, output_dir: str, logger) -> Union[str, None]:
    if not image_url: return None
    absolute_image_url = urljoin(base_url, image_url)
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

def upload_image_to_storage(supabase_client: SupabaseClient, local_path: str, asset_id: int, image_order: int, logger) -> str | None:
    logger.info(f"Iniciando intento de subida a Supabase Storage para: {local_path}")
    if not local_path or not os.path.exists(local_path):
        logger.warning("La subida se omitió porque la ruta local no es válida o no existe.")
        return None
    try:
        file_ext = os.path.splitext(local_path)[1]
        remote_path = f"asset_{asset_id}/{asset_id}_{image_order}{file_ext}"
        with open(local_path, 'rb') as f:
            supabase_client.storage.from_(BUCKET_NAME).upload(
                path=remote_path, file=f, file_options={"cache-control": "3600", "upsert": "true"}
            )
        logger.info(f"Subida a Supabase Storage completada para la ruta remota: {remote_path}")
        response = supabase_client.storage.from_(BUCKET_NAME).get_public_url(remote_path)
        logger.info(f"URL pública de Supabase obtenida: {response}")
        return response
    except Exception as e:
        logger.error(f"Error al subir a Supabase Storage: {e}", exc_info=True)
        return None
