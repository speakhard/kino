"""Production entrypoint — Waitress, loopback by default.

Disclose nothing beyond this machine unless explicitly told to. Production sets
KINO_HOST to the Tailscale address; the default binds to 127.0.0.1 so a
misconfigured deployment fails closed rather than exposing the authoring
interface to the network.
"""
import os

from waitress import serve

from app import app

HOST = os.environ.get("KINO_HOST", "127.0.0.1")
# "kin" -> k=11, i=9, n=14 -> 11914, following the convention used by crows
# (31823) and lens (12514).
PORT = int(os.environ.get("KINO_PORT", "11914"))

if __name__ == "__main__":
    print(f"Serving Kino on http://{HOST}:{PORT}")
    serve(app, host=HOST, port=PORT)
