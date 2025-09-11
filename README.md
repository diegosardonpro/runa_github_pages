# Proyecto Runa: Curador de Contenido Automatizado

## 1. Resumen

Runa es un worker automatizado diseñado para procesar URLs de artículos web, extraer su contenido de texto y, lo más importante, identificar, analizar y seleccionar las imágenes más relevantes de dichos artículos. Utiliza un sistema de filtrado inteligente de 3 capas para asegurar la calidad y relevancia de las imágenes curadas.

## 2. Características Principales

- **Procesamiento de URLs:** Monitorea una tabla en la base de datos (`urls_para_procesar`) en busca de nuevos artículos para analizar.
- **Filtrado Inteligente de 3 Capas:**
  - **Capa 1 (Estructural):** Analiza la estructura DOM de la página para buscar imágenes únicamente dentro del contenido principal del artículo (ej. dentro de la etiqueta `<article>`), ignorando logos y banners de la cabecera o pie de página.
  - **Capa 2 (Heurístico):** Revisa los atributos de las imágenes para descartar rápidamente aquellas que son muy pequeñas, tienen formatos de icono (como `.svg`) o contienen palabras clave irrelevantes en su URL (como `avatar`, `logo`, `badge`). Es compatible con "Lazy Loading" al priorizar el atributo `data-src`.
  - **Capa 3 (Semántico):** Utiliza un modelo de IA de visión (Gemini Pro Vision) para realizar un análisis final. La IA clasifica la imagen (`fotografia_principal`, `grafico_o_diagrama`, etc.) y determina si es relevante para el contexto de un artículo, descartando el resto.
- **Almacenamiento Automatizado:** Las imágenes aprobadas se descargan y se suben a un servicio de almacenamiento en la nube (Supabase Storage), y sus metadatos se guardan en la base de datos.

## 3. Arquitectura y Archivos Clave

- `curator.py`: El orquestador principal. Inicia el proceso, busca URLs pendientes y coordina a los otros módulos.
- `src/content_processor.py`: El cerebro del sistema. Se encarga de la navegación web (Playwright), el parseo de HTML (BeautifulSoup) y la ejecución de los filtros de 3 capas, incluyendo la llamada al modelo de IA.
- `src/db_manager.py`: Gestiona toda la interacción con la base de datos de Supabase, incluyendo la definición del esquema y las operaciones de guardado.
- `run_test_cycle.py`: Un script de utilidad para automatizar las pruebas. Resetea el estado de las URLs en la base de datos y ejecuta `curator.py`.

## 4. Configuración

1.  **Instalar Dependencias:** Asegúrate de tener todas las librerías necesarias.
    ```bash
    pip install -r requirements.txt
    ```
2.  **Variables de Entorno:** Crea un archivo `.env` en la raíz del proyecto (`runa_github_pages/.env`) con las siguientes claves:
    ```
    SUPABASE_URL="la_url_de_tu_proyecto_supabase"
    SUPABASE_SERVICE_KEY="tu_service_key_de_supabase"
    GEMINI_API_KEY="tu_api_key_de_google_gemini"
    ```

## 5. Uso

Hay dos formas de ejecutar el sistema:

### a) Ejecución Única del Worker

Para procesar las URLs pendientes una sola vez.

```bash
python curator.py
```

### b) Ciclo de Pruebas Automatizado

Para resetear todas las URLs a "pendiente" y luego ejecutar el worker. Ideal para depuración y pruebas repetidas.

```bash
python run_test_cycle.py
```