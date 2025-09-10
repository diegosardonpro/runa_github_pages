# process_one.py (v1.0)

# --- Carga de Entorno ---
from dotenv import load_dotenv
load_dotenv()

# --- Importaciones del Módulo ---
import os
import uuid
import argparse
from src.utils import logger
from src import db_manager, content_processor

# --- CONSTANTES ---
IMAGES_OUTPUT_DIR = 'output_images'
SUPPORTED_ASSET_TYPES = ['ARTICULO_TEXTO']

def main():
    """
    Punto de entrada para el procesamiento de una única URL.
    Ejecuta el pipeline de curación completo para el enlace proporcionado.
    """
    # --- 1. Configuración y Argumentos ---
    parser = argparse.ArgumentParser(description="Procesa y cura una única URL de un artículo.")
    parser.add_argument('--url', type=str, required=True, help='La URL completa del artículo a procesar.')
    args = parser.parse_args()

    run_id = str(uuid.uuid4())
    log = logger.get_logger(f"process-one-{run_id[:8]}")
    log.info(f"--- INICIANDO PROCESAMIENTO DE URL INDIVIDUAL (RUN ID: {run_id}) ---")
    log.info(f"URL a procesar: {args.url}")

    supabase = None
    master_asset_id = None
    url_id = None

    try:
        # --- 2. Inicialización de la Base de Datos ---
        supabase = db_manager.get_supabase_client(log)
        db_manager.log_execution_start(supabase, log, run_id)
        db_manager.setup_database_schema(supabase, log)

        # --- 3. Gestión de la URL en la Base de Datos ---
        url_record_response = db_manager.add_url_if_not_exists(supabase, log, args.url)
        if not url_record_response or not url_record_response.data:
            raise ValueError(f"No se pudo crear ni encontrar el registro para la URL: {args.url}")
        
        url_id = url_record_response.data[0]['id']
        log.info(f"URL registrada/encontrada con ID: {url_id}")
        db_manager.update_url_status(supabase, log, url_id, 'en_proceso')

        # --- 4. Pipeline de Curación ---
        # Clasificar el tipo de activo
        asset_type = content_processor.classify_url_type(args.url, log)
        if not asset_type or asset_type not in SUPPORTED_ASSET_TYPES:
            log.warning(f"El tipo de activo '{asset_type}' no está soportado. Finalizando.")
            db_manager.update_url_status(supabase, log, url_id, 'no_soportado')
            return

        # Crear registro maestro del activo
        master_asset = db_manager.create_master_asset(supabase, log, url_id, asset_type, args.url)
        if not master_asset:
            raise ValueError("No se pudo crear el registro de activo maestro.")
        master_asset_id = master_asset['id']

        # Procesamiento específico para artículos
        if asset_type == 'ARTICULO_TEXTO':
            # 1. Extraer metadatos (incluye HTML y URLs de imágenes)
            metadata = content_processor.extract_article_metadata(args.url, log)
            if not metadata:
                raise ValueError("La extracción de metadatos del artículo falló.")

            image_urls = metadata.pop('urls_imagenes', [])
            article_html = metadata.get('contenido_html')
            
            # 2. Guardar metadatos del artículo
            db_manager.save_article_metadata(supabase, log, master_asset_id, metadata)
            log.info(f"Metadatos del artículo para Asset ID {master_asset_id} guardados.")

            # 3. Procesar imágenes encontradas
            log.info(f"Se encontraron {len(image_urls)} imágenes. Procesando...")
            for i, image_url in enumerate(image_urls):
                log.info(f"Procesando imagen {i+1}/{len(image_urls)}: {image_url[:100]}...")
                try:
                    vision_data = content_processor.analyze_image_with_vision(image_url, log)
                    if not vision_data:
                        vision_data = {}

                    local_path = content_processor.download_image(
                        image_url=image_url,
                        article_html=article_html,
                        asset_id=master_asset_id,
                        image_order=i,
                        output_dir=IMAGES_OUTPUT_DIR,
                        logger=log
                    )
                    
                    image_metadata_to_save = {
                        'asset_id': master_asset_id,
                        'url_original_imagen': image_url,
                        'ruta_local': local_path,
                        'tags_visuales_ia': vision_data.get('tags_visuales_ia'),
                        'descripcion_ia': vision_data.get('descripcion_ia'),
                        'orden_aparicion': i
                    }
                    db_manager.save_image_metadata(supabase, log, image_metadata_to_save)
                    log.info(f"Metadatos de la imagen {i+1} guardados.")

                except Exception as img_exc:
                    log.error(f"Error procesando la imagen {image_url}: {img_exc}", exc_info=True)

        # --- 5. Finalización y Limpieza ---
        db_manager.update_asset_status(supabase, log, master_asset_id, 'completado')
        db_manager.update_url_status(supabase, log, url_id, 'completado')
        summary = f"URL curada con éxito como {asset_type} (Asset ID: {master_asset_id})."
        db_manager.log_execution_end(supabase, log, run_id, 'exitoso', 1, summary)
        log.info(summary)

    except Exception as e:
        log.error(f"Error fatal durante el procesamiento de la URL: {e}", exc_info=True)
        if supabase:
            if url_id:
                db_manager.update_url_status(supabase, log, url_id, 'error', str(e))
            if master_asset_id:
                db_manager.update_asset_status(supabase, log, master_asset_id, 'fallido')
            db_manager.log_execution_end(supabase, log, run_id, 'fallido', 0, f"Error fatal: {e}")
        exit(1)
    finally:
        log.info(f"--- FINALIZANDO PROCESAMIENTO DE URL INDIVIDUAL (RUN ID: {run_id}) ---")

if __name__ == "__main__":
    main()
