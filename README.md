# Runa - Sistema de Curación de Activos Digitales

Este repositorio contiene el motor de automatización para el proyecto Runa, una iniciativa dedicada a visibilizar y combatir la desigualdad a través del análisis de información y la promoción de los derechos humanos y ambientales.

## Misión del Proyecto

El objetivo de este sistema no es solo tecnológico, sino social. Busca proporcionar las herramientas para una "Investigación Anfibia", integrando y analizando información de diversas fuentes para apoyar la toma de decisiones, fortalecer la participación ciudadana y amplificar las voces de comunidades vulnerables, todo ello guiado por un estricto **[Marco Ético](MARCO_ETICO.md)**.

## Arquitectura del Sistema (v2.0 - Modular)

El sistema opera bajo una arquitectura modular y desacoplada para gestionar la complejidad y facilitar el mantenimiento.

- **`curator.py` (El Orquestador):** Es el punto de entrada y el director de orquesta. No contiene lógica de negocio compleja. Su única tarea es llamar a los módulos especializados en el orden correcto para procesar URLs de artículos.

- **`src/db_manager.py` (El Guardián de la Base de Datos):** Encapsula toda la interacción con la base de datos de Supabase. Gestiona tanto la creación de la infraestructura (tablas, funciones) como las operaciones de datos del día a día (leer, insertar, actualizar).

- **`src/content_processor.py` (El Cerebro de IA):** Contiene la lógica de procesamiento de contenido. Esto incluye el web scraping para extraer datos de una URL, el enriquecimiento del texto usando la API de Gemini, y la gestión de activos como la descarga de imágenes.

## Flujo de Trabajo de Curación

1.  **Entrada:** Se añade una URL a la tabla `urls_para_procesar`.
2.  **Ejecución:** El workflow de GitHub Actions ejecuta `curator.py`.
3.  **Procesamiento:** Para cada URL, el orquestador invoca a los módulos para extraer, enriquecer con IA y descargar los activos.
4.  **Almacenamiento:** Los datos se guardan en la tabla `activos_curados`.
5.  **Salida:** Una base de datos de activos curados, con metadatos enriquecidos.

## Herramientas de Utilidad

### `download_all_images.py`

**Propósito:**
Esta herramienta sirve para descargar en lote las imágenes de todos los activos que ya han sido curados y guardados en la base de datos. El flujo de trabajo normal solo descarga la imagen de las nuevas URLs que procesa; este script es para poblar tu carpeta local con las imágenes de *todo* tu histórico de activos. Es ideal para preparar el lanzamiento de una web o para análisis de imágenes locales.

**Funcionamiento Detallado:**
1.  **Conexión Segura:** Inicia una conexión con la base de datos de Supabase.
2.  **Búsqueda Inteligente:** No descarga todo ciegamente. Busca únicamente los activos que tienen una `url_imagen_original` registrada pero cuya `ruta_imagen_local` está vacía (`null`). Esto asegura que solo descarga las imágenes que faltan.
3.  **Bucle de Descarga:** Itera sobre cada activo pendiente y realiza las siguientes acciones:
    *   Descarga la imagen desde la `url_imagen_original`.
    *   La guarda en la carpeta `output_images`.
    *   Nombra el archivo de imagen usando el `id` único del activo (ej: `42.jpg`), asegurando que no haya conflictos y que cada imagen esté directamente asociada a su activo.
4.  **Actualización de la Base de Datos:** Una vez que la imagen se ha descargado correctamente, el script actualiza la fila del activo en la tabla `activos_curados`, rellenando el campo `ruta_imagen_local` con la ruta del archivo recién guardado (ej: `output_images/42.jpg`).

**Uso:**
Este script se ejecuta manualmente desde tu entorno local. Asegúrate de tener las dependencias instaladas (`pip install -r requirements.txt`) y las variables de entorno (`.env`) configuradas.

```bash
# Desde la carpeta raíz del proyecto (runa_github_pages)
python download_all_images.py
```

## Configuración y Uso del Workflow

1.  **Secretos de GitHub:** Asegúrate de que los siguientes secretos están configurados en tu repositorio:
    *   `SUPABASE_URL`
    *   `SUPABASE_SERVICE_KEY`
    *   `GEMINI_API_KEY`

2.  **Ejecución:** Para procesar nuevas URLs, activa el workflow "Curador de Activos" desde la pestaña "Actions" de tu repositorio.