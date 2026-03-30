import http.server
import socketserver
import json
import threading

def run_server(engine, port, route_name, line_num):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.handle_swara_request()
            
        def do_POST(self):
            self.handle_swara_request()
            
        def handle_swara_request(self):
            # Reset state for this request
            engine.variables["sys.api_status"] = {"value": 200, "type": "num"}
            engine.variables["sys.api_reply"] = {"value": "OK", "type": "txt"}
            
            try:
                if route_name not in engine.routes:
                    engine.error("SERVER ERROR", f"Route for API '{route_name}' not found.", line_num)
                
                # Execute the bound route
                engine.run_vm(engine.routes[route_name])
                
                status_val = engine.variables.get("sys.api_status", {}).get("value", 200)
                reply_val = engine.variables.get("sys.api_reply", {}).get("value", "")
                
                self.send_response(int(status_val))
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # Respond
                self.wfile.write(str(reply_val).encode('utf-8'))
                
            except Exception as e:
                print(f"[API SERVER ERROR] {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                
        def log_message(self, format, *args):
            print(f"[API_SERVER] HTTP {self.command} - {format % args}")

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", int(port)), Handler)
    print(f"[API_SERVER] Listo y escuchando en el puerto {port} -> Redirigiendo a ruta '{route_name}'...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[API_SERVER] Apagando el servidor...")
    finally:
        httpd.server_close()
