# curator.py (v9.2 - Final Polish)

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
    # ... (lógica de argparse y setup inicial sin cambios)
    log = logger.get_logger("curator-worker-v9.2")
    supabase = db_manager.get_supabase_client(log)
    urls_to_process = supabase.table(db_manager.URLS_TABLE).select('id, url').eq('estado', 'pendiente').execute().data
    if not urls_to_process: return

    for url_item in urls_to_process:
        url_id, url = url_item['id'], url_item['url']
        log.info(f"--- Procesando URL ID {url_id}: {url} ---")
        supabase.table(db_manager.URLS_TABLE).update({'estado': 'en_proceso'}).eq('id', url_id).execute()
        
        master_asset_id = None
        try:
            asset_response = supabase.table(db_manager.ASSETS_TABLE).insert({'source_url_id': url_id, 'asset_type': 'ARTICULO_TEXTO', 'url_original': url}, returning="representation").execute()
            master_asset_id = asset_response.data[0]['id']

            metadata = content_processor.extract_article_metadata(url, log)
            if not metadata: raise ValueError("Extracción de metadatos falló.")
            
            image_urls = metadata.pop('urls_imagenes', [])
            supabase.table(db_manager.ASSETS_TABLE).update(metadata).eq('id', master_asset_id).execute()

            article_html = metadata.get('contenido_html')
            for i, image_url in enumerate(image_urls):
                try:
                    # FILTRO IA: Analizar primero
                    vision_data = content_processor.analyze_image_with_vision(image_url, log) or {}
                    description = vision_data.get('descripcion_ia', '').lower()
                    if any(keyword in description for keyword in ['logo', 'icono', 'banner']):
                        log.warning(f"Imagen descartada por filtro de IA (logo/icono): {image_url}")
                        continue # Saltar a la siguiente imagen

                    # Pasar la URL original del artículo para construir la URL absoluta de la imagen
                    local_path = content_processor.download_image(url, image_url, article_html, master_asset_id, i, IMAGES_OUTPUT_DIR, log)
                    
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
            if master_asset_id: supabase.table(db_manager.ASSETS_TABLE).update({'estado_curacion': 'fallido'}).eq('id', master_asset_id).execute()
            supabase.table(db_manager.URLS_TABLE).update({'estado': 'error', 'ultimo_error': str(e)}).eq('id', url_id).execute()

if __name__ == "__main__":
    main()
