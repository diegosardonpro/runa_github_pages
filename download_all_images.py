# download_all_images.py
# Herramienta de utilidad para descargar en lote todas las imágenes de los activos curados.

import os
import sys

# --- Añadir la carpeta 'src' al path para poder importar los módulos ---
# Esto permite ejecutar el script directamente desde la raíz del proyecto.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.utils import logger
from src import db_manager, content_processor

# --- CONSTANTES ---
IMAGES_OUTPUT_DIR = 'output_images'

def main():
    """Punto de entrada principal para el script de descarga masiva."""
    log = logger.get_logger('image-downloader')
    log.info("--- INICIANDO SCRIPT DE DESCARGA MASIVA DE IMÁGENES ---")

    try:
        # --- 1. Conexión a la Base de Datos ---
        supabase = db_manager.get_supabase_client(log)

        # --- 2. Obtener Activos con Imágenes Pendientes ---
        log.info(f"Buscando activos curados con imágenes pendientes de descarga...")
        response = supabase.table(db_manager.ASSETS_TABLE)\
            .select('id, url_imagen_original')\
            .not_.is_('url_imagen_original', 'null')\
            .is_('ruta_imagen_local', 'null')\
            .execute()

        assets_to_download = response.data
        if not assets_to_download:
            log.info("No hay imágenes nuevas para descargar. Todos los activos están al día.")
            return

        log.info(f"Se encontraron {len(assets_to_download)} imágenes para descargar.")

        # --- 3. Bucle de Descarga ---
        success_count = 0
        failure_count = 0
        for asset in assets_to_download:
            asset_id, image_url = asset['id'], asset['url_imagen_original']
            log.info(f"Procesando Asset ID {asset_id} - URL: {image_url}")

            try:
                local_path = content_processor.download_image(
                    image_url, 
                    asset_id, 
                    IMAGES_OUTPUT_DIR, 
                    log
                )

                if local_path:
                    # Actualizar la base de datos con la ruta local
                    supabase.table(db_manager.ASSETS_TABLE)\
                        .update({'ruta_imagen_local': local_path})\
                        .eq('id', asset_id)\
                        .execute()
                    log.info(f"Asset ID {asset_id} actualizado en la BD con la ruta: {local_path}")
                    success_count += 1
                else:
                    raise ValueError("La función de descarga no devolvió una ruta local.")

            except Exception as e:
                log.error(f"Fallo al procesar Asset ID {asset_id}: {e}", exc_info=True)
                failure_count += 1

        # --- 4. Resumen Final ---
        log.info("--- PROCESO DE DESCARGA FINALIZADO ---")
        log.info(f"Imágenes descargadas con éxito: {success_count}")
        log.info(f"Fallos: {failure_count}")

    except Exception as e:
        log.error(f"Error fatal en el script de descarga: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
