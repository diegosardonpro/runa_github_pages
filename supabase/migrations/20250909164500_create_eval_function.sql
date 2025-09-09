CREATE OR REPLACE FUNCTION public.eval(query text)
RETURNS json
LANGUAGE plpgsql
AS $$
BEGIN
    EXECUTE query;
    RETURN '{"status": "success"}'::json;
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'status', 'error',
            'message', SQLERRM,
            'code', SQLSTATE
        )::json;
END;
$$;