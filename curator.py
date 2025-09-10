# curator.py (v3.2.1 - Carga de Entorno Corregida)

# --- Carga de Entorno --- 
# Debe ser lo primero que se ejecuta para que las variables estén disponibles para los otros módulos.
from dotenv import load_dotenv
load_dotenv()

# --- Importaciones del Módulo ---
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
                    # 1. Extraer metadatos del artículo (incluyendo URLs de imágenes y HTML)
                    metadata = content_processor.extract_article_metadata(url, log)
                    if not metadata:
                        raise ValueError("La extracción de metadatos del artículo falló.")

                    # 2. Separar metadatos, URLs de imágenes y el contenido HTML
                    image_urls = metadata.pop('urls_imagenes', [])
                    article_html = metadata.get('contenido_html') # Obtenemos el HTML para el análisis avanzado
                    
                    # 3. Guardar los metadatos principales del artículo
                    db_manager.save_article_metadata(supabase, log, master_asset_id, metadata)
                    log.info(f"Metadatos del artículo para Asset ID {master_asset_id} guardados.")

                    # 4. Procesar las imágenes encontradas (máximo 5)
                    log.info(f"Se encontraron {len(image_urls)} imágenes. Procesando las primeras 5 con análisis HTML...")
                    for i, image_url in enumerate(image_urls[:5]):
                        log.info(f"Procesando imagen {i+1}/5: {image_url[:100]}...")
                        try:
                            # 4a. Analizar la imagen con IA de Visión
                            vision_data = content_processor.analyze_image_with_vision(image_url, log)
                            if not vision_data:
                                log.warning(f"El análisis de visión para {image_url} no devolvió datos.")
                                # No continuamos, pero guardaremos un registro sin datos de IA
                                vision_data = {}

                            # 4b. Descargar el archivo de la imagen
                            local_path = content_processor.download_image(
                                image_url=image_url,
                                article_html=article_html,
                                asset_id=master_asset_id,
                                image_order=i,
                                output_dir=IMAGES_OUTPUT_DIR,
                                logger=log
                            )

                            # 4c. Subir la imagen a Supabase Storage
                            storage_url = None
                            if local_path:
                                storage_url = content_processor.upload_image_to_storage(
                                    supabase_client=supabase,
                                    local_path=local_path,
                                    asset_id=master_asset_id,
                                    image_order=i,
                                    logger=log
                                )
                            
                            # 4d. Guardar toda la información en la base de datos
                            image_metadata_to_save = {
                                'asset_id': master_asset_id,
                                'url_original_imagen': image_url,
                                'ruta_local': local_path, # Puede ser None si la descarga falló
                                'url_almacenamiento': storage_url, # Puede ser None si la carga falló
                                'tags_visuales_ia': vision_data.get('tags_visuales_ia'),
                                'descripcion_ia': vision_data.get('descripcion_ia'),
                                'orden_aparicion': i
                            }
                            db_manager.save_image_metadata(supabase, log, image_metadata_to_save)
                            log.info(f"Metadatos de la imagen {i+1} guardados en la base de datos.")

                        except Exception as img_exc:
                            log.error(f"Error procesando la imagen {image_url}: {img_exc}", exc_info=True)
                            # No detenemos el bucle principal, solo esta imagen falla

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