# Proyecto Runa v10.0 - Documentación Final

## 1. Meta-documentación y Filosofía ("Nuestra Vibra")

El desarrollo de Runa fue un proceso iterativo centrado en la **simplificación robusta**. Se exploraron múltiples arquitecturas (aplicación de escritorio, panel web con `config.js`, etc.), pero cada una presentó complejidades o puntos de fricción. La lección fundamental del proyecto es que la arquitectura correcta es aquella que es simple, segura y funcional, y que a veces es necesario pivotar drásticamente para alcanzar ese objetivo.

### Lecciones Clave de la Depuración:
- **La Complejidad es el Enemigo:** Intentar soluciones "profesionales" como Funciones Serverless o empaquetados `.exe` sin una necesidad clara introdujo errores de configuración, seguridad y entorno que nos desviaron del objetivo.
- **Validar Supuestos:** Los errores más persistentes surgieron de suposiciones sobre el entorno de ejecución (rutas de archivos, variables de entorno en GitHub vs. local, políticas de seguridad de navegadores y Supabase).
- **El Flujo de Trabajo del Usuario es Rey:** La solución final se eligió no por ser la más elegante técnicamente, sino por ser la más simple y directa para el usuario final.

## 2. Arquitectura Final (v10.0 - Serverless Frontend)

El sistema en su estado final y funcional se compone de tres partes desacopladas:

1.  **Frontend (Panel de Control):** Un archivo `panel_de_control.html` estático, desplegado en GitHub Pages. Su única función es capturar una URL y enviarla a la Función Serverless.
2.  **Intermediario (La Función Segura):** Una **Edge Function** de Supabase que actúa como una API pública. Recibe la URL y la inserta de forma segura en la tabla `urls_para_procesar`.
3.  **Backend (El Worker Asíncrono):** El script `curator.py`, ejecutado por una **Acción de GitHub** (`run_curator.yml`) que se activa de forma programada (o manual).

## 3. Estructura de la Base de Datos (Optimizada)

La base de datos final consta de solo 3 tablas esenciales:
- `urls_para_procesar`: La cola de trabajo.
- `activos`: Almacena los metadatos principales de cada URL procesada.
- `imagenes`: Almacena la información de cada imagen extraída, incluyendo su URL en Supabase Storage.

## 4. Guía de Uso Final

1.  **Añadir Tareas:** Abrir la URL pública del [Panel de Control](https://diegosardonpro.github.io/runa_github_pages/panel_de_control.html), pegar una URL y hacer clic en "Enviar".
2.  **Procesamiento:** La Acción de GitHub se ejecuta automáticamente cada 15 minutos. Opcionalmente, se puede activar manualmente desde la pestaña "Actions" del repositorio.
3.  **Verificar Resultados:** Los resultados aparecen en las tablas `activos` e `imagenes` en el panel de Supabase.

## 5. Mantenimiento

- **Credenciales:** Las claves se gestionan como "Secrets" en la configuración del repositorio de GitHub.
- **Código del Worker:** La lógica de procesamiento está en `curator.py`.
- **Código del Frontend:** La interfaz está en `panel_de_control.html`.
- **Ajustar Temporizador:** Para cambiar la frecuencia de ejecución, edita el archivo `.github/workflows/run_curator.yml` y modifica la expresión `cron`.