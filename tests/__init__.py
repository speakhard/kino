"""The Kino test suite.

**The suite does not inherit an ambient publication.** `KINO_PUBLICATION` is
removed from the environment here, before any test module is imported, because a
test process that inherits one is a test process whose writes can be redirected
into somebody's real publication — which is exactly what happened to Lens on
2026-09-01, when the deployed suite was run on the publishing host and twelve
fixture photographs landed in Framed's working tree.

Kino gains that same hazard the moment `KINO_PUBLICATION` exists, so the guard
arrives with it rather than after the equivalent incident.

This is deliberately not a heuristic. Nothing here inspects a path and guesses
whether it looks like production; that would be both unreliable and insulting to
the next person with an unusual layout. The rule is simpler and complete: tests
select their own publication explicitly, via `publications.temporary()`, and
ambient configuration has no vote.

A test that wants to exercise `KINO_PUBLICATION` sets it itself, inside the test,
where it is visible.
"""
import os

os.environ.pop("KINO_PUBLICATION", None)
