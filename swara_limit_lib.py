import time

# Almacenamiento global en memoria para rastrear IPs y timestamps
# Formato: { "ip_address": [timestamp1, timestamp2, ...] }
_RATE_LIMITS = {}

def check_limit(engine, ip_val, max_requests, time_window, line_num="?"):
    """
    Verifica si una IP ha excedido el límite de peticiones en un periodo de tiempo.
    Bloquea la ejecución (levantando un error nativo) si se excede el límite.
    """
    current_time = time.time()
    
    if ip_val not in _RATE_LIMITS:
        _RATE_LIMITS[ip_val] = []
        
    # Filtrar timestamps que estén dentro del periodo de tiempo permitido
    valid_times = [t for t in _RATE_LIMITS[ip_val] if current_time - t <= time_window]
    
    # Comprobar límite
    if len(valid_times) >= max_requests:
        engine.error("RATE LIMIT ERROR", f"La IP '{ip_val}' ha excedido el limite de {max_requests} peticiones por {time_window} segundos. Bloqueo DoS activado.", line_num)
        
    # Registrar la peticion actual
    valid_times.append(current_time)
    _RATE_LIMITS[ip_val] = valid_times
