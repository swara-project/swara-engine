import hashlib
import hmac
import base64

def _stream_cipher(data_bytes, key_string):
    """
    Motor básico de cifrado simétrico tipo stream-cipher usando la librería estándar.
    Genera un keystream a partir de SHA-256 encadenado y aplica XOR.
    Útil para no requerir dependencias externas (ej. 'cryptography'),
    manteniendo Swara puramente nativo.
    """
    key_bytes = key_string.encode('utf-8')
    digest = hashlib.sha256(key_bytes).digest()
    
    out = bytearray()
    for i, b in enumerate(data_bytes):
        if i > 0 and i % len(digest) == 0:
            digest = hashlib.sha256(digest + key_bytes).digest()
        out.append(b ^ digest[i % len(digest)])
    return out

def execute_crypto_function(engine, func_name, args, line_num):
    """
    Despachador para las funciones nativas std.crypto.
    - std.crypto.hash[txt] -> txt (SHA-256)
    - std.crypto.sign[txt, key] -> txt (HMAC-SHA256)
    - std.crypto.encrypt[txt, key] -> txt (B64 XOR Cipher)
    - std.crypto.decrypt[txt, key] -> txt 
    """
    
    resolved_args = []
    
    for arg in args:
        if arg in engine.variables:
            engine._enforce_scope(arg, line_num)
            resolved_args.append(engine.variables[arg]["value"])
        else:
            clean_arg = str(arg).strip(' "\'')
            resolved_args.append(clean_arg)

    if func_name == "std.crypto.hash":
        if len(resolved_args) < 1:
            engine.error("RUNTIME ERROR", f"La función {func_name} espera 1 argumento.", line_num)
        
        data = str(resolved_args[0]).encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    elif func_name == "std.crypto.sign":
        if len(resolved_args) < 2:
            engine.error("RUNTIME ERROR", f"La función {func_name} espera 2 argumentos: [data, key].", line_num)
            
        data = str(resolved_args[0]).encode('utf-8')
        key = str(resolved_args[1]).encode('utf-8')
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    elif func_name == "std.crypto.encrypt":
        if len(resolved_args) < 2:
            engine.error("RUNTIME ERROR", f"La función {func_name} espera 2 argumentos: [txt, key].", line_num)
            
        data_text = str(resolved_args[0])
        key_str = str(resolved_args[1])
        
        try:
            encrypted_bytes = _stream_cipher(data_text.encode('utf-8'), key_str)
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            engine.error("RUNTIME ERROR", f"Fallo en encriptado: {str(e)}", line_num)

    elif func_name == "std.crypto.decrypt":
        if len(resolved_args) < 2:
            engine.error("RUNTIME ERROR", f"La función {func_name} espera 2 argumentos: [txt_encriptado, key].", line_num)
            
        b64_text = str(resolved_args[0])
        key_str = str(resolved_args[1])
        
        try:
            encrypted_bytes = base64.b64decode(b64_text)
            decrypted_bytes = _stream_cipher(encrypted_bytes, key_str)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            engine.error("RUNTIME ERROR", f"Fallo en desencriptado (Llave o base64 inválido): {str(e)}", line_num)

    else:
        engine.error("REFERENCE ERROR", f"La función nativa '{func_name}' no es válida dentro del módulo std.crypto.", line_num)

    return None
