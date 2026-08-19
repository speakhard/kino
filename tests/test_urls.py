"""The public-address convention: one canonical root, and nothing outside it.

Two invariants, both broken at once when a publication first moved to a path:

    the canonical publication URL is the final, non-redirecting root URL
    a relative reference resolved from that document stays inside the publication

They are the same invariant seen from two ends. A root written without its
trailing slash — `…/filmed` — makes the browser resolve the page's own
`feed.xml` against a base with no slash, landing on `…/feed.xml`: off the
publication, onto whatever else the origin serves. The page returns 200 and
every link on it is wrong, which is the failure shape that survives review.

At a domain root the trailing slash is implicit and none of this shows, which is
why it went unnoticed until the first subpath move.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

import builder
import urls

MANIFEST = json.loads(Path("masthead.json").read_text(encoding="utf-8"))
ROOT = urls.root(MANIFEST)


class TheJoiningMechanism(unittest.TestCase):
    """One way to build a URL beneath the root, and it cannot double a slash."""

    def test_a_root_always_ends_in_exactly_one_slash(self):
        for value in ("https://x.test/p", "https://x.test/p/", "https://x.test"):
            got = urls.root({"canonical_url": value})
            self.assertTrue(got.endswith("/"), got)
            self.assertFalse(got.endswith("//"), got)

    def test_joining_never_emits_a_doubled_slash_in_the_path(self):
        for base in ("https://x.test/p", "https://x.test/p/", "https://x.test/"):
            for part in ("feed.xml", "/feed.xml", "f/a/", "/f/a/"):
                got = urls.url(base, part)
                self.assertNotIn("//", urlparse(got).path, f"{base!r} + {part!r} -> {got}")

    def test_a_trailing_slash_on_the_last_part_survives(self):
        """`f/a/` and `f/a` are different addresses and only the first is a
        directory-like resource whose own relative references behave."""
        self.assertTrue(urls.url("https://x.test/p/", "f/a/").endswith("/f/a/"))

    def test_a_part_never_replaces_the_last_path_segment(self):
        """String arithmetic gets this right; naive urljoin against a base with
        no trailing slash does not, and that is the whole bug."""
        self.assertEqual(urls.url("https://x.test/filmed", "feed.xml"),
                         "https://x.test/filmed/feed.xml")


class TheCanonicalRoot(unittest.TestCase):
    def test_the_manifest_root_ends_in_a_slash(self):
        self.assertTrue(ROOT.endswith("/"), ROOT)

    def test_the_page_declares_that_exact_root_as_canonical(self):
        """The canonical must equal the address that serves it without
        redirecting — not a bare form that 301s to the real one."""
        html = (builder.SITE_DIR / "index.html").read_text(encoding="utf-8")
        declared = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
        self.assertEqual(declared, ROOT)

    def test_og_url_agrees_with_the_canonical(self):
        html = (builder.SITE_DIR / "index.html").read_text(encoding="utf-8")
        og = re.search(r'<meta property="og:url" content="([^"]+)"', html).group(1)
        self.assertEqual(og, ROOT)


class NothingEscapesThePublication(unittest.TestCase):
    """Every reference the root page emits, resolved the way a browser would."""

    def setUp(self):
        self.html = (builder.SITE_DIR / "index.html").read_text(encoding="utf-8")

    def _references(self):
        for attr in ("href", "src"):
            for value in re.findall(rf'{attr}="([^"]+)"', self.html):
                if value.startswith(("mailto:", "data:", "#", "javascript:")):
                    continue
                yield value

    def test_every_relative_reference_resolves_beneath_the_root(self):
        for ref in self._references():
            if ref.startswith(("http://", "https://")):
                continue
            resolved = urls.url(ROOT, ref) if not ref.startswith("/") else None
            if resolved is None:
                self.fail(f"root-relative reference {ref!r} escapes a subpath "
                          f"publication; it resolves to the origin, not to {ROOT}")
            self.assertTrue(resolved.startswith(ROOT),
                            f"{ref!r} -> {resolved}, outside {ROOT}")

    def test_every_absolute_reference_to_our_own_origin_is_beneath_the_root(self):
        origin = "{0.scheme}://{0.netloc}".format(urlparse(ROOT))
        for ref in self._references():
            if ref.startswith(origin) and not ref.startswith(ROOT):
                self.fail(f"{ref!r} is on this origin but outside {ROOT}")

    def test_the_feed_is_discoverable_from_the_root_and_stays_beneath_it(self):
        link = re.search(
            r'<link rel="alternate"[^>]*type="application/(?:atom|rss)\+xml"[^>]*href="([^"]+)"',
            self.html)
        self.assertIsNotNone(link, "the root page advertises no feed")
        resolved = urls.url(ROOT, link.group(1))
        self.assertTrue(resolved.startswith(ROOT), resolved)


class TheFeedStaysInside(unittest.TestCase):
    def setUp(self):
        self.xml = (builder.SITE_DIR / "feed.xml").read_text(encoding="utf-8")

    def test_no_url_in_the_feed_has_a_doubled_slash(self):
        for found in re.findall(r'https?://[^"<\s]+', self.xml):
            self.assertNotIn("//", urlparse(found).path, found)

    def test_rel_self_is_the_feed_beneath_the_root(self):
        self_link = re.search(r'<link href="([^"]+)" rel="self"/>', self.xml).group(1)
        self.assertTrue(self_link.startswith(ROOT), self_link)

    def test_every_entry_link_is_beneath_the_root(self):
        import xml.etree.ElementTree as ET
        A = "{http://www.w3.org/2005/Atom}"
        root = ET.fromstring(self.xml.encode("utf-8"))
        links = [next(l.get("href") for l in e.findall(f"{A}link")
                      if (l.get("rel") or "alternate") == "alternate")
                 for e in root.findall(f"{A}entry")]
        self.assertTrue(links)
        for link in links:
            self.assertTrue(link.startswith(ROOT), link)

    def test_the_feeds_identity_is_exempt_because_it_is_not_an_address(self):
        """The one URL in the feed that may sit outside the root: atom:id is a
        permanent identifier, not a place. It is frozen at whatever the feed
        was first published under."""
        import xml.etree.ElementTree as ET
        A = "{http://www.w3.org/2005/Atom}"
        root = ET.fromstring(self.xml.encode("utf-8"))
        self.assertEqual(root.findtext(f"{A}id"), MANIFEST["feed_guid"])


if __name__ == "__main__":
    unittest.main()
