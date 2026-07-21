"""The cover image pipeline — one image in, the sizes a page needs out.

A cover image reaches Kino from one of two places: artwork the publisher
uploaded, or a frame captured from the film in the browser while publishing.
Both arrive here as an ordinary image upload, and this module cannot tell them
apart. That is deliberate — provenance stops mattering the moment the image is
chosen, so nothing downstream records it.

Unlike Lens there is no original to preserve. A cover is a derived, replaceable
representation of a film, not the work itself; the work lives on the video host
and, upstream, in an archive Kino knows nothing about.
"""
from __future__ import annotations

from pathlib import Path

# Pillow is imported lazily inside save_cover(), not at module load. The build
# path imports this module only for the size/name constants below, and the
# Cloudflare Pages deploy build must not have to install Pillow — a compiled
# extension — just to read a few strings. Authoring, which actually derives
# images, carries the full dependency set.

# Wide enough for a full-bleed page on a large display without being a heavy
# download; the card is what the feed loads, and is much smaller.
COVER_MAX = 1600
CARD_MAX = 800

COVER_QUALITY = 88
CARD_QUALITY = 82

COVER_NAME = "cover.jpg"
CARD_NAME = "card.jpg"

DERIVED = (COVER_NAME, CARD_NAME)


class CoverError(RuntimeError):
    """The cover image could not be read."""


def save_cover(upload, directory: Path) -> dict:
    """Write the derived cover images. Returns what the record needs.

    Anything Pillow can open is accepted, including the JPEG a browser canvas
    produces from a captured video frame. The image is flattened to RGB and
    saved as JPEG so the published site never carries a format a browser might
    refuse.
    """
    from PIL import Image, ImageOps

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    try:
        image = Image.open(upload)
        image.load()
    except Exception as error:  # noqa: BLE001 - Pillow raises many types here
        raise CoverError(f"Could not read the cover image: {error}") from error

    # Honour EXIF rotation before anything else, or a phone photograph used as
    # artwork publishes sideways.
    image = ImageOps.exif_transpose(image)

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    width, height = image.size

    cover = image.copy()
    cover.thumbnail((COVER_MAX, COVER_MAX), Image.LANCZOS)
    cover.save(directory / COVER_NAME, "JPEG", quality=COVER_QUALITY,
               optimize=True, progressive=True)

    card = image.copy()
    card.thumbnail((CARD_MAX, CARD_MAX), Image.LANCZOS)
    card.save(directory / CARD_NAME, "JPEG", quality=CARD_QUALITY,
              optimize=True, progressive=True)

    return {
        "cover": COVER_NAME,
        "card": CARD_NAME,
        "width": width,
        "height": height,
        "aspect_ratio": round(width / height, 4) if height else None,
    }
