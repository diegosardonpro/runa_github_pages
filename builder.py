import os
import json
import re
import gspread
import jinja2
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN ---
# ID del archivo de Google Sheets (de la URL)
GOOGLE_SHEET_ID = '1yGmAxcIVwMOE31iC_B6iNWAtTrro_JiYaeKdFHp3TAE'
TEMPLATES_DIR = 'templates'
ARTICLE_TEMPLATE = 'articulo_plantilla.html'
PUBLICACIONES_TEMPLATE = 'publicaciones_plantilla.html'
PUBLICACIONES_OUTPUT_PATH = 'publicaciones.html'
ARTICLES_OUTPUT_DIR = 'publicaciones'

# --- FUNCIONES AUXILIARES ---
def slugify(text):
    """Convierte un texto en un nombre de archivo URL-friendly."""
    if not text: return ''
    text = str(text).lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^a-z0-9\-]', '', text)
    return text.strip('-')

def get_gspread_client():
    """Autentica con Google Sheets API usando las credenciales de los secretos de GitHub."""
    creds_json_str = os.getenv('GCP_CREDENTIALS')
    if not creds_json_str:
        raise ValueError("El secreto GCP_CREDENTIALS no fue encontrado. Asegúrate de configurarlo en GitHub.")
    
    creds_info = json.loads(creds_json_str)
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# --- LÓGICA PRINCIPAL ---
def main():
    print("Iniciando el generador de sitio v2.0...")
    try:
        # 1. Configurar Jinja2
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIR), autoescape=True)
        article_template = env.get_template(ARTICLE_TEMPLATE)
        publicaciones_template = env.get_template(PUBLICACIONES_TEMPLATE)

        # 2. Obtener datos de Google Sheets
        client = get_gspread_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        all_articles = sheet.get_all_records()
        print(f"Se encontraron {len(all_articles)} filas en total en la hoja de cálculo.")

        # 3. Filtrar y preparar artículos publicados
        published_articles = [article for article in all_articles if article.get('Estado') == 'Publicado']
        if not published_articles:
            print("No se encontraron artículos con estado 'Publicado'. No se generará ningún archivo.")
            return

        print(f"Se encontraron {len(published_articles)} artículos para publicar.")

        # Añadir 'Slug' a cada artículo para usar en las URLs
        for article in published_articles:
            article['Slug'] = slugify(article['Titulo'])

        # 4. Generar páginas de artículos individuales
        os.makedirs(ARTICLES_OUTPUT_DIR, exist_ok=True)
        for article in published_articles:
            article_id = article.get('ID')
            if not article_id:
                print(f"ADVERTENCIA: El artículo '{article['Titulo']}' no tiene ID y será omitido.")
                continue
            
            print(f"Generando artículo ID {article_id}: {article['Titulo']}")
            content = article_template.render(article)
            output_filename = f"{article_id}-{article['Slug']}.html"
            output_path = os.path.join(ARTICLES_OUTPUT_DIR, output_filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 5. Generar la página principal de publicaciones
        print("Generando la página de publicaciones principal...")
        publicaciones_content = publicaciones_template.render(articles=published_articles)
        with open(PUBLICACIONES_OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(publicaciones_content)

        print("¡Generación del sitio completada con éxito!")

    except Exception as e:
        print(f"Ha ocurrido un error durante la generación del sitio: {e}")
        exit(1)

if __name__ == "__main__":
    main()