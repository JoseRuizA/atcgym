import os
from dotenv import load_dotenv

# 1. Carga el .env que está en la carpeta raíz (FACE ID)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# 2. Expone cada valor como variable Python
PANEL_IP          = os.getenv("PANEL_IP")
USUARIO_PANEL     = os.getenv("USUARIO_PANEL")
CONTRASENA_PANEL  = os.getenv("CONTRASENA_PANEL")
SERVER_IP         = os.getenv("SERVER_IP")
DB_USER           = os.getenv("DB_USER")
DB_PASS           = os.getenv("DB_PASS")
DB_NAME           = os.getenv("DB_NAME")
RFOTO_PATH        = os.getenv("RFOTO_PATH")
