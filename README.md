# Runa - Sistema de Curación de Activos Digitales

Este repositorio contiene el motor de automatización para el proyecto Runa, una iniciativa dedicada a visibilizar y combatir la desigualdad a través del análisis de información y la promoción de los derechos humanos y ambientales.

## Misión del Proyecto

El objetivo de este sistema no es solo tecnológico, sino social. Busca proporcionar las herramientas para una "Investigación Anfibia", integrando y analizando información de diversas fuentes para apoyar la toma de decisiones, fortalecer la participación ciudadana y amplificar las voces de comunidades vulnerables, todo ello guiado por un estricto **[Marco Ético](MARCO_ETICO.md)**.

## Arquitectura del Sistema

El sistema está diseñado con una arquitectura modular y desacoplada para garantizar su robustez, mantenibilidad y escalabilidad.

- **`curator.py` (Orquestador Principal):** Es el punto de entrada del sistema. Su única responsabilidad es orquestar el flujo de trabajo, llamando a los módulos especializados en el orden correcto.

- **`src/db_manager.py` (Gestor de Base de Datos):** Este módulo encapsula toda la interacción con la base de datos de Supabase. Se encarga de la creación de la infraestructura (tablas) y de todas las operaciones de lectura y escritura de datos.

- **`src/content_processor.py` (Procesador de Contenido):** Es el "cerebro" del sistema. Contiene la lógica para:
    1.  **Web Scraping:** Extraer texto e imágenes de URLs.
    2.  **Enriquecimiento con IA:** Utilizar modelos de lenguaje (Gemini) para analizar el texto, generar resúmenes y proponer etiquetas (tags).
    3.  **Gestión de Activos:** Descargar las imágenes y guardarlas localmente.

- **`src/utils/logger.py` (Módulo de Logging):** Proporciona un sistema de logging centralizado para registrar cada paso del proceso, facilitando la depuración y la monitorización.

- **`.github/workflows/curator.yml` (Workflow de CI/CD):** Define la automatización en GitHub Actions, que ejecuta el orquestador `curator.py` de forma manual o programada.

## Flujo de Trabajo de Curación

1.  **Entrada (Input):** Un usuario añade una o más URLs a la tabla `urls_para_procesar` en la base de datos de Supabase, con el estado `pendiente`.
2.  **Ejecución:** El workflow de GitHub Actions se activa (manual o automáticamente).
3.  **Procesamiento:** El script `curator.py` se ejecuta:
    a. Lee las URLs pendientes.
    b. Para cada URL, el `content_processor` extrae el contenido, lo enriquece con IA y descarga la imagen.
    c. El `db_manager` guarda el resultado final (texto, tags, ruta de la imagen local) en la tabla `activos_curados`.
    d. Se actualiza el estado de la URL procesada a `completado`.
4.  **Salida (Output):** Una base de datos estructurada y enriquecida con activos digitales curados, listos para el análisis.

## Configuración y Uso

1.  **Secretos de GitHub:** Asegúrate de que los siguientes secretos están configurados en tu repositorio:
    *   `SUPABASE_URL`
    *   `SUPABASE_SERVICE_KEY`
    *   `GEMINI_API_KEY`

2.  **Ejecución:** Para procesar nuevas URLs, activa el workflow "Curador de Activos" desde la pestaña "Actions" de tu repositorio.
