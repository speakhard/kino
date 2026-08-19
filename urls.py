"""One way to build a URL beneath a publication's canonical root.

Vendored, like commons-ui and discovery.py: every publication stays runnable on
its own and depends on nothing central.

**The invariant this exists to hold:**

    the canonical publication URL is the final, non-redirecting root URL, and a
    relative reference resolved from that document stays inside the publication

Both halves were broken at once when a publication first moved to a path. The
canonical root was written without a trailing slash — `…/filmed` — because every
template built subordinate URLs by concatenation:

    canonical_url + "/feed.xml"

which needs the root NOT to end in a slash or it produces `…/filmed//feed.xml`.
That works perfectly at a domain root, where the trailing slash is implicit, and
breaks the moment a publication is mounted at a path: a browser at `…/filmed`
resolves the page's own relative `feed.xml` against a base with no trailing
slash, and lands on `…/feed.xml` — off the publication, onto whatever else is
served at that origin. The page returns 200 and every link on it is wrong.

So the root carries its slash, and nothing concatenates. `root()` guarantees the
first; `url()` guarantees the second and can never emit a doubled slash.
"""
from __future__ import annotations

import urllib.parse


def root(manifest: dict) -> str:
    """A publication's canonical root, ending in exactly one slash.

    `canonical_url` is §2's field; `url` is the older spelling some manifests
    still carry. Either may be written with or without the trailing slash — the
    convention is the slash, and this is what enforces it rather than trusting
    every manifest to be edited correctly.
    """
    base = str(manifest.get("canonical_url") or manifest.get("url") or "").strip()
    if not base:
        return ""
    return base if base.endswith("/") else base + "/"


def url(base: str, *parts: str) -> str:
    """A URL beneath `base`, with exactly one slash between segments.

    Resolution is RFC 3986's, not string arithmetic: each part is resolved
    against a base guaranteed to end in a slash, so a part never replaces the
    last path segment and a doubled slash cannot be produced.

        url("https://x.test/filmed/", "feed.xml")   https://x.test/filmed/feed.xml
        url("https://x.test/filmed",  "feed.xml")   https://x.test/filmed/feed.xml
        url("https://x.test/filmed/", "f/a/")       https://x.test/filmed/f/a/

    A trailing slash on the last part is preserved, because `f/a/` and `f/a` are
    different addresses and only the first is a directory-like resource whose
    own relative references behave.
    """
    out = str(base or "")
    for part in parts:
        piece = str(part or "").lstrip("/")
        if not piece:
            continue
        if not out.endswith("/"):
            out += "/"
        out = urllib.parse.urljoin(out, piece)
    return out
