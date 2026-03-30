import sqlite3
import re
import os

connections = {}

def execute_open_db(engine, ruta, conexion_id, line_num):
    try:
        # Resolve path
        if ruta in engine.variables:
            engine._enforce_scope(ruta, line_num)
            db_path = str(engine.variables[ruta]["value"])
        else:
            db_path = str(ruta)
            
        # Register the connection
        conn = sqlite3.connect(db_path)
        connections[conexion_id] = conn
        
        # We also need to save it into Swara's memory as a reference maybe
        # but just keeping it in the dict is ok for now.
        if conexion_id not in engine.variables:
            engine._register_variable(conexion_id, db_path, "txt", line_num)
            
        print(f"[DB_TUNNEL] Open to '{db_path}' assigned to '{conexion_id}'")
        return True
    except Exception as e:
        engine.error("DATABASE ERROR", f"Cannot open database: {str(e)}", line_num)

def execute_exec_db(engine, conexion_id, query, resultado_list, line_num):
    try:
        if conexion_id not in connections:
            engine.error("DATABASE ERROR", f"Connection '{conexion_id}' not found.", line_num)
            
        conn = connections[conexion_id]
        cursor = conn.cursor()
        
        # Replace variable references in query if necessary like `{var_name}` or just execute
        # the query string. Let's process arguments if it has them.
        final_query = str(query)
        if final_query in engine.variables:
            engine._enforce_scope(final_query, line_num)
            final_query = str(engine.variables[final_query]["value"])
        
        # Execute Query
        if final_query.startswith('"') and final_query.endswith('"'):
            final_query = final_query[1:-1]
        
        cursor.execute(final_query)
        
        # Only fetch if it's a SELECT type of query
        if final_query.strip().upper().startswith("SELECT") or final_query.strip().upper().startswith("PRAGMA"):
            rows = cursor.fetchall()
            
            # Format rows as a list of strings or dicts
            result_data = []
            for row in rows:
                if len(row) == 1:
                    result_data.append(str(row[0]))
                else:
                    # Convert row tuple to a list inside
                    result_data.append([str(item) for item in row])
        else:
            conn.commit()
            result_data = [f"Rows affected: {cursor.rowcount}"]
            
        # Put result into Swara list
        engine._register_variable(resultado_list, result_data, "list", line_num)
        
    except Exception as e:
        engine.error("DATABASE ERROR", f"Failed to execute query: {str(e)}", line_num)
