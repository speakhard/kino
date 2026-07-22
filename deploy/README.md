# Deploying Kino on ppmanchester

Kino has two halves, and they live in different places.

    ppmanchester                     GitHub                Cloudflare Pages
    ────────────                     ──────                ────────────────
    authoring service                entries/*.json        builds site/
    (private, Tailscale only)   →    artifacts/*/cover…   →  kino.joshbernhard.com
    references the films             (covers, in git)      (public, static)

The authoring interface is never public. The public site is static files and
never talks to the authoring service. The films themselves are on Vimeo/YouTube
and never touch either half — Kino stores a `{host, id}` and a cover, nothing
more.

> Produced for hand-install. Verify each step on the host; nothing here has
> been run against `ppmanchester`.

## Nothing irreplaceable lives here

Worth stating up front, because it shapes how much this deployment has to
protect. Kino holds no master. A film's bytes live on its host; Kino's canonical
records (`entries/*.json`) and its cover images (`artifacts/*/`) are **all
committed to git**. So a lost or rebuilt checkout costs nothing an ordinary
`git clone` does not restore, and a service swap risks no authored data. This is
the one place Kino is simpler than Lens, which holds the only copy of each
original and must back it up.

## 1. The Cloudflare Pages project — already configured

`kino.joshbernhard.com` is already live, built from `github.com/speakhard/kino`.
Recorded here for reproducibility:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Build command | `pip install -r requirements-build.txt && python builder.py` |
| Build output directory | `site` |
| Root directory | *(leave empty)* |

`requirements-build.txt` is deliberately not `requirements.txt`. Building the
site renders templates and copies already-derived covers; it never opens an
image. Keeping Pillow out of the deploy build means the public site's build does
not depend on a compiled extension. (`covers.py` imports Pillow lazily so
`builder.py` can read its constants without it.)

## 2. The deploy key

Publishing pushes to `origin/main` from ppmanchester. That needs a
**repository-scoped deploy key with write access** — the minimum required to
push to this one repository and nothing else. Never commit the key.

    # on ppmanchester, as the service user
    ssh-keygen -t ed25519 -f ~/.ssh/kino_deploy -N "" -C "kino-deploy@ppmanchester"

Add the public key at **github.com/speakhard/kino → Settings → Deploy keys**,
with *Allow write access* checked. Then teach SSH to use it for this repo only:

    # ~/.ssh/config
    Host github-kino
        HostName github.com
        User git
        IdentityFile ~/.ssh/kino_deploy
        IdentitiesOnly yes

    # in the checkout
    git remote set-url origin git@github-kino:speakhard/kino.git

Verify before relying on it:

    ssh -T git@github-kino        # expect: "successfully authenticated"

## 3. The authoring service

    # on ppmanchester
    git clone git@github-kino:speakhard/kino.git ~/kino
    cd ~/kino
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt

    sudo cp deploy/kino.service /etc/systemd/system/kino.service
    sudo editor /etc/systemd/system/kino.service   # fill the __PLACEHOLDERS__
    sudo systemctl daemon-reload
    sudo systemctl enable --now kino
    systemctl is-active kino

Fill the placeholders in the copied unit:

| Placeholder | Value |
|---|---|
| `__USER__` / `__GROUP__` | the unprivileged owner of the checkout |
| `__KINO_DIR__` | absolute path to the checkout (e.g. `/home/<user>/kino`) |
| `__TAILSCALE_IP__` | output of `tailscale ip -4` |

**The service binds to the Tailscale address, not loopback.** A health check
against `127.0.0.1:11914` will fail on a perfectly healthy service — this cost
real time on Crows. Check the bind address before concluding anything is wrong:

    systemctl cat kino | grep KINO_HOST
    curl -s -o /dev/null -w "%{http_code}\n" http://<tailscale-ip>:11914/

## 4. Verify (do all of these)

Bound to Tailscale, serving:

    curl -s -o /dev/null -w '%{http_code}\n' http://<TAILSCALE_IP>:11914/        # 200
    curl -s -o /dev/null -w '%{http_code}\n' http://<TAILSCALE_IP>:11914/films   # 200

**The debugger is absent** (serve.py runs under Waitress, never Flask's dev
server — a routed dev-server debugger would answer here):

    curl -s -o /dev/null -w '%{http_code}\n' http://<TAILSCALE_IP>:11914/console # 404

**Not exposed on all interfaces** — a request to a non-Tailscale address of the
host must fail to connect (not 200):

    curl -s -o /dev/null -w '%{http_code}\n' http://<PUBLIC_OR_LAN_IP>:11914/     # connection refused

## 5. Roll back

Remove the service without touching any published film:

    sudo systemctl disable --now kino
    sudo rm /etc/systemd/system/kino.service
    sudo systemctl daemon-reload

Or roll the checkout back to a previous commit:

    cd ~/kino && git checkout <previous-commit> && sudo systemctl restart kino

Because canonical records and covers live in git and the films live on their
hosts, no authored data is ever at risk in a service swap or rollback.

## Notes

- `KINO_HOST` / `KINO_PORT` configure the bind (defaults `127.0.0.1` /
  `11914`, port from `kin` → 11-9-14). Only the unit sets `KINO_HOST` to the
  tailnet address; the code default stays on loopback so nothing is exposed by
  accident.
- There are no secrets in this service and none in the environment — only a
  bind host and port. Syndication credentials, if ever added, live in a
  gitignored `.env` read only by the local app, never by the deploy.

## Publishing (the deploy key in use)

Publishing a film is a single transaction:

    sync -> save cover -> write entries/<year>/<id>.json -> rebuild -> verify
         -> commit -> push

If any step fails, the repository and the published site are left exactly as
they were. Each successful publish is one `Publish film <id>` commit — the audit
trail. `git` carries the records and covers; Cloudflare Pages builds `site/`
from them. The push uses the deploy key from §2.
