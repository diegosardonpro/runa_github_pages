import os
from supabase import create_client

URL_TO_ADD = "https://es.mongabay.com/2025/05/puno-declara-lago-titicaca-sujeto-de-derecho-peru/"

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
if not url or not key: raise ValueError("Secretos no encontrados")

supabase = create_client(url, key)

data, count = supabase.table('urls_para_procesar').insert({
    "url": URL_TO_ADD,
    "estado": "pendiente"
}).execute()

print(f"URL añadida a la cola. Respuesta: {data}")
