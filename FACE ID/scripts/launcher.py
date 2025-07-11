import threading
import subprocess
import os
import sys
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

def run_server():
    base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
    python_path = os.path.join(base_dir, "python_embebido", "python.exe")
    config = {}
    config_path = os.path.join(base_dir, "config.txt")
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
    server_ip = config.get("SERVER_IP", "127.0.0.1")
    # Ejecuta el servidor y muestra la salida en la consola principal
    subprocess.Popen([
        python_path,
        "-m", "waitress",
        "--host=" + server_ip,
        "--port=5000",
        "app:app"
    ], cwd=base_dir)




def create_image():
    base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
    icon_path = os.path.join(base_dir, "icono.png")
    return Image.open(icon_path)




def on_open(icon, item=None):
    import webbrowser
    base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
    config = {}
    config_path = os.path.join(base_dir, "config.txt")
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
    server_ip = config.get("SERVER_IP", "127.0.0.1")
    webbrowser.open(f"http://{server_ip}:5000")




def on_quit(icon, item):
    icon.stop()
    # Aquí podrías agregar lógica para cerrar el servidor si lo deseas

if __name__ == '__main__':
    threading.Thread(target=run_server, daemon=True).start()
    icon = Icon(
        "Gimnasio",
        create_image(),
        "Control Acceso Gimnasio",
        menu=Menu(
            MenuItem('Abrir aplicación', on_open),
            MenuItem('Salir', on_quit)
        )
    )
    icon.run(setup=lambda i: i.visible)
    # Doble clic abre la app
    icon.visible = True
    icon._MENU_HANDLE = on_open  # Para algunos entornos, pero pystray ya soporta doble clic