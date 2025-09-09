# Contexto de Reinicio y Directiva para Continuación (Handover v3.2)

## 1. Misión Actual: Implementar la Arquitectura de Visión (v3.2)

El objetivo estratégico es pivotar desde la extracción de enlaces de texto (tarea que se ha demostrado poco fiable) hacia el **análisis de contenido visual**. El sistema debe ser capaz de, dentro de un artículo de texto, identificar las imágenes, analizarlas con un modelo de IA con capacidad de visión para generar etiquetas descriptivas, y descargar un máximo de 5 imágenes por ejecución.

## 2. Estado del Proyecto (Dónde nos quedamos):

El trabajo de refactorización está avanzado en un 66%. Se han completado dos de las tres fases críticas:

- **FASE 1: Base de Datos (COMPLETADA):**
    - El archivo `src/db_manager.py` ha sido completamente refactorizado.
    - El schema de la base de datos (v3.2) ya está definido en el código, eliminando la tabla `enlaces_extraidos` y rediseñando `metadata_imagenes` para que pueda almacenar los nuevos datos que generará la IA de visión (ej. `tags_visuales_ia`).

- **FASE 2: Procesador de Contenido (COMPLETADA):**
    - El archivo `src/content_processor.py` ha sido refactorizado.
    - Ahora contiene la lógica de IA en dos pasos: `classify_url_type` para determinar el tipo de activo, `extract_article_metadata` que ahora extrae una **lista de URLs de imágenes**, y la nueva función `analyze_image_with_vision` que está lista para analizar una imagen y devolver tags.

## 3. Instrucción Inmediata para la Versión Refrescada (Tu Tarea Pendiente):

Tu única tarea restante es la **FASE 3: Actualizar el orquestador `curator.py`**.

Debes modificar la lógica principal del script para que orqueste el nuevo flujo de trabajo de visión. Específicamente, en el bucle que procesa cada URL de tipo `ARTICULO_TEXTO`, debes:

1.  Después de extraer los metadatos del artículo, obtener la **lista de URLs de imágenes** que devuelve la función `extract_article_metadata`.
2.  Aplicar la restricción del usuario: tomar solo las **primeras 5 imágenes** de esa lista.
3.  Crear un **nuevo bucle** que itere sobre esas 5 (o menos) imágenes.
4.  Dentro de este nuevo bucle, para cada imagen, debes llamar a:
    -   `content_processor.analyze_image_with_vision()` para obtener los tags y la descripción visual.
    -   `content_processor.download_image()` para descargar el archivo de la imagen.
    -   `db_manager.save_image_metadata()` para guardar toda esta nueva información en la base de datos.

El objetivo final de tu labor es que `curator.py` ensamble correctamente estas piezas, completando así la implementación de la arquitectura v3.2.
