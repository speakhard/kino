"""Feed identity survives a publication moving; the address does not.

The regression test for the one Phase B change that cannot be undone. An object
has three identifiers and they are constantly collapsed into one:

    id              addresses the object inside this publication
    canonical URL   where it can be fetched today — moves if rehosted
    guid            what every subscribed reader already holds — must never move

Recompute `guid` from the current canonical URL, move the publication, and every
reader is handed the whole archive as new work. PROTOCOL.md §8.1 states the rule
for Cast; it was never Cast-specific.

The publication is rebuilt at a *different* canonical URL and the ids compared.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import builder

ATOM = "{http://www.w3.org/2005/Atom}"
MOVED_TO = "https://joshbernhard.com/filmed"


def _build_at(canonical):
    tmp = Path(tempfile.mkdtemp(prefix="kino-identity-"))
    real_site, real_staging = builder.SITE_DIR, builder.STAGING_DIR
    manifest = Path("masthead.json")
    original = manifest.read_text(encoding="utf-8")
    builder.SITE_DIR, builder.STAGING_DIR = tmp / "site", tmp / "site.tmp"
    try:
        if canonical is not None:
            data = json.loads(original)
            data["canonical_url"] = canonical
            data["url"] = canonical
            manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        builder.build()
        return ET.parse(builder.SITE_DIR / "feed.xml").getroot()
    finally:
        manifest.write_text(original, encoding="utf-8")
        builder.SITE_DIR, builder.STAGING_DIR = real_site, real_staging
        shutil.rmtree(tmp, ignore_errors=True)


def _ids(feed):
    return [e.findtext(f"{ATOM}id") for e in feed.findall(f"{ATOM}entry")]


def _links(feed):
    out = []
    for entry in feed.findall(f"{ATOM}entry"):
        for link in entry.findall(f"{ATOM}link"):
            if (link.get("rel") or "alternate") == "alternate":
                out.append(link.get("href"))
                break
    return out


class MovingThePublication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.here = _build_at(None)
        cls.moved = _build_at(MOVED_TO)

    def test_the_link_moves_with_the_publication(self):
        """The control. Without it the test below proves nothing."""
        before, after = _links(self.here), _links(self.moved)
        self.assertTrue(before)
        self.assertNotEqual(before, after)
        for href in after:
            self.assertTrue(href.startswith(MOVED_TO), href)

    def test_the_identity_does_not(self):
        """The whole of Phase B, in one assertion."""
        self.assertEqual(_ids(self.here), _ids(self.moved))

    def test_no_identity_points_at_the_new_address(self):
        for identity in _ids(self.moved):
            self.assertFalse(identity.startswith(MOVED_TO), identity)

    def test_identity_and_address_differ_after_a_move(self):
        """Before a move these are the same string, which is why the mistake is
        invisible to a test that only ever builds once."""
        for identity, href in zip(_ids(self.moved), _links(self.moved)):
            self.assertNotEqual(identity, href)

    def test_every_entry_still_has_an_identity(self):
        ids = _ids(self.moved)
        self.assertTrue(ids)
        for identity in ids:
            self.assertTrue((identity or "").strip())


class TheBuildRefusesAnObjectWithoutOne(unittest.TestCase):
    def test_an_object_with_no_stored_identity_fails_the_build(self):
        """Refused rather than computed: the plausible fallback is right until
        the publication moves, and then it is catastrophic and silent."""
        with self.assertRaises(builder.BuildError) as caught:
            builder.verify(Path("."), [], [{"id": "deadbeef", "guid": ""}])
        self.assertIn("feed identity", str(caught.exception))

    def test_the_same_object_with_an_identity_passes_that_check(self):
        try:
            builder.verify(Path("."), [], [{"id": "deadbeef", "guid": "https://example.test/f/deadbeef/"}])
        except builder.BuildError as error:
            self.assertNotIn("feed identity", str(error))


if __name__ == "__main__":
    unittest.main()
