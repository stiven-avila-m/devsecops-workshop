"""
DevSecOps Workshop - App Demo
Microservicio Flask sencillo que sirve como payload del contenedor.
La aplicacion en si NO es el problema; el problema esta en el Dockerfile.
"""
from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify({
        "service": "devsecops-demo",
        "host": socket.gethostname(),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "message": "Hello from a (hopefully) secure container!"
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # Bind 0.0.0.0 para que el contenedor sea accesible
    app.run(host="0.0.0.0", port=8080)
