# Runa - Sistema de Curación de Activos Digitales (v3.0)

Este repositorio contiene el motor de automatización para el proyecto Runa, una iniciativa dedicada a visibilizar y combatir la desigualdad a través del análisis de información y la promoción de los derechos humanos y ambientales.

## Misión del Proyecto

El objetivo de este sistema no es solo tecnológico, sino social. Busca proporcionar las herramientas para una "Investigación Anfibia", integrando y analizando información de diversas fuentes para apoyar la toma de decisiones, fortalecer la participación ciudadana y amplificar las voces de comunidades vulnerables, todo ello guiado por un estricto **[Marco Ético](MARCO_ETICO.md)**.

## Arquitectura del Sistema (v3.0 - Normalizada)

El sistema ha evolucionado a una arquitectura de base de datos normalizada y un procesamiento de IA en dos fases para maximizar la escalabilidad, la calidad del dato y la mantenibilidad.

- **Base de Datos Relacional:** Hemos abandonado la tabla única en favor de un schema profesional:
    - **`activos`:** Una tabla central que registra cada activo y su tipo (ej. `ARTICULO_TEXTO`).
    - **`metadata_articulos`:** Una tabla especializada que guarda la información extraída de artículos (título, resumen, etc.), vinculada a la tabla `activos`.
    - **`metadata_imagenes`:** Preparada para el futuro, guardará información específica de activos de imagen.

- **`curator.py` (Orquestador Inteligente):** Dirige el flujo de trabajo. Primero pide a la IA que clasifique el tipo de activo de una URL y luego invoca al módulo de procesamiento correcto para ese tipo.

- **`src/db_manager.py` (Guardián de la Base de Datos):** Encapsula toda la lógica de la nueva estructura de base de datos, incluyendo la creación del schema y las funciones para guardar datos en las tablas relacionadas.

- **`src/content_processor.py` (Cerebro de IA Especializado):** Contiene la lógica para el proceso de dos pasos: una función para **clasificar** y funciones especializadas para **extraer** metadatos de cada tipo de activo, cada una con su propio prompt optimizado.

## Flujo de Trabajo de Curación (v3.0)

1.  **Entrada:** Se añade una URL a la tabla `urls_para_procesar`.
2.  **Ejecución:** El workflow de GitHub Actions ejecuta `curator.py`.
3.  **Clasificación:** La IA determina el tipo de activo de la URL (ej. `ARTICULO_TEXTO`).
4.  **Extracción Especializada:** Se invoca la función de procesamiento correspondiente al tipo de activo, usando un prompt específico para extraer los metadatos relevantes.
5.  **Almacenamiento Relacional:** Los datos se guardan de forma estructurada: un registro en `activos` y los metadatos correspondientes en `metadata_articulos` (o la tabla que corresponda).
6.  **Salida:** Una base de datos normalizada de activos curados, clasificados y con metadatos de alta calidad.

## Herramientas de Utilidad

### `download_all_images.py`

**Propósito:**
Esta herramienta sirve para descargar en lote las imágenes de todos los activos de tipo artículo que ya han sido curados. Es ideal para preparar el lanzamiento de una web o para análisis de imágenes locales.

**Uso:**
```bash
# Desde la carpeta raíz del proyecto (runa_github_pages)
python download_all_images.py
```

## Configuración y Uso del Workflow

1.  **¡IMPORTANTE! Migración a v3.0:** Esta versión introduce cambios estructurales en la base de datos. Antes de la primera ejecución, debes limpiar las tablas antiguas para permitir que la nueva estructura se cree correctamente. Conéctate a tu base de datos de Supabase y ejecuta el siguiente script SQL:

    ```sql
    -- Script de limpieza para la transición a v3.0
    -- Elimina la tabla dependiente primero para evitar errores.
    DROP TABLE IF EXISTS public.encuestas_anonimas;

    -- Elimina las tablas de la arquitectura v2.0 y v3.0 para un inicio limpio.
    DROP TABLE IF EXISTS public.metadata_articulos;
    DROP TABLE IF EXISTS public.metadata_imagenes;
    DROP TABLE IF EXISTS public.activos_curados; -- Tabla antigua
    DROP TABLE IF EXISTS public.activos;       -- Nueva tabla central
    ```

2.  **Secretos de GitHub:** Asegúrate de que los siguientes secretos están configurados en tu repositorio:
    *   `SUPABASE_URL`
    *   `SUPABASE_SERVICE_KEY`
    *   `GEMINI_API_KEY`

3.  **Ejecución:** Para procesar nuevas URLs, activa el workflow "Curador de Activos" desde la pestaña "Actions" de tu repositorio.
