import os
import mysql.connector
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime, timedelta
import MySQLdb

def cargar_config():
    config = {}
    if os.path.exists("config.txt"):
        with open("config.txt", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
    return config

config = cargar_config()
PANEL_IP = config.get("PANEL_IP", "192.168.1.54")
USUARIO_PANEL = config.get("USUARIO_PANEL", "admin")
CONTRASENA_PANEL = config.get("CONTRASENA_PANEL", "atcgym1379")
SERVER_IP = config.get("SERVER_IP", "192.168.1.100")
DB_USER = config.get("DB_USER", "ATCGYM")
DB_PASS = config.get("DB_PASS", "atcgym1379")
DB_NAME = config.get("DB_NAME", "atcgym")

def conectar_db():
    return MySQLdb.connect(
        host=SERVER_IP,
        user=DB_USER,
        passwd=DB_PASS,
        db=DB_NAME
    )

def eliminar_persona_del_panel(id):
    url = f"http://{PANEL_IP}/ISAPI/AccessControl/UserInfo/Delete?format=json"
    payload = {
        "UserInfoDelCond": {
            "employeeNoList": [
                {"employeeNo": str(id)}
            ]
        }
    }
    response = requests.put(
        url,
        json=payload,
        auth=HTTPDigestAuth(USUARIO_PANEL, CONTRASENA_PANEL),
        headers={"Content-Type": "application/json"}
    )
    print(f"Eliminando {id} del panel: {response.status_code} {response.text}")

def main():
    conn = conectar_db()
    cursor = conn.cursor()
    # Buscar personas cuya membresía venció hace más de 8 días
    limite = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("SELECT id FROM personas WHERE fin < %s", (limite,))
    vencidos = cursor.fetchall()
    for (id,) in vencidos:
        eliminar_persona_del_panel(id)
    conn.close()

if __name__ == "__main__":
    main()