"""Git operations for the publish transaction.

Adapted from Crows, which learned these lessons the expensive way:

*   `sync()` before publishing. The publishing host is not the only writer;
    development happens elsewhere and pushes to the same branch. A checkout that
    has fallen behind commits onto a stale base and has its push rejected at the
    very end, after all the work, with an error about refs that explains nothing.

*   Never force. A genuinely diverged remote rejects the push and the
    transaction rolls back, rather than overwriting someone else's work.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
PUBLISH_BRANCH = "main"


class DistributionError(RuntimeError):
    """A git operation in the publish transaction failed."""


def _git(*args) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, check=True,
                                capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        raise DistributionError(f"git {' '.join(args)} failed: {detail}") from error
    return result.stdout.strip()


def current_head() -> str:
    """The commit publishing starts from, so a failure can restore it."""
    return _git("rev-parse", "HEAD")


def sync() -> None:
    """Fast-forward onto the publication branch before publishing.

    --ff-only deliberately: a real divergence needs a person, and silently
    merging inside a publish would make the audit trail lie about what happened.
    """
    _git("fetch", "origin", PUBLISH_BRANCH)
    _git("merge", "--ff-only", f"origin/{PUBLISH_BRANCH}")


def commit_paths(paths, message: str) -> None:
    _git("add", *[str(p) for p in paths])
    _git("commit", "-m", message)


def push() -> None:
    _git("push", "origin", f"HEAD:{PUBLISH_BRANCH}")


def reset_hard(ref: str) -> None:
    _git("reset", "--hard", ref)
