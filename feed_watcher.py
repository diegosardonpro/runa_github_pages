# feed_watcher.py

from dotenv import load_dotenv
# Cargar variables de entorno primero
load_dotenv()

import feedparser
import time
from src.utils import logger
from src import db_manager

# --- CONFIGURACIÓN ---
# Lista de RSS feeds a vigilar. Por ahora, solo Mongabay Latam.
RSS_FEEDS = [
    "https://es.mongabay.com/feed/"
]

LOG = logger.get_logger("feed_watcher")

def fetch_and_parse_feeds():
    """Recorre la lista de RSS_FEEDS, los analiza y devuelve una lista de entradas."""
    LOG.info(f"Iniciando la revisión de {len(RSS_FEEDS)} feed(s)...")
    all_entries = []
    for feed_url in RSS_FEEDS:
        try:
            parsed_feed = feedparser.parse(feed_url)
            if parsed_feed.bozo:
                # Bozo es 1 si el feed tiene errores de formato
                LOG.warning(f"El feed {feed_url} podría estar mal formado. Error: {parsed_feed.bozo_exception}")
            
            LOG.info(f"Feed '{parsed_feed.feed.title}' analizado. Se encontraron {len(parsed_feed.entries)} entradas.")
            all_entries.extend(parsed_feed.entries)
        except Exception as e:
            LOG.error(f"No se pudo obtener o analizar el feed {feed_url}: {e}", exc_info=True)
            
    return all_entries

def main():
    """Punto de entrada principal del vigilante de feeds."""
    LOG.info("--- INICIANDO FEED WATCHER ---")
    
    entries = fetch_and_parse_feeds()
    
    if not entries:
        LOG.info("No se encontraron nuevas entradas en los feeds.")
        return

    try:
        LOG.info("Conectando a la base de datos para guardar las nuevas entradas...")
        supabase = db_manager.get_supabase_client(LOG)
        
        # Usamos un set para contar las URLs únicas que intentamos añadir
        urls_to_process = {entry.link for entry in entries}
        
        for url in urls_to_process:
            db_manager.add_url_if_not_exists(supabase, LOG, url)
            
        LOG.info(f"{len(urls_to_process)} URLs de feeds procesadas y añadidas a la base de datos si no existían.")
        LOG.info("Ejecución de Feed Watcher completada con éxito.")

    except Exception as e:
        LOG.error(f"Ocurrió un error durante la conexión o el guardado en la base de datos: {e}", exc_info=True)


if __name__ == "__main__":
    main()
