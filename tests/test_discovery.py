"""The built site describes itself (§11.1) and answers a dead address honestly.

Before this, Kino published neither. `/filmed/commons.json` returned the home
page, as HTML, at 200 — Cloudflare Pages' answer to any path it has no file for
— so Commons Publisher reported Filmed as `config_error` and any client that
trusted the status code would have parsed a web page as a manifest.

Also frozen here: adding those files changes no identity. The feed's id and
every entry's id are compared with the values published before the change.
"""
from __future__ import annotations

import contextlib
import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import builder
import discovery
import publication
from tests import publications

ATOM = "{http://www.w3.org/2005/Atom}"

# Exactly what https://joshbernhard.com/filmed/feed.xml carried at 295f5c4.
# Not derived from anything: an identity is a value to preserve, not recompute.
FEED_ID = "https://kino.joshbernhard.com/"
ENTRY_IDS = [
    "https://kino.joshbernhard.com/f/f85244c8/",
    "https://kino.joshbernhard.com/f/acc00770/",
    "https://joshbernhard.com/filmed/f/246d2edd/",
    "https://kino.joshbernhard.com/f/dd6a8dd4/",
    "https://kino.joshbernhard.com/f/067bec90/",
]

SITE = None
_OPEN = None


def setUpModule():
    global SITE, _OPEN
    _OPEN = contextlib.ExitStack()
    tmp = Path(_OPEN.enter_context(tempfile.TemporaryDirectory(prefix="kino-disc-")))
    _OPEN.enter_context(publications.temporary(tmp, records=True))
    builder.build()
    SITE = publication.site_dir()


def tearDownModule():
    _OPEN.close()


class TheDiscoveryDocument(unittest.TestCase):
    def read(self, relative):
        return (SITE / relative).read_bytes()

    def test_both_addresses_exist_and_are_identical(self):
        self.assertEqual(self.read(".well-known/commons.json"), self.read("commons.json"))

    def test_it_is_json_with_every_required_field(self):
        doc = json.loads(self.read("commons.json"))
        for field in discovery.REQUIRED_FIELDS:
            with self.subTest(field=field):
                self.assertTrue(doc.get(field))

    def test_it_is_a_projection_of_the_manifest(self):
        doc = json.loads(self.read("commons.json"))
        manifest = publication.manifest()
        self.assertEqual(doc["commons_spec"], manifest["commons_spec"])
        self.assertEqual(doc["profile"], "kino")
        self.assertEqual(doc["canonical_url"], manifest["canonical_url"])
        self.assertEqual(doc["capabilities"], ["syndication"])

    def test_it_advertises_no_authoring_surface(self):
        # Kino serves no §11.3 commands; absence is the complete answer.
        self.assertNotIn("authoring", json.loads(self.read("commons.json")))

    def test_the_manifest_speaks_the_version_its_siblings_do(self):
        # 0.3 is the version that defines this document. Declaring 0.2 while
        # publishing a 0.3 feature is two handshakes for one publication.
        self.assertEqual(publication.manifest()["commons_spec"], "0.3")

    def test_the_well_known_address_is_redirected_where_hosts_honour_it(self):
        self.assertIn("/.well-known/commons.json /commons.json 302",
                      self.read("_redirects").decode())

    def test_a_manifest_missing_a_required_field_fails_the_build(self):
        with self.assertRaises(discovery.DiscoveryError):
            discovery.document({"profile": "kino", "name": "x", "canonical_url": "y"})


class TheNotFoundPage(unittest.TestCase):
    def setUp(self):
        self.html = (SITE / "404.html").read_text(encoding="utf-8")

    def test_it_exists(self):
        self.assertIn("Not found", self.html)

    def test_every_reference_is_absolute_beneath_the_root(self):
        # Served at any depth, so nothing in it may be relative.
        root = publication.manifest()["canonical_url"]
        refs = re.findall(r'(?:href|src)="([^"]*)"', self.html)
        self.assertTrue(refs)
        for ref in refs:
            with self.subTest(ref=ref):
                self.assertTrue(ref.startswith(root), ref)

    def test_it_is_not_indexed(self):
        self.assertIn('name="robots" content="noindex"', self.html)


class NoIdentityMoved(unittest.TestCase):
    def setUp(self):
        self.feed = ET.parse(SITE / "feed.xml").getroot()

    def test_the_feed_id_is_unchanged(self):
        self.assertEqual(self.feed.findtext(f"{ATOM}id"), FEED_ID)

    def test_every_entry_id_is_unchanged(self):
        self.assertEqual([e.findtext(f"{ATOM}id") for e in self.feed.findall(f"{ATOM}entry")],
                         ENTRY_IDS)

    def test_the_canonical_root_is_unchanged(self):
        self.assertEqual(publication.manifest()["canonical_url"],
                         "https://joshbernhard.com/filmed/")


if __name__ == "__main__":
    unittest.main()
