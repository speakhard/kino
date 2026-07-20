"""Kino — the private authoring interface.

Paste a video host and identifier, describe the film, choose a cover image,
publish. The public site is static and built from the records; this application
exists only to add to them.

Kino's responsibility starts after a film already exists on its host. It does
not upload, encode, or store video, and knows nothing about how the film was
made or how it got there.

Never served by Flask's development server. serve.py runs it under Waitress,
bound to loopback unless told otherwise — the Werkzeug debugger is a remote
code execution surface.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for)

import entries as entry_store
import hosts
import visibility
from builder import site_config
from covers import CARD_NAME, COVER_NAME
from models import MAX_DESCRIPTION, MAX_TITLE
from publisher import PublishError, erase, publish, revise, withdraw

app = Flask(__name__)

# A cover image, not a film. Generous but bounded — nothing large should ever
# reach this application, because the video never comes here at all.
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024


def _runtime_from(form):
    """Seconds, as measured by the browser from the local file.

    The compose page reads duration from the video element while the publisher
    is choosing a frame, so the runtime is determined rather than typed. Absent
    when the cover came from uploaded artwork and no video was ever opened —
    which is a fact about that film, not an error.
    """
    raw = (form.get("runtime") or "").strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        return None
    return int(round(seconds)) if seconds > 0 else None


def _created_from(form):
    """The publication date, if the publisher set one."""
    raw = (form.get("created") or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).astimezone()
    except ValueError:
        return None


@app.route("/", methods=["GET", "POST"])
def compose():
    error = None

    if request.method == "POST":
        try:
            film = publish(
                title=request.form.get("title", ""),
                description=request.form.get("description", ""),
                video_host=request.form.get("video_host", hosts.DEFAULT_HOST),
                video_id=request.form.get("video_id", ""),
                cover=request.files.get("cover"),
                runtime=_runtime_from(request.form),
                created=_created_from(request.form),
            )
            return redirect(url_for("published", entry_id=film["id"]))
        except (ValueError, PublishError) as failure:
            error = str(failure)

    return render_template("compose.html", error=error, hosts=hosts.HOSTS,
                           default_host=hosts.DEFAULT_HOST,
                           max_title=MAX_TITLE, max_description=MAX_DESCRIPTION,
                           site=site_config())


@app.route("/published/<entry_id>")
def published(entry_id):
    film = entry_store.find_entry(entry_id)
    if not film:
        return "Not found", 404
    return render_template("published.html", film=film, site=site_config(),
                           watch_url=hosts.watch_url(film["video"]))


@app.route("/cover/<entry_id>/<name>")
def cover(entry_id, name):
    """Serve a cover image to the authoring interface.

    Restricted to the derived filenames on purpose: a name from the URL never
    reaches the filesystem unchecked.
    """
    if name not in (COVER_NAME, CARD_NAME):
        return "Not found", 404
    directory = (Path(entry_store.ARTIFACTS_DIR) / entry_id).resolve()
    if not directory.is_dir():
        return "Not found", 404
    return send_from_directory(directory, name)


@app.route("/films")
def catalogue():
    """Every film in every state — the way back to one.

    load_all rather than load_entries: a withdrawn film must stay reachable
    here, or withdrawing would be a one-way door.
    """
    return render_template("films.html", films=entry_store.load_all(),
                           states=visibility.STATES,
                           state_of=visibility.effective_state,
                           error=request.args.get("error"),
                           notice=request.args.get("notice"),
                           site=site_config())


@app.route("/edit/<entry_id>", methods=["GET", "POST"])
def edit(entry_id):
    film = entry_store.find_entry(entry_id)
    if not film:
        return "Not found", 404

    error = None

    if request.method == "POST":
        form = request.form
        changes = {
            "title": form.get("title", ""),
            "description": form.get("description", ""),
            "video_host": form.get("video_host", film["video"]["host"]),
            "video_id": form.get("video_id", film["video"]["id"]),
            "visibility": form.get("visibility", film.get("visibility")),
            "cover": request.files.get("cover"),
        }
        runtime = _runtime_from(form)
        if runtime is not None:
            changes["runtime"] = runtime

        try:
            revise(entry_id, changes)
            return redirect(url_for("catalogue", notice=f"Revised {entry_id}."))
        except (ValueError, PublishError) as failure:
            error = str(failure)
            film = entry_store.find_entry(entry_id)

    return render_template("edit.html", film=film, error=error,
                           hosts=hosts.HOSTS, states=visibility.STATES,
                           current=visibility.effective_state(film),
                           max_title=MAX_TITLE, max_description=MAX_DESCRIPTION,
                           site=site_config())


@app.route("/withdraw/<entry_id>", methods=["POST"])
def withdraw_film(entry_id):
    try:
        withdraw(entry_id)
    except (ValueError, PublishError) as failure:
        return redirect(url_for("catalogue", error=str(failure)))
    return redirect(url_for("catalogue",
                            notice=f"Withdrew {entry_id}. Its permalink still answers."))


@app.route("/erase/<entry_id>", methods=["POST"])
def erase_film(entry_id):
    try:
        erase(entry_id)
    except (ValueError, PublishError) as failure:
        return redirect(url_for("catalogue", error=str(failure)))
    return redirect(url_for("catalogue",
                            notice=f"Erased {entry_id}. The video is untouched on its host."))
