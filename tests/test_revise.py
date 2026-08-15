"""Revising a film.

Kino's first tests. They exist because of a defect that reached the authoring
service: opening a film's edit form and saving it unchanged reported

    Revision failed; nothing was changed (git commit -m Revise film e2db18f0
    failed: ... nothing to commit, working tree clean)

The record was rewritten byte-identically, git found nothing staged, `git
commit` exited non-zero, and the transaction rolled back and announced a
failure for what had actually succeeded at doing nothing.

`git=False` throughout: these test the editorial transaction, not git.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import entries as entry_store
import publisher

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
}


class ReviseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kino-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.entries = self.tmp / "entries"
        self.artifacts = self.tmp / "artifacts"
        (self.entries / "2026").mkdir(parents=True)
        self.artifacts.mkdir()
        self.path = self.entries / "2026" / "e2db18f0.json"
        self.path.write_text(json.dumps(FILM, indent=2) + "\n", encoding="utf-8")

        # The build is exercised elsewhere; here it would only write a site into
        # the repository as a side effect of a unit test.
        patch = mock.patch.object(publisher.builder, "build")
        self.build = patch.start()
        self.addCleanup(patch.stop)

    def revise(self, changes):
        return publisher.revise("e2db18f0", changes, entries_root=self.entries,
                                artifacts_root=self.artifacts, git=False)

    def stored(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def unchanged_form(self, **overrides):
        """What the edit form posts back when nothing was touched."""
        form = {
            "title": FILM["title"],
            "description": FILM["description"],
            "video_host": FILM["video"]["host"],
            "video_id": FILM["video"]["id"],
            "visibility": FILM["visibility"],
            "cover": None,
        }
        form.update(overrides)
        return form

    # --- the defect ----------------------------------------------------------

    def test_saving_an_unchanged_film_is_not_a_failure(self):
        revised, changed = self.revise(self.unchanged_form())

        self.assertFalse(changed)
        self.assertEqual(revised["title"], FILM["title"])

    def test_an_unchanged_save_does_not_rebuild_the_site(self):
        """Nothing changed, so there is nothing to rebuild, commit or push."""
        self.revise(self.unchanged_form())
        self.build.assert_not_called()

    def test_an_unchanged_save_leaves_the_record_byte_identical(self):
        before = self.path.read_bytes()
        self.revise(self.unchanged_form())
        self.assertEqual(self.path.read_bytes(), before)

    # --- and the ordinary case still works -----------------------------------

    def test_a_real_edit_is_written_and_reported_as_a_change(self):
        revised, changed = self.revise(self.unchanged_form(title="Love Bug"))

        self.assertTrue(changed)
        self.assertEqual(revised["title"], "Love Bug")
        self.assertEqual(self.stored()["title"], "Love Bug")
        self.build.assert_called_once()

    def test_editing_the_description_counts_as_a_change(self):
        _, changed = self.revise(self.unchanged_form(description="On film."))
        self.assertTrue(changed)
        self.assertEqual(self.stored()["description"], "On film.")

    def test_correcting_the_video_reference_counts_as_a_change(self):
        _, changed = self.revise(self.unchanged_form(video_id="1212341451"))
        self.assertTrue(changed)
        self.assertEqual(self.stored()["video"], {"host": "vimeo", "id": "1212341451"})

    def test_whitespace_only_edits_are_not_changes(self):
        """The record stores stripped values, so re-saving with stray spaces is
        the same film — and must not be reported as a failure either."""
        _, changed = self.revise(self.unchanged_form(title="  Love Bug @ The New Beverly  "))
        self.assertFalse(changed)

    def test_an_unknown_film_is_refused(self):
        with self.assertRaises(ValueError):
            publisher.revise("nosuchid", self.unchanged_form(),
                             entries_root=self.entries,
                             artifacts_root=self.artifacts, git=False)


class WithdrawTest(unittest.TestCase):
    """withdraw() rides on revise(), so it had to keep working when revise
    started reporting whether anything changed."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kino-withdraw-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.entries = self.tmp / "entries"
        (self.entries / "2026").mkdir(parents=True)
        self.artifacts = self.tmp / "artifacts"
        self.artifacts.mkdir()
        self.path = self.entries / "2026" / "e2db18f0.json"
        self.path.write_text(json.dumps(FILM, indent=2) + "\n", encoding="utf-8")

        patch = mock.patch.object(publisher.builder, "build")
        patch.start()
        self.addCleanup(patch.stop)

    def test_withdrawing_returns_the_record_not_a_pair(self):
        record = publisher.withdraw("e2db18f0", entries_root=self.entries,
                                    artifacts_root=self.artifacts, git=False)

        self.assertIsInstance(record, dict)
        self.assertEqual(record["id"], "e2db18f0")
        self.assertEqual(json.loads(self.path.read_text())["visibility"],
                         record["visibility"])


if __name__ == "__main__":
    unittest.main()
