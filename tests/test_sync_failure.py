"""A publish transaction whose first step fails says so, in words.

`distributor.sync()` — fetch and fast-forward before touching anything — used to
run *outside* the transaction's `try`. When it failed (origin unreachable, a
diverged branch needing a person) the DistributionError was not one of the
errors the authoring interface reports, and the publisher saw a bare 500 with
no explanation. Nothing had changed, which was the one thing the page could
not tell them.

Every transaction that syncs — publish, revise (and so withdraw), erase — is
checked, at the publisher and through the app.
"""
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import distributor
import publisher
from app import app
from tests import publications

FILM = {
    "id": "e2db18f0",
    "created": "2026-07-22T00:00:00-07:00",
    "title": "Love Bug @ The New Beverly",
    "description": "Always on film.",
    "runtime": 44,
    "visibility": "public",
    "publish_at": None,
    "feed": {"pinned": False, "rank": None, "sequence": None},
    "video": {"host": "vimeo", "id": "1211882034"},
    "cover": "cover.jpg",
    "guid": "https://kino.example/f/e2db18f0/",
}

REFUSAL = distributor.DistributionError(
    "git merge --ff-only origin/main failed: fatal: Not possible to fast-forward")


class _Cover(io.BytesIO):
    filename = "cover.jpg"


class SyncFails(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kino-sync-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.entries = self.tmp / "entries"
        self.artifacts = self.tmp / "artifacts"
        (self.entries / "2026").mkdir(parents=True)
        self.artifacts.mkdir()
        self.path = self.entries / "2026" / "e2db18f0.json"
        self.before = json.dumps(FILM, indent=2) + "\n"
        self.path.write_text(self.before, encoding="utf-8")

        for name, kwargs in (("sync", {"side_effect": REFUSAL}),
                             ("current_head", {"return_value": "abc"}),
                             ("commit_paths", {}), ("push", {}), ("reset_hard", {})):
            patch = mock.patch.object(distributor, name, **kwargs)
            setattr(self, name, patch.start())
            self.addCleanup(patch.stop)
        patch = mock.patch.object(publisher.builder, "build")
        self.build = patch.start()
        self.addCleanup(patch.stop)

    def roots(self):
        return {"entries_root": self.entries, "artifacts_root": self.artifacts}

    def assert_untouched(self):
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.before)
        self.assertEqual(sorted(p.name for p in self.entries.rglob("*.json")),
                         ["e2db18f0.json"])
        self.assertEqual(list(self.artifacts.iterdir()), [])
        self.commit_paths.assert_not_called()
        self.push.assert_not_called()

    def test_publish_reports_it(self):
        with self.assertRaises(publisher.PublishError) as caught:
            publisher.publish(title="New", video_id="1", cover=_Cover(b"x"),
                              **self.roots())
        self.assertIn("nothing was changed", str(caught.exception))
        self.assertIn("Not possible to fast-forward", str(caught.exception))
        self.assert_untouched()

    def test_revise_reports_it(self):
        with self.assertRaises(publisher.PublishError):
            publisher.revise("e2db18f0", {"title": "Changed"}, **self.roots())
        self.assert_untouched()

    def test_withdraw_reports_it(self):
        with self.assertRaises(publisher.PublishError):
            publisher.withdraw("e2db18f0", **self.roots())
        self.assert_untouched()

    def test_erase_reports_it(self):
        with self.assertRaises(publisher.PublishError):
            publisher.erase("e2db18f0", **self.roots())
        self.assert_untouched()


class TheAppShowsIt(unittest.TestCase):
    """Through the authoring interface: an explained page, never a 500."""

    def setUp(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("KINO_")}
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.tmp = Path(tempfile.mkdtemp(prefix="kino-sync-app-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        opened = publications.temporary(self.tmp / "pub")
        root = opened.__enter__()
        self.addCleanup(opened.__exit__, None, None, None)
        (root / "entries" / "2026").mkdir(parents=True)
        (root / "entries" / "2026" / "e2db18f0.json").write_text(
            json.dumps(FILM, indent=2) + "\n", encoding="utf-8")

        patch = mock.patch.object(distributor, "sync", side_effect=REFUSAL)
        patch.start()
        self.addCleanup(patch.stop)
        self.client = app.test_client()
        self.headers = {"Origin": "http://localhost"}

    def test_composing(self):
        response = self.client.post("/", headers=self.headers, data={
            "title": "New", "video_host": "vimeo", "video_id": "1",
            "cover": (io.BytesIO(b"x"), "cover.jpg")})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Not possible to fast-forward", response.data)

    def test_withdrawing(self):
        response = self.client.post("/withdraw/e2db18f0", headers=self.headers)
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=", response.headers["Location"])

    def test_erasing(self):
        response = self.client.post("/erase/e2db18f0", headers=self.headers)
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
