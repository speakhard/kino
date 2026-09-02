"""Where the publication is — and the fact that it is not where Kino is.

**A publishing service opens a publication. It does not have to live inside it.**

`PROTOCOL.md` §0 defines a publishing service as a program that *opens and
serves* a Commons publication, and says it is not part of any publication. §2
says a publication is not required to contain software. §9 requires that any
implementation be able to **import an existing conformant publication** — which
Kino cannot do today, because every path it uses is implicit: either relative to
the working directory the process happened to be started in, or, in the git
layer, relative to the directory `distributor.py` was installed in.

Those two implicit answers agree with each other only by the accident of Kino
being run from inside the publication it authors. Nothing says so and nothing
checks it. Lens found the gap the expensive way on 2026-08-30: a publish
transaction fast-forwarded the same directory the running service had been
loaded from, and the rebuild failed on a Jinja filter that the newly-arrived
templates required and the already-loaded code did not have. Kino has the same
shape — `distributor.sync()` at `publisher.py:63` followed by an in-process
`builder.build()` at `:86` — and was shown to reproduce the identical message.

This module is the one place that answers the question, so there is a boundary
to see rather than eight separate assumptions to rediscover:

    root()              the publication Kino is opening
    entries_dir()       its records
    artifacts_dir()     its cover images
    masthead()          its manifest
    site_dir()          where its public presentation is built
    staging_dir()       where a build is assembled before replacing it
    templates_dir()     the renderer's templates, carried by the publication
    static_dir()        the renderer's static assets, carried by the publication
    state_dir()         this host's state ABOUT the publication — not part of it

Three of those deserve their own note.

`templates_dir()` and `static_dir()` resolve beneath the publication because that
is where they live today: the reference renderer travels inside the publication
so a clone rebuilds with no other software obtained, and Cloudflare Pages builds
the public site by running that renderer from the repository. §2 is explicit that
this is a *choice an implementation makes* and not part of the conformant
publication — the files may be ignored or removed by any implementation. They are
resolved here, beside the publication's own data, to keep that choice visible
rather than scattered.

**These are not the authoring interface's templates.** Flask resolves those
relative to `app.py`, which is correct and must stay that way: `compose.html`,
`edit.html`, `entries.html` and `published.html` belong to the publishing
service, not to any publication it opens. They presently share the `templates/`
directory with the renderer's templates; the two sets are disjoint, so nothing
depends on the confusion.

`state_dir()` is this installation's state *about* a publication. Protocol §9
forbids an implementation writing anything into a publication beyond conformant
protocol data, so this is deliberately not publication data. Kino writes nothing
there today — it has no publish lock, and its syndication credential lives in a
gitignored `.env`. It is named here because it is where a lock belongs if one is
ever added, and because a lock owned by one service does not protect a
publication a second service is also writing.

Resolution order, most explicit first:

1. `opened(path)` — a programmatic override, for tests and for a service that
   opens several publications in one process.
2. `KINO_PUBLICATION` — explicit configuration, the intended production answer.
3. the current working directory — the transition default, which is exactly
   today's behaviour and is what keeps this change inert until something sets
   one of the above.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

ENV_VAR = "KINO_PUBLICATION"

# The programmatic override. None means "not overridden" — which is different
# from an override deliberately set to the current directory.
_opened: Path | None = None


def root() -> Path:
    """The publication this service is currently opening."""
    if _opened is not None:
        return _opened
    configured = os.environ.get(ENV_VAR, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.cwd()


@contextmanager
def opened(path):
    """Open a different publication for the duration of a block.

    Restores the previous answer afterwards, including "no override", so a test
    that opens a publication cannot leak that choice into the next one.
    """
    global _opened
    previous = _opened
    _opened = Path(path).expanduser().resolve()
    try:
        yield _opened
    finally:
        _opened = previous


def path(*parts) -> Path:
    """A path beneath the publication root."""
    return root().joinpath(*parts)


# --- The Kino profile's layout ---------------------------------------------
# One function per location, rather than constants, because the publication a
# service is opening is a runtime fact. A module-level constant would freeze the
# answer at import time — which is the same class of mistake as a long-running
# process holding a module the publication has since changed.

def entries_dir() -> Path:
    return path("entries")


def artifacts_dir() -> Path:
    return path("artifacts")


def masthead() -> Path:
    return path("masthead.json")


def site_dir() -> Path:
    return path("site")


def staging_dir() -> Path:
    return path("site.tmp")


def templates_dir() -> Path:
    return path("templates")


def static_dir() -> Path:
    return path("static")


def state_dir() -> Path:
    return path(".commons")


class ManifestError(RuntimeError):
    """The publication's manifest is missing, unreadable, or incomplete."""


def manifest() -> dict:
    """The publication's identity, read from its manifest.

    Reading a manifest is a **publication-data** operation, not a rendering one.
    It lived in `builder.py` while the service and the renderer were the same
    program; the service needs to know what publication it has open — its name
    for the composer, its canonical URL — and should be able to learn that
    without executing anything the publication carries.

    That separation is the trust boundary in miniature: opening a publication
    reads data; rendering one runs code, and is a separate, deliberate act.
    """
    try:
        data = json.loads(masthead().read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ManifestError(f"masthead.json is missing or unreadable: {error}") from error

    # The feed's own durable identity must be stored, never derived. Checked
    # here rather than in the build verifier because by then the template has
    # already failed with an UndefinedError that says nothing about what to do.
    if not str(data.get("feed_guid") or "").strip():
        raise ManifestError(
            "masthead.json has no feed_guid — the feed's durable atom:id "
            "(RFC 4287 §4.2.6). It must be stored rather than derived from "
            "canonical_url, or rehosting reissues the feed's identity along "
            "with its address. Freeze it at the feed's current <id>."
        )

    return data


def looks_like_a_publication(candidate=None) -> bool:
    """Whether a directory presents as a Commons publication.

    The manifest is the test, because §2 makes it the one file a publication MUST
    have. Nothing here judges the profile or the spec version: that is
    `builder.site_config()`'s job, and it fails with a message about the specific
    field that is wrong, which is more useful than a boolean.
    """
    base = Path(candidate).expanduser().resolve() if candidate else root()
    return (base / "masthead.json").is_file()
