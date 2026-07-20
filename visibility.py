"""Publication state, and the promise a permalink makes.

Six states, and one rule that shapes all of them:

    **A published URL is a promise. Nothing may break it.**

That rule divides the six cleanly. Three states describe work that has *never*
been published — draft, scheduled, private — and those have no public permalink
to keep, so refusing to serve them breaks nothing. Three describe work that
*was* published — public, unlisted, archived — and every one of those must keep
resolving forever, whatever the publisher later decides about listing it.

There is deliberately no `deleted`. Withdrawing a work means moving it to
`archived`, where the permalink still answers and says plainly that it was
withdrawn. A 404 where something used to be is a broken promise, and it is also
a lie: the work existed, and somebody may have linked to it.

This module is Commons-shared. A Crow, a Photograph and a Film have different
composition surfaces but the same publication lifecycle.
"""
from __future__ import annotations

from datetime import datetime, timezone

DRAFT = "draft"
SCHEDULED = "scheduled"
PUBLIC = "public"
UNLISTED = "unlisted"
ARCHIVED = "archived"
PRIVATE = "private"

ALL = (DRAFT, SCHEDULED, PUBLIC, UNLISTED, ARCHIVED, PRIVATE)

# Every state, described by what it does rather than by what it is called.
#
#   permalink — is there a public page at its permanent address?
#   listed    — does it appear in the feed, the archive, tags and collections?
#   syndicated— does it go out in the RSS/Atom feed?
#   published — has this work ever been public? (the permalink promise)
STATES = {
    DRAFT: {
        "permalink": False, "listed": False, "syndicated": False, "published": False,
        "label": "Draft",
        "note": "Never published. No permalink exists, so none can be broken.",
    },
    SCHEDULED: {
        "permalink": False, "listed": False, "syndicated": False, "published": False,
        "label": "Scheduled",
        "note": "Becomes public automatically at its publication date.",
    },
    PUBLIC: {
        "permalink": True, "listed": True, "syndicated": True, "published": True,
        "label": "Published",
        "note": "Listed everywhere.",
    },
    UNLISTED: {
        "permalink": True, "listed": False, "syndicated": False, "published": True,
        "label": "Unlisted",
        "note": "Reachable by anyone with the link; absent from feeds and indexes.",
    },
    ARCHIVED: {
        "permalink": True, "listed": False, "syndicated": False, "published": True,
        "label": "Archived",
        "note": "Withdrawn from the publication. The permalink still answers, "
                "and says so — this is what replaces deletion.",
    },
    PRIVATE: {
        "permalink": False, "listed": False, "syndicated": False, "published": False,
        "label": "Private",
        "note": "Visible only in the Publisher's Desk.",
    },
}


def state_of(work) -> str:
    """The work's state, defaulting to public for records written before states."""
    state = (work or {}).get("visibility") or PUBLIC
    return state if state in STATES else PUBLIC


def _now():
    return datetime.now(timezone.utc)


def effective_state(work, now=None) -> str:
    """The state accounting for time.

    A scheduled work whose moment has arrived is public, without anything having
    to run. Publication is thus correct even if a scheduler never fires — the
    build simply tells the truth about the current time.
    """
    state = state_of(work)
    if state != SCHEDULED:
        return state

    publish_at = work.get("publish_at") or work.get("created")
    try:
        due = datetime.fromisoformat(publish_at)
    except (TypeError, ValueError):
        return SCHEDULED

    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return PUBLIC if due <= (now or _now()) else SCHEDULED


def has_permalink(work, now=None) -> bool:
    """Should a public page exist at this work's permanent address?"""
    return STATES[effective_state(work, now)]["permalink"]


def is_listed(work, now=None) -> bool:
    """Should it appear in the feed, archive, tags and collections?"""
    return STATES[effective_state(work, now)]["listed"]


def is_syndicated(work, now=None) -> bool:
    return STATES[effective_state(work, now)]["syndicated"]


def was_published(work, now=None) -> bool:
    """Has this work ever been public? Governs whether a promise exists to keep."""
    return STATES[effective_state(work, now)]["published"]


def transition(work, to_state, now=None) -> tuple[bool, str | None]:
    """May this work move to `to_state`? Returns (allowed, reason_if_not).

    The one forbidden move is back across the published line: a work that has
    been public cannot become a draft, because its permalink is already out in
    the world. Withdrawing it means `archived`, which keeps the promise.
    """
    if to_state not in STATES:
        return False, f"{to_state!r} is not a publication state."

    if was_published(work, now) and not STATES[to_state]["published"]:
        return False, (
            f"This work has been published, so it cannot return to "
            f"{STATES[to_state]['label'].lower()} — its permalink is already public. "
            f"Use archived to withdraw it while keeping the link alive."
        )
    return True, None
