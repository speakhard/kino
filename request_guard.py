"""Refuse the requests a browser can be tricked into making.

This service has no login. Its protection is the network: it binds to the
tailnet address and nothing else. That boundary stops strangers reaching the
service, but not a page a stranger wrote, open in a browser *on* the tailnet —
a browser will happily send a form POST to any address it can reach, and will
happily resolve a hostile hostname to a private address. Two checks close those
two holes, and neither is visible to the person using the service normally.

**DNS rebinding — the Host allowlist.** A hostile page at `evil.example` can
re-point its own name at this service's address after the page has loaded; the
browser then treats this service as same-origin with the hostile page and lets
it read the responses. What it cannot change is the `Host` header, which still
says `evil.example`. So every request, of every method, must name a host this
service answers to: its bound address and port, loopback, and anything the
operator adds in `<PREFIX>_ALLOWED_HOSTS`.

**Cross-site request forgery — the origin check.** A state-changing request
(POST, PUT, PATCH, DELETE) must come from this service's own pages. Browsers
say where a request came from in two headers, and the check reads both:

    Sec-Fetch-Site   cross-site / same-site           refused
    Origin           present and not this origin      refused
    neither header                                    refused, unless
                                                      <PREFIX>_ALLOW_LEGACY_CLIENTS=1

Every browser that can run this service's forms sends at least one of them, so
the only clients the last row affects are non-browser tools (curl, scripts),
and those are exactly the clients the operator can name and opt in.
"Same-site" is refused as well as "cross-site": on a tailnet every host is the
same site as every other, which is precisely the case to defend.

No endpoint is exempt. This service receives no bearer-authenticated API
calls; if one is added, exempt it only when a valid bearer is presented, never
by path alone.

Vendored, byte-identical, into Kino and Commons Publisher; configured by the
two lines in each app that call `install()`.
"""
from __future__ import annotations

import os

from flask import Flask, request

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Loopback is always allowed, on any port: a rebinding attack cannot make a
# browser send `Host: 127.0.0.1`, because the attacker's page is not loaded
# from there.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})

REFUSED_FETCH_SITES = frozenset({"cross-site", "same-site"})

TRUTHY = frozenset({"1", "true", "yes", "on"})


def split_host(value: str) -> tuple[str, str | None]:
    """`host[:port]` -> (host, port or None), lowercased; IPv6 kept bracketed."""
    value = (value or "").strip().lower()
    if value.startswith("["):
        end = value.find("]")
        if end == -1:
            return value, None
        rest = value[end + 1:]
        return value[:end + 1], (rest[1:] if rest.startswith(":") else None)
    if value.count(":") == 1:
        host, port = value.split(":")
        return host, port
    return value, None


def allowed_hosts(bind_host: str, bind_port: str | int, extra: str = "") -> set[str]:
    """The exact `host:port` values this service answers to (loopback aside).

    A wildcard bind (0.0.0.0, ::) names no address, so it contributes nothing;
    such a deployment must list its names in `<PREFIX>_ALLOWED_HOSTS`.
    """
    allowed = set()
    host = (bind_host or "").strip().lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if host and host not in ("0.0.0.0", "[::]"):
        allowed.add(f"{host}:{bind_port}")
        if str(bind_port) == "80":
            allowed.add(host)
    for item in (extra or "").split(","):
        item = item.strip().lower()
        if item:
            allowed.add(item)
    return allowed


def host_is_allowed(header: str, allowed: set[str]) -> bool:
    host, port = split_host(header)
    if not host:
        return False
    if host in LOOPBACK_HOSTS:
        return True
    return (f"{host}:{port}" if port else host) in allowed


def origin_problem(method: str, headers, own_origin: str, allow_legacy: bool) -> str | None:
    """Why an unsafe request must be refused, or None if it may proceed."""
    if method.upper() not in UNSAFE_METHODS:
        return None
    site = (headers.get("Sec-Fetch-Site") or "").strip().lower()
    origin = headers.get("Origin")
    if site in REFUSED_FETCH_SITES:
        return f"request came from another site (Sec-Fetch-Site: {site})"
    if origin is not None:
        if origin.strip().lower() != own_origin.lower():
            return f"request came from another origin ({origin.strip() or 'empty'})"
        return None
    if site in ("same-origin", "none"):
        return None
    if allow_legacy:
        return None
    return "request carried neither Origin nor Sec-Fetch-Site"


def install(app: Flask, *, prefix: str, default_host: str, default_port: int) -> None:
    """Guard every request `app` serves.

    Reads `<prefix>_HOST` / `<prefix>_PORT` (the same variables serve.py binds
    with), `<prefix>_ALLOWED_HOSTS` and `<prefix>_ALLOW_LEGACY_CLIENTS` at
    request time, so the answer always matches the running configuration.
    """

    @app.before_request
    def _guard():
        env = os.environ
        allowed = allowed_hosts(env.get(f"{prefix}_HOST", default_host),
                                env.get(f"{prefix}_PORT", str(default_port)),
                                env.get(f"{prefix}_ALLOWED_HOSTS", ""))
        if not host_is_allowed(request.host, allowed):
            return (f"Refused: this service does not answer to the host "
                    f"{request.host!r}. Add it to {prefix}_ALLOWED_HOSTS if it "
                    f"should.\n", 403, {"Content-Type": "text/plain; charset=utf-8"})

        problem = origin_problem(
            request.method, request.headers, f"{request.scheme}://{request.host}",
            env.get(f"{prefix}_ALLOW_LEGACY_CLIENTS", "").strip().lower() in TRUTHY)
        if problem:
            return (f"Refused: {problem}. State-changing requests must come from "
                    f"this service's own pages.\n", 403,
                    {"Content-Type": "text/plain; charset=utf-8"})
        return None
