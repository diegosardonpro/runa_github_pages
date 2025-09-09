# Marco Ético y Límites Técnicos del Proyecto Runa

## 1. Principios Fundamentales

Este documento establece el marco ético que rige el diseño y la implementación de todas las herramientas y sistemas dentro del proyecto Runa. Nuestra filosofía no es solo construir tecnología, sino hacerlo de una manera que respete la dignidad, la privacidad y la autonomía de las personas, especialmente las de comunidades vulnerables.

*   **Propósito por Encima de la Técnica:** La finalidad de nuestra tecnología es siempre visibilizar y analizar las desigualdades para combatirlas. Cualquier funcionalidad que no sirva directamente a este propósito, o que pueda comprometerlo, será descartada.

*   **Consentimiento y Transparencia Radical:** No se recolectará ningún dato sin el consentimiento informado, voluntario y explícito del usuario. Todas nuestras herramientas explicarán de forma clara y sencilla qué datos se solicitan y con qué finalidad social se utilizarán.

*   **Anonimato por Diseño:** El sistema está diseñado para que sea técnicamente imposible vincular los datos demográficos o de uso con una identidad personal. No se almacenará ninguna información de identificación personal (IIP), como nombres, correos electrónicos, direcciones IP o huellas digitales del navegador (`fingerprinting`).

*   **Minimización de Datos:** Solo se solicitarán los datos demográficos anónimos que sean estrictamente necesarios para el análisis de las brechas sociales que buscamos entender.

## 2. Límites Técnicos y Fronteras Éticas

Para mantenernos fieles a nuestros principios, establecemos las siguientes fronteras operativas.

### Lo que Haremos:

*   **Implementar Encuestas Voluntarias:** Ofreceremos cuestionarios opcionales y anónimos para que los usuarios contribuyan con datos demográficos (ej. tipo de dispositivo, rango de edad, nivel de confianza digital).
*   **Analizar Datos Agregados:** Cruzaremos los datos temáticos del contenido analizado con los datos demográficos anónimos para identificar patrones y brechas (ej. "¿Los usuarios que acceden desde móviles analizan más contenido sobre derechos laborales?").
*   **Ofrecer Valor Directo:** Nuestras herramientas siempre proporcionarán un resultado útil y directo al usuario a cambio de su interacción.

### Lo que NUNCA Haremos:

*   **Rastrear Direcciones IP:** No almacenaremos ni procesaremos las direcciones IP de los usuarios.
*   **Usar Cookies de Seguimiento:** No utilizaremos cookies ni tecnologías de `fingerprinting` para rastrear a los usuarios a través de diferentes sitios o sesiones.
*   **Recolectar Datos sin Consentimiento:** No habrá ninguna recolección de datos pasiva o sin una acción explícita del usuario.
*   **Intentar Re-identificar Usuarios:** No intentaremos cruzar datos de ninguna manera que pueda comprometer el anonimato de un participante.

## 3. La Diferencia Metodológica: Nuestro Enfoque vs. el Uso Indebido

La tecnología es neutral; su aplicación define su ética. La diferencia entre nuestro enfoque y un uso indebido radica en la **intención**, la **transparencia** y el **poder**.

*   **Uso Indebido (Descartado):** Rastrear a un usuario de forma opaca para crear un perfil, predecir su comportamiento y utilizarlo para fines comerciales o de influencia sin su control.

*   **Uso Adecuado (Nuestro Enfoque):** Invitar a una persona a participar voluntariamente en un estudio social. Le explicamos el "porqué", le damos el control total para participar o no, y utilizamos sus datos anónimos para generar un bien común: la visibilización de la desigualdad para poder combatirla.

Este marco es un documento vivo y guiará todas nuestras decisiones técnicas futuras.

---

## 5. Decisiones de Arquitectura y Pivotes Técnicos

Esta sección documenta las decisiones técnicas clave y los pivotes realizados durante el desarrollo, incluyendo el razonamiento detrás de ellos.

### 5.1. Método de Conexión a Supabase: El Pivote a la Arquitectura Dual

*   **Contexto:** Durante el desarrollo inicial, se encontraron errores de conectividad persistentes (`Network is unreachable`) al intentar ejecutar comandos de infraestructura (`CREATE TABLE`) desde el entorno de GitHub Actions hacia la base de datos de Supabase.
*   **Iteración 1 (Fallida):** Se intentó unificar todas las interacciones con la base de datos a través de una sola librería (`supabase-py`). Esta aproximación falló porque dicha librería, por diseño y seguridad, es una cliente de datos (DML) y no tiene la capacidad de ejecutar comandos de modificación de esquema (DDL) de forma directa y robusta.
*   **Decisión Estratégica (La Solución Actual):** Se tomó la decisión de implementar una **arquitectura de conexión dual**, reconociendo la naturaleza distinta de las tareas de infraestructura y las de contenido.
    *   **Componente 1 (Infraestructura - DDL):** Para tareas de alta sensibilidad que modifican la estructura de la base de datos, se utiliza una conexión directa vía `psycopg2` autenticada con la cadena de conexión del "Pooler" (`SUPABASE_CONNECTION_STRING`). Este método es robusto y está diseñado para este tipo de operaciones.
    *   **Componente 2 (Contenido - DML):** Para las operaciones diarias de lectura y escritura de datos, se utiliza la librería oficial `supabase-py`, autenticada con `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`. Este método es más seguro para la manipulación de datos y aprovecha las abstracciones de la API de Supabase.
*   **Conclusión:** Este "vaivén" en la implementación no representa un error, sino un **proceso de descubrimiento iterativo** que nos llevó a una solución más segura, resiliente y técnicamente correcta, alineada con las mejores prácticas para interactuar con servicios de base de datos gestionados.

---

## 4. Análisis de Plataformas y Proveedores

Esta sección documenta nuestro análisis de las políticas y límites de las tecnologías de terceros que utilizamos, asegurando que se alineen con nuestros principios.

### 4.1 Supabase (Backend y Base de Datos)

*   **Fecha de Análisis:** 2025-09-09
*   **Servicio Analizado:** Política de uso de datos para las funcionalidades de IA de Supabase.
*   **Conclusión:** La política de Supabase es **compatible** con nuestro Marco Ético.
*   **Análisis Detallado:**
    *   **Seguridad por Defecto:** Por defecto, Supabase no comparte ningún dato de contenido con sus proveedores de IA, solo metadatos del esquema de la base de datos (nombres de tablas/columnas), lo cual es una práctica segura.
    *   **Consentimiento Explícito:** El uso compartido de datos de contenido (prompts, datos de filas) para funciones de IA requiere una activación manual y explícita por parte del administrador del proyecto (nosotros). Tenemos el control total.
    *   **Prohibición de Re-entrenamiento:** Supabase y sus proveedores de IA se comprometen a no retener los datos de contenido y a no utilizarlos para entrenar sus modelos. Los datos se usan únicamente para generar la respuesta a una consulta y luego se descartan.
*   **Implicación para Runa:** Podemos utilizar las herramientas de IA de Supabase en el futuro con la confianza de que nuestros datos y los de nuestros usuarios no serán explotados o utilizados para fines ajenos a nuestra misión. La responsabilidad de activar cualquier compartición de datos recae en nosotros, y solo lo haríamos si se alinea con nuestros principios de transparencia y valor para el usuario.