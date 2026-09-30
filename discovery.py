"""Emit the Commons discovery document — PROTOCOL.md §11.1.

Vendored from Lens (itself vendored from Crow) with one deliberate difference:
Kino has no §11.3 authoring surface, so this copy never emits an `authoring`
object and has no `authoring_block()`. Lens's version imports its
`commons_author` module to describe its endpoint; Kino has no such module and
must not advertise one it does not serve. Everything else — the projection,
both addresses, the required set, the redirect — is Lens's, unchanged. Three
copies is past the moment to extract a shared toolkit; this file is the third.

The document is a projection of `masthead.json` and nothing else. Every field it
carries is read from the manifest; none is minted here. That is deliberate: if
this module wrote its own `commons_spec`, a publication could advertise one
protocol version in its manifest and a different one at its well-known URI, and
§1.1 allows exactly one handshake per publication. The manifest is the single
place a publication says what it speaks.

No `authoring` object is emitted: Kino serves no command surface, and §11.1
treats an absent object as a complete answer — rung one, discoverable but not
authorable — which a client is forbidden to probe past.

Nothing in this module is Crow-specific. When a second publishing service needs
the same projection, this is what moves into a shared toolkit — kept to one file
and one public function so that move is mechanical rather than archaeological.
"""
from __future__ import annotations

import json
from pathlib import Path

# The one well-known URI the protocol defines (§11.1).
WELL_KNOWN_RELATIVE = Path(".well-known/commons.json")

# The required fallback address (§11.1). Not a workaround: the specification
# names both, because some static hosts do not serve dot-prefixed paths and a
# publication should not be undiscoverable for want of a hosting quirk.
# Cloudflare Pages confirmed the concern in production — the dot-directory is
# absent from the deployed output entirely — and the protocol answered with a
# second address rather than with a redirect rule, which would have been
# deployment detail dressed up as interoperability.
#
# The two MUST be identical, so both are written from the same bytes.
MIRROR_RELATIVE = Path("commons.json")
# A courtesy, not a requirement, and no longer load-bearing now that the
# fallback is part of the protocol: on hosts that read this file the canonical
# URI resolves directly, sparing conformant clients a second request and giving
# non-Commons tooling something at the conventional address. Harmless where it
# is ignored.
REDIRECTS_RELATIVE = Path("_redirects")
_REDIRECT_RULE = "/.well-known/commons.json /commons.json 302"

# The frozen required set (§11.6 rule 1). A client may depend on these and
# nothing else, so a document missing any of them is not worth serving.
REQUIRED_FIELDS = ("commons_spec", "profile", "name", "canonical_url")

class DiscoveryError(RuntimeError):
    """Raised when the manifest cannot produce a conformant discovery document."""


def document(manifest: dict) -> dict:
    """Project a manifest into a §11.1 discovery document.

    Raises DiscoveryError rather than emitting a document that a conformant
    client would reject — a publication that cannot describe itself correctly
    should fail its build, not advertise something broken.
    """
    doc = {
        "commons_spec": manifest.get("commons_spec"),
        "profile": manifest.get("profile"),
        "name": manifest.get("name"),
        # §2 names `canonical_url`; `url` is accepted as the older spelling some
        # of these manifests still carry.
        "canonical_url": manifest.get("canonical_url") or manifest.get("url"),
    }

    # Optional capabilities, projected from the manifest (§11.6 rule 3: new
    # features are advertised as capabilities, not as new structure). This is
    # how an aggregator learns a publication has a feed (§7) without guessing
    # at /feed.xml and without being told out of band.
    capabilities = manifest.get("capabilities")
    if isinstance(capabilities, list):
        declared = [c for c in capabilities if isinstance(c, str)]
        if declared:
            doc["capabilities"] = declared

    missing = [
        field for field in REQUIRED_FIELDS
        if not isinstance(doc.get(field), str) or not doc[field].strip()
    ]
    if missing:
        raise DiscoveryError(
            "masthead.json cannot produce a discovery document; "
            f"missing or empty: {', '.join(missing)}"
        )

    return doc


def write(manifest: dict, root: Path) -> Path:
    """Write the discovery document into a built site rooted at `root`.

    Both addresses §11.1 requires, from one set of bytes so they cannot drift,
    plus the optional redirect described above.
    """
    body = json.dumps(document(manifest), indent=2) + "\n"

    destination = root / WELL_KNOWN_RELATIVE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(body, encoding="utf-8")
    (root / MIRROR_RELATIVE).write_text(body, encoding="utf-8")

    redirects = root / REDIRECTS_RELATIVE
    existing = redirects.read_text(encoding="utf-8") if redirects.exists() else ""
    if _REDIRECT_RULE not in existing:
        redirects.write_text(
            (existing.rstrip("\n") + "\n" if existing.strip() else "") + _REDIRECT_RULE + "\n",
            encoding="utf-8",
        )
    return destination
