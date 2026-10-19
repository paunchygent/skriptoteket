---
type: task
id: TASK-SKRIPT-06-18-01
title: Repair vitest-run target resolution, separator handling and the include transport
  type
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-19'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Review ecea35b6 findings F1-F3 are repaired with real-collection proof; default
  discovery lists exactly the src/**/*.spec.ts set (505 at bf79abce, 506 after the
  new vitestInclude.spec.ts).
story: ST-SKRIPT-06-18
backlog_document_profile: contract-derived
---

## Resume here

- 2026-10-19, lead cebb6d3d in worktree `skriptoteket-fe-vitest-run-repair-remote` (branch `codex/fe-vitest-run-repair-remote`, base `bf79abce`). Retained root `01a15524-776a-7857-8a94-c2c3e11dce51`: review in `evidence/reviews/ecea35b6-46f1-4148-b483-02cfe0e36e89.md`, work orders U1-U5 in `evidence/work-orders/`, proof in `evidence/repair-proof/`.
- Delivered: U1 typed include transport (F3), U2 real-match resolution and separator handling (F1, F2), U3 Node tsconfig project for `vitest.config.ts`, U4 loud `statSync` and file-only line selector, U5 the two Node-environment wrapper specs moved into the Node project.
- Real collection, `before-bf79abce.txt` -> `after-worktree.txt`: brace file+folder glob 1 -> 2 files (run: 2 files, 34 tests); `src/test/*.{spec,test}.ts` and `src/test/*.ts` exit 1 -> exit 0 with 2 specs; `list --filesOnly -- -- src/no-such-folder` exit 0 with 505 specs -> exit 1. Kept: spec + folder 2 files; missing and spec-free folders exit 1; typo exits 1 in watch and coverage mode; line selector 1 passed, 1 skipped; repo-root and absolute folders; `--reporter dot`. Default discovery equals the `src/**/*.spec.ts` set exactly (506 = 505 + the new `vitestInclude.spec.ts`).
- Real route: `pdm run fe-test -- src/composables/home` and `pdm run fe-test -- --reporter dot src/composables/home` each run 1 file, 2 tests; an absolute out-of-app spec plus an in-app folder lists 2 files (`real-route-checks.txt`).
- Checks (before U6): focused specs 43/43, fe-type-check, fe-lint, docs-validate, handoff-validate pass.
- Rereview ed8a6e7b cleared F1 and raised R1 (medium, extglobs rejected). U6 makes `fs.globSync` the single glob authority and prefixes unreadable-match failures. `extglob-before-c17e1afd.txt` -> `extglob-after-u6.txt`: `@(...)` exit 1 -> exit 0 with 1 spec; `@(a|b)` and `+(a|b)` exit 1 -> exit 0 with 2 specs; dangling symlink raw `ENOENT` -> `vitest-run: ... cannot read`. `after-u6.txt` holds every earlier case; default set still identical (506). Focused specs 47/47, fe-type-check, fe-lint pass (`closing-checks-u6.txt`).
- Next: R1 is admitted on focused proof (no rereview); orchestrator hands the branch to the Mac.

## Implementation Contract

`frontend/apps/skriptoteket/scripts/vitest-run.mjs` turns every Vitest path argument into an include target (commits `900db302` and `5e7c646b`, merged to main in `bf79abce` without review). The independent review ecea35b6 (2026-10-19, changes_requested) found three defects, repaired here:

- F1 (high): `expandVitestTarget` guessed a target's kind from its spelling and appended `/**/*.spec.ts` to any target without a spec suffix. A glob matching a spec file and a folder (`src/{test/vitestRunPathNormalization.spec.ts,composables/home}`) dropped the file and ran 1 file green; valid file globs (`src/test/*.{spec,test}.ts`, `src/test/*.ts`) exited 1.
- F2 (medium): `splitVitestArgs` removed only the first `--`. Vitest's `parseCLI` puts tokens after a remaining `--` into `options["--"]`, so `list --filesOnly -- -- src/no-such-folder` forwarded the typo unexamined, exited 0 and listed all 505 specs.
- F3 (medium): `vitest.config.ts` read the include list with `JSON.parse(...) as string[]`, a forbidden cast, and vue-tsc did not type-check the config at all.

Non-goals: changing Vitest itself, the default include `src/**/*.spec.ts`, or the package scripts.

## Contract Inputs

- Review ecea35b6 and its probe logs (retained root above).
- Wrapper contract (orchestrator brief, 2026-10-19): every path target contributes all its spec files; any target that matches no spec file exits non-zero; the default run discovers all of `src/**/*.spec.ts`.
- Vitest 4.0.16 `parseCLI` (cac) behaviour, probed: `parseCLI(["vitest","run","--reporter","dot","a","--","b","--","c"])` gives `filter: ["a"]`, `options["--"]: ["b","--","c"]`.

## Core Vertical And Performance

The vertical is one wrapper invocation: arguments are split into Vitest flags and path targets, each target resolves to real spec files, and the include list reaches `vitest.config.ts` through one typed transport. Resolution runs one filesystem glob per target; no performance concern for local tooling.

## Validation

- Real collection, fail-first: `evidence/repair-proof/wrapper-matrix.sh <checkout> src/composables/home/useHomeDashboard.spec.ts:81` before (at `bf79abce`) and after the repair, using `vitest list --filesOnly` counts and small runs.
- Default discovery: `list --filesOnly` with no target lists exactly the `src/**/*.spec.ts` set (505 at `bf79abce`). This list check replaces the domain suite for this task (orchestrator ruling 2026-10-19); no full frontend suite runs.
- Focused specs `src/test/vitestRunPathNormalization.spec.ts` and `src/test/vitestInclude.spec.ts`; `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run docs-validate`.

## Stop Conditions

Stop and report to the orchestrator if a fix needs a change to Vitest's own configuration beyond the include list, a backward-compatible reader, or a cast.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | A target resolves through real matches: `fs.globSync` with file types is the one authority for literal paths and patterns alike (only `.` is the app folder directly), never the target's spelling. A matched spec file contributes itself; a matched folder contributes `<folder>/**/*.spec.ts`; other matched files are ignored. |
| D2  | A matched path that does not name itself (`fs.globSync(path)` returns something other than exactly that path) fails the run: probes showed backslash escaping works in neither Node glob nor tinyglobby, so Vitest's include cannot name it exactly. A match that `statSync` cannot read fails the run with a `vitest-run:` message. |
| D3  | The first `--` is package-manager forwarding and is removed. Every token after a remaining `--` is a path target and is validated; none is forwarded to Vitest unexamined. Flag values such as `--reporter dot` before it stay flag values. |
| D4  | `scripts/vitest-include.mjs` owns the include transport: `VITEST_INCLUDE_ENV`, `encodeVitestInclude` and `decodeVitestInclude` (a non-empty JSON array of strings, validated at runtime, typed by `vitest-include.d.mts`). No cast and no comma-separated decoder. |
| D5  | `vitest.config.ts` joins the vue-tsc `include` so the decoder's type is checked at its consumer. |
| D6  | A line selector is valid only on a literal target that is itself a spec file; a folder holding one spec file with a selector is rejected. |
| D8  | Lead-found repairs of returned work: U3 moves `vitest.config.ts` into `tsconfig.node.json` because adding it to the browser project leaked Node `Timeout` types; U4 lets a `statSync` failure stop the run instead of dropping the match, and narrows D6 to file targets; U5 type-checks the two Node-environment wrapper specs in the Node project. |
| D9  | Rereview ed8a6e7b (2026-10-19) cleared F1 and found R1 (medium): the hand-kept glob character list missed extglobs `@(...)` and `+(...)`. U6 deletes `isGlob` so `fs.globSync` alone classifies, and adds the prefixed unreadable-match failure. R1 is admitted on focused proof without rereview. |
| D7  | The repaired F1 (high) returns to reviewer ecea35b6 for rereview through the orchestrator; F2 and F3 return with focused proof. |
