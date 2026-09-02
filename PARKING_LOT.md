---
schema: devtracker/parking-lot@1
project: kino
items:
  - id: pl-2026-07-25-6805
    text: Printable guide view
    added_at: '2026-07-25T23:59:05Z'
    source: human
    status: deferred
    reason: Wants its own milestone; not part of M3
  - id: pl-2026-07-25-7664
    text: Multi-machine sync
    added_at: '2026-07-25T23:59:05Z'
    source: model
    status: promoted
    promoted_to: M6 — ecosystem
    transitioned_at: '2026-07-25T23:59:05Z'
  - id: pl-2026-09-02-9531
    text: Kino has no commons_author.py and no discovery.py - it does not implement PROTOCOL.md §11. Noted, not addressed.
    added_at: '2026-09-02T15:40:34Z'
    source: model
    status: deferred
  - id: pl-2026-09-02-8725
    text: tests/publications.py copies templates and static but not the renderer's module closure; that list joins the fixture at Stage 2, when the service stops importing the renderer.
    added_at: '2026-09-02T15:40:34Z'
    source: model
    status: deferred
  - id: pl-2026-09-02-7078
    text: state_dir() is named but unwritten - Kino has no publish lock. It is where one belongs if publication-level concurrency is addressed.
    added_at: '2026-09-02T15:40:34Z'
    source: model
    status: deferred
updated_at: '2026-09-02T15:40:34Z'
---

# kino — Parking Lot

_Deferred ideas. Items transition; they are never deleted._

## Deferred

- **Printable guide view**  
  _added 2026-07-25, human_  
  Wants its own milestone; not part of M3
- **Kino has no commons_author.py and no discovery.py - it does not implement PROTOCOL.md §11. Noted, not addressed.**  
  _added 2026-09-02, model_
- **tests/publications.py copies templates and static but not the renderer's module closure; that list joins the fixture at Stage 2, when the service stops importing the renderer.**  
  _added 2026-09-02, model_
- **state_dir() is named but unwritten - Kino has no publish lock. It is where one belongs if publication-level concurrency is addressed.**  
  _added 2026-09-02, model_

## Promoted

- **Multi-machine sync**  
  _added 2026-07-25, model, → M6 — ecosystem_
