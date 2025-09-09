import os
import re
import jinja2
from supabase import create_client, Client
from src.utils.logger import get_logger

# --- CONFIGURACIÓN ---
LOGGER = get_logger(__name__)
TEMPLATES_DIR = 'templates'
ARTICLE_TEMPLATE = 'articulo_plantilla.html'
PUBLICACIONES_TEMPLATE = 'publicaciones_plantilla.html'
PUBLICACIONES_OUTPUT_PATH = 'publicaciones.html'
ARTICLES_OUTPUT_DIR = 'publicaciones'

# --- FUNCIONES AUXILIARES ---
def slugify(text):
    if not text: return ''
    text = str(text).lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^a-z0-9\-]', '', text)
    return text.strip('-')

def get_supabase_client():
    """Crea y devuelve un cliente de Supabase autenticado."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    if not url or not key:
        LOGGER.error("Los secretos SUPABASE_URL o SUPABASE_SERVICE_KEY no fueron encontrados.")
        raise ValueError("Credenciales de Supabase no configuradas.")
    LOGGER.info("Cliente de Supabase creado exitosamente.")
    return create_client(url, key)

# --- LÓGICA DE CONSTRUCCIÓN DEL SITIO ---
def main():
    LOGGER.info("--- Iniciando Publicador de Contenido v3.0 (Supabase) ---")
    try:
        supabase = get_supabase_client()
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIR), autoescape=True)
        article_template = env.get_template(ARTICLE_TEMPLATE)
        publicaciones_template = env.get_template(PUBLICACIONES_TEMPLATE)

        # 1. Buscar y procesar artículos listos para publicar
        LOGGER.info("Buscando artículos con estado 'Listo para Publicar'...")
        response = supabase.table('articulos').select('*').eq('estado', 'Listo para Publicar').execute()
        articles_to_publish = response.data

        if not articles_to_publish:
            LOGGER.info("No hay nuevos artículos para publicar en este ciclo.")
        else:
            LOGGER.info(f"Se encontraron {len(articles_to_publish)} artículo(s) para publicar.")
            os.makedirs(ARTICLES_OUTPUT_DIR, exist_ok=True)
            ids_to_update = []

            for article in articles_to_publish:
                article['slug'] = slugify(article['titulo'])
                LOGGER.info(f"Generando página para ID {article['id']}: {article['titulo']}")
                content = article_template.render(article=article)
                output_path = os.path.join(ARTICLES_OUTPUT_DIR, f"{article['id']}-{article['slug']}.html")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                ids_to_update.append(article['id'])

            # 2. Actualizar el estado de los artículos publicados
            if ids_to_update:
                LOGGER.info(f"Actualizando estado a 'Publicado' para IDs: {ids_to_update}")
                supabase.table('articulos').update({'estado': 'Publicado'}).in_('id', ids_to_update).execute()

        # 3. Regenerar la página de publicaciones con TODOS los artículos publicados
        LOGGER.info("Regenerando la página de publicaciones principal...")
        response = supabase.table('articulos').select('*').eq('estado', 'Publicado').order('fecha_publicacion', desc=True).execute()
        all_published_articles = response.data

        for article in all_published_articles:
            article['slug'] = slugify(article['titulo'])

        publicaciones_content = publicaciones_template.render(articles=all_published_articles)
        with open(PUBLICACIONES_OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(publicaciones_content)
        LOGGER.info(f"Página de publicaciones regenerada con {len(all_published_articles)} artículo(s).")

        LOGGER.info("\n¡Proceso de publicación completado con éxito!")

    except Exception as e:
        LOGGER.error(f"Ha ocurrido un error fatal durante la publicación: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()