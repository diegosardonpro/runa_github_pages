import os
import re
import json
import requests
import uuid
from supabase import create_client, Client
from src.utils.logger import get_logger
import google.generativeai as genai

# --- CONFIGURACIÓN ---
# v6.1: Implementación completa de ciclo AI-First
URLS_TABLE = 'urls_para_procesar'
ASSETS_TABLE = 'activos_curados'
IMAGES_OUTPUT_DIR = 'output_images'

# --- INICIALIZACIÓN DE IA ---
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: No se encontró la GEMINI_API_KEY.")
    else:
        genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error configurando Gemini: {e}")
    GEMINI_API_KEY = None

# --- FUNCIONES ---
def get_supabase_client(logger):
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not url or not key: raise ValueError("Secretos SUPABASE_URL o SUPABASE_SERVICE_KEY no encontrados.")
    logger.info("Cliente de Supabase creado.")
    return create_client(url, key)

def get_runa_curation_prompt(url):
    return f"""Actúa como un analista experto para el proyecto Runa. Tu objetivo es extraer información clave de la página web en la siguiente URL. Analiza el contenido de la URL y devuelve un objeto JSON con las siguientes claves: \"titulo\", \"resumen\", \"tags\", y \"url_imagen_original\".

- El \"titulo\" debe ser el título principal del artículo.
- El \"resumen\" debe ser un párrafo conciso de 2-4 frases que capture la esencia del artículo.
- Los \"tags\" deben ser una lista de 5 a 7 palabras clave o conceptos relevantes en español.
- La \"url_imagen_original\" debe ser la URL completa de la imagen de portada o la más representativa del artículo.

URL para analizar: {url}

Responde únicamente con el objeto JSON, sin texto introductorio, explicaciones, ni markdown.
"""

def enrich_with_ai(url, logger):
    logger.info(f"Iniciando enriquecimiento AI-First para la URL: {url}")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no configurada.")

    try:
        prompt = get_runa_curation_prompt(url)
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        enriched_data = json.loads(cleaned_response)
        
        if isinstance(enriched_data.get('tags'), list):
            enriched_data['tags'] = ", ".join(enriched_data['tags'])

        logger.info("Enriquecimiento con IA completado con éxito.")
        return enriched_data
    except Exception as e:
        logger.error(f"Error en la llamada a la API de IA: {e}", exc_info=True)
        return None

def download_image(image_url, asset_id, logger):
    if not image_url: 
        logger.warning("La IA no devolvió una URL de imagen para descargar.")
        return None
    logger.info(f"Iniciando descarga de imagen: {image_url}")
    try:
        response = requests.get(image_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        ext = '.jpg'
        content_type = response.headers.get('content-type')
        if content_type and 'png' in content_type: ext = '.png'
        
        os.makedirs(IMAGES_OUTPUT_DIR, exist_ok=True)
        local_path = os.path.join(IMAGES_OUTPUT_DIR, f"{asset_id}{ext}")
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Imagen guardada exitosamente en: {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Error al descargar la imagen {image_url}: {e}", exc_info=True)
        return None

def main():
    run_id = str(uuid.uuid4())[:8]
    logger = get_logger(f"curator-{run_id}")
    logger.info(f"--- INICIANDO EJECUCIÓN DEL CURADOR (RUN ID: {run_id}) ---")
    try:
        supabase = get_supabase_client(logger)
        # La creación del schema ya no es necesaria en cada ejecución

        logger.info(f"Buscando URLs con estado 'pendiente'...")
        response = supabase.table(URLS_TABLE).select('id, url').eq('estado', 'pendiente').limit(1).execute() # Procesar una a la vez
        urls_to_process = response.data

        if not urls_to_process:
            logger.info("No hay nuevas URLs para procesar. Finalizando.")
            return

        logger.info(f"Se encontraron {len(urls_to_process)} URLs para procesar.")
        ids_in_process = [item['id'] for item in urls_to_process]
        supabase.table(URLS_TABLE).update({'estado': 'en_proceso'}).in_('id', ids_in_process).execute()

        for item in urls_to_process:
            url_id, url = item['id'], item['url']
            logger.info(f"--- Procesando ID de URL {url_id}: {url} ---")
            try:
                enriched_data = enrich_with_ai(url, logger)
                if not enriched_data: raise ValueError("El enriquecimiento con IA falló o no devolvió datos.")

                new_asset_id_response = supabase.table(ASSETS_TABLE).select("id").order("id", desc=True).limit(1).execute()
                next_asset_id = (new_asset_id_response.data[0]['id'] + 1) if new_asset_id_response.data else 1
                logger.info(f"Siguiente ID de activo disponible: {next_asset_id}")

                local_image_path = download_image(enriched_data.get('url_imagen_original'), next_asset_id, logger)

                new_asset = {
                    'id': next_asset_id,
                    'url_original': url,
                    'titulo': enriched_data.get('titulo'),
                    'resumen': enriched_data.get('resumen'),
                    'tags': enriched_data.get('tags'),
                    'ruta_imagen_local': local_image_path,
                    'url_imagen_original': enriched_data.get('url_imagen_original')
                }
                supabase.table(ASSETS_TABLE).insert(new_asset).execute()
                logger.info(f"Activo curado guardado en tabla '{ASSETS_TABLE}' con ID {next_asset_id}.")

                supabase.table(URLS_TABLE).update({'estado': 'completado'}).eq('id', url_id).execute()
                logger.info(f"URL ID {url_id} marcada como 'completado'.")

            except Exception as e:
                error_message = str(e).replace('\n', ' ')
                logger.error(f"Error procesando URL ID {url_id}: {error_message}", exc_info=True)
                supabase.table(URLS_TABLE).update({'estado': 'error', 'ultimo_error': error_message}).eq('id', url_id).execute()

    except Exception as e:
        logger.error(f"Ha ocurrido un error fatal en el script: {e}", exc_info=True)
        exit(1)
    finally:
        logger.info(f"--- FINALIZANDO EJECUCIÓN DEL CURADOR (RUN ID: {run_id}) ---")

if __name__ == "__main__":
    main()
