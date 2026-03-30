import math

def execute_math_function(engine, func_name, args, line_num):
    """
    Despachador para las funciones nativas std.math.
    Ideal para finanzas o IoT.
    - std.math.round[number, decimals] -> dec
    - std.math.sum[list] -> num/dec
    - std.math.mean[list] -> dec
    - std.math.min[list] -> num/dec
    - std.math.max[list] -> num/dec
    - std.math.abs[number] -> num/dec
    """
    
    resolved_args = []
    
    for arg in args:
        if arg in engine.variables:
            engine._enforce_scope(arg, line_num)
            val = engine.variables[arg]["value"]
            # En caso de que el valor venga de una lista literal registrada como txt
            if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
                try:
                    inner = val[1:-1].split(",")
                    val = [float(x.strip()) for x in inner if x.strip()]
                except:
                    pass
            resolved_args.append(val)
        else:
            clean_arg = str(arg).strip(' "\'')
            # Determinar si es una lista literal proporcionada como argumento
            if clean_arg.startswith("[") and clean_arg.endswith("]"):
                try:
                    inner = clean_arg[1:-1].split(",")
                    list_vals = [float(x.strip()) for x in inner if x.strip()]
                    resolved_args.append(list_vals)
                except Exception:
                    resolved_args.append(clean_arg)
            else:
                try:
                    if "." in clean_arg:
                        resolved_args.append(float(clean_arg))
                    else:
                        resolved_args.append(int(clean_arg))
                except ValueError:
                    resolved_args.append(clean_arg)

    if func_name == "std.math.round":
        if len(resolved_args) < 1:
            engine.error("RUNTIME ERROR", f"La función {func_name} espera al menos 1 argumento.", line_num)
        val = resolved_args[0]
        decimals = int(resolved_args[1]) if len(resolved_args) > 1 else 0
        try:
            return round(float(val), decimals)
        except (ValueError, TypeError):
            engine.error("TYPE ERROR", f"Argumentos inválidos para {func_name}.", line_num)

    elif func_name == "std.math.sum":
        if len(resolved_args) != 1 or not isinstance(resolved_args[0], list):
            engine.error("TYPE ERROR", f"La función {func_name} espera una lista.", line_num)
        return sum(float(x) for x in resolved_args[0])

    elif func_name == "std.math.mean":
        if len(resolved_args) != 1 or not isinstance(resolved_args[0], list) or len(resolved_args[0]) == 0:
            engine.error("TYPE ERROR", f"La función {func_name} espera una lista no vacía.", line_num)
        vals = [float(x) for x in resolved_args[0]]
        return sum(vals) / len(vals)

    elif func_name in ["std.math.min", "std.math.max"]:
        if len(resolved_args) != 1 or not isinstance(resolved_args[0], list) or len(resolved_args[0]) == 0:
            engine.error("TYPE ERROR", f"La función {func_name} espera una lista no vacía.", line_num)
        vals = [float(x) for x in resolved_args[0]]
        return min(vals) if func_name == "std.math.min" else max(vals)
        
    elif func_name == "std.math.abs":
        if len(resolved_args) != 1:
            engine.error("RUNTIME ERROR", f"La función {func_name} espera 1 argumento.", line_num)
        try:
            val = float(resolved_args[0])
            return abs(int(val) if val.is_integer() else val)
        except (ValueError, TypeError):
            engine.error("TYPE ERROR", f"Argumentos inválidos para {func_name}: {resolved_args[0]}.", line_num)
            
    else:
        engine.error("REFERENCE ERROR", f"La función nativa '{func_name}' no es válida dentro del módulo std.math.", line_num)

    return None