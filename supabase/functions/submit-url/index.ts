// Importa los módulos necesarios de Deno y Supabase
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.0.0'

// Definición de la función principal que maneja las peticiones
serve(async (req) => {
  // Manejar la petición pre-vuelo (CORS) para permitir el acceso desde cualquier origen
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type' } })
  }

  try {
    // Crear un cliente de Supabase usando las variables de entorno del proyecto
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: req.headers.get('Authorization')! } } }
    )

    // Extraer la URL del cuerpo de la petición
    const { url } = await req.json()

    // Validar que la URL exista
    if (!url) {
      throw new Error('La URL es requerida en el cuerpo de la petición.')
    }

    // Insertar la nueva URL en la tabla 'urls_para_procesar'
    const { error } = await supabaseClient
      .from('urls_para_procesar')
      .insert({ url: url, estado: 'pendiente' })

    // Si hay un error en la inserción, lanzarlo
    if (error) {
      console.error('Error de Supabase:', error)
      throw error
    }

    // Devolver una respuesta de éxito
    return new Response(JSON.stringify({ message: `URL añadida a la cola: ${url}` }), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      status: 200,
    })

  } catch (error) {
    // Devolver una respuesta de error
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      status: 400,
    })
  }
})
