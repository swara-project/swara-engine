import json

def execute_json_function(engine, func_name, args, line_num):
    """
    Despachador para las funciones nativas std.json.
    - std.json.parse[txt, Form] -> dtta form
    - std.json.serialize[Form] -> txt
    """
    resolved_args = []
    
    for arg in args:
        if isinstance(arg, str) and arg in engine.variables:
            engine._enforce_scope(arg, line_num)
            resolved_args.append(engine.variables[arg]["value"])
        else:
            clean_arg = str(arg).strip(' "\'')
            resolved_args.append(clean_arg)
            
    if func_name == "std.json.parse":
        if len(args) != 2:
            engine.error("SYNTX ERROR", f"{func_name} expects 2 arguments: JSON string and Form name", line_num)
            
        json_txt = resolved_args[0]
        # Evaluamos form_name sobre los args sin resolver 
        # para que "UsuarioForm" no se parse como string interpolado sino el nombre del molde.
        form_name = str(args[1]).strip(' "\'') 
        
        if form_name not in engine.forms:
            engine.error("FORM ERROR", f"Form '{form_name}' no definido en capa dtta.", line_num)
            
        try:
            parsed = json.loads(json_txt)
        except json.JSONDecodeError as e:
            engine.error("JSON PARSE ERROR", f"Invalid JSON: {e}", line_num)
            
        if not isinstance(parsed, dict):
            engine.error("TYPE ERROR", "Parsed JSON must be an object (Form mapping).", line_num)
            
        form_schema = engine.forms[form_name].get("fields", {})
        schema_keys = set(form_schema.keys())
        parsed_keys = set(parsed.keys())
        
        missing = schema_keys - parsed_keys
        extra = parsed_keys - schema_keys
        
        if missing or extra:
            err_msg = "SCHEMA ERROR"
            engine.error("SCHEMA ERROR", f"JSON mismatch for form {form_name}.", line_num)
            
        return parsed
        
    elif func_name == "std.json.serialize":
        if len(args) != 1:
            engine.error("SYNTX ERROR", f"{func_name} expects 1 argument: Form instance", line_num)
            
        form_data = resolved_args[0]
        
        try:
            return json.dumps(form_data)
        except Exception as e:
            engine.error("JSON SERIALIZE ERROR", f"Could not serialize: {e}", line_num)
            
    else:
        engine.error("LIB ERROR", f"Unknown json function: {func_name}", line_num)
