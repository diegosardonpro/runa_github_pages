# Runa - Sistema de Curación de Activos Digitales (v3.1)

Este repositorio contiene el motor de automatización para el proyecto Runa, una iniciativa dedicada a visibilizar y combatir la desigualdad a través del análisis de información y la promoción de los derechos humanos y ambientales.

## Misión del Proyecto

El objetivo de este sistema no es solo tecnológico, sino social. Busca proporcionar las herramientas para una "Investigación Anfibia", integrando y analizando información de diversas fuentes para apoyar la toma de decisiones, fortalecer la participación ciudadana y amplificar las voces de comunidades vulnerables, todo ello guiado por un estricto **[Marco Ético](MARCO_ETICO.md)**.

## Arquitectura del Sistema (v3.1 - Análisis de Enlaces)

El sistema utiliza una arquitectura de base de datos normalizada y un procesamiento de IA en dos fases para maximizar la escalabilidad, la calidad del dato y la mantenibilidad.

- **Base de Datos Relacional:**
    - **`activos`:** Tabla central que registra cada activo y su tipo (ej. `ARTICULO_TEXTO`).
    - **`metadata_articulos`:** Tabla especializada para metadatos de artículos (título, resumen, etc.).
    - **`enlaces_extraidos`:** ¡NUEVO! Tabla que almacena cada URL encontrada dentro de un artículo, creando un mapa de relaciones.
    - **`metadata_imagenes`:** Preparada para el futuro, para activos de imagen.

- **`curator.py` (Orquestador Inteligente):** Dirige el flujo de trabajo. Clasifica el tipo de activo y luego invoca al módulo de procesamiento correcto.

- **`src/db_manager.py` (Guardián de la Base de Datos):** Encapsula toda la lógica de la base de datos, incluyendo la creación del schema y las funciones para guardar datos en todas las tablas relacionadas.

- **`src/content_processor.py` (Cerebro de IA Especializado):** Contiene la lógica para el proceso de dos pasos: una función para **clasificar** y funciones especializadas para **extraer** metadatos y ahora también **todos los enlaces** de cada tipo de activo.

## Estado Actual del Sistema (Hito v3.1)

- **Éxito Funcional:** El motor para procesar `ARTICULO_TEXTO` es robusto. El sistema clasifica, extrae metadatos, **extrae todos los enlaces internos y externos**, guarda en la estructura relacional y descarga la imagen asociada.
- **Manejo Inteligente de Tipos:** El sistema identifica y aparta correctamente los tipos de activos no soportados (ej. `VIDEO`).
- **Limitación Conocida (Resiliencia):** La IA puede ocasionalmente proporcionar URLs de imágenes inválidas (error 404). El sistema maneja este error de forma robusta, registrándolo y continuando con la curación del resto de los datos.

## Flujo de Trabajo de Curación (v3.1)

1.  **Entrada:** Se añade una URL a la tabla `urls_para_procesar`.
2.  **Ejecución:** El workflow de GitHub Actions ejecuta `curator.py`.
3.  **Clasificación:** La IA determina el tipo de activo de la URL.
4.  **Extracción Especializada:** Se invoca la función de procesamiento para extraer metadatos Y todos los enlaces del contenido.
5.  **Almacenamiento Relacional:** Los datos se guardan en las tablas `activos`, `metadata_articulos` y `enlaces_extraidos`.

## Herramientas de Utilidad

### `download_all_images.py`

**Propósito:**
Descargar en lote las imágenes de todos los activos de tipo artículo ya curados.

**Uso:**
```bash
python download_all_images.py
```

## Configuración y Uso del Workflow

1.  **¡IMPORTANTE! Migración a v3.1:** Esta versión añade una nueva tabla. Antes de la primera ejecución, debes limpiar las tablas antiguas para permitir que la nueva estructura se cree correctamente. Conéctate a tu base de datos de Supabase y ejecuta el script SQL de limpieza más reciente.

2.  **Secretos de GitHub:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`.

3.  **Ejecución:** Activa el workflow "Curador de Activos" desde la pestaña "Actions" de tu repositorio.
