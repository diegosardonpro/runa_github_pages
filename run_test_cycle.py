# run_test_cycle.py
import os
import sys
import subprocess
import logging
from dotenv import load_dotenv
import pathlib

# --- Configuración Inicial ---
# Asegurarse de que 'src' está en el path para poder importar db_manager
project_root = pathlib.Path(__file__).parent
sys.path.append(str(project_root / 'src'))

# Cargar variables de entorno
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print(f"Advertencia: No se encontró el archivo .env en {env_path}")

try:
    from src import db_manager
except ImportError as e:
    print(f"Error fatal: No se pudo importar db_manager. Asegúrate de que la estructura de carpetas es correcta. {e}")
    sys.exit(1)

# Configurar logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("TestCycleRunner")

def cleanup_and_reset():
    """
    Limpia los datos de ejecuciones anteriores (activos, imágenes) y luego
    resetea el estado de todas las URLs en la tabla 'urls_para_procesar' a 'pendiente'.
    """
    log.info("--- INICIANDO LIMPIEZA Y RESETEO DE LA BASE DE DATOS ---")
    try:
        supabase = db_manager.get_supabase_client(log)
        
        # 1. Eliminar todos los activos existentes. La configuración ON DELETE CASCADE
        #    en la base de datos se encargará de borrar las imágenes asociadas.
        log.info("Eliminando registros antiguos de la tabla 'activos' e 'imagenes'...")
        response_assets = supabase.table(db_manager.ASSETS_TABLE).delete().gt('id', 0).execute()
        log.info(f"{len(response_assets.data)} registros de activos eliminados.")

        # 2. Resetear el estado de todas las URLs a 'pendiente'
        log.info("Reseteando estados en la tabla 'urls_para_procesar'...")
        response_urls = supabase.table(db_manager.URLS_TABLE).update({
            'estado': 'pendiente',
            'ultimo_error': None
        }).neq('estado', 'pendiente').execute()
        log.info(f"{len(response_urls.data)} URLs actualizadas a 'pendiente'.")

        log.info("--- LIMPIEZA Y RESETEO COMPLETADOS ---")

    except Exception as e:
        log.error(f"Ocurrió un error durante la limpieza y reseteo: {e}", exc_info=True)
        sys.exit(1)

def run_curator_worker():
    """
    Ejecuta el script curator.py como un subproceso.
    """
    log.info("--- INICIANDO EJECUCIÓN DEL WORKER curator.py ---")
    try:
        curator_script_path = project_root / 'curator.py'
        # Usamos sys.executable para asegurarnos de que se usa el mismo intérprete de Python
        result = subprocess.run(
            [sys.executable, str(curator_script_path)],
            capture_output=True,
            text=True,
            check=False,  # Lo ponemos en False para manejar el error manualmente
            encoding='utf-8',
            errors='replace'  # Reemplaza caracteres problemáticos en lugar de fallar
        )
        
        if result.stdout:
            log.info("Salida del worker:\n" + result.stdout)
        if result.stderr:
            log.warning("Errores estándar del worker:\n" + result.stderr)

        if result.returncode != 0:
            log.error(f"El script curator.py finalizó con el código de error {result.returncode}")
        else:
            log.info("--- EJECUCIÓN DEL WORKER COMPLETADA ---")

    except FileNotFoundError:
        log.error(f"Error: No se encontró el script 'curator.py' en {curator_script_path}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Error inesperado al ejecutar el subproceso: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    log.info("====== INICIANDO CICLO DE PRUEBA AUTOMATIZADO ======")
    cleanup_and_reset()
    run_curator_worker()
    log.info("====== CICLO DE PRUEBA FINALIZADO ======")
