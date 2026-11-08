"""The feed names each film's card as a Media RSS thumbnail (2026-11-07).

A reader (thecommons.pub) shows a picture beside a film only if the feed names
one; until now each entry carried a title and a link. The card is the one
covers.save_cover() already derives and the build already serves at
covers/<id>/card.jpg. Its size comes from the JPEG header (builder.jpeg_size),
because the deploy build has no Pillow.
"""
import io
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

import builder
from tests import publications

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"


def jpeg(path: Path, size, progressive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, "gray").save(path, "JPEG", progressive=progressive)


class JpegSize(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kino-jpeg-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_baseline_and_progressive(self):
        jpeg(self.tmp / "b.jpg", (800, 463))
        jpeg(self.tmp / "p.jpg", (720, 480), progressive=True)
        self.assertEqual(builder.jpeg_size(self.tmp / "b.jpg"), (800, 463))
        self.assertEqual(builder.jpeg_size(self.tmp / "p.jpg"), (720, 480))

    def test_with_exif_before_the_frame_header(self):
        buf = io.BytesIO()
        exif = Image.Exif()
        exif[0x010E] = "a description long enough to push the frame header along" * 20
        Image.new("RGB", (640, 360)).save(buf, "JPEG", exif=exif)
        (self.tmp / "e.jpg").write_bytes(buf.getvalue())
        self.assertEqual(builder.jpeg_size(self.tmp / "e.jpg"), (640, 360))

    def test_unknown_is_none_not_an_error(self):
        (self.tmp / "fake.jpg").write_bytes(b"not rendered, only copied")
        (self.tmp / "short.jpg").write_bytes(b"\xff\xd8\xff\xc0\x00")
        Image.new("RGB", (10, 10)).save(self.tmp / "png.jpg", "PNG")
        for name in ("fake.jpg", "short.jpg", "png.jpg", "missing.jpg"):
            with self.subTest(name=name):
                self.assertIsNone(builder.jpeg_size(self.tmp / name))


class FeedThumbnails(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kino-feed-media-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def build(self):
        with publications.temporary(self.tmp / "pub", records=True) as root:
            builder.build()
            feed = ET.parse(root / "site" / "feed.xml").getroot()
            return root, feed

    def test_every_entry_names_its_served_card_with_its_size(self):
        root, feed = self.build()
        entries = feed.findall(ATOM + "entry")
        self.assertTrue(entries, "the publication's own records should be listed")
        base = feed.find(ATOM + "link[@rel='self']").get("href").removesuffix("feed.xml")
        for entry in entries:
            link = entry.find(ATOM + "link").get("href")
            film_id = link.rstrip("/").rsplit("/", 1)[-1]
            thumb = entry.find(MEDIA + "thumbnail")
            with self.subTest(film=film_id):
                self.assertEqual(thumb.get("url"), f"{base}covers/{film_id}/card.jpg")
                served = root / "site" / "covers" / film_id / "card.jpg"
                self.assertTrue(served.is_file())
                with Image.open(served) as image:
                    self.assertEqual((int(thumb.get("width")), int(thumb.get("height"))),
                                     image.size)

    def test_ids_and_links_are_what_they_were(self):
        # The identity and the address are read from the records and the
        # canonical root exactly as before; the thumbnail adds, never replaces.
        root, feed = self.build()
        import entries as entry_store
        import visibility
        listed = [f for f in entry_store.load_entries(root / "entries")
                  if visibility.is_syndicated(f)]
        self.assertEqual([e.findtext(ATOM + "id") for e in feed.findall(ATOM + "entry")],
                         [f["guid"] for f in listed])
        self.assertEqual([e.find(ATOM + "link").get("href") for e in feed.findall(ATOM + "entry")],
                         [f"https://joshbernhard.com/filmed/f/{f['id']}/" for f in listed])

    def test_every_entry_names_its_player_and_no_watch_page(self):
        # media:player is the same embed URL the film's page loads in its
        # iframe (hosts.embed_url). The host-invisibility rule forbids a link
        # to the film's WATCH page on its host; the feed carries none.
        import hosts
        import entries as entry_store
        import visibility
        root, feed = self.build()
        listed = [f for f in entry_store.load_entries(root / "entries")
                  if visibility.is_syndicated(f)]
        players = [e.find(MEDIA + "player").get("url") for e in feed.findall(ATOM + "entry")]
        self.assertEqual(players, [hosts.embed_url(f["video"]) for f in listed])
        text = (root / "site" / "feed.xml").read_text(encoding="utf-8")
        for f in listed:
            self.assertNotIn(hosts.watch_url(f["video"]), text)

    def test_a_card_whose_size_is_unknown_still_gets_a_thumbnail(self):
        with publications.temporary(self.tmp / "pub2", records=True) as root:
            for card in (root / "artifacts").glob("*/card.jpg"):
                card.write_bytes(b"not a jpeg")
            builder.build()
            feed = ET.parse(root / "site" / "feed.xml").getroot()
        thumbs = [e.find(MEDIA + "thumbnail") for e in feed.findall(ATOM + "entry")]
        self.assertTrue(thumbs)
        for thumb in thumbs:
            self.assertEqual(set(thumb.attrib), {"url"})


if __name__ == "__main__":
    unittest.main()
