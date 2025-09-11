# curator.py (v9.0 - Final Worker)

from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import os
import uuid
import argparse
from src.utils import logger
from src import db_manager, content_processor

IMAGES_OUTPUT_DIR = 'output_images'
SUPPORTED_ASSET_TYPES = ['ARTICULO_TEXTO']

def main():
    parser = argparse.ArgumentParser(description="Worker para curar activos de Runa.")
    parser.add_argument('--setup-db', action='store_true', help='Ejecuta la configuración inicial del schema de la base de datos.')
    args = parser.parse_args()

    log = logger.get_logger("curator-worker-v9")
    log.info(f"--- INICIANDO WORKER DE CURACIÓN v9.0 ---")

    supabase = db_manager.get_supabase_client(log)

    if args.setup_db:
            log.info("Se ha solicitado la configuración del schema de la base de datos.")
            db_manager.setup_database_schema(supabase, log)
            log.info("Configuración del schema finalizada.")
            return # Terminar después de la configuración

    try:
        urls_to_process = supabase.table(db_manager.URLS_TABLE).select('id, url').eq('estado', 'pendiente').execute().data
        if not urls_to_process:
            log.info("No hay URLs pendientes para procesar. Finalizando.")
            return

        log.info(f"Se encontraron {len(urls_to_process)} URLs para procesar.")
        for url_item in urls_to_process:
            url_id, url = url_item['id'], url_item['url']
            log.info(f"--- Procesando URL ID {url_id}: {url} ---")
            supabase.table(db_manager.URLS_TABLE).update({'estado': 'en_proceso'}).eq('id', url_id).execute()
            
            master_asset_id = None
            try:
                asset_type = content_processor.classify_url_type(url, log)
                if not asset_type or asset_type not in SUPPORTED_ASSET_TYPES:
                    raise ValueError(f"Tipo de activo no soportado: {asset_type}")

                asset_response = supabase.table(db_manager.ASSETS_TABLE).insert({'source_url_id': url_id, 'asset_type': asset_type, 'url_original': url}, returning="representation").execute()
                master_asset_id = asset_response.data[0]['id']

                if asset_type == 'ARTICULO_TEXTO':
                    metadata = content_processor.extract_article_metadata(url, log)
                    if not metadata: raise ValueError("Extracción de metadatos falló.")
                    
                    image_urls = metadata.pop('urls_imagenes', [])
                    supabase.table(db_manager.ASSETS_TABLE).update(metadata).eq('id', master_asset_id).execute()
                    log.info(f"Metadatos del artículo guardados para Asset ID {master_asset_id}.")

                    article_html = metadata.get('contenido_html')
                    for i, image_url in enumerate(image_urls):
                        try:
                            vision_data = content_processor.analyze_image_with_vision(image_url, log) or {}
                            local_path = content_processor.download_image(image_url, article_html, master_asset_id, i, IMAGES_OUTPUT_DIR, log)
                            storage_url = None
                            if local_path:
                                storage_url = content_processor.upload_image_to_storage(supabase, local_path, master_asset_id, i, log)
                            
                            supabase.table(db_manager.IMAGES_TABLE).insert({
                                'asset_id': master_asset_id, 'url_original_imagen': image_url,
                                'ruta_local': local_path, 'url_almacenamiento': storage_url,
                                'descripcion_ia': vision_data.get('descripcion_ia'), 'tags_visuales_ia': vision_data.get('tags_visuales_ia'),
                                'orden_aparicion': i
                            }).execute()
                        except Exception as img_exc:
                            log.error(f"Error procesando imagen {image_url}: {img_exc}")

                supabase.table(db_manager.ASSETS_TABLE).update({'estado_curacion': 'completado'}).eq('id', master_asset_id).execute()
                supabase.table(db_manager.URLS_TABLE).update({'estado': 'completado'}).eq('id', url_id).execute()
                log.info(f"URL ID {url_id} curada con éxito.")

            except Exception as e:
                log.error(f"Error procesando URL ID {url_id}: {e}")
                supabase.table(db_manager.URLS_TABLE).update({'estado': 'error', 'ultimo_error': str(e)}).eq('id', url_id).execute()
                if master_asset_id:
                    supabase.table(db_manager.ASSETS_TABLE).update({'estado_curacion': 'fallido'}).eq('id', master_asset_id).execute()

    except Exception as e:
        log.error(f"Error fatal en el worker: {e}", exc_info=True)
        exit(1)
    finally:
        log.info(f"--- EJECUCIÓN DEL WORKER FINALIZADA ---")

if __name__ == "__main__":
    main()