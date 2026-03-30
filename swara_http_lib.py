import json
import time
import urllib.request
import urllib.error

def envia_peticion(engine, target_route, payload, dtta_form_name, line_num="?"):
    """
    Función nativa de Swara que asume mapear un JSON a un form dtta.
    Maneja retry, idempotency con sys.tx_id, status 200, 400, 500.
    """
    
    # Resolucion de url, method y body 
    if isinstance(payload, dict):
        url = payload.get("url", target_route)
        method = payload.get("method", "POST")
        body = payload.get("body", {})
    elif isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            url = parsed.get("url", target_route)
            method = parsed.get("method", "POST")
            body = parsed.get("body", {})
        except:
            url = target_route if target_route else str(payload)
            method = "POST"
            body = payload
    else:
        url = str(payload)
        method = "POST"
        body = {}

    tx_id_obj = engine.variables.get("sys.tx_id", {})
    tx_id = tx_id_obj.get("value", "") if isinstance(tx_id_obj, dict) else str(tx_id_obj)
    
    headers = {
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(tx_id) if tx_id else ""
    }

    req_data = json.dumps(body).encode("utf-8") if isinstance(body, dict) else str(body).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req) as response:
                status = response.getcode()
                response_body = response.read().decode('utf-8')
                
                if status == 200:
                    engine.output_handler(f"\n[HTTP 200] Éxito. TX_ID: {tx_id}")
                    
                    try:
                        parsed_json = json.loads(response_body)
                    except json.JSONDecodeError:
                        return response_body
                    
                    # Transformar el JSON a un form dtta nativo validando contra el schema en dtta
                    if dtta_form_name and dtta_form_name in engine.forms:
                        form_schema = engine.forms[dtta_form_name]["fields"]
                        validated_data = {}
                        for field_name, field_meta in form_schema.items():
                            if field_name in parsed_json:
                                validated_data[field_name] = parsed_json[field_name]
                        return {"value": validated_data, "type": "form", "form_type": dtta_form_name}
                    else:
                        # Si no hay form definido o no se encuentra, retornarlo como lista o txt
                        return str(parsed_json)
                        
        except urllib.error.HTTPError as e:
            status = e.code
            response_body = e.read().decode('utf-8')

            if status == 400 or status == 404:
                engine.error("NETWORK ERROR", f"Bad Request ({status}) at '{url}'. Body: {response_body}", line_num)
                break
                
            elif status >= 500:
                engine.output_handler(f"[HTTP {status}] Server Error at '{url}'. Reintentando {attempt+1}/{max_retries}...")
                
            else:
                engine.error("NETWORK ERROR", f"HTTP Error ({status}) at '{url}'", line_num)
                break

        except urllib.error.URLError as e:
            engine.output_handler(f"[NETWORK ERROR] Falló la conexión: {str(e.reason)}. Reintentando {attempt+1}/{max_retries}...")
            
        time.sleep(retry_delay)
        retry_delay *= 2
        
    engine.error("NETWORK ERROR", f"Max retries reached for '{url}'.", line_num)
    return None

