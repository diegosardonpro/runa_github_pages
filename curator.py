# curator.py (v8.1 - Final Worker)

from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import os
import uuid
from src.utils import logger
from src import db_manager, content_processor

IMAGES_OUTPUT_DIR = 'output_images'
SUPPORTED_ASSET_TYPES = ['ARTICULO_TEXTO']

def main():
    log = logger.get_logger("curator-worker")
    log.info("--- INICIANDO WORKER DE CURACIÓN ---")
    supabase = None
    try:
        supabase = db_manager.get_supabase_client(log)
        # La configuración del schema ya no se ejecuta aquí, se hace manualmente si es necesario.

        urls_to_process = supabase.table('urls_para_procesar').select('id, url').eq('estado', 'pendiente').execute().data
        
        if not urls_to_process:
            log.info("No hay URLs pendientes para procesar. Finalizando.")
            return

        log.info(f"Se encontraron {len(urls_to_process)} URLs para procesar.")
        
        # --- BUCLE DE PROCESAMIENTO RESTAURADO ---
        for url_item in urls_to_process:
            url_id, url = url_item['id'], url_item['url']
            log.info(f"--- Procesando URL ID {url_id}: {url} ---")
            supabase.table('urls_para_procesar').update({'estado': 'en_proceso'}).eq('id', url_id).execute()
            
            master_asset_id = None
            try:
                asset_type = content_processor.classify_url_type(url, log)
                if not asset_type or asset_type not in SUPPORTED_ASSET_TYPES:
                    raise ValueError(f"Tipo de activo no soportado: {asset_type}")

                asset_response = supabase.table('activos').insert({'source_url_id': url_id, 'asset_type': asset_type, 'url_original': url}, returning="representation").execute()
                master_asset_id = asset_response.data[0]['id']

                if asset_type == 'ARTICULO_TEXTO':
                    metadata = content_processor.extract_article_metadata(url, log)
                    if not metadata: raise ValueError("Extracción de metadatos falló.")
                    
                    supabase.table('activos').update(metadata).eq('id', master_asset_id).execute()
                    log.info(f"Metadatos del artículo guardados para Asset ID {master_asset_id}.")

                    image_urls = metadata.get('urls_imagenes', [])
                    article_html = metadata.get('contenido_html')
                    for i, image_url in enumerate(image_urls):
                        try:
                            vision_data = content_processor.analyze_image_with_vision(image_url, log) or {}
                            local_path = content_processor.download_image(image_url, article_html, master_asset_id, i, IMAGES_OUTPUT_DIR, log)
                            storage_url = None
                            if local_path:
                                storage_url = content_processor.upload_image_to_storage(supabase, local_path, master_asset_id, i, log)
                            
                            supabase.table('imagenes').insert({
                                'asset_id': master_asset_id, 'url_original_imagen': image_url,
                                'ruta_local': local_path, 'url_almacenamiento': storage_url,
                                'descripcion_ia': vision_data.get('descripcion_ia'), 'tags_visuales_ia': vision_data.get('tags_visuales_ia'),
                                'orden_aparicion': i
                            }).execute()
                        except Exception as img_exc:
                            log.error(f"Error procesando imagen {image_url}: {img_exc}")

                supabase.table('activos').update({'estado_curacion': 'completado'}).eq('id', master_asset_id).execute()
                supabase.table('urls_para_procesar').update({'estado': 'completado'}).eq('id', url_id).execute()
                log.info(f"URL ID {url_id} curada con éxito.")

            except Exception as e:
                log.error(f"Error procesando URL ID {url_id}: {e}")
                supabase.table('urls_para_procesar').update({'estado': 'error', 'ultimo_error': str(e)}).eq('id', url_id).execute()
                if master_asset_id:
                    supabase.table('activos').update({'estado_curacion': 'fallido'}).eq('id', master_asset_id).execute()

    except Exception as e:
        log.error(f"Error fatal en el worker: {e}", exc_info=True)
        exit(1)
    finally:
        log.info(f"--- EJECUCIÓN DEL WORKER FINALIZADA ---")

if __name__ == "__main__":
    main()
