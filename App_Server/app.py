import os
import socket
from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

# This helps us see which "parallel" server is answering the request
container_id = socket.gethostname()

def get_db_connection():
    return mysql.connector.connect(
        host='db', # This matches the service name in your docker-compose.yml
        user='flask_user',
        password='your_secure_password',
        database='gsu_catalog'
    )

@app.route('/')
def hello():
    return f"<h1>Hello from Flask!</h1><p>Served by Container ID: <b>{container_id}</b></p>"

@app.route('/test-db')
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"status": "Success", "database": db_name[0], "server": container_id})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e), "server": container_id}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)