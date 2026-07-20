"""Publishing a film as one transaction.

    sync -> save the cover -> write the record -> rebuild -> verify
         -> commit -> push

Every step must succeed or the whole thing rolls back: on any failure the
repository, the records and the published site are left exactly as they were.
Each successful publish is one git commit, so history is a complete audit trail.

Kino's transaction is smaller than Lens's, because the irreplaceable part is
not here. A photograph's original must survive a failed publish; a film's
master was never Kino's to hold. What can be lost here is a cover image and a
record, and both are cheap to write again.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import builder
import covers as cover_pipeline
import distributor
import entries as entry_store
import hosts
import visibility
from models import MAX_DESCRIPTION, MAX_TITLE, build_entry, entry_date, new_id


class PublishError(RuntimeError):
    """Publishing failed; the repository and published site are unchanged."""


def _validate(title, description, video_host, video_id):
    if not (title or "").strip():
        raise ValueError("A film needs a title.")
    if len(title) > MAX_TITLE:
        raise ValueError(f"Title cannot be more than {MAX_TITLE} characters.")
    if len(description or "") > MAX_DESCRIPTION:
        raise ValueError(
            f"Description cannot be more than {MAX_DESCRIPTION} characters."
        )
    if video_host not in hosts.HOSTS:
        raise ValueError(f"Unknown video host: {video_host!r}")
    if not str(video_id or "").strip():
        raise ValueError("A video identifier is required.")


def publish(*, title, description="", video_host=hosts.DEFAULT_HOST, video_id,
            cover, runtime=None, created=None, entries_root=None,
            artifacts_root=None, git=True):
    """Publish a film that already exists on its host. Returns the record."""
    _validate(title, description, video_host, video_id)

    if cover is None or not getattr(cover, "filename", ""):
        raise ValueError("A cover image is required.")

    entries_root = Path(entries_root or entry_store.ENTRIES_DIR)
    artifacts_root = Path(artifacts_root or entry_store.ARTIFACTS_DIR)

    if git:
        distributor.sync()
    original_head = distributor.current_head() if git else None

    entry_id = new_id()
    artifact_dir = artifacts_root / entry_id
    entry_path = None
    committed = False

    try:
        cover_pipeline.save_cover(cover, artifact_dir)

        entry = build_entry(
            title=title, description=description,
            video={"host": video_host, "id": video_id},
            cover=cover_pipeline.COVER_NAME, runtime=runtime,
            entry_id=entry_id,
            created=created or datetime.now(timezone.utc).astimezone(),
        )
        entry_path = entry_store.save_entry(entry, entries_root)

        builder.build(entries_root=entries_root, artifacts_root=artifacts_root)

        # The record and its cover images travel together: Cloudflare Pages
        # builds the site from this repository and cannot see anything git does
        # not carry. Covers are small; there is no original to keep out.
        if git:
            distributor.commit_paths([entry_path, artifact_dir],
                                     f"Publish film {entry_id}")
            committed = True
            distributor.push()

        return entry

    except Exception as error:
        _rollback(original_head, committed, entry_path, artifact_dir,
                  entries_root, artifacts_root, git)
        raise PublishError(f"Publishing failed; nothing was changed ({error}).") from error


EDITABLE = ("title", "description", "runtime", "visibility")


def revise(entry_id, changes, entries_root=None, artifacts_root=None, git=True):
    """Revise a film's editorial layer, and optionally replace its cover.

    The video reference can be corrected — a mistyped identifier is a typo, not
    a different work — but doing so is the one edit that changes what the page
    actually shows, so it is validated as strictly as publishing.
    """
    entries_root = Path(entries_root or entry_store.ENTRIES_DIR)
    artifacts_root = Path(artifacts_root or entry_store.ARTIFACTS_DIR)

    entry = entry_store.find_entry(entry_id, entries_root)
    if entry is None:
        raise ValueError(f"No such film: {entry_id}")

    title = changes.get("title", entry.get("title"))
    description = changes.get("description", entry.get("description"))
    video_host = changes.get("video_host", entry["video"]["host"])
    video_id = changes.get("video_id", entry["video"]["id"])
    _validate(title, description, video_host, video_id)

    if "visibility" in changes:
        allowed, reason = visibility.transition(entry, changes["visibility"])
        if not allowed:
            raise ValueError(reason)

    if git:
        distributor.sync()
    original_head = distributor.current_head() if git else None

    before = json.dumps(entry, indent=2, ensure_ascii=False)
    artifact_dir = artifacts_root / entry_id
    committed = False

    try:
        revised = dict(entry)
        revised["title"] = title.strip()
        revised["description"] = (description or "").strip()
        revised["video"] = {"host": video_host, "id": str(video_id).strip()}

        if "runtime" in changes:
            revised["runtime"] = changes["runtime"]
        if "visibility" in changes:
            revised["visibility"] = changes["visibility"]

        cover = changes.get("cover")
        if cover is not None and getattr(cover, "filename", ""):
            cover_pipeline.save_cover(cover, artifact_dir)

        path = entry_store.save_entry(revised, entries_root)

        builder.build(entries_root=entries_root, artifacts_root=artifacts_root)

        if git:
            distributor.commit_paths([path, artifact_dir],
                                     f"Revise film {entry_id}")
            committed = True
            distributor.push()

        return revised

    except Exception as error:
        _restore_record(original_head, committed, entry, before, entries_root,
                        artifacts_root, git)
        raise PublishError(f"Revision failed; nothing was changed ({error}).") from error


def withdraw(entry_id, entries_root=None, artifacts_root=None, git=True):
    """Withdraw a film from the publication, keeping its permalink.

    Lens's rule, and Kino inherits it: a published URL is a promise, so
    withdrawing means `archived` — the page still answers and says the film was
    withdrawn. The video is not touched, because Kino does not own it. Whether
    it remains watchable on its host is the publisher's business, set there.
    """
    return revise(entry_id, {"visibility": visibility.ARCHIVED},
                  entries_root=entries_root, artifacts_root=artifacts_root, git=git)


def erase(entry_id, entries_root=None, artifacts_root=None, git=True):
    """Erase a film page outright — the record, its covers, its permalink.

    For accidents, as in Lens: a page published by mistake was never something
    anyone could have linked to, and archiving it would leave a permanent
    notice about a work that was never meant to exist.

    This removes Kino's page and nothing else. The video remains exactly where
    it was on its host, untouched, because it was never Kino's to delete.
    """
    entries_root = Path(entries_root or entry_store.ENTRIES_DIR)
    artifacts_root = Path(artifacts_root or entry_store.ARTIFACTS_DIR)

    entry = entry_store.find_entry(entry_id, entries_root)
    if entry is None:
        raise ValueError(f"No such film: {entry_id}")

    if git:
        distributor.sync()
    original_head = distributor.current_head() if git else None

    path = entry_store.entry_path(entry_id, entry_date(entry), entries_root)
    artifact_dir = artifacts_root / entry_id
    before = json.dumps(entry, indent=2, ensure_ascii=False)
    committed = False

    try:
        path.unlink()
        shutil.rmtree(artifact_dir, ignore_errors=True)

        builder.build(entries_root=entries_root, artifacts_root=artifacts_root)

        if git:
            distributor.commit_paths([path, artifact_dir], f"Erase film {entry_id}")
            committed = True
            distributor.push()

        return entry

    except Exception as error:
        _restore_record(original_head, committed, entry, before, entries_root,
                        artifacts_root, git)
        raise PublishError(f"Erasure failed; nothing was changed ({error}).") from error


def _rollback(original_head, committed, entry_path, artifact_dir,
              entries_root, artifacts_root, git):
    """Undo a failed publish."""
    if git and committed and original_head:
        distributor.reset_hard(original_head)
    elif entry_path and Path(entry_path).exists():
        Path(entry_path).unlink()

    # Safe: this directory is named for an id generated moments ago and belongs
    # to no completed film.
    shutil.rmtree(artifact_dir, ignore_errors=True)

    _rebuild_quietly(entries_root, artifacts_root)


def _restore_record(original_head, committed, entry, before, entries_root,
                    artifacts_root, git):
    """Undo a failed revision or erasure."""
    if git and original_head:
        distributor.reset_hard(original_head)
    else:
        path = entry_store.entry_path(entry["id"], entry_date(entry), entries_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(before + "\n", encoding="utf-8")

    _rebuild_quietly(entries_root, artifacts_root)


def _rebuild_quietly(entries_root, artifacts_root):
    """Bring the built site back in line. The site is disposable, so a failure
    here must never mask the error that caused the rollback."""
    try:
        builder.build(entries_root=entries_root, artifacts_root=artifacts_root)
    except Exception:  # noqa: BLE001
        pass
