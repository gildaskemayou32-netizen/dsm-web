#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   Digital Services CM — Enterprise Web v3.0.0        ║
║   Flask + SQLite + Chart.js                          ║
╠══════════════════════════════════════════════════════╣
║  Installation : pip install -r requirements.txt      ║
║  Lancement    : python run.py                        ║
║  Accès local  : http://localhost:5000                ║
║  Accès réseau : http://<TON-IP>:5000                 ║
║  Login        : admin / admin123                     ║
╚══════════════════════════════════════════════════════╝
"""
import os
import socket
from app import create_app

app = create_app()


def get_local_ip():
    """Trouve l'IP locale pour l'accès depuis téléphone."""
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

    print("\n" + "═" * 52)
    print("  💰  Digital Services CM — Enterprise Web v3.0.0")
    print("═" * 52)
    print(f"  🌐  Local   : http://localhost:{port}")
    print(f"  📱  Réseau  : http://{ip}:{port}  ← téléphone")
    print(f"  🔑  Login   : admin / admin123")
    print("═" * 52 + "\n")

    app.run(
        host="0.0.0.0",   # accessible depuis téléphone sur le même WiFi
        port=port,
        debug=os.getenv("FLASK_DEBUG", "1") == "1",
    )
