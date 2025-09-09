import os
import json
import gspread
import re
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN ---
# Nombre de la hoja de cálculo de Google Sheets
GOOGLE_SHEET_NAME = 'Runa CMS'
# Ruta al archivo de plantilla
TEMPLATE_PATH = 'templates/plantilla_articulo.html'
# Ruta a la página de listado de publicaciones
PUBLICACIONES_PAGE_PATH = 'publicaciones.html'
# Directorio donde se guardarán los artículos generados
OUTPUT_DIR = 'publicaciones'

# --- FUNCIONES AUXILIARES ---
def slugify(text):
    """Convierte un texto en un nombre de archivo URL-friendly."""
    text = text.lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^a-z0-9\-]', '', text)
    return text

def get_gspread_client():
    """Autentica con Google Sheets API usando las credenciales de los secretos de GitHub."""
    creds_json_str = os.getenv('GCP_CREDENTIALS')
    if not creds_json_str:
        raise ValueError("El secreto GCP_CREDENTIALS no fue encontrado.")
    
    creds_info = json.loads(creds_json_str)
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# --- LÓGICA PRINCIPAL ---
def main():
    print("Iniciando el script de publicación...")
    try:
        # Autenticar y abrir la hoja de cálculo
        client = get_gspread_client()
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        articles = sheet.get_all_records()
        print(f"Se encontraron {len(articles)} artículos en total.")

        # Cargar la plantilla de artículo
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            article_template = f.read()

        # Crear directorio de salida si no existe
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        all_published_cards = []
        new_articles_published = False

        # Procesar cada artículo de la hoja
        for index, article in enumerate(articles, start=2): # start=2 porque gspread es 1-indexado y hay una fila de cabecera
            if article.get('Estado') == 'Listo para Publicar':
                print(f"Procesando nuevo artículo: '{article['Titulo']}'")
                new_articles_published = True

                # Rellenar plantilla
                content = article_template.replace('{{TITULO}}', article['Titulo'])
                content = content.replace('{{AUTOR}}', article['Autor'])
                content = content.replace('{{FECHA}}', article['Fecha'])
                content = content.replace('{{IMAGEN_URL}}', article['ImagenURL'])
                content = content.replace('{{CONTENIDOHTML}}', article['ContenidoHTML'])

                # Guardar nuevo archivo HTML
                slug = slugify(article['Titulo'])
                output_path = os.path.join(OUTPUT_DIR, f"{slug}.html")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Artículo guardado en: {output_path}")

                # Actualizar estado en Google Sheet
                sheet.update_cell(index, list(article.keys()).index('Estado') + 1, 'Publicado')
                print(f"Estado actualizado a 'Publicado' en Google Sheets.")

            # Generar tarjeta para la página de publicaciones (para todos los ya publicados)
            if article.get('Estado') in ['Publicado', 'Listo para Publicar']:
                slug = slugify(article['Titulo'])
                card_html = f"""
                <!-- Tarjeta de Artículo -->
                <div class="bg-white rounded-lg shadow-md overflow-hidden transform hover:-translate-y-2 transition-transform duration-300">
                    <img src="{article['ImagenURL']}" alt="Imagen del artículo" class="w-full h-48 object-cover">
                    <div class="p-6">
                        <h2 class="text-xl font-bold mb-2">{article['Titulo']}</h2>
                        <p class="text-gray-600 mb-4">{article['Resumen']}</p>
                        <a href="publicaciones/{slug}.html" class="font-semibold text-green-700 hover:text-green-800 hover:underline">Leer más &rarr;</a>
                    </div>
                </div>"""
                all_published_cards.append(card_html)

        # Actualizar la página de publicaciones si hubo cambios
        if new_articles_published:
            print("Actualizando la página de listado de publicaciones...")
            with open(PUBLICACIONES_PAGE_PATH, 'r', encoding='utf-8') as f:
                publicaciones_content = f.read()
            
            cards_grid = '\n'.join(all_published_cards)
            # Reemplazar el grid existente con el nuevo
            # Se asume que el grid está entre estos dos comentarios
            publicaciones_content = re.sub(r'(<!-- Grid de Publicaciones -->)(.*?)(<!-- Fin Grid de Publicaciones -->)', 
                                         f'\g<1>\n{cards_grid}\n\g<3>', 
                                         publicaciones_content, flags=re.DOTALL)

            with open(PUBLICACIONES_PAGE_PATH, 'w', encoding='utf-8') as f:
                f.write(publicaciones_content)
            print("Página de publicaciones actualizada.")
        else:
            print("No hay nuevos artículos para publicar.")

    except Exception as e:
        print(f"Ha ocurrido un error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
