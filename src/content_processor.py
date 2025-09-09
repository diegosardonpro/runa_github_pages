# src/content_processor.py
import os
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

# --- CONFIGURACIÓN DE IA ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # No usamos logger aquí porque puede ser importado antes de que el logger se configure
    print("ADVERTENCIA: No se encontró la GEMINI_API_KEY. La funcionalidad de IA estará desactivada.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- FUNCIONES DE PROCESAMIENTO DE CONTENIDO ---
def scrape_article_data(url, logger):
    logger.info(f"Iniciando scraping de URL: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else 'Sin Título'
        article_body = soup.find('div', class_='article-content') or soup.find('article') or soup.body
        paragraphs = article_body.find_all('p')
        text_content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs])
        og_image = soup.find('meta', property='og:image')
        image_url = og_image['content'] if og_image else None
        
        logger.info(f"Scraping exitoso. Título: '{title[:50]}...'\n")
        return {'title': title, 'text': text_content, 'image_url': image_url}
    except Exception as e:
        logger.error(f"Error durante el scraping de {url}: {e}", exc_info=True)
        return None

def enrich_with_ai(text_content, logger):
    logger.info("Iniciando enriquecimiento de contenido con IA...")
    if not GEMINI_API_KEY:
        logger.warning("No hay API Key de Gemini. Usando lógica de simulación.")
        resumen = text_content[:300].strip().replace('\n', ' ') + '...'
        tags = ["Medio Ambiente", "Perú", "Legislación", "Conservación"]
        return {'resumen': resumen, 'tags': ", ".join(tags), 'contenido_html': text_content}

    try:
        prompt = f"""Actúa como un analista experto para el proyecto Runa. Analiza el siguiente texto de un artículo y devuelve un objeto JSON con las claves "resumen", "tags", y "contenido_html". El resumen debe ser un párrafo conciso. Los tags deben ser una lista de 5 a 7 palabras clave relevantes. El contenido_html debe ser el texto original formateado en párrafos HTML. Texto: 

{text_content}"""
        
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        
        # Limpieza básica de la respuesta para asegurar que sea un JSON válido
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        enriched_data = json.loads(cleaned_response)
        logger.info("Enriquecimiento con IA completado con éxito.")
        return enriched_data
    except Exception as e:
        logger.error(f"Error en la llamada a la API de IA: {e}", exc_info=True)
        return None

def download_image(image_url, asset_id, output_dir, logger):
    if not image_url: 
        logger.warning("No se proporcionó URL de imagen para descargar.")
        return None
    logger.info(f"Iniciando descarga de imagen: {image_url}")
    try:
        response = requests.get(image_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        ext = '.jpg'
        content_type = response.headers.get('content-type')
        if content_type and 'png' in content_type: ext = '.png'
        
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
