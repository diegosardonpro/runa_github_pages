import logging
import sys
import os

def get_logger(name):
    """
    Configura y devuelve un logger estándar para el proyecto.
    Los logs se envían tanto a la consola como a un archivo.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Corrección: Definir el formato en una sola línea o con concatenación explícita
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(fmt=log_format, datefmt='%Y-%m-%d %H:%M:%S')

        # Manejador para la consola
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # Manejador para el archivo
        # Usar una ruta relativa al directorio del script actual
        log_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'runa_automation.log'))
        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger