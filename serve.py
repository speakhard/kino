"""Production entrypoint — Waitress, loopback by default.

Disclose nothing beyond this machine unless explicitly told to. Production sets
KINO_HOST to the Tailscale address; the default binds to 127.0.0.1 so a
misconfigured deployment fails closed rather than exposing the authoring
interface to the network.
"""
import os

from waitress import serve

import publication
from app import app

HOST = os.environ.get("KINO_HOST", "127.0.0.1")
# "kin" -> k=11, i=9, n=14 -> 11914, following the convention used by crows
# (31823) and lens (12514).
PORT = int(os.environ.get("KINO_PORT", "11914"))

if __name__ == "__main__":
    # Say which publication is open. Kino serves a publication rather than being
    # one, so *which* is a fact about this process — and one worth reading in a
    # log, because until now it was only ever implied by where the process was
    # started. A directory with no manifest is reported rather than refused:
    # Kino is still perfectly able to serve its own interface, and a publication
    # that is merely absent should say so in words rather than as a stack trace
    # on the first request.
    opened = publication.root()
    print(f"Serving Kino on http://{HOST}:{PORT}")
    print(f"Publication: {opened}"
          + ("" if publication.looks_like_a_publication(opened)
             else "  (no masthead.json here — set "
                  f"{publication.ENV_VAR} to the publication to open)"))
    serve(app, host=HOST, port=PORT)
