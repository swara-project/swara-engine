import os
from .swara_bytecode_engine import swaraBytecodeEngine

class swaraRuntime:
    def __init__(self, workspace_dir, input_handler=input, output_handler=print):
        self.workspace_dir = workspace_dir
        
        # Inicializa y configura el motor
        self.engine = swaraBytecodeEngine()
        self.engine.input_handler = input_handler
        self.engine.output_handler = output_handler

    def find_entry_point(self):
        main_file = None
        
        # 1. Buscamos un archivo de estructura que defina entry_point.
        #    En swara, entry_point apunta a una ruta interna (no a un archivo).
        try:
            for filename in os.listdir(self.workspace_dir):
                if filename.endswith(".swara"):
                    path = os.path.join(self.workspace_dir, filename)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        if "ass sttr" in content and "entry_point" in content:
                            main_file = path
                    except Exception:
                        pass
                    if main_file: break
        except Exception:
            pass

        # 2. Si no encontramos sttr, buscamos si hay algun lgca base
        if not main_file:
            try:
                for filename in os.listdir(self.workspace_dir):
                    if filename.endswith(".swara"):
                        path = os.path.join(self.workspace_dir, filename)
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                content = f.read()
                            if "ass lgca" in content:
                                main_file = path
                                break
                        except Exception:
                            pass
            except Exception:
                pass

        return main_file

    def run_project(self):
        main_file = self.find_entry_point()

        if not main_file or not os.path.exists(main_file):
            self.engine.output_handler("[Error] No entry point found. Ensure a file declares 'ass lgca' or an 'ass sttr' points to one.\n")
            return

        self.engine.output_handler(f"[Compiling entry point: {os.path.basename(main_file)}]\n")

        try:
            with open(main_file, "r", encoding="utf-8") as f:
                code = f.read()
            
            # Delega todo el parseo y ejecución al motor
            self.engine.run(code)
            
            self.engine.output_handler("\n[Execution finished successfully]\n")
        except Exception as e:
            self.engine.output_handler(f"\n[Terminated with Error] {str(e)}\n")
