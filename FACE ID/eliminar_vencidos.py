# eliminar_vencidos.py

import os
import mysql.connector
from datetime import date

from config import SERVER_IP, DB_USER, DB_PASS, DB_NAME, RFOTO_PATH

def get_connection():
    return mysql.connector.connect(
        host=SERVER_IP,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def borrar_vencidos():
    hoy = date.today()
    cnx = get_connection()
    cursor = cnx.cursor(dictionary=True)

    # Busca socios con vencimiento anterior a hoy
    cursor.execute(
        "SELECT id FROM socios WHERE vencimiento < %s",
        (hoy,)
    )
    vencidos = cursor.fetchall()

    # Si no hay nada que borrar, salimos
    if not vencidos:
        cursor.close()
        cnx.close()
        return

    # Por cada socio vencido, borra de la BD y de disco
    for socio in vencidos:
        member_id = socio['id']

        # Elimina de la tabla
        cursor.execute(
            "DELETE FROM socios WHERE id = %s",
            (member_id,)
        )

        # Borra foto si existe
        filename = f"{member_id}.jpg"
        photo_path = os.path.join(RFOTO_PATH, filename)
        try:
            os.remove(photo_path)
        except FileNotFoundError:
            pass

    cnx.commit()
    cursor.close()
    cnx.close()

if __name__ == "__main__":
    borrar_vencidos()