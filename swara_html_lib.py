import re

def execute_fill_html(engine, plantilla, datos_form, destino_txt, line_num):
    try:
        # Resolver la plantilla
        template_text = str(plantilla)
        if plantilla in engine.variables:
            engine._enforce_scope(plantilla, line_num)
            template_text = str(engine.variables[plantilla]["value"])
        elif plantilla.startswith('"') and plantilla.endswith('"'):
            template_text = plantilla[1:-1]
        elif plantilla.endswith('.html'):
            try:
                with open(plantilla, "r", encoding="utf-8") as f:
                    template_text = f.read()
            except IOError:
                engine.error("IO ERROR", f"No se pudo leer el archivo de plantilla: {plantilla}", line_num)

        # Resolver el origen de datos (formulario)
        form_data = {}
        if type(datos_form) == dict:
            form_data = datos_form
        elif datos_form in engine.variables:
            engine._enforce_scope(datos_form, line_num)
            form_val = engine.variables[datos_form]["value"]
            if isinstance(form_val, dict):
                form_data = form_val
            else:
                engine.error("TYPE ERROR", f"La variable '{datos_form}' no es un Form válido (tipo dict).", line_num)
        elif datos_form == "empty":
            form_data = {}
        else:
            engine.error("REFERENCE ERROR", f"El origen de datos '{datos_form}' no existe o no es de tipo Form.", line_num)
            
        # Reemplazar variables {{variable}} en la plantilla
        # Usamos re.sub con una funcion personalizada
        def replacer(match):
            key = match.group(1).strip()
            if key in form_data:
                return str(form_data[key])
            return match.group(0)  # No reemplazar si no encuentra el dato
            
        filled_text = re.sub(r'\{\{(.*?)\}\}', replacer, template_text)
        
        # Guardar en destino
        engine._register_variable(destino_txt, filled_text, "txt", line_num)
        
    except Exception as e:
        if "ERROR" in str(e):
            raise e
        else:
            engine.error("HTML RENDER ERROR", f"Error procesando la plantilla HTML: {str(e)}", line_num)
