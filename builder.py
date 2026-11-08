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

import urls
from markupsafe import escape

import discovery
import entries as entry_store
import hosts
import publication
import visibility
from covers import CARD_NAME, COVER_NAME
from models import display_title, entry_date, runtime_display



class BuildError(RuntimeError):
    """A built site is missing or renders blank."""


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(publication.templates_dir()),
        autoescape=select_autoescape(["html", "xml"]),
        # An undefined variable is a build failure, not a silently blank page.
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["url"] = urls.url
    env.filters["root"] = urls.root
    env.filters["date"] = lambda f, fmt="%B %-d, %Y": entry_date(f).strftime(fmt)
    env.filters["runtime"] = runtime_display
    env.filters["title_of"] = display_title
    # The public build knows one thing about the host: how to embed its player.
    # watch_url() and label() stay in the adapter, but no public page links out
    # to a host or names one — the film lives here, and only here.
    env.filters["embed"] = hosts.embed_url
    return env


def site_config() -> dict:
    """Publication identity, from the manifest.

    Kept as the renderer's name for it: this module is the reference renderer and
    travels with the publication, so it reads the manifest through the same
    boundary the service does rather than parsing it a second way.
    """
    try:
        return publication.manifest()
    except publication.ManifestError as error:
        raise BuildError(str(error)) from error


# --- card dimensions, for the feed -------------------------------------------
#
# The feed names each film's card.jpg as its media:thumbnail, and a reader lays
# out a card without a layout shift only if it knows the picture's size. The
# card is derived on the authoring host (covers.save_cover: thumbnail() into an
# 800px box, so its size depends on the upload) and the deploy build has no
# Pillow on purpose (requirements-build.txt). So the size is read from the JPEG
# header — the frame header, a few bytes in — not by decoding the image.
#
# Own, not adopt: these are JPEGs Kino itself wrote, the only question asked is
# the frame size, and the answer for anything unexpected is "unknown", which
# omits width/height rather than failing the build.

_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def jpeg_size(path: Path):
    """(width, height) from a baseline or progressive JPEG's frame header, or
    None if the file is missing, not a JPEG, or has no readable frame header."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:          # fill byte
            i += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:   # no length field
            i += 2
            continue
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in _SOF:
            if i + 9 > len(data):
                return None
            height = int.from_bytes(data[i + 5:i + 7], "big")
            width = int.from_bytes(data[i + 7:i + 9], "big")
            return (width, height) if width and height else None
        if marker == 0xDA or length < 2:    # image data began first: give up
            return None
        i += 2 + length
    return None


def _feed_cards(syndicated, permalinked, artifacts_root) -> dict:
    """{film id: (width, height) or None} for each syndicated film whose card
    the build will publish — a permalinked film's covers/<id>/card.jpg, copied
    by _copy_covers(), which fails the build if it is missing. A film not in
    this dict gets no media:thumbnail, so the feed never names an unserved file."""
    served = {f["id"] for f in permalinked}
    cards = {}
    for film in syndicated:
        source = Path(artifacts_root) / film["id"] / CARD_NAME
        if film["id"] in served and source.exists():
            cards[film["id"]] = jpeg_size(source)
    return cards


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
    entries_root = Path(entries_root or publication.entries_dir())
    artifacts_root = Path(artifacts_root or publication.artifacts_dir())

    env = _env()
    site = site_config()

    listed = entry_store.load_entries(entries_root)
    permalinked = entry_store.load_permalinked(entries_root)

    # Bound once, for the duration of this build. A build must not change which
    # publication it is writing into halfway through, so the question is asked
    # here rather than at each of the fourteen places that used to answer it
    # with a module-level constant.
    staging = publication.staging_dir()
    site_out = publication.site_dir()

    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        _render(env, "index.html", staging / "index.html",
                films=listed, site=site, depth=0)

        _render(env, "archive.html", staging / "archive" / "index.html",
                years=entry_store.group_by_year(listed), site=site, depth=1)

        syndicated = [f for f in listed if visibility.is_syndicated(f)]
        _render(env, "feed.xml", staging / "feed.xml",
                films=syndicated, site=site, depth=0,
                cards=_feed_cards(syndicated, permalinked, artifacts_root))

        # `page_canonical` is the film's own address (PROTOCOL.md §3 — "the
        # object's single source of truth"), built the same way the feed builds
        # its <entry><link> so the two cannot disagree. `page_title` is the same
        # display title the <title> tag uses, so og:title names the film rather
        # than the publication.
        for film in permalinked:
            newer, older = entry_store.neighbours(listed, film["id"])
            _render(env, "film.html", staging / "f" / film["id"] / "index.html",
                    film=film, site=site, depth=2,
                    page_canonical=urls.url(urls.root(site), f"f/{film['id']}/"),
                    page_title=display_title(film),
                    withdrawn=visibility.effective_state(film) == visibility.ARCHIVED,
                    newer=newer, older=older)

        if publication.static_dir().exists():
            # compose.css styles the authoring interface, which the published
            # site has no way to reach. Shipping it would only describe
            # surfaces a reader cannot use.
            shutil.copytree(publication.static_dir(), staging / "static",
                            ignore=shutil.ignore_patterns("compose.css"))

        shutil.copy(publication.masthead(), staging / "masthead.json")

        # The publication describes itself at the two addresses §11.1 names.
        # Without it a client asking for /commons.json got the home page, as
        # HTML, at 200. A manifest that cannot produce the document fails the
        # build here rather than publishing something a client would reject.
        discovery.write(site, staging)

        # And a dead address answers as one. Without a 404.html, Cloudflare
        # Pages serves the home page at 200 for every unknown path.
        _render(env, "404.html", staging / "404.html", site=site)

        missing = _copy_covers(permalinked, staging, artifacts_root)
        if missing:
            raise BuildError("Missing cover images: " + "; ".join(missing[:5]))

        verify(staging, permalinked, listed)

        # Destructive step last, after a complete site exists.
        if site_out.exists():
            shutil.rmtree(site_out)
        staging.rename(site_out)

    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    print(f"Built {site.get('name', 'Kino')}: {len(listed)} film(s) listed, "
          f"{len(permalinked)} permalinked into {site_out}/")


def verify(site_dir: Path, permalinked, listed) -> None:
    # Every object must carry a stored feed identity. Refused at build rather
    # than computed from the current canonical URL, because that fallback is
    # right until the publication moves and then silently reissues the identity
    # of everything that lacked one — re-delivering the archive to every
    # subscriber (PROTOCOL.md §8.1).
    missing = [e["id"] for e in listed if not (e.get("guid") or "").strip()]
    if missing:
        raise BuildError(
            "objects with no stored feed identity (guid): "
            + ", ".join(missing[:5])
            + " — backfill from the object's current canonical URL before building"
        )

    """Assert a built site is present and complete; raise on any gap.

    A publication with no films is a valid state, not a failure — it is what a
    new publication looks like. So the checks are about films that exist, not
    about there being any.
    """
    index = site_dir / "index.html"
    if not index.exists():
        raise BuildError("index.html was not generated")

    # Part of the published artifact (§11.1), so a build without it is
    # incomplete — the same check Crows makes.
    for relative in (discovery.WELL_KNOWN_RELATIVE, discovery.MIRROR_RELATIVE):
        path = site_dir / relative
        if not path.exists():
            raise BuildError(f"discovery document {relative} was not generated")
        try:
            advertised = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise BuildError(f"discovery document {relative} is not valid JSON: {error}")
        absent = [f for f in discovery.REQUIRED_FIELDS if not advertised.get(f)]
        if absent:
            raise BuildError(f"discovery document {relative} is missing: {', '.join(absent)}")

    if not (site_dir / "404.html").exists():
        raise BuildError("404.html was not generated")

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
