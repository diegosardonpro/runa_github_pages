import os
import json
import psycopg2
from urllib.parse import urlparse
from src.utils.logger import get_logger

# --- CONFIGURACIÓN ---
SCHEMA_FILE = 'schema.json'
LOGGER = get_logger(__name__)

def get_db_connection():
    """Establece una conexión directa con la base de datos de Supabase."""
    try:
        db_url = os.getenv('SUPABASE_URL')
        db_password = os.getenv('SUPABASE_DB_PASSWORD')

        if not db_url or not db_password:
            LOGGER.error("Los secretos SUPABASE_URL o SUPABASE_DB_PASSWORD no fueron encontrados.")
            raise ValueError("Credenciales de base de datos no configuradas en los secretos de GitHub.")

        project_ref = urlparse(db_url).hostname.split('.')[0]
        db_host = f"db.{project_ref}.supabase.co"

        conn_string = f"postgresql://postgres:{db_password}@{db_host}:5432/postgres"
        
        LOGGER.info(f"Conectando a la base de datos en host: {db_host}...")
        connection = psycopg2.connect(conn_string)
        LOGGER.info("Conexión a la base de datos exitosa.")
        return connection
    except Exception as e:
        LOGGER.error(f"Error al conectar con la base de datos: {e}")
        raise

def generate_sql_from_schema(schema):
    """Genera sentencias SQL CREATE TABLE a partir de un schema JSON."""
    sql_statements = []
    for table in schema['tablas']:
        table_name = table['nombre']
        columns_sql = []
        constraints_sql = []

        for column in table['columnas']:
            col_name = column['nombre']
            col_type = column['tipo']
            col_sql = f'"{col_name}" {col_type}'

            if not column.get('nullable', False):
                col_sql += ' NOT NULL'
            if 'default' in column:
                col_sql += f" DEFAULT {column['default']}"
            
            columns_sql.append(col_sql)

            if column.get('primaria'):
                constraints_sql.append(f'PRIMARY KEY ("{col_name}")')
            if column.get('unique'):
                 constraints_sql.append(f'UNIQUE ("{col_name}")')

        # Unir columnas y constraints
        full_columns_sql = ', '.join(columns_sql + constraints_sql)

        # Deshabilitar RLS por defecto al crear la tabla para permitir acceso de API
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS public.{table_name} (
            {full_columns_sql}
        );
        ALTER TABLE public.{table_name} DISABLE ROW LEVEL SECURITY;
        """
        sql_statements.append(create_table_sql)
    
    LOGGER.debug(f"SQL generado: {sql_statements}")
    return sql_statements

def main():
    LOGGER.info("--- Iniciando Orquestador de Infraestructura ---")
    conn = None
    try:
        with open(SCHEMA_FILE, 'r') as f:
            schema = json.load(f)
        LOGGER.info(f"Schema '{SCHEMA_FILE}' cargado correctamente.")

        sql_to_execute = generate_sql_from_schema(schema)
        LOGGER.info("Sentencias SQL generadas a partir del schema.")

        conn = get_db_connection()
        cursor = conn.cursor()

        for statement in sql_to_execute:
            table_name = statement.split(' ')[5] # Heurística para obtener el nombre de la tabla
            LOGGER.info(f"Ejecutando SQL para la tabla '{table_name}'...")
            cursor.execute(statement)
            LOGGER.info(f"Sentencia para '{table_name}' ejecutada.")

        conn.commit()
        LOGGER.info("Cambios confirmados en la base de datos.")

    except FileNotFoundError:
        LOGGER.error(f"Error: El archivo de schema '{SCHEMA_FILE}' no fue encontrado.")
        exit(1)
    except Exception as e:
        LOGGER.error(f"Ha ocurrido un error fatal durante la orquestación: {e}")
        if conn: conn.rollback()
        exit(1)
    finally:
        if conn:
            conn.close()
            LOGGER.info("Conexión a la base de datos cerrada.")

    LOGGER.info("¡Infraestructura de base de datos configurada con éxito!")

if __name__ == "__main__":
    main()