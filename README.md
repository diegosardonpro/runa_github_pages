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

## Estado Actual del Sistema (Hito v3.0)

Tras un ciclo de refactorización y depuración intensivo, el sistema ha alcanzado un estado de **Producto Mínimo Viable (MVP)**, robusto y funcional.

- **Éxito Funcional:** El motor principal para procesar activos de tipo `ARTICULO_TEXTO` está 100% operativo. El sistema clasifica, extrae, guarda en la nueva estructura relacional y descarga la imagen asociada.
- **Manejo Inteligente de Tipos:** El sistema es capaz de clasificar diferentes tipos de activos (ej. `VIDEO`) y marcarlos como no soportados sin detener la ejecución, demostrando la resiliencia del orquestador.
- **Limitación Conocida (Resiliencia):** Se ha observado que la IA puede, en ocasiones, proporcionar URLs de imágenes que ya no existen (resultando en un error `404 Not Found`). El sistema actual es robusto ante este fallo: registra el error en el log, pero completa exitosamente la curación del resto de los metadatos del artículo. No se considera un bug del código, sino una característica del comportamiento de la IA que manejamos correctamente.

## Flujo de Trabajo de Curación (v3.0)

1.  **Entrada:** Se añade una URL a la tabla `urls_para_procesar`.
2.  **Ejecución:** El workflow de GitHub Actions ejecuta `curator.py`.
3.  **Clasificación:** La IA determina el tipo de activo de la URL.
4.  **Extracción Especializada:** Se invoca la función de procesamiento correspondiente.
5.  **Almacenamiento Relacional:** Los datos se guardan en las tablas `activos` y `metadata_articulos`.

## Herramientas de Utilidad

### `download_all_images.py`

**Propósito:**
Descargar en lote las imágenes de todos los activos de tipo artículo ya curados.

**Uso:**
```bash
python download_all_images.py
```

## Configuración y Uso del Workflow

1.  **¡IMPORTANTE! Migración a v3.0:** Antes de la primera ejecución, debes limpiar las tablas antiguas con el script SQL proporcionado.

2.  **Secretos de GitHub:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`.

3.  **Ejecución:** Activa el workflow "Curador de Activos" desde la pestaña "Actions" de tu repositorio.