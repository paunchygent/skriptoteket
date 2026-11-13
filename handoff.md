## Current

- Dark mode (EPIC-SKRIPT-42, story 3 of skill-repository EPIC-SKILL-17), Mac orchestrator, 2026-11-01:
  ST-SKRIPT-42-01 tasks 01-04 are merged and deployed (`b09ebf40c`, with the 360 px signed-out
  top-bar repair). Walked on production: the theme applies before first paint, the cookie is set
  on `.hule.education`, choices persist, `/theme-sample` is 404, landing and Klassrumskartan
  signed out (Ljust and Bläck, 360 px), and the catalogue and Provhantering signed in (Midnatt
  and Bläck). Not walked: the editor (the user's account lacks the contributor role), a tool
  page with output, Reagensberedning, a share page, print and the seating PDF in Bläck, and the
  signed-in bar at phone width. Next action: walk those, then close the story. Worktree
  `../Skriptoteket-st-skript-42-01` stays until closeout. Plan: retained root
  `01a193d4-6820-7dd3-b25c-7f8c58836241`.

- Hemma orchestrator (Claude desktop SSH session, cwd `~/apps/skriptoteket`), 2026-10-29.
  User priority order of 2026-10-28; all Kodredigerare (script editor) tasks are deferred:
  REP-0037, 41-03-02, 41-03-03. No Skriptoteket child is running; no task worktree is left.

  - Production: Skriptoteket `00fa763fa` (deployed 2026-10-30, seating-export gate passed,
    log `.artifacts/hemma-deploy-20261030-123856.log`); HuleEdu `f59ea3b61`. Production `.env`
    holds `ALLOWED_HOSTS=skriptoteket.hule.education`. `ssh hemma` does not resolve on Hemma
    itself; run the deploy script detached locally. Healthz returned 503 twice at 14:09Z
    (database check timeout at load average about 20), then 200.
  - Staging runs `d0064b1ce`, healthy. If `hemma-dev start` says "container with given ID
    already exists", stop the orphaned process (postgres with SIGINT), remove
    `/run/user/1000/docker/runtime-runc/moby/<id>` dirs whose init PID is dead, start again.
  - Follow-ups seen in the 27-09-04 walk, not yet tracked: raw seat id `plats-1` in the Fast
    plats row; stacked lock badges overlap the KLASSRUM header; Håll nära/isär A/B letters swap
    after a reload; the share page draws a one-seat room at full size, so phones pan sideways.
    Staging walk data left: class `Walk 40-01-02`, room `Walk 27-09-04 B`.
  - Decisions open with the user: REP-0017 (criterion 3 names Sir Convert settings that
    `smoke-seating-export-readiness` does not read; criteria 4-6 unmet), ST-SKRIPT-02-06
    (criteria 1, 2, 5, 6 unmet), EPIC-SKRIPT-40 (required HuleEdu release: map says 0.1.34,
    current is 0.1.37).
  - Story closeout waiting: 39-10 (every task is done; no proof-set walk is on record).
  - Left as is by REP-0056: 11-26-01, 14-39-01, REP-0001, 26-08-01, REP-0022; stale guidance at
    `SandboxInputPanel.vue:104` and `scripts/playwright_ui_editor_smoke.py:315`.
  - Branch `codex/task-skript-39-06-09` (Exam.net ordering-in-part probe builder) is kept
    unmerged on purpose; probe package in `.artifacts/probe-39-06-09/`.

- [ST-SKRIPT-08-36](docs/backlog/stories/st-skript-08-36-klassrumskartan-tutorial-clips-in-hj%C3%A4lp-with-a-first-use.md)
  Klassrumskartan tutorial clips: tasks 01
  and 02 `done`; guide Steg 1 corrected on main 2026-10-28. Real clips wait on HuleFilm
  ST-VIDEO-12-01 gates (talmanus approval, ElevenLabs spend, render approval, prod media
  deploy); the Steg 1 clip script still shows a Skola24 paste.
  Retained `01a13d03-cc0c-731e-a9e5-b3d536821e55`.

- [TASK-SKRIPT-REP-0037](docs/backlog/tasks/task-skript-rep-0037-multi-file-script-bank-tool-bundles-and-the-split-of-four.md)
  `in_progress`, deferred by the user
  2026-10-28. Next when resumed: staging editor walk (edit sibling `grouping.py`, sandbox run,
  save). Production gruppgeneratorn is depublished.

- Exam epics 39/40/41 working model (user decisions G1-G30 of 2026-10-17, retained
  `01a1495e-8398-75be-b2da-f0b08ba11afa`): walk only exam-converter changes; restyle and
  repairs close on approved review plus unit tests. The Hemma orchestrator runs leads, merges,
  pushes and rebuilds staging; the Mac thread walks staging and Exam.net. Exam.net takes QTI;
  the print PDF renders the DOCX house template. Historical planning:
  `.codex/long-term-memory/entries/session-2026-09-05-epic-39-handoff-compaction.md`.

## Recent

Task ids are `TASK-SKRIPT-*`; a short id such as 39-04-22 is `TASK-SKRIPT-39-04-22`. Each task doc
under `docs/backlog/tasks/` records its review and walk evidence.

- 2026-11-08 `done` REP-0066: shared tooling block and pre-push check (`check --pushed`) adopted;
  review 84b73b42 approved `c8dd5e8a8`; suite 9024 passed. Mypy stays until REP-0067, INFO
  producer logging until REP-0068.
- 2026-11-01 `merged` ST-SKRIPT-42-01 tasks 01-03: colours read `--huleedu-*` tokens, lint rule
  `frontend/eslint-rules/no-hardcoded-colour.js`, themed CodeMirror, share pages follow the
  theme (legacy grouping shares stay light); Light scrim 0.40 by user decision (`933cfd750`).
- 2026-10-30 `done` REP-0061 40 px logo link in both top bars, 20 px title role, glyph-only
  Hjälp on phones (production `00fa763fa`); HuleEdu sign-in on design package 0.1.39
  (HULE-REP-0150, `86344a83d`).
- 2026-10-30 `done` REP-0060 signed-in top-bar logo (`5b9cf6981`; the user withdrew approval,
  REP-0061 repairs it); shared logo fix 0.1.38 in skill-repository REP-0423 (`fb10caa5`);
  REP-0059 copy (`dad31d98e`).
- 2026-10-29 `done` 39-06-11 and 26-06-01 (Mac staging walk `d0064b1ce`, main `bd6cae1c8`);
  ST-SKRIPT-39-06 (exam 5395761, `625aaf585`); 09-07-01 production refuses loopback
  ALLOWED_HOSTS (`f4ae80743`); REP-0056 backlog leftovers (`6ab51ee9c`).
- 2026-10-29 `done` (Hemma orchestrator) 27-09-04, 27-09-05 (`de4c60e93`), REP-0024, 27-09-03,
  REP-0057 (`cbbf5d969`), REP-0058 (`a58dc8ed8`), REP-0059 (`ecf66f5e1`); the user checked each
  on their iPhone in production.
- 2026-10-28 `done` REP-0055 (main `817a0cf67`): 24 tasks closed on merge evidence, 10 tasks and
  ST-21-04 canceled, 10 items deferred, six stories closed, EPIC-SKRIPT-20 active; 26-06-01
  (D4) and 09-07-01 (D5) stay open.
- 2026-10-28 `done` 39-10-03 (`ec810361f`), 39-06-09 (`c0112dfdc`), and (Hemma orchestrator)
  40-04-26 (`23309e478`), 40-02-01 (`1b2ce75cc`), 39-04-24, 39-06-08, 40-04-09, REP-0048,
  39-01-02 (walks `.artifacts/staging-walk-05b3fc12a/walk-record.md`), 41-02-07 (`a5aa760c6`),
  REP-0052/0053/0054, 39-04-20; HuleEdu REP-0149 and REP-0148.
- 2026-10-28 `done` REP-0040 Sir Convert public-host retirement (`ced7971b`, rereview `d97caf5b`;
  the user deleted the CNAME); REP-0038 repository rules retired (`eee397e31`, `e559cae0e`);
  REP-0035 passive web liveness (user closure; evidence in the task doc).
- 2026-10-22 `done` 41-03-01 AI for every signed-in teacher (production `976d89b5b`); 39-04-23
  import phases (`8569092ba`); 41-01-02 and ST-SKRIPT-41-01 script editor on Luna and Sol
  (`8569092ba`); 41-01-04 AI capacity (`d44e946b5`) with HuleEdu door 14-03-04/05/06 (`ca7ff9700`).
- 2026-10-22 `done` 39-04-22 Word drawn shapes (`74eeceb2d`, follow-up `cae867222`); 39-10-02 PDF
  pictures (`7adde567`); 39-10-01, 39-10-04, 40-04-05/12/19, 39-04-11, 41-01-03, REP-0049.
- 2026-10-22 `done` (user closure) 40-04-21/23, 39-07-03, 39-04-12, 40-01-04, 06-18-01, REP-0036,
  ST-SKRIPT-39-07, 41-02, 40-01 (walks `.artifacts/staging-walk-closure-ede1ea0d/walk-record.md`);
  Mina filer shows every workspace version by user choice; head-only listing is later.
- 2026-10-21 `done` [TASK-SKRIPT-REP-0050](docs/backlog/tasks/task-skript-rep-0050-backend-pytest-runs-parallel-and-quiet-by-default-and-serial.md) parallel and quiet pytest (merge `6a557b5d`, review 321854a9
  repaired `b1f019e6`).
- 2026-10-20 `done` (user closure) 40-04-20 (`43f47eda`), 41-02-06 (`0ab8ccb8`), 40-04-13/14
  (`f84eb85d`), 06-17-02 (`3d3f867a`; 06-17-01 canceled), 39-05-16 (`5611f0c8`), 41-02-05
  (`8be9aefa`; follow-ups D10, D24 in the task), 39-05-15 (`e4d15c4a`).
- 2026-10-19 `done` 39-04-21 (`99378586`; U4 offer line parked), 40-04-07 (`003c874a`), 41-02-01,
  39-04-15..20, REP-0046, REP-0047, HULE-14-03-01; pre-push SIGPIPE false skip fixed (`003c874a`).
- 2026-10-19 `canceled` 40-04-11 as superseded by 40-04-17 (user decision); reuse list on branch
  `codex/task-skript-40-04-compact-tools-remote`, inventory and mocks in root 01a15383.
- 2026-10-10: sir-convert-a-lot `main` `3fb6f672` holds the EPIC-SIRCON-07/08 supersession notes;
  their closure waits on migrating both epics to the contract-derived profile (user decision
  pending; ST-SIRCON-07-01 still states the old QTI 2.1 claim).

## Facts

- Session Date: 2026-10-15
- Last Refreshed: 2026-11-12
- Docs validate with `pdm run docs-validate`; historical terminal docs audit separately with
  `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- Flunk-Out Frenzy donor work never flattens a richer donor object into local bounds or a
  "good enough" approximation; the rule text is in
  `data/pinball_resources_and_repos/vpw-rom-example-table-donor-map.md` and the
  `pinball-board-authoring` skill.
- Open product questions (undecided, not silently resolved): native doc format internals (new
  versioned doc type vs file-plus-sidecar state); digital-PDF slice detail follows ST-39-04 review.
- Next: eval triage, item-type and parent/child authoring planning.
- Tutorial media: web serves `MEDIA_ROOT` read-only at `/static/media` (404 while absent); dev bind
  `/home/paunchygent/apps/skriptoteket-media/dev`, prod bind inert until `hemma-deploy`.
