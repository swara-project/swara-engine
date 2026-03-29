import argparse
import sys
import os

# Agregar la raíz al sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.swara_runtime import swaraRuntime

def main():
    parser = argparse.ArgumentParser(description="swara Language Compiler & Runtime")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Comando: run
    run_parser = subparsers.add_parser("run", help="Run a swara file or project workspace")
    run_parser.add_argument("path", nargs="?", default=".", help="Path to the .swara file or workspace directory (default: current dir)")

    # Comando: version
    subparsers.add_parser("version", help="Show swara Language version")

    args = parser.parse_args()

    if args.command == "version":
        print("swara Language (Runtime v1.0.0)")
        sys.exit(0)
        
    elif args.command == "run":
        target_path = os.path.abspath(args.path)
        
        # Si el usuario pasa un archivo específico
        if os.path.isfile(target_path):
            if not target_path.endswith(".swara"):
                print(f"[ERROR] Can only run .swara files. '{target_path}' provided.")
                sys.exit(1)
                
            workspace_dir = os.path.dirname(target_path)
            runtime = swaraRuntime(workspace_dir=workspace_dir)
            
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    code = f.read()
                runtime.engine.run(code)
            except Exception as e:
                print(f"\n[Terminated with Error] {e}")
                sys.exit(1)
                
        # Si el usuario pasa una carpeta (o el default '.')
        elif os.path.isdir(target_path):
            runtime = swaraRuntime(workspace_dir=target_path)
            runtime.run_project()
            
        else:
            print(f"[ERROR] Path not found: {target_path}")
            sys.exit(1)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
