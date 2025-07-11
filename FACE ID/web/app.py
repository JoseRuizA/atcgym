import os
from flask import Flask, request, jsonify
import mysql.connector
import datetime
from dateutil.relativedelta import relativedelta

from config import SERVER_IP, DB_USER, DB_PASS, DB_NAME, RFOTO_PATH

app = Flask(__name__)

def get_connection():
    return mysql.connector.connect(
        host=SERVER_IP,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

@app.route('/api/create_member', methods=['POST'])
def create_member():
    data = request.json
    member_id = data['id']
    name = data['name']
    card = data['card']
    photo_bytes = data.get('photo')  # asumimos bytes

    cnx = get_connection()
    cursor = cnx.cursor()
    expiration = (
        datetime.date.today()
        + relativedelta(months=+1)
    ).strftime('%Y-%m-%d')
    query = """
        INSERT INTO socios (id, name, card, vencimiento)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (member_id, name, card, expiration))
    cnx.commit()
    cursor.close()
    cnx.close()

    if photo_bytes:
        filename = f"{member_id}.jpg"
        photo_path = os.path.join(RFOTO_PATH, filename)
        with open(photo_path, 'wb') as f:
            f.write(photo_bytes)

    return jsonify(success=True), 201


@app.route('/api/events', methods=['GET'])
def get_events():
    cnx = get_connection()
    cursor = cnx.cursor(dictionary=True)
    start = request.args.get('startDate')
    end = request.args.get('endDate')
    query = "SELECT * FROM eventos WHERE date >= %s AND date <= %s"
    cursor.execute(query, (start, end))
    events = cursor.fetchall()
    cursor.close()
    cnx.close()
    return jsonify(events), 200


@app.route('/api/delete_member/<member_id>', methods=['DELETE'])
def delete_member(member_id):
    cnx = get_connection()
    cursor = cnx.cursor()
    cursor.execute("DELETE FROM socios WHERE id = %s", (member_id,))
    cnx.commit()
    cursor.close()
    cnx.close()

    # Borra la foto del disco
    filename = f"{member_id}.jpg"
    photo_path = os.path.join(RFOTO_PATH, filename)
    try:
        os.remove(photo_path)
    except FileNotFoundError:
        pass

    return jsonify(success=True), 200


if __name__ == '__main__':
    # Cambia host/port si lo deseas, aquí escucha en todas las interfaces
    app.run(host='0.0.0.0', port=5000)