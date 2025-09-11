# curator.py (v10.0 - Final Worker)

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

def main():
    parser = argparse.ArgumentParser(description="Worker para curar activos de Runa.")
    parser.add_argument('--setup-db', action='store_true', help='Ejecuta la configuración inicial del schema de la base de datos.')
    args = parser.parse_args()

    log = logger.get_logger("curator-worker-v10")
    log.info(f"--- INICIANDO WORKER DE CURACIÓN v10.0 ---")

    supabase = db_manager.get_supabase_client(log)

    if args.setup_db:
        db_manager.setup_database_schema(supabase, log)
        return

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
                asset_response = supabase.table(db_manager.ASSETS_TABLE).insert({'source_url_id': url_id, 'url_original': url}, returning="representation").execute()
                master_asset_id = asset_response.data[0]['id']

                metadata = content_processor.extract_article_metadata(url, log)
                if not metadata: raise ValueError("Extracción de metadatos falló.")
                
                image_urls = metadata.pop('urls_imagenes', [])
                # El HTML ya no se guarda en la BD, se usa y se descarta
                article_html = metadata.pop('contenido_html', '')
                
                supabase.table(db_manager.ASSETS_TABLE).update(metadata).eq('id', master_asset_id).execute()
                log.info(f"Metadatos del artículo guardados para Asset ID {master_asset_id}.")

                # Aplicar la restricción de procesar solo las primeras 10 imágenes
                image_urls_limitadas = image_urls[:10]
                log.info(f"Se encontraron {len(image_urls)} imágenes en el artículo. Procesando las primeras {len(image_urls_limitadas)} según la directiva.")

                # Importar json para procesar la respuesta de la IA
                import json

                for i, image_url in enumerate(image_urls_limitadas):
                    try:
                        # CAPA 3: Analizar primero con la IA para la clasificación final
                        vision_analysis_json = content_processor.analyze_image_with_vision(image_url, log)
                        
                        if not vision_analysis_json:
                            log.warning(f"El análisis de visión no devolvió nada para {image_url}. Se omite.")
                            continue

                        # Parsear la respuesta JSON del modelo
                        vision_data = json.loads(vision_analysis_json)

                        # Tomar la decisión final basada en la clasificación de la IA
                        if not vision_data.get('es_relevante') or vision_data.get('tipo') in ['logo_o_banner', 'irrelevante']:
                            log.info(f"Capa 3: Imagen descartada por filtro de IA (tipo: {vision_data.get('tipo')}, relevante: {vision_data.get('es_relevante')}): {image_url}")
                            continue

                        # Si pasa el filtro, procedemos a descargar y guardar
                        log.info(f"Imagen APROBADA por la IA. Procediendo a descargar: {image_url}")
                        
                        local_path = content_processor.download_image(
                            base_url=url, 
                            image_url=image_url, 
                            asset_id=master_asset_id, 
                            image_order=i, 
                            output_dir=IMAGES_OUTPUT_DIR, 
                            logger=log
                        )
                        
                        storage_url = None
                        if local_path:
                            storage_url = content_processor.upload_image_to_storage(supabase, local_path, master_asset_id, i, log)
                        
                        # Guardar metadatos usando la información del JSON de la IA
                        supabase.table(db_manager.IMAGES_TABLE).insert({
                            'asset_id': master_asset_id,
                            'url_original_imagen': image_url,
                            'url_almacenamiento': storage_url,
                            'descripcion_ia': vision_data.get('descripcion_ia'),
                            'tags_visuales_ia': vision_data.get('tipo'), # Usamos el 'tipo' como tag principal
                            'orden_aparicion': i
                        }).execute()

                    except json.JSONDecodeError as json_err:
                        log.error(f"Error al parsear JSON de la IA para {image_url}: {json_err}")
                    except Exception as img_exc:
                        log.error(f"Error procesando imagen {image_url}: {img_exc}")

                supabase.table(db_manager.ASSETS_TABLE).update({'estado_curacion': 'completado'}).eq('id', master_asset_id).execute()
                supabase.table(db_manager.URLS_TABLE).update({'estado': 'completado'}).eq('id', url_id).execute()
                log.info(f"URL ID {url_id} curada con éxito.")

            except Exception as e:
                log.error(f"Error procesando URL ID {url_id}: {e}")
                if master_asset_id: supabase.table(db_manager.ASSETS_TABLE).update({'estado_curacion': 'fallido'}).eq('id', master_asset_id).execute()
                supabase.table(db_manager.URLS_TABLE).update({'estado': 'error', 'ultimo_error': str(e)}).eq('id', url_id).execute()

    except Exception as e:
        log.error(f"Error fatal en el worker: {e}", exc_info=True)
        exit(1)
    finally:
        log.info(f"--- EJECUCIÓN DEL WORKER FINALIZADA ---")

if __name__ == "__main__":
    main()