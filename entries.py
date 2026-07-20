"""Reading and writing films — the canonical record of what has been published.

One JSON file per film, filed under its publication year:

    entries/2026/abc123.json

The record is small, readable with `cat`, diffable in git, and independent of
this code. Cover images live in `artifacts/<id>/`, addressed by the same id.

The video itself lives nowhere near here. That is the point.
"""
from __future__ import annotations

import json
from pathlib import Path

import visibility
from models import entry_date, feed_key

ENTRIES_DIR = Path("entries")
ARTIFACTS_DIR = Path("artifacts")


def entry_path(entry_id: str, created, root: Path | None = None) -> Path:
    root = Path(root or ENTRIES_DIR)
    return root / str(created.year) / f"{entry_id}.json"


def artifact_dir(entry_id: str, root: Path | None = None) -> Path:
    return Path(root or ARTIFACTS_DIR) / entry_id


def save_entry(entry: dict, root: Path | None = None) -> Path:
    path = entry_path(entry["id"], entry_date(entry), root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def load_entry(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # One malformed record must never take down the whole publication.
        return None


def load_all(root: Path | None = None) -> list[dict]:
    """Every film on disk regardless of state — the authoring view."""
    root = Path(root or ENTRIES_DIR)
    films = []
    for path in sorted(root.glob("*/*.json")):
        film = load_entry(path)
        if film and film.get("id"):
            films.append(film)
    return sorted(films, key=feed_key)


def load_entries(root: Path | None = None) -> list[dict]:
    """Films that belong in the feed, in curated order."""
    return [f for f in load_all(root) if visibility.is_listed(f)]


def load_permalinked(root: Path | None = None) -> list[dict]:
    """Everything that must have a page at its permanent address.

    Wider than load_entries(): a withdrawn film appears in no index, but its
    permalink must keep answering — it was published, and a published URL is a
    promise.
    """
    return [f for f in load_all(root) if visibility.has_permalink(f)]


def find_entry(entry_id: str, root: Path | None = None) -> dict | None:
    root = Path(root or ENTRIES_DIR)
    for path in root.glob(f"*/{entry_id}.json"):
        return load_entry(path)
    return None


def group_by_year(films: list[dict]) -> dict[int, list[dict]]:
    """{year: [films]}, newest year first — the archive's spine."""
    years: dict[int, list[dict]] = {}
    for film in films:
        years.setdefault(entry_date(film).year, []).append(film)
    return {year: years[year] for year in sorted(years, reverse=True)}


def neighbours(films: list[dict], entry_id: str):
    """(newer, older) around a film, for previous/next navigation."""
    ids = [f["id"] for f in films]
    try:
        i = ids.index(entry_id)
    except ValueError:
        return None, None
    return (films[i - 1] if i > 0 else None,
            films[i + 1] if i + 1 < len(films) else None)
