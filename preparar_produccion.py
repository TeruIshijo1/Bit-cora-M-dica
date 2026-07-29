import os
import shutil
import subprocess

DEPLOY_DIR = "pase_a_produccion"

def main():
    print("=========================================================")
    print("   Preparando Empaquetado para Pase a Produccion")
    print("=========================================================")
    print()

    # 1. Limpiar carpeta anterior
    print("[1/4] Limpiando carpeta anterior...")
    if os.path.exists(DEPLOY_DIR):
        shutil.rmtree(DEPLOY_DIR)
    os.makedirs(DEPLOY_DIR)

    # 2. Compilar el Frontend
    print("\n[2/4] Compilando el Frontend (React)...")
    try:
        subprocess.run("npm run build", shell=True, cwd="frontend", check=True)
    except Exception as e:
        print(f"Error compilando el frontend: {e}")
        return

    # 3. Copiar archivos
    print("\n[3/4] Copiando archivos de forma segura...")

    # Frontend
    print("  - Copiando Frontend (dist)...")
    shutil.copytree(os.path.join("frontend", "dist"), os.path.join(DEPLOY_DIR, "frontend", "dist"))

    # Backend
    print("  - Copiando Backend de Python (Excluyendo DB local y contraseñas)...")
    def ignore_backend(dir, files):
        ignored = []
        if 'venv' in dir or '__pycache__' in dir or '.pytest_cache' in dir:
            return files
        for f in files:
            if f == "venv" or f == "__pycache__" or f == ".pytest_cache":
                ignored.append(f)
            if f == ".env" or f.endswith(".db") or f.endswith(".sqlite") or f in ["migrate_to_postgres.py", "fix_sequences.py"]:
                ignored.append(f)
        return ignored
    
    shutil.copytree("backend", os.path.join(DEPLOY_DIR, "backend"), ignore=ignore_backend)

    # Backend Node
    print("  - Copiando Microservicio Biometrico (Node)...")
    def ignore_node(dir, files):
        return [f for f in files if f == "node_modules"]
    
    shutil.copytree("backend_node", os.path.join(DEPLOY_DIR, "backend_node"), ignore=ignore_node)

    # Scripts raiz y extras
    print("  - Copiando Scripts de arranque...")
    if os.path.exists("iniciar.bat"):
        shutil.copy("iniciar.bat", DEPLOY_DIR)
    if os.path.exists("instalar server.bat"):
        shutil.copy("instalar server.bat", DEPLOY_DIR)
    if os.path.exists("ngrok.exe"):
        shutil.copy("ngrok.exe", DEPLOY_DIR)

    # Mobile App Source
    print("  - Copiando Codigo de App Movil (Excluyendo carpetas pesadas)...")
    def ignore_mobile(dir, files):
        return [f for f in files if f in ["node_modules", "android", "ios", ".expo", ".DS_Store"]]
    if os.path.exists("mobile_app"):
        shutil.copytree("mobile_app", os.path.join(DEPLOY_DIR, "mobile_app"), ignore=ignore_mobile)

    # APK Instalador
    print("  - Copiando archivo instalador APK para las tablets...")
    apk_release_dir = os.path.join("mobile_app", "android", "app", "build", "outputs", "apk", "release")
    apk_found = False
    if os.path.exists(apk_release_dir):
        for f in os.listdir(apk_release_dir):
            if f.endswith(".apk"):
                apk_source = os.path.join(apk_release_dir, f)
                apk_dest_dir = os.path.join(DEPLOY_DIR, "APK_Tablets")
                os.makedirs(apk_dest_dir, exist_ok=True)
                shutil.copy(apk_source, os.path.join(apk_dest_dir, "Bitacora_HES.apk"))
                print(f"    (APK copiado exitosamente en {apk_dest_dir})")
                apk_found = True
                break
                
    if not apk_found:
        print("    (No se encontro el APK. Si necesitas el instalador, recuerda compilarlo primero).")

    print("\n[4/4] ¡Listo!")
    print("=========================================================")
    print("Tu proyecto ha sido empaquetado de forma segura.")
    print(f"Todos tus cambios estan en la carpeta: {DEPLOY_DIR}")
    print()
    print("Toma esa carpeta, llevala a tu servidor,")
    print("y pega su contenido reemplazando lo viejo.")
    print()
    print("(NOTA IMPORTANTE: Al no incluir el archivo .env, cuando lo")
    print("pegues en tu servidor NO SOBRESCRIBIRA la configuracion")
    print("ni las contrasenas reales del servidor, cuidando la DB).")
    print("=========================================================")

if __name__ == "__main__":
    main()
