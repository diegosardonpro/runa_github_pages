# curator.py - Orquestador Principal
import os
import uuid
from src.utils.logger import get_logger
from src.db_manager import get_supabase_client, setup_database_schema, URLS_TABLE, ASSETS_TABLE
from src.content_processor import scrape_article_data, enrich_with_ai, download_image

# --- CONFIGURACIÓN ---
# v5.0: Arquitectura modular final
IMAGES_OUTPUT_DIR = 'output_images'

def main():
    """Función principal que orquesta el flujo de curación."""
    run_id = str(uuid.uuid4())[:8]
    logger = get_logger(f"curator-{run_id}")

    logger.info(f"--- INICIANDO EJECUCIÓN DEL CURADOR (RUN ID: {run_id}) ---")
    try:
        # 1. Conexión e infraestructura
        supabase = get_supabase_client(logger)
        # setup_database_schema(supabase, logger) # Comentado para ejecuciones posteriores

        # 2. Ingesta de URLs
        logger.info(f"Buscando URLs con estado 'pendiente' en la tabla '{URLS_TABLE}'...")
        response = supabase.table(URLS_TABLE).select('id, url').eq('estado', 'pendiente').limit(5).execute()
        urls_to_process = response.data

        if not urls_to_process:
            logger.info("No hay nuevas URLs para procesar. Finalizando.")
            return

        logger.info(f"Se encontraron {len(urls_to_process)} URLs para procesar.")
        ids_in_process = [item['id'] for item in urls_to_process]
        supabase.table(URLS_TABLE).update({'estado': 'en_proceso'}).in_('id', ids_in_process).execute()

        # 3. Procesamiento de cada URL
        for item in urls_to_process:
            url_id, url = item['id'], item['url']
            logger.info(f"--- Procesando ID de URL {url_id}: {url} ---")
            try:
                raw_data = scrape_article_data(url, logger)
                if not raw_data: raise ValueError("El scraping no devolvió datos.")

                enriched_data = enrich_with_ai(raw_data['text'], logger)
                if not enriched_data: raise ValueError("El enriquecimiento con IA falló.")

                new_asset_id_response = supabase.table(ASSETS_TABLE).select("id").order("id", desc=True).limit(1).execute()
                next_asset_id = (new_asset_id_response.data[0]['id'] + 1) if new_asset_id_response.data else 1
                logger.info(f"Siguiente ID de activo disponible: {next_asset_id}")

                local_image_path = download_image(raw_data['image_url'], next_asset_id, IMAGES_OUTPUT_DIR, logger)

                new_asset = {
                    'id': next_asset_id,
                    'url_original': url,
                    'titulo': raw_data['title'],
                    'resumen': enriched_data['resumen'],
                    'contenido_html': enriched_data['contenido_html'],
                    'tags': enriched_data['tags'],
                    'ruta_imagen_local': local_image_path,
                    'url_imagen_original': raw_data['image_url']
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
        logger.info(f"Ha ocurrido un error fatal en el script: {e}", exc_info=True)
        exit(1)
    finally:
        logger.info(f"--- FINALIZANDO EJECUCIÓN DEL CURADOR (RUN ID: {run_id}) ---")

if __name__ == "__main__":
    main()
