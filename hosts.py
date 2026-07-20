"""Where a film is hosted — the whole of Kino's knowledge of video providers.

Kino does not upload, transcode, or store video. A film arrives already
published on a host, identified by nothing more than a provider name and an
identifier. This module turns that pair into the two URLs a page needs.

Deliberately two pure functions and a table. No credentials, no API calls, no
network at build time — a provider being down cannot break a build, and the
whole thing is testable offline.

**The record stores `{host, id}`, never embed HTML.** Embed markup is
provider-specific and changes without notice; baking it into the record would
put today's provider in the history permanently. Keeping the pair means
changing providers is a re-upload and a record edit rather than a migration.

Adding a provider is a dict entry. If this file ever grows conditionals about
what individual providers can do, the abstraction has stopped paying for itself
and should be reconsidered rather than extended.
"""
from __future__ import annotations

HOSTS = {
    "vimeo": {
        "label": "Vimeo",
        "embed": "https://player.vimeo.com/video/{id}",
        "watch": "https://vimeo.com/{id}",
    },
    "youtube": {
        "label": "YouTube",
        "embed": "https://www.youtube-nocookie.com/embed/{id}",
        "watch": "https://www.youtube.com/watch?v={id}",
    },
}

DEFAULT_HOST = "vimeo"


class UnknownHost(ValueError):
    """A film references a video host Kino has no entry for."""


def _template(video, key: str) -> str:
    host = (video or {}).get("host") or ""
    entry = HOSTS.get(host)
    if entry is None:
        raise UnknownHost(f"Unknown video host: {host!r}")
    return entry[key].format(id=(video or {}).get("id", ""))


def embed_url(video) -> str:
    """The URL an iframe points at."""
    return _template(video, "embed")


def watch_url(video) -> str:
    """The film's canonical address on its host, for linking out."""
    return _template(video, "watch")


def label(video) -> str:
    """The host's human name, for 'Watch on Vimeo'."""
    host = (video or {}).get("host") or ""
    if host not in HOSTS:
        raise UnknownHost(f"Unknown video host: {host!r}")
    return HOSTS[host]["label"]
