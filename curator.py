# curator.py (v3.0 - Arquitectura Normalizada)
import os
import uuid
from src.utils import logger
from src import db_manager, content_processor

# --- CONSTANTES ---
IMAGES_OUTPUT_DIR = 'output_images'
SUPPORTED_ASSET_TYPES = ['ARTICULO_TEXTO'] # Lista de tipos que sabemos procesar

def main():
    """Punto de entrada principal para el orquestador de curación de activos v3.0."""
    run_id = str(uuid.uuid4())
    log = logger.get_logger(f"curator-{run_id[:8]}")
    log.info(f"--- INICIANDO EJECUCIÓN DEL ORQUESTADOR v3.0 (RUN ID: {run_id}) ---")

    supabase = None
    processed_count = 0
    try:
        # --- 1. Inicialización y Configuración ---
        supabase = db_manager.get_supabase_client(log)
        db_manager.log_execution_start(supabase, log, run_id)
        # NOTA: El setup del schema puede fallar si las tablas viejas existen.
        # Requiere una limpieza manual de la BD para la transición a v3.0.
        db_manager.setup_database_schema(supabase, log)

        # --- 2. Obtener URLs para Procesar ---
        urls_to_process = db_manager.get_pending_urls(supabase, log, limit=5)
        if not urls_to_process:
            log.info("No hay nuevas URLs para procesar.")
            db_manager.log_execution_end(supabase, log, run_id, 'exitoso', 0, "No hay URLs pendientes.")
            return

        # --- 3. Bucle de Procesamiento de URLs ---
        for url_item in urls_to_process:
            url_id, url = url_item['id'], url_item['url']
            log.info(f"--- Iniciando URL ID {url_id}: {url} ---")
            db_manager.update_url_status(supabase, log, url_id, 'en_proceso')
            
            master_asset_id = None
            try:
                # --- 3a. Clasificar el tipo de activo ---
                asset_type = content_processor.classify_url_type(url, log)
                if not asset_type or asset_type not in SUPPORTED_ASSET_TYPES:
                    log.warning(f"El tipo de activo '{asset_type}' no está soportado. Marcando URL como no soportada.")
                    db_manager.update_url_status(supabase, log, url_id, 'no_soportado')
                    continue

                # --- 3b. Crear registro maestro del activo ---
                master_asset = db_manager.create_master_asset(supabase, log, url_id, asset_type, url)
                if not master_asset:
                    raise ValueError("No se pudo crear el registro de activo maestro.")
                master_asset_id = master_asset['id']

                # --- 3c. Procesamiento especializado según el tipo ---
                if asset_type == 'ARTICULO_TEXTO':
                    # Extraer metadatos y enlaces
                    metadata = content_processor.extract_article_metadata(url, log)
                    if not metadata:
                        raise ValueError("La extracción de metadatos del artículo falló.")
                    
                    # La IA devuelve los enlaces en una clave separada
                    links_data = metadata.pop('enlaces', None)
                    
                    # Guardar metadatos principales del artículo
                    db_manager.save_article_metadata(supabase, log, master_asset_id, metadata)

                    # Guardar enlaces extraídos en su propia tabla
                    if links_data:
                        db_manager.save_extracted_links(supabase, log, master_asset_id, links_data)

                    # Descargar imagen asociada al artículo
                    image_url = metadata.get('url_imagen_extraida')
                    local_image_path = content_processor.download_image(image_url, master_asset_id, IMAGES_OUTPUT_DIR, log)
                    if local_image_path:
                        # Actualizar la tabla de metadatos con la ruta local
                        supabase.table(db_manager.METADATA_ARTICLES_TABLE)\
                            .update({'ruta_imagen_local': local_image_path})\
                            .eq('asset_id', master_asset_id).execute()

                # --- 3d. Finalizar y marcar como completado ---
                db_manager.update_asset_status(supabase, log, master_asset_id, 'completado')
                db_manager.update_url_status(supabase, log, url_id, 'completado')
                processed_count += 1
                log.info(f"URL ID {url_id} curada con éxito como {asset_type} (Asset ID: {master_asset_id}).")

            except Exception as e:
                log.error(f"Error procesando URL ID {url_id}: {e}", exc_info=True)
                db_manager.update_url_status(supabase, log, url_id, 'error', str(e))
                if master_asset_id:
                    db_manager.update_asset_status(supabase, log, master_asset_id, 'fallido')

        # --- 4. Finalizar Ejecución ---
        summary = f"{processed_count} de {len(urls_to_process)} URLs curadas con éxito."
        db_manager.log_execution_end(supabase, log, run_id, 'exitoso', processed_count, summary)
        log.info(summary)

    except Exception as e:
        log.error(f"Error fatal en el orquestador: {e}", exc_info=True)
        if supabase:
            db_manager.log_execution_end(supabase, log, run_id, 'fallido', processed_count, f"Error fatal: {e}")
        exit(1)
    finally:
        log.info(f"--- FINALIZANDO EJECUCIÓN DEL ORQUESTADOR v3.0 (RUN ID: {run_id}) ---")

if __name__ == "__main__":
    main()