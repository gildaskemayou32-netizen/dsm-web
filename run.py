#!/usr/bin/env python3
"""
Digital Services CM — Enterprise v3.1.3
Lancement : python run.py
"""
import os, socket, sys, pathlib

# S'assurer que le dossier courant est dans le path
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from app import create_app

app = create_app()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


if __name__ == "__main__":
    ip   = get_local_ip()
    port = int(os.getenv("PORT", 5000))

    print("\n" + "═" * 54)
    print("  💰  Digital Services CM — Enterprise v3.1.3")
    print("═" * 54)
    print(f"  🌐  Local   : http://localhost:{port}")
    print(f"  📱  Réseau  : http://{ip}:{port}  ← téléphone WiFi")
    print(f"  🔑  Login   : admin / admin123")
    print("═" * 54 + "\n")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
