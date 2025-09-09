import logging
import sys

def get_logger(name):
    """
    Configura y devuelve un logger estándar para el proyecto.
    Los logs se envían tanto a la consola como a un archivo.
    """
    # Crear un logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG) # Nivel más bajo para capturar todo

    # Evitar añadir manejadores múltiples si el logger ya existe
    if not logger.handlers:
        # Formateador para los logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s
            ',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Manejador para la consola (StreamHandler)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO) # Solo mostrar INFO y superior en la consola
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # Manejador para el archivo (FileHandler)
        # Se usa os.path.join para asegurar compatibilidad de rutas
        import os
        log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..\/..\/runa_automation.log')
        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG) # Guardar todo (DEBUG y superior) en el archivo
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
