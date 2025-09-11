# Proyecto Runa v8.0 - Arquitectura Final y Documentación Completa

## 1. Meta-documentación y Filosofía del Proyecto ("Nuestra Vibra")

El desarrollo de este proyecto ha sido un viaje iterativo. La filosofía central ha sido la **búsqueda incansable de la arquitectura más simple y robusta posible**, descartando sin piedad cualquier complejidad que no aportara un valor claro al usuario final.

### Lecciones Aprendidas en la Depuración

Este proyecto superó numerosos desafíos técnicos que sirven como lecciones valiosas:

- **La Falacia del "Arreglo Rápido":** Múltiples intentos de aplicar pequeños parches a problemas de fondo (CORS, carga de scripts, errores de API) solo añadieron capas de complejidad. La solución real siempre fue detenerse, re-evaluar la arquitectura y resetear a una base estable, como hicimos al volver a la etiqueta de Git `v4.0-pre-refactor`.

- **La Arquitectura Correcta es la Más Simple que Funcione:** Exploramos un `.exe` de escritorio, un panel web con `config.js` local y, finalmente, la arquitectura de Función Serverless. La lección es que la solución más "profesional" no siempre es la mejor si introduce fricción. La arquitectura final (Frontend Estático -> Función Serverless -> Worker Asíncrono) es el estándar de la industria precisamente porque es segura, escalable y ofrece la mejor experiencia de usuario.

- **Depuración de la "Caja Negra":** El `runa.exe` y la Función Edge inicialmente fallaban de forma silenciosa. La solución fue instrumentar el código con logging explícito (a una consola o a un archivo) para entender qué estaba ocurriendo internamente. Nunca se debe asumir que un proceso funciona; siempre se debe verificar.

- **Verificar Supuestos del Entorno:** Dimos por sentado cómo funcionaba `sed` en GitHub, los nombres de las variables de entorno en Supabase y las políticas de RLS. En todos los casos, el error se solucionó al dejar de asumir y verificar explícitamente la configuración del entorno (o, en el caso de `sed`, reemplazarlo con una herramienta más predecible como Python).

## 2. Arquitectura Final (v8.0 - Serverless Frontend)

El sistema en su estado final y funcional se compone de tres partes desacopladas:

1.  **Frontend (El Panel de Control):** Un archivo `panel_de_control.html` estático, desplegado en GitHub Pages. No contiene ninguna credencial. Su única función es capturar una URL y enviarla a la Función Serverless.

2.  **Intermediario (La Función Segura):** Una **Edge Function** de Supabase (`submit-url` o `smooth-task`) que actúa como una API pública. Es el único componente que conoce la clave secreta del servicio (`SERVICE_ROLE_KEY`) y su única función es recibir una URL e insertarla de forma segura en la tabla `urls_para_procesar`.

3.  **Backend (El Worker Asíncrono):** El script `curator.py`, que se ejecuta como una **Acción de GitHub** programada. Se activa periódicamente, revisa la tabla `urls_para_procesar` en busca de tareas pendientes y realiza todo el trabajo pesado de extracción y análisis.

## 3. Flujo de Trabajo del Usuario Final

1.  **Añadir Tareas:** El usuario abre la URL pública del [Panel de Control](https://diegosardonpro.github.io/runa_github_pages/panel_de_control.html), pega una URL y hace clic en "Enviar".
2.  **Procesamiento Automático:** La Acción de GitHub se ejecuta según la programación establecida (ver sección 4), encuentra la URL pendiente y la procesa.
3.  **Verificar Resultados:** El usuario puede ver los resultados finales directamente en las tablas `activos_curados` e `imagenes_curadas` en su panel de Supabase.

## 4. Guía de Configuración y Mantenimiento

- **Credenciales de la Acción:** Las claves `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `GEMINI_API_KEY` deben estar configuradas como "Secrets" en la sección `Settings > Secrets and variables > Actions` del repositorio de GitHub.

- **Código de la Función Serverless:** El código fuente de la función intermediaria se encuentra en el historial de este chat y debe ser desplegado desde el panel de Supabase en la sección "Edge Functions".

- **Ajustar el Temporizador de la Curaduría:** Para cambiar la frecuencia con la que se ejecuta el procesador automático, debes editar el archivo `.github/workflows/run_curator.yml`...
