"""Building a publication for a test to open.

A test that publishes into, or builds, a publication must say **which** one. Two
fixtures in this suite used to answer that question by accident instead:

*   `test_feed_identity` rebuilt at a different canonical URL by editing the real
    `masthead.json` in the working directory and restoring it in a `finally`. A
    crash between the two left the live manifest holding a fictional address.
*   `test_urls` asserted against `site/` in the working directory — whatever
    happened to be built there. On the publishing host that was a nineteen-day-old
    build declaring a pre-migration canonical, and five tests failed for a reason
    that had nothing to do with the code under test.

Both are the same mistake: reaching for the ambient publication rather than
naming one. `temporary()` is the replacement.

Stage 1 scope: a publication carries its **data** (manifest, records, artifacts)
and the renderer's **resources** (templates, static), because `publication.py`
now resolves all five beneath the publication root. It does not yet carry the
renderer's *modules* — the service still imports and runs the renderer in-process.
When Stage 2 makes the service invoke the renderer as a subprocess, the module
closure joins this file, the way it has in Lens.
"""
import json
import shutil
from contextlib import contextmanager
from pathlib import Path

import publication

APPLICATION_DIR = Path(__file__).resolve().parent.parent

# What the renderer reads that is not code.
RESOURCES = ("templates", "static")


def make(destination, *, name=None, canonical=None, feed_guid=None,
         records=False) -> Path:
    """A publication at `destination`, able to be opened, published to and built.

    `name` and `canonical` override the manifest's, so a test can prove *which*
    publication an operation reached rather than merely that it reached one.
    `records` copies this publication's existing films, for tests that need real
    ones rather than the ones they create. `feed_guid` is separate from
    `canonical` on purpose — see below.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    for resource in RESOURCES:
        shutil.copytree(APPLICATION_DIR / resource, destination / resource,
                        dirs_exist_ok=True)

    for directory in ("entries", "artifacts"):
        source = APPLICATION_DIR / directory
        target = destination / directory
        if records and source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.mkdir(exist_ok=True)

    manifest = json.loads(
        (APPLICATION_DIR / "masthead.json").read_text(encoding="utf-8"))
    if name is not None:
        manifest["name"] = name
    if canonical is not None:
        manifest["canonical_url"] = canonical
        manifest["url"] = canonical
    # Deliberately NOT derived from `canonical`. A feed's identity is carried
    # across a rehost, never reissued with the address (PROTOCOL.md §8.1), and a
    # fixture that quietly moved the two together would make the tests which
    # exist to prove that pass for the wrong reason.
    if feed_guid is not None:
        manifest["feed_guid"] = feed_guid
    (destination / "masthead.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return destination


@contextmanager
def temporary(destination, **kwargs):
    """Create a publication and open it — both, because either alone is a trap.

    Creating one without opening it leaves publication selection to whatever the
    process happens to be configured with, and Stage 1's precedence puts
    `KINO_PUBLICATION` *above* the working directory. A fixture that established
    its temporary publication with `os.chdir` would therefore keep working
    perfectly on a developer's machine and silently write into the live
    publication on a host where the service sets that variable. That is not
    hypothetical: it happened to Lens on 2026-09-01.

    So the two halves are welded together here. A test that wants a temporary
    publication asks for one, and gets it selected as well as built.
    """
    root = make(destination, **kwargs)
    with publication.opened(root):
        yield root
