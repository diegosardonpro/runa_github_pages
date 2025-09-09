# curator.py (v2.1 - IA-Driven)
import os
import uuid
from src.utils import logger
from src import db_manager, content_processor

# --- CONSTANTES ---
IMAGES_OUTPUT_DIR = 'output_images'

def main():
    """Punto de entrada principal para el orquestador de curación de activos."""
    run_id = str(uuid.uuid4())
    log = logger.get_logger(f"curator-{run_id[:8]}")
    log.info(f"--- INICIANDO EJECUCIÓN DEL ORQUESTADOR (RUN ID: {run_id}) ---")

    supabase = None
    processed_count = 0
    try:
        # --- 1. Inicialización y Configuración ---
        supabase = db_manager.get_supabase_client(log)
        db_manager.log_execution_start(supabase, log, run_id)
        db_manager.setup_database_schema(supabase, log)

        # --- 2. Obtener URLs para Procesar ---
        urls_to_process = db_manager.get_pending_urls(supabase, log, limit=5)
        if not urls_to_process:
            log.info("No hay nuevas URLs para procesar. Finalizando ejecución.")
            db_manager.log_execution_end(supabase, log, run_id, 'exitoso', 0, "No hay URLs pendientes.")
            return

        # --- 3. Bucle de Procesamiento de URLs ---
        for url_item in urls_to_process:
            url_id, url = url_item['id'], url_item['url']
            log.info(f"--- Iniciando procesamiento para URL ID {url_id}: {url} ---")
            db_manager.update_url_status(supabase, log, url_id, 'en_proceso')

            try:
                # --- 3a. Procesamiento Unificado con IA ---
                # Se delega tanto el scraping como el enriquecimiento a la IA en un solo paso.
                processed_data = content_processor.process_url_with_ai(url, log)
                if not processed_data:
                    raise ValueError("El procesamiento con IA falló o no devolvió datos.")

                # --- 3b. Guardar Activo Principal ---
                asset_payload = {
                    'source_url_id': url_id,
                    'url_original': url,
                    'titulo': processed_data.get('titulo'),
                    'resumen': processed_data.get('resumen'),
                    'contenido_html': processed_data.get('contenido_html'),
                    'tags': processed_data.get('tags'),
                    'url_imagen_original': processed_data.get('url_imagen_original')
                }
                new_asset = db_manager.save_curated_asset(supabase, log, asset_payload)
                if not new_asset:
                    raise ValueError("Falló el guardado del activo curado en la base de datos.")

                # --- 3c. Descargar Imagen (si existe) ---
                local_image_path = content_processor.download_image(
                    processed_data.get('url_imagen_original'), 
                    new_asset['id'], 
                    IMAGES_OUTPUT_DIR, 
                    log
                )
                if local_image_path:
                    # Actualizar el activo con la ruta de la imagen local
                    supabase.table(db_manager.ASSETS_TABLE).update({'ruta_imagen_local': local_image_path}).eq('id', new_asset['id']).execute()

                # --- 3d. Marcar como Completado ---
                db_manager.update_url_status(supabase, log, url_id, 'completado')
                processed_count += 1
                log.info(f"URL ID {url_id} procesada y curada con éxito.")

            except Exception as e:
                log.error(f"Error procesando URL ID {url_id}: {e}", exc_info=True)
                db_manager.update_url_status(supabase, log, url_id, 'error', str(e))

        # --- 4. Finalizar Ejecución ---
        summary_message = f"Procesamiento completado. {processed_count} de {len(urls_to_process)} URLs curadas con éxito."
        db_manager.log_execution_end(supabase, log, run_id, 'exitoso', processed_count, summary_message)
        log.info(summary_message)

    except Exception as e:
        log.error(f"Error fatal en el orquestador: {e}", exc_info=True)
        if supabase:
            summary_message = f"La ejecución falló con un error fatal: {e}"
            db_manager.log_execution_end(supabase, log, run_id, 'fallido', processed_count, summary_message)
        exit(1)
    finally:
        log.info(f"--- FINALIZANDO EJECUCIÓN DEL ORQUESTADOR (RUN ID: {run_id}) ---")

if __name__ == "__main__":
    main()
