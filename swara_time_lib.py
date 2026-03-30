import time
import datetime

def execute_time_function(engine, func_name, args, line_num):
    """
    Despachador para las funciones nativas std.time.
    - std.time.now[] -> txt
    - std.time.delay[segundos] -> empty
    - std.time.compare[fecha1, fecha2] -> num (diferencia en segundos)
    - std.time.format[timestamp, formato] -> txt
    """
    
    # Resolver argumentos (si son variables o literales)
    resolved_args = []
    for arg in args:
        if arg in engine.variables:
            engine._enforce_scope(arg, line_num)
            resolved_args.append(engine.variables[arg]["value"])
        else:
            # Limpiar comillas si es literal de string extraido del parseo
            clean_arg = arg.strip('"').strip("'")
            # Tratar de parsear como número si es posible
            try:
                if "." in clean_arg:
                    clean_arg = float(clean_arg)
                else:
                    clean_arg = int(clean_arg)
            except ValueError:
                pass
            resolved_args.append(clean_arg)

    if func_name == "std.time.now":
        return datetime.datetime.now(datetime.timezone.utc).isoformat()
        
    elif func_name == "std.time.delay":
        if len(resolved_args) < 1:
            engine.error("RUNTIME ERROR", f"La función {func_name} esperaba 1 argumento, obtuvo 0.", line_num)
        
        delay_time = resolved_args[0]
        try:
            delay_time = float(delay_time)
            time.sleep(delay_time)
            # engine.output_handler(f"[TIME]: Operación bloqueada (delay) por {delay_time} segundos.")
            return ""
        except ValueError:
            engine.error("TYPE ERROR", f"El argumento de {func_name} debe ser un número. Obtuvo: {type(delay_time).__name__}", line_num)

    elif func_name == "std.time.compare":
        if len(resolved_args) < 2:
            engine.error("RUNTIME ERROR", f"La función {func_name} esperaba 2 argumentos (fechas formato ISO).", line_num)
        
        try:
            date1 = datetime.datetime.fromisoformat(str(resolved_args[0]).replace('Z', '+00:00'))
            date2 = datetime.datetime.fromisoformat(str(resolved_args[1]).replace('Z', '+00:00'))
            diff = date1 - date2
            return diff.total_seconds()
        except Exception as e:
            engine.error("RUNTIME ERROR", f"Fallo al parsear las fechas en {func_name}. Deben ser formato ISO 8601. Detalle: {str(e)}", line_num)

    elif func_name == "std.time.format":
        if len(resolved_args) < 2:
            engine.error("RUNTIME ERROR", f"La función {func_name} esperaba timestamp y string de formato (ej: '%Y-%m-%d').", line_num)
            
        try:
            date_obj = datetime.datetime.fromisoformat(str(resolved_args[0]).replace('Z', '+00:00'))
            return date_obj.strftime(str(resolved_args[1]))
        except Exception as e:
            engine.error("RUNTIME ERROR", f"Fallo al formatear fecha en {func_name}. Detalle: {str(e)}", line_num)
            
    else:
        engine.error("REFERENCE ERROR", f"La función nativa '{func_name}' no es válida dentro del módulo std.time.", line_num)

    return None
