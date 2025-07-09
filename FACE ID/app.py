# Imports estándar
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "python_embebido", "Lib", "site-packages"))

import time
import json
import threading
import traceback
from datetime import datetime, timedelta, timezone
import webbrowser
import logging
#import waitress

# Imports de terceros
import MySQLdb
import requests
from requests.auth import HTTPDigestAuth
from werkzeug.utils import secure_filename  
import asyncio
import hypercorn.asyncio
from hypercorn.config import Config
from dbutils.pooled_db import PooledDB

# Imports locales
import eliminar_vencidos

from flask import Flask, render_template, request, redirect, jsonify





os.environ["FLASK_RUN_FROM_CLI"] = "false"



def resource_path(relative_path):
    """
    Devuelve la ruta absoluta al recurso, siempre relativa a la carpeta ATC-GYM 4.0,
    sin importar si se ejecuta como script o como ejecutable.
    """
    # Busca la carpeta raíz ATC-GYM 4.0 en la ruta actual
    base_path = os.path.abspath(os.path.dirname(sys.executable if hasattr(sys, '_MEIPASS') else __file__))
    while True:
        if os.path.basename(base_path).lower() == "atc-gym 4.0":
            break
        new_base = os.path.dirname(base_path)
        if new_base == base_path:
            # No se encontró la carpeta raíz, usa la ruta original
            break
        base_path = new_base
    return os.path.normpath(os.path.join(base_path, relative_path))


# --------------------------
# CONFIGURACIÓN DEL LOGGING
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)



# --------------------------
# CARGAR CONFIGURACIÓN DESDE config.txt
# --------------------------
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




# --------------------------
# POOL DE CONEXIONES A LA BASE DE DATOS
# --------------------------

POOL = PooledDB(
    creator=MySQLdb,
    maxconnections=8,  # Número máximo de conexiones abiertas al mismo tiempo
    mincached=2,       # Conexiones abiertas al iniciar
    maxcached=4,       # Máximo de conexiones en el pool
    blocking=True,
    host=SERVER_IP,
    user=DB_USER,
    passwd=DB_PASS,
    db=DB_NAME,
    charset='utf8'
)



# --------------------------
# FUNCIONES AUXILIARES PANEL HIKVISION
# --------------------------

tz = timezone(timedelta(hours=-5))





# --------------------------
# Funciones para manejar fechas y formatos
# --------------------------
def parse_fecha(fecha):
    if isinstance(fecha, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(fecha, fmt)
            except ValueError:
                continue
    return fecha if isinstance(fecha, datetime) else None




# --------------------------
# Funciones para manejar la base de datos
# --------------------------
def get_persona_por_id(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, fin, rfoto, membresia FROM personas WHERE id=%s", (id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado






# --------------------------
# Funciones para interactuar con el panel Hikvision
# --------------------------
def enviar_persona_al_panel(id, nombre, fin):
    url = f"http://{PANEL_IP}/ISAPI/AccessControl/UserInfo/Record?format=json"
    begin_time = datetime.now().strftime("%Y-%m-%dT00:00:00")
    end_time = fin.strftime("%Y-%m-%dT23:59:59")
    payload = {
        "UserInfo": {
            "employeeNo": id,
            "name": nombre,
            "userType": "normal",
            "Valid": {
                "enable": True,
                "beginTime": begin_time,
                "endTime": end_time,
                "timeType": "local"
            },
            "doorRight": "1",
            "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
            "gender": "male",
            "localUIRight": False,
            "maxOpenDoorTime": 0,
            "floorNumbers": [],
            "callNumbers": [],
            "password": ""
        }
    }
    response = requests.post(
        url,
        json=payload,
        auth=HTTPDigestAuth(USUARIO_PANEL, CONTRASENA_PANEL),
        headers={"Content-Type": "application/json"}
    )
    print("Respuesta al crear usuario:", response.status_code, response.text)
    return response.status_code, response.text






# --------------------------
# Funciones para enviar fotos al panel Hikvision
# --------------------------
def enviar_foto_al_panel(id, ruta_foto):
    url = f"http://{PANEL_IP}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"
    time.sleep(1)
    with open(ruta_foto, "rb") as f:
        foto_bytes = f.read()
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }
    face_json = (
        f'{{"faceLibType":"blackFD","FDID":"1","FPID":"{id}"}}'
    )
    data = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="FaceDataRecord";\r\n'
        f"Content-Type: application/json\r\n\r\n"
        f"{face_json}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="img"; filename="{id}.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + foto_bytes + f"\r\n--{boundary}--\r\n".encode()
    response = requests.post(
        url,
        data=data,
        auth=HTTPDigestAuth(USUARIO_PANEL, CONTRASENA_PANEL),
        headers=headers
    )
    print("Respuesta al subir foto:", response.status_code, response.text)
    return response.status_code, response.text







# --------------------------
# Funciones para eliminar usuarios del panel Hikvision
# --------------------------
def eliminar_persona_del_panel(id):
    url = f"http://{PANEL_IP}/ISAPI/AccessControl/UserInfo/Delete?format=json"
    payload = {
        "UserInfoDelCond": {
            "employeeNoList": [
                {"employeeNo": id}
            ]
        }
    }
    response = requests.put(
        url,
        json=payload,
        auth=HTTPDigestAuth(USUARIO_PANEL, CONTRASENA_PANEL),
        headers={"Content-Type": "application/json"}
    )
    print("Respuesta al eliminar usuario del panel:", response.status_code, response.text)
    return response.status_code, response.text





#---------------------------
# Función para eliminar la foto del panel Hikvision
#---------------------------
def eliminar_foto_del_panel(id):
    url = f"http://{PANEL_IP}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"
    payload = {
        "FaceDataRecord": {
            "FDID": "1",
            "FPID": str(id),
            "faceURL": ""
        }
    }
    response = requests.put(
        url,
        json=payload,
        auth=HTTPDigestAuth(USUARIO_PANEL, CONTRASENA_PANEL),
        headers={"Content-Type": "application/json"}
    )
    print(f"Respuesta al eliminar foto (PUT): {response.status_code} {response.text}")
    return response.status_code, response.text






#--------------------------
# Función para actualizar una persona en el panel Hikvision
#--------------------------
def actualizar_persona_en_panel(id, nombre, beginTime, endTime):
    url = f"http://{PANEL_IP}/ISAPI/AccessControl/UserInfo/Modify?format=json"
    payload = {
        "UserInfo": {
            "employeeNo": str(id),
            "name": nombre,
            "userType": "normal",
            "Valid": {
                "enable": True,
                "beginTime": beginTime,
                "endTime": endTime,
                "timeType": "local"
            },
            "doorRight": "1",
            "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
            "gender": "male",
            "localUIRight": False,
            "maxOpenDoorTime": 0,
            "floorNumbers": [],
            "callNumbers": [],
            "password": ""
        }
    }
    response = requests.put(
        url,
        json=payload,
        auth=HTTPDigestAuth(USUARIO_PANEL, CONTRASENA_PANEL),
        headers={"Content-Type": "application/json"}
    )
    print(f"Respuesta al actualizar usuario: {response.status_code} {response.text}")
    return response.status_code, response.text





# --------------------------
# CONFIGURACIÓN INICIAL
# --------------------------
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.get("RFOTO_PATH", "static/fotos")
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)






# --------------------------
# Función para conectar a la base de datos
# --------------------------
def conectar_db():
    return POOL.connection()







# --------------------------
# Función para validar la extensión de los archivos subidos
# --------------------------
def extension_valida(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']






# --------------------------
# RUTA: Página principal
# --------------------------
@app.route('/')
def index():
    busqueda = request.args.get('busqueda', '').strip()
    conn = conectar_db()
    cursor = conn.cursor()
    if busqueda:
        cursor.execute(
            "SELECT npersona, nombre, id, fin, membresia, tpersona FROM personas WHERE nombre LIKE %s OR id LIKE %s",
            (f"%{busqueda}%", f"%{busqueda}%")
        )
    else:
        cursor.execute("SELECT npersona, nombre, id, fin, membresia, tpersona FROM personas")
    personas = cursor.fetchall()
    conn.close()
    ahora = datetime.now()
    personas_vigencia = []
    for p in personas:
        fin_raw = p[3]
        fin = parse_fecha(fin_raw)
        vigente = fin is not None and fin >= ahora
        dias_para_eliminar = None
        if not vigente and fin is not None:
            dias_vencido = (ahora - fin).days
            dias_para_eliminar = max(0, 8 - dias_vencido)
        if fin:
            mostrar_fecha = fin.strftime('%Y-%m-%d %H:%M:%S')
        else:
            mostrar_fecha = fin_raw or "-"
        # p[4] = ti.po (ti.po de membresía), p[5] = tpersona
        personas_vigencia.append((p[0], p[1], p[2], mostrar_fecha, vigente, p[4], dias_para_eliminar, p[5]))
    return render_template("index.html", personas=personas_vigencia, busqueda=busqueda)







# --------------------------
# Función para sincronizar todo con el panel en segundo plano
# --------------------------
def sincronizar_todo_panel(id, nombre, fin_dt, ruta_foto):
    eliminar_persona_del_panel(id)
    enviar_persona_al_panel(id, nombre, fin_dt)
    eliminar_foto_del_panel(id)
    enviar_foto_al_panel(id, ruta_foto)





# --------------------------
# RUTA: Renovar membresía (reutilizada para subir solo la foto al panel cuando esta se elimina)
# --------------------------
@app.route('/renovar/<id>', methods=['POST'])
def renovar_membresia(id):
    """
    Renueva la membresía de una persona:
    - Solo actualiza la foto si corresponde.
    - NO modifica la fecha de membresía (fin).
    - Sincroniza los datos y la foto con el panel Hikvision.
    """
    resultado = get_persona_por_id(id)
    if not resultado:
        return "Usuario no encontrado", 404
    nombre, fin, ruta_foto_db, membresia = resultado

    foto = request.files.get('foto')
    ruta_foto = None

    # 1. Si subieron una foto nueva, guárdala y actualiza la ruta en la base de datos
    if foto and foto.filename:
        nombre_archivo = secure_filename(f"{id}.jpg")
        ruta_foto = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
        foto.save(ruta_foto)
        # Guardar la ruta relativa con separador "/"
        ruta_foto_relativa = f"../FOTOS/{nombre_archivo}"
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE personas SET rfoto=%s, sincronizado=0 WHERE id=%s",
            (ruta_foto_relativa, id)
        )
        conn.commit()
        conn.close()
    # 2. Si no subieron foto, pero hay una ruta en la base y el archivo existe, úsala
    elif ruta_foto_db and os.path.exists(ruta_foto_db):
        ruta_foto = ruta_foto_db
    # 3. Si no hay foto ni en la base ni subida, muestra error
    else:
        return "Debes subir una foto válida para este usuario.", 400

    # Sincroniza con el panel en segundo plano
    fin_dt = parse_fecha(fin)
    threading.Thread(
        target=sincronizar_todo_panel,
        args=(id, nombre, fin_dt, ruta_foto),
        daemon=True
    ).start()

    return redirect('/')






# --------------------------
# RUTA API: Verificación de acceso por cédula (para Hikvision)
# --------------------------
@app.route('/api/verificar_acceso/<id>', methods=['GET'])
def verificar_acceso(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fin FROM personas WHERE id = %s", (id,))
    resultado = cursor.fetchone()
    conn.close()
    ahora = datetime.now()
    fin = parse_fecha(resultado[0]) if resultado else None
    if fin and fin >= ahora:
        return jsonify({"id": id, "acceso": True})
    else:
        return jsonify({"id": id, "acceso": False})






# --------------------------
# DICCIONARIO DE EVENTOS
# --------------------------
eventos_dict = {
    "21": "Acceso Bloqueado",
    "22": "Acceso Desbloqueado",
    "75": "Autenticación Face ID",
    "77": "Autenticado mediante huella",
    "78": "Autenticado mediante tarjeta",
    "79": "Autenticado mediante contraseña",
}





# --------------------------
# RUTA: Ver eventos del panel Hikvision
# --------------------------
@app.route('/eventos_panel')
def eventos_panel():
    url = f"http://{PANEL_IP}/ISAPI/AccessControl/AcsEvent?format=json"
    hoy = datetime.now(tz)
    start_time = hoy.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_time = hoy.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    payload = {
        "AcsEventCond": {
            "searchID": "python-search-1",
            "searchResultPosition": 0,
            "maxResults": 24,
            "major": 0,
            "minor": 0,
            "startTime": start_time,
            "endTime": end_time,
            "timeReverseOrder": True
        }
    }
    data = json.dumps(payload)
    eventos = []
    try:
        response = requests.post(
            url,
            data=data,
            auth=HTTPDigestAuth(USUARIO_PANEL, CONTRASENA_PANEL),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            eventos = data.get('AcsEvent', {}).get('InfoList', [])
            if eventos:
                logging.info(f"Ejemplo de evento recibido del panel: {eventos[0]}")
            else:
                logging.info("No hay eventos recibidos del panel.")
    except Exception as e:
        logging.error("Error de conexión: %s", e, exc_info=True)
        eventos = []
    return render_template('eventos_panel.html', eventos=eventos, eventos_dict=eventos_dict)






# --------------------------
# RUTA: Recibir eventos de acceso (para Hikvision)  
# --------------------------
ultimo_usuario_autenticado = {}

@app.route('/lectura', methods=['POST'])
def recibir_evento():
    t0 = time.time()
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({"mensaje": "Formato de datos no soportado"}), 415

    if 'event_log' in data:
        try:
            evento = json.loads(data['event_log'])
            acceso_evento = evento.get('AccessControllerEvent', {})
            minor = str(acceso_evento.get('subEventType', ''))
            id = acceso_evento.get('employeeNoString') or "desconocido"
            nombre = acceso_evento.get('name', None)
            fecha_evento = evento.get('dateTime') or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print("Error al parsear event_log:", e)
            return jsonify({"mensaje": "Error al parsear event_log"}), 400
    else:
        minor = str(data.get('minor', ''))
        id = data.get('cardNo') or data.get('employeeNoString') or "desconocido"
        nombre = data.get('name', None)
        fecha_evento = data.get('time') or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if minor == "75":
        t1 = time.time()
        conn = conectar_db()
        t2 = time.time()
        cursor = conn.cursor()
        t3 = time.time()
        cursor.execute("SELECT nombre, fin FROM personas WHERE id=%s", (id,))
        resultado = cursor.fetchone()
        t4 = time.time()
        nombre_db = resultado[0] if resultado else nombre
        fin = resultado[1] if resultado else None
        permitido = 0
        if fin:
            ahora = datetime.now()
            membresia_dt = parse_fecha(fin)
            if membresia_dt and membresia_dt >= ahora:
                permitido = 1
        cursor.execute(
            "INSERT INTO eventos (id, nombre, tipo_evento, fecha, fin, accesos) VALUES (%s, %s, %s, %s, %s, %s)",
            (id, nombre_db, "Reconocimiento facial", fecha_evento, fin, permitido)
        )
        t5 = time.time()
        conn.commit()
        conn.close()
        t6 = time.time()
        print(f"Conexión: {t2-t1:.3f}s | Cursor: {t3-t2:.3f}s | SELECT: {t4-t3:.3f}s | INSERT: {t5-t4:.3f}s | COMMIT+CLOSE: {t6-t5:.3f}s | TOTAL: {t6-t0:.3f}s")
        return jsonify({"mensaje": "Evento de reconocimiento facial registrado"}), 200

    return jsonify({"mensaje": "Evento ignorado"}), 200





# --------------------------
# RUTA: tipo de persona
# --------------------------
@app.route('/cambiar_tipo/<id>', methods=['POST'])
def cambiar_tipo(id):
    nuevo_tipo = request.form.get('membresia')
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE personas SET membresia=%s WHERE id=%s", (nuevo_tipo, id))
    conn.commit()
    conn.close()
    return redirect('/')





def fin_valida(fin):
    fin_dt = parse_fecha(fin)
    return fin_dt is not None





# --------------------------
# TAREA: Sincronizar membresías con el panel Hikvision
# --------------------------
def sincronizar_membresias_con_panel():
    while True:
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, fin, rfoto FROM personas WHERE sincronizado = 0")
            personas = cursor.fetchall()
            for id, nombre, fin, rfoto in personas:
                print(f"Intentando sincronizar persona: {id} - {nombre}")

                
                # Validar fecha de fin ANTES de cualquier intento de sincronización
                logging.info(f"Intentando sincronizar persona: {id} - {nombre}")
                if not fin_valida(fin):
                    logging.warning(f"Usuario {id} tiene fecha de fin inválida o vacía. Se marca como sincronizado para evitar bucle.")
                    cursor.execute(
                        "UPDATE personas SET sincronizado=1 WHERE id=%s",
                        (id,)
                    )
                    conn.commit()
                    continue  # Salta a la siguiente persona

                fin_dt = parse_fecha(fin)
                beginTime = datetime.now().strftime("%Y-%m-%dT00:00:00")
                endTime = fin_dt.strftime("%Y-%m-%dT23:59:59")
                status, resp = actualizar_persona_en_panel(id, nombre, beginTime, endTime)
                print(f"Respuesta del panel para {id}: {status} - {resp}")

                # Si el error es por endTime o badJsonContent, marcar como sincronizado para evitar bucle
                logging.info(f"Respuesta del panel para {id}: {status} - {resp}")
                if status == 400 and ("badJsonContent" in resp or "endTime" in resp):
                    logging.warning(f"Error de fecha de fin al actualizar usuario {id}. Se marca como sincronizado para evitar bucle.")
                    cursor.execute(
                        "UPDATE personas SET sincronizado=1 WHERE id=%s",
                        (id,)
                    )
                    conn.commit()
                    continue

                # Si el usuario no existe, intenta crearlo (solo una vez)
                if status == 400 and "employeeNoNotExist" in resp:
                    logging.info(f"El usuario {id} no existe en el panel, intentando crearlo...")
                    if not fin_valida(fin):
                        logging.warning(f"Usuario {id} tiene fecha de fin inválida o vacía al crear. Se marca como sincronizado para evitar bucle.")

                        cursor.execute(
                            "UPDATE personas SET sincronizado=1 WHERE id=%s",
                            (id,)
                        )
                        conn.commit()
                        continue
                    status, resp = enviar_persona_al_panel(id, nombre, fin_dt)
                    logging.info(f"Respuesta al crear usuario {id}: {status} - {resp}")
                    if status == 400 and ("badJsonContent" in resp or "endTime" in resp):
                        logging.warning(f"Error de fecha de fin al crear usuario {id}. Se marca como sincronizado para evitar bucle.")
                        cursor.execute(
                            "UPDATE personas SET sincronizado=1 WHERE id=%s",
                            (id,)
                        )
                        conn.commit()
                        continue

                # Usar la ruta relativa de la base de datos para sincronizar
                ruta_foto_relativa = rfoto
                ruta_foto = resource_path(ruta_foto_relativa.lstrip("./\\"))
                logging.info(f"Ruta absoluta de la foto para sincronización: {ruta_foto}")
                logging.info(f"¿Existe el archivo de foto?: {os.path.exists(ruta_foto)}")

                foto_subida = False
                if status in (200, 201) and os.path.exists(ruta_foto):
                    status_foto, resp_foto = enviar_foto_al_panel(id, ruta_foto)
                    logging.info(f"Respuesta al subir foto para {id}: {status_foto} - {resp_foto}")
                    if status_foto in (200, 201):
                        foto_subida = True
                    elif status_foto == 400 and "deviceUserAlreadyExistFace" in resp_foto:
                        logging.info("La foto ya existe en el panel, se marca como sincronizado.")
                        foto_subida = True
                    else:
                        foto_subida = False
                elif not os.path.exists(ruta_foto):
                    foto_subida = True  # No hay foto que subir

                if status in (200, 201) and foto_subida:
                    cursor.execute(
                        "UPDATE personas SET sincronizado=1 WHERE id=%s",
                        (id,)
                    )
                    conn.commit()
                    logging.info(f"Persona {id} sincronizada correctamente.")
                else:
                    logging.error(f"Error actualizando/creando usuario o subiendo foto para {id}: {resp}")
            conn.close()
        except Exception as e:
            logging.error("Error en la sincronización automática con el panel: %s", e, exc_info=True)
            traceback.print_exc()
        time.sleep(0.1)





# --------------------------
# RUTA: Tabla de eventos para AJAX/actualización
# --------------------------
@app.route('/tabla_eventos')
def tabla_eventos():
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT nevento, id, nombre, tipo_evento, fecha, fin FROM eventos ORDER BY fecha DESC LIMIT 30"
    )
    eventos = cursor.fetchall()
    conn.close()
    return render_template('tabla_eventos.html', eventos=eventos, eventos_dict=eventos_dict)






# --------------------------
# Iniciar hilos de sincronización y eliminación
# --------------------------

if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and os.environ.get("RUN_MAIN") != "true":
    #print(">>> Lanzando hilo de sincronización (al importar el módulo)", flush=True)
    threading.Thread(target=sincronizar_membresias_con_panel, daemon=True).start()
    #print(">>> Ejecutando eliminación de vencidos al iniciar", flush=True)
    try:
        eliminar_vencidos.main()
        #print(">>> eliminación de vencidos ejecutada correctamente.")
    except Exception as e:
        logging.error("Error al ejecutar eliminación de vencidos al inicio: %s", e, exc_info=True)
        traceback.print_exc()
    #threading.Thread(target=tarea_eliminar_vencidos, daemon=True).start()





# --------------------------
# INICIAR LA APP
# --------------------------
if __name__ == '__main__':
    
    config = Config()
    config.bind = [f"{SERVER_IP}:5000"]
    asyncio.run(hypercorn.asyncio.serve(app, config))