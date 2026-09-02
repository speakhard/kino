---
schema: devtracker/current-state@1
project: kino
status: Stage 1 committed locally as f466c63, not pushed and not deployed. Kino now resolves which publication it is opening through publication.py (opened(path) -> KINO_PUBLICATION -> cwd) rather than through eight module-level constants frozen at import time. The default is unchanged and was proven so by diffing built output across the change. The test fixtures carried the same defect as the source and were fixed in the same commit.
milestone:
  current: Stage 1 complete and verified - publication root is explicit configuration, no behaviour change
  next: Stage 2 - invoke the renderer as a subprocess, which is the stage that actually closes the defect
goal: Repeat on Kino the publisher/publication separation Lens went through first, so that synchronising a publication cannot modify the service performing the publish.
definition_of_done: Kino resolves every path through an explicit publication root rather than by accident of working directory or install location; the change is provably inert by default; the renderer is invoked as a subprocess so a sync cannot swap modules under a running publish; the transitional risk class is closed by construction rather than by vigilance.
docs:
  - ~/Development/reports/2026-08-31-commons-publisher-publication-boundary.md
  - ~/Development/lens/publication.py and lens/tests/publications.py - the proven shape Kino is following
git:
  branch: main
  head: f466c63
  head_subject: Kino opens a publication; it does not have to live inside one
  dirty: 5
  ahead: 1
  behind: 0
  observed_at: '2026-09-02T15:40:34Z'
resume:
  directory: /home/fs42/Development/kino
  command: cd /home/fs42/Development/kino && claude
updated_at: '2026-09-02T15:40:34Z'
provenance:
  status:
    source: model
    at: '2026-09-02T15:40:34Z'
  milestone:
    source: model
    at: '2026-09-02T15:40:34Z'
  goal:
    source: model
    at: '2026-09-02T15:40:34Z'
  definition_of_done:
    source: model
    at: '2026-09-02T15:40:34Z'
  docs:
    source: model
    at: '2026-09-02T15:40:34Z'
  git:
    source: observed
    at: '2026-09-02T15:40:34Z'
  next_task:
    source: model
    at: '2026-09-02T15:40:34Z'
  risks:
    source: model
    at: '2026-09-02T15:40:34Z'
  estimated_remaining:
    source: model
    at: '2026-09-02T15:40:34Z'
  summary:
    source: recovered
    at: '2026-08-01T19:57:37Z'
  blockers:
    source: model
    at: '2026-09-02T15:40:34Z'
next_task: 'Stage 2 on Kino: extract the renderer invocation into a subprocess call that matches the Cloudflare build command, re-point the rollback tests at it, and prove a failed build leaves no record, no artifact, no commit, with the service still up.'
risks:
  - Stage 1 alone does not close the defect. Kino still syncs and then rebuilds in-process (publisher.py sync followed by builder.build), so a publish that fast-forwards the checkout can still swap templates under already-loaded code. Kino is currently level with origin so the condition is not armed, but nothing prevents it re-arming.
  - Kino's distributor.sync() is called outside the try, so a DistributionError still reaches the author as an unexplained 500 rather than a rolled-back transaction with a message. Unchanged by this stage.
  - The build's closing log line now prints an absolute path where it printed 'site/'. Cosmetic, but it is a real output difference and anything parsing that line would see it.
  - f466c63 is committed locally only. Kino on ppmanchester is level with origin, so the two are now divergent until this is pushed and pulled deliberately.
estimated_remaining: Stages 2-4 for Kino, then the same sequence for Crows with its publish lock resolved first. Multiple sessions.
summary: 'Currently on M3 — configurable player themes. Most recently: Scoped the theme model. Outstanding: Settings migration not written.'
latest_session: 20260902T154034Z-9ae8f081.md
blockers: []
---

# kino — Current State

_Generated 2026-09-02T15:40:34Z. The front-matter above is the source of truth; this body is rendered from it._

| | |
|---|---|
| **Status** | Stage 1 committed locally as f466c63, not pushed and not deployed. Kino now resolves which publication it is opening through publication.py (opened(path) -> KINO_PUBLICATION -> cwd) rather than through eight module-level constants frozen at import time. The default is unchanged and was proven so by diffing built output across the change. The test fixtures carried the same defect as the source and were fixed in the same commit. |
| **Current milestone** | Stage 1 complete and verified - publication root is explicit configuration, no behaviour change |
| **Next milestone** | Stage 2 - invoke the renderer as a subprocess, which is the stage that actually closes the defect |
| **Branch** | main |
| **HEAD** | f466c63 — Kino opens a publication; it does not have to live inside one |
| **Working tree** | 5 changed |
| **Observed** | 2026-09-02T15:40:34Z |

## Today's goal

Repeat on Kino the publisher/publication separation Lens went through first, so that synchronising a publication cannot modify the service performing the publish.

## Definition of done

Kino resolves every path through an explicit publication root rather than by accident of working directory or install location; the change is provably inert by default; the renderer is invoked as a subprocess so a sync cannot swap modules under a running publish; the transitional risk class is closed by construction rather than by vigilance.

## Next task

Stage 2 on Kino: extract the renderer invocation into a subprocess call that matches the Cloudflare build command, re-point the rollback tests at it, and prove a failed build leaves no record, no artifact, no commit, with the service still up.

## Blockers

_None._

## Known risks

- Stage 1 alone does not close the defect. Kino still syncs and then rebuilds in-process (publisher.py sync followed by builder.build), so a publish that fast-forwards the checkout can still swap templates under already-loaded code. Kino is currently level with origin so the condition is not armed, but nothing prevents it re-arming.
- Kino's distributor.sync() is called outside the try, so a DistributionError still reaches the author as an unexplained 500 rather than a rolled-back transaction with a message. Unchanged by this stage.
- The build's closing log line now prints an absolute path where it printed 'site/'. Cosmetic, but it is a real output difference and anything parsing that line would see it.
- f466c63 is committed locally only. Kino on ppmanchester is level with origin, so the two are now divergent until this is pushed and pulled deliberately.

## Estimated remaining

Stages 2-4 for Kino, then the same sequence for Crows with its publish lock resolved first. Multiple sessions.

## Resuming

```bash
cd /home/fs42/Development/kino && claude
```

### Resume prompt

```text
Continue development of kino.

Repository:
/home/fs42/Development/kino

Read:
~/Development/reports/2026-08-31-commons-publisher-publication-boundary.md
~/Development/lens/publication.py and lens/tests/publications.py - the proven shape Kino is following

Current milestone:
Stage 1 complete and verified - publication root is explicit configuration, no behaviour change

Today's Goal:
Repeat on Kino the publisher/publication separation Lens went through first, so that synchronising a publication cannot modify the service performing the publish.

Definition of Done:
Kino resolves every path through an explicit publication root rather than by accident of working directory or install location; the change is provably inert by default; the renderer is invoked as a subprocess so a sync cannot swap modules under a running publish; the transitional risk class is closed by construction rather than by vigilance.

First task:
Stage 2 on Kino: extract the renderer invocation into a subprocess call that matches the Cloudflare build command, re-point the rollback tests at it, and prove a failed build leaves no record, no artifact, no commit, with the service still up.

Known risks:
- Stage 1 alone does not close the defect. Kino still syncs and then rebuilds in-process (publisher.py sync followed by builder.build), so a publish that fast-forwards the checkout can still swap templates under already-loaded code. Kino is currently level with origin so the condition is not armed, but nothing prevents it re-arming.
- Kino's distributor.sync() is called outside the try, so a DistributionError still reaches the author as an unexplained 500 rather than a rolled-back transaction with a message. Unchanged by this stage.
- The build's closing log line now prints an absolute path where it printed 'site/'. Cosmetic, but it is a real output difference and anything parsing that line would see it.
- f466c63 is committed locally only. Kino on ppmanchester is level with origin, so the two are now divergent until this is pushed and pulled deliberately.

Do not revisit completed architectural decisions unless necessary.
```

## Provenance

| Field | Source | When | By |
|---|---|---|---|
| status | model | 2026-09-02T15:40:34Z | — |
| milestone | model | 2026-09-02T15:40:34Z | — |
| goal | model | 2026-09-02T15:40:34Z | — |
| definition_of_done | model | 2026-09-02T15:40:34Z | — |
| docs | model | 2026-09-02T15:40:34Z | — |
| git | observed | 2026-09-02T15:40:34Z | — |
| next_task | model | 2026-09-02T15:40:34Z | — |
| risks | model | 2026-09-02T15:40:34Z | — |
| estimated_remaining | model | 2026-09-02T15:40:34Z | — |
| summary | recovered | 2026-08-01T19:57:37Z | — |
| blockers | model | 2026-09-02T15:40:34Z | — |

_Latest session log: `20260902T154034Z-9ae8f081.md`_
