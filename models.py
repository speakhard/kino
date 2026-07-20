"""The Film record, and the small amount of shaping the templates need.

A Film is a publication entry that references a video someone else is hosting.
Kino owns the page, the cover image and the description; the host owns the
bytes. That division is the whole design.

The record deliberately does not say where its cover image came from. It may
have been uploaded artwork or a frame captured from the film while publishing;
once chosen it is simply the cover, and its provenance is not the record's
business.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

MAX_TITLE = 200
MAX_DESCRIPTION = 4000


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def entry_date(entry) -> datetime:
    """The film's publication date, as a datetime."""
    raw = (entry or {}).get("created")
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
    return parsed


def feed_key(entry):
    """Curated chronology: pinned first, then placement, then newest first.

    The same rule Crows and Lens use — feed order is editorial and deliberately
    independent of the timestamp, so a film can be placed without rewriting when
    it was published.
    """
    feed = (entry or {}).get("feed") or {}
    return (
        0 if feed.get("pinned") else 1,
        feed.get("rank") if feed.get("rank") is not None else 10**6,
        -entry_date(entry).timestamp(),
    )


def runtime_display(entry) -> str:
    """372 -> "6:12"; 3730 -> "1:02:10"; nothing -> "".

    Empty rather than "0:00" when unknown: a film whose runtime was never
    determined should say nothing, not claim to be zero seconds long.
    """
    seconds = (entry or {}).get("runtime")
    try:
        total = int(round(float(seconds)))
    except (TypeError, ValueError):
        return ""
    if total <= 0:
        return ""

    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def display_title(entry) -> str:
    return (entry or {}).get("title") or "Untitled"


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", str(value or "")).strip().lower()
    return re.sub(r"[\s_-]+", "-", value)


def build_entry(*, title, description, video, cover, runtime=None,
                entry_id=None, created=None, visibility="public") -> dict:
    """Assemble a Film record.

    `video` is {host, id} and nothing more. `cover` is the stored filename —
    how it was chosen is not recorded, because it does not matter once chosen.
    """
    created = created or datetime.now(timezone.utc).astimezone()

    return {
        "id": entry_id or new_id(),
        "created": created.isoformat(),
        "title": (title or "").strip(),
        "description": (description or "").strip(),
        "runtime": runtime,
        "visibility": visibility,
        "publish_at": None,
        "feed": {"pinned": False, "rank": None, "sequence": None},
        "video": {"host": video["host"], "id": str(video["id"]).strip()},
        "cover": cover,
    }
