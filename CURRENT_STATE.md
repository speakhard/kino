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
  head: '9832299'
  head_subject: 'CI: run the test suite on every push and pull request'
  dirty: 0
  ahead: 7
  behind: 0
  observed_at: '2026-09-30T18:47:18Z'
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
    at: '2026-09-30T18:47:18Z'
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
    source: model
    at: '2026-09-30T18:47:18Z'
  blockers:
    source: model
    at: '2026-09-02T15:40:34Z'
next_task: 'Stage 2 on Kino: extract the renderer invocation into a subprocess call that matches the Cloudflare build command, re-point the rollback tests at it, and prove a failed build leaves no record, no artifact, no commit, with the service still up.'
risks:
  - Stage 1 alone does not close the defect. Kino still syncs and then rebuilds in-process (publisher.py sync followed by builder.build), so a publish that fast-forwards the checkout can still swap templates under already-loaded code. Kino is currently level with origin so the condition is not armed, but nothing prevents it re-arming.
  - The build's closing log line now prints an absolute path where it printed 'site/'. Cosmetic, but it is a real output difference and anything parsing that line would see it.
  - Seven commits are local only (f466c63, 295f5c4 and the five M0 commits of 2026-09-30); origin/main is 404d101. Kino on ppmanchester was observed at 404d101 with kino.service active on 2026-09-30, so host and local copy diverge until a push and pull are approved.
  - 'M0 hardening (2026-09-30), local only and not deployed: request guard (Host allowlist + Origin/Sec-Fetch-Site check), sync failures reported rather than 500, discovery document + 404.html, commons_spec 0.3, MIT LICENSE, CI workflow. Deploying the guard needs KINO_ALLOWED_HOSTS set if Kino is opened by any name other than its tailnet IP.'
estimated_remaining: Stages 2-4 for Kino, then the same sequence for Crows with its publish lock resolved first. Multiple sessions.
summary: 'Stage 1 (publication root) and M0 hardening are committed locally and unpushed. Stage 2 (renderer as subprocess) is next.'
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
| **HEAD** | 9832299 — CI: run the test suite on every push and pull request |
| **Working tree** | clean |
| **Observed** | 2026-09-30T18:47:18Z |

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
- The build's closing log line now prints an absolute path where it printed 'site/'. Cosmetic, but it is a real output difference and anything parsing that line would see it.
- Seven commits are local only (f466c63, 295f5c4 and the five M0 commits of 2026-09-30); origin/main is 404d101. Kino on ppmanchester was observed at 404d101 with kino.service active on 2026-09-30, so host and local copy diverge until a push and pull are approved.
- M0 hardening (2026-09-30), local only and not deployed: request guard (Host allowlist + Origin/Sec-Fetch-Site check), sync failures reported rather than 500, discovery document + 404.html, commons_spec 0.3, MIT LICENSE, CI workflow. Deploying the guard needs KINO_ALLOWED_HOSTS set if Kino is opened by any name other than its tailnet IP.

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
- The build's closing log line now prints an absolute path where it printed 'site/'. Cosmetic, but it is a real output difference and anything parsing that line would see it.
- Seven commits are local only (f466c63, 295f5c4 and the five M0 commits of 2026-09-30); origin/main is 404d101. Kino on ppmanchester was observed at 404d101 with kino.service active on 2026-09-30, so host and local copy diverge until a push and pull are approved.
- M0 hardening (2026-09-30), local only and not deployed: request guard (Host allowlist + Origin/Sec-Fetch-Site check), sync failures reported rather than 500, discovery document + 404.html, commons_spec 0.3, MIT LICENSE, CI workflow. Deploying the guard needs KINO_ALLOWED_HOSTS set if Kino is opened by any name other than its tailnet IP.

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
| git | observed | 2026-09-30T18:47:18Z | — |
| next_task | model | 2026-09-02T15:40:34Z | — |
| risks | model | 2026-09-02T15:40:34Z | — |
| estimated_remaining | model | 2026-09-02T15:40:34Z | — |
| summary | model | 2026-09-30T18:47:18Z | — |
| blockers | model | 2026-09-02T15:40:34Z | — |

_Latest session log: `20260902T154034Z-9ae8f081.md`_
