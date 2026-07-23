"""Build the published site from the canonical records.

Same shape as Crows and Lens: render everything into a staging directory,
verify it, and only then swap it into place. A failed build can never leave a
half-published site, and the live site is destroyed only after a complete one
exists.

What Kino adds is nothing, which is the interesting part. The video is not
here; the page carries an embed URL constructed from a provider and an
identifier. So the build makes no network calls, needs no image library, and
copies a cover image and some HTML. Kino's published site is the lightest of
the three publications despite being the one about the largest medium.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import escape

import entries as entry_store
import hosts
import visibility
from covers import CARD_NAME, COVER_NAME
from models import display_title, entry_date, runtime_display

SITE_DIR = Path("site")
STAGING_DIR = Path("site.tmp")
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
MASTHEAD = Path("masthead.json")


class BuildError(RuntimeError):
    """A built site is missing or renders blank."""


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        # An undefined variable is a build failure, not a silently blank page.
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["date"] = lambda f, fmt="%B %-d, %Y": entry_date(f).strftime(fmt)
    env.filters["runtime"] = runtime_display
    env.filters["title_of"] = display_title
    # The public build knows one thing about the host: how to embed its player.
    # watch_url() and label() stay in the adapter, but no public page links out
    # to a host or names one — the film lives here, and only here.
    env.filters["embed"] = hosts.embed_url
    return env


def site_config() -> dict:
    try:
        return json.loads(MASTHEAD.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BuildError(f"masthead.json is missing or unreadable: {error}") from error


def _render(env, template, out: Path, **context) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(env.get_template(template).render(**context), encoding="utf-8")


def _copy_covers(films, staging: Path, artifacts_root) -> list[str]:
    """Copy each film's cover images into the site. Returns films missing them."""
    missing = []
    for film in films:
        source = Path(artifacts_root) / film["id"]
        target = staging / "covers" / film["id"]
        target.mkdir(parents=True, exist_ok=True)

        for name in (COVER_NAME, CARD_NAME):
            if not (source / name).exists():
                missing.append(f"{film['id']}/{name}")
                continue
            shutil.copy(source / name, target / name)
    return missing


def build(entries_root=None, artifacts_root=None) -> None:
    entries_root = Path(entries_root or entry_store.ENTRIES_DIR)
    artifacts_root = Path(artifacts_root or entry_store.ARTIFACTS_DIR)

    env = _env()
    site = site_config()

    listed = entry_store.load_entries(entries_root)
    permalinked = entry_store.load_permalinked(entries_root)

    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True)

    try:
        _render(env, "index.html", STAGING_DIR / "index.html",
                films=listed, site=site, depth=0)

        _render(env, "archive.html", STAGING_DIR / "archive" / "index.html",
                years=entry_store.group_by_year(listed), site=site, depth=1)

        _render(env, "feed.xml", STAGING_DIR / "feed.xml",
                films=[f for f in listed if visibility.is_syndicated(f)],
                site=site, depth=0)

        for film in permalinked:
            newer, older = entry_store.neighbours(listed, film["id"])
            _render(env, "film.html", STAGING_DIR / "f" / film["id"] / "index.html",
                    film=film, site=site, depth=2,
                    withdrawn=visibility.effective_state(film) == visibility.ARCHIVED,
                    newer=newer, older=older)

        if STATIC_DIR.exists():
            # compose.css styles the authoring interface, which the published
            # site has no way to reach. Shipping it would only describe
            # surfaces a reader cannot use.
            shutil.copytree(STATIC_DIR, STAGING_DIR / "static",
                            ignore=shutil.ignore_patterns("compose.css"))

        shutil.copy(MASTHEAD, STAGING_DIR / "masthead.json")

        missing = _copy_covers(permalinked, STAGING_DIR, artifacts_root)
        if missing:
            raise BuildError("Missing cover images: " + "; ".join(missing[:5]))

        verify(STAGING_DIR, permalinked, listed)

        # Destructive step last, after a complete site exists.
        if SITE_DIR.exists():
            shutil.rmtree(SITE_DIR)
        STAGING_DIR.rename(SITE_DIR)

    except BaseException:
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        raise

    print(f"Built Kino: {len(listed)} film(s) listed, "
          f"{len(permalinked)} permalinked into {SITE_DIR}/")


def verify(site_dir: Path, permalinked, listed) -> None:
    """Assert a built site is present and complete; raise on any gap.

    A publication with no films is a valid state, not a failure — it is what a
    new publication looks like. So the checks are about films that exist, not
    about there being any.
    """
    index = site_dir / "index.html"
    if not index.exists():
        raise BuildError("index.html was not generated")

    index_html = index.read_text(encoding="utf-8")

    def embedded(video, html) -> bool:
        # The embed URL carries query parameters, so its `&`s render as `&amp;`
        # in the page. Compare against the escaped form the template actually
        # emits, not the raw URL, or every player would read as missing.
        return str(escape(hosts.embed_url(video))) in html

    for film in listed:
        # The feed is a stream of players now, not a poster wall: a listed film
        # must carry its embed in the index itself, watchable without leaving.
        if not embedded(film["video"], index_html):
            raise BuildError(f"{film['id']} is listed but its player is absent from the feed")

    for film in permalinked:
        page = site_dir / "f" / film["id"] / "index.html"
        if not page.exists():
            raise BuildError(f"missing permalink page for {film['id']}")

        html = page.read_text(encoding="utf-8")

        # The one thing a film page must carry: a way to watch the film. If the
        # embed URL is missing the page is decoration, however well it renders.
        if not embedded(film["video"], html):
            raise BuildError(f"{film['id']} renders no video embed")

        if not (site_dir / "covers" / film["id"] / COVER_NAME).exists():
            raise BuildError(f"{film['id']} has no cover image in the site")

    # The host stays invisible. No public page may name a provider or link out to
    # a film's home on its host. The embed URL necessarily contains the player
    # domain — that is the player itself, the one sanctioned appearance — but an
    # outbound "Watch on …" link or a bare watch URL is a leak, and fails the
    # build rather than shipping.
    watch_urls = [hosts.watch_url(film["video"]) for film in permalinked]
    for page in sorted(site_dir.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        if "Watch on" in text:
            raise BuildError(f"{page.relative_to(site_dir)} names an external host ('Watch on …')")
        for watch in watch_urls:
            if watch in text:
                raise BuildError(f"{page.relative_to(site_dir)} links out to the host ({watch})")


if __name__ == "__main__":
    build()
