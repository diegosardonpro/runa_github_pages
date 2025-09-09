# Runa - Sistema de Curación de Activos Digitales

Este repositorio contiene el motor de automatización para el proyecto Runa, una iniciativa dedicada a visibilizar y combatir la desigualdad a través del análisis de información y la promoción de los derechos humanos y ambientales.

## Misión del Proyecto

El objetivo de este sistema no es solo tecnológico, sino social. Busca proporcionar las herramientas para una "Investigación Anfibia", integrando y analizando información de diversas fuentes para apoyar la toma de decisiones, fortalecer la participación ciudadana y amplificar las voces de comunidades vulnerables, todo ello guiado por un estricto **[Marco Ético](MARCO_ETICO.md)**.

## Arquitectura del Sistema (v2.0 - Basada en Clases)

El sistema ha evolucionado a una arquitectura polimórfica y modular que distingue entre diferentes "clases" de activos digitales.

- **`curator.py` (Orquestador Principal):** Orquesta el flujo de "Clasificar y Procesar". Primero, usa un modelo de IA para clasificar el tipo de contenido en una URL (ej. 'imagen', 'texto'). Luego, invoca el módulo de procesamiento adecuado para esa clase de activo.

- **`src/db_manager.py`:** Gestiona la comunicación con la base de datos de Supabase, que ahora incluye una tabla central `activos` y tablas de metadatos especializadas (ej. `metadata_imagenes`).

- **`src/content_processor.py`:** Contiene los "cerebros" de procesamiento para cada clase de activo. Incluye funciones para extraer metadatos específicos usando prompts de IA especializados, y para gestionar tareas como la descarga de imágenes.

## Flujo de Trabajo de Curación

1.  **Entrada:** Se añade una URL a la tabla `urls_para_procesar`.
2.  **Ejecución:** El workflow de GitHub Actions ejecuta `curator.py`.
3.  **Clasificación:** El script determina el tipo de activo en la URL.
4.  **Procesamiento Especializado:** Se ejecuta la cadena de funciones para esa clase específica (ej. para una imagen, se extraen sus metadatos visuales y se descarga).
5.  **Almacenamiento Estructurado:** Los datos se guardan en las tablas correspondientes (`activos` y la tabla de metadatos relevante).
6.  **Salida:** Una base de datos de activos curados, clasificados y con metadatos enriquecidos.

## Configuración y Uso

1.  **Secretos de GitHub:** Asegúrate de que los siguientes secretos están configurados en tu repositorio:
    *   `SUPABASE_URL`
    *   `SUPABASE_SERVICE_KEY`
    *   `GEMINI_API_KEY`

2.  **Ejecución:** Para procesar nuevas URLs, activa el workflow "Curador de Activos" desde la pestaña "Actions" de tu repositorio.
