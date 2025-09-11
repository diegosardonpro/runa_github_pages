# Handover para Sucesor del Proyecto Runa

**Para:** Agente Sucesor con Contexto Refrescado
**De:** Agente Predecesor
**Fecha:** 2025-09-11

## 1. Contexto del Proyecto

El Proyecto Runa es un pipeline de curación de contenido. El flujo de trabajo final y estable es:

1.  **Frontend:** Un panel estático (`panel_de_control.html`) en una URL pública de GitHub Pages.
2.  **Envío:** El usuario envía una URL a través del panel. El panel realiza una llamada `fetch` a una Edge Function de Supabase.
3.  **Intermediario:** La **Edge Function** recibe la URL y la inserta de forma segura en la tabla `urls_para_procesar` de la base de datos de Supabase.
4.  **Backend:** Una **Acción de GitHub** (`.github/workflows/run_curator.yml`) se ejecuta de forma programada (cada 15 min) o manual.
5.  **Procesamiento:** La acción ejecuta el script `curator.py`, que lee las URLs pendientes de la base de datos, las procesa (usando Playwright y Gemini AI), y guarda los resultados (metadatos y URLs de imágenes en Supabase Storage) en las tablas `activos` e `imagenes`.

## 2. Estado Actual del Código

- El código es **estable** y la arquitectura está **validada**.
- El script principal del worker es `curator.py`.
- La estructura de la base de datos es gestionada por `src/db_manager.py` y consta de 3 tablas.
- El frontend es `panel_de_control.html`.
- **Lección Clave:** El proyecto pasó por muchas iteraciones (apps locales, `.exe`, `config.js`). La arquitectura actual fue elegida por ser la más robusta y tener la mejor experiencia de usuario. No intentes volver a un flujo de trabajo de archivos locales; causó numerosos problemas de seguridad y de carga de scripts en el navegador.

## 3. Instrucciones para Futuras Tareas

- **Revisar Documentación:** Antes de cualquier cambio, lee el archivo `README_PROYECTO_FINAL.md` para entender la arquitectura completa.
- **Cambios en el Backend (`curator.py`):** Realiza los cambios y súbelos con `git push`. La Acción de GitHub usará automáticamente el nuevo código en su próxima ejecución.
- **Cambios en el Frontend (`panel_de_control.html`):** Realiza los cambios y súbelos con `git push`. La acción `deploy.yml` (si existe) o la configuración de GitHub Pages actualizará el sitio web. Asegúrate de no introducir claves o secretos en el código del frontend.
- **Cambios en la Base de Datos:** Modifica el `SCHEMA_SQL` en `src/db_manager.py`. Después de subir el cambio, deberás ejecutar manualmente el `curator.py` con el flag `--setup-db` una vez para aplicar los cambios, ya sea localmente (si tienes un `.env` configurado) o modificando temporalmente la Acción de GitHub.
