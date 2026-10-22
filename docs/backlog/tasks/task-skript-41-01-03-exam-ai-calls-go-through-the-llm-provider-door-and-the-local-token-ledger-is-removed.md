---
type: task
id: TASK-SKRIPT-41-01-03
title: Exam AI calls go through the LLM provider door and the local token ledger is removed
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Answer keys, DOCX conversion, labeling and content tags call the LLM provider door with the internal key and the teacher's user id, on GPT-6 Luna low
  - The token lease, the OpenAI key settings and the GLM failover are removed, and a guard test fails when a paid call bypasses the door client
  - A door limit 429 before a job starts shows the limit note with no toast; a started job finishes as paid overage up to USD 1 (C7); admin users are sent exempt; the paid-overage override exists only in agent-run tooling, off by default, set per approved run (C6)
  - A staging walk shows an answer-key suggestion through the door
story: ST-SKRIPT-41-01
backlog_document_profile: contract-derived
---

## Implementation Contract

The walking skeleton of ST-SKRIPT-41-01: point the exam providers (`openai/answer_key_structured_provider.py`, `responses_item_labeler.py`, `decisions_item_labeler.py`, the content-tag classifier) at the door through one door client, keeping their request bodies, and delete the token lease, its migrations' table, the OpenAI key settings and the OpenRouter failover (B1-B6). The REP-0044 admin-only gate stays.

Non-goals: the script editor (TASK-SKRIPT-41-01-02); capacity (TASK-SKRIPT-41-01-04); public AI.

## Contract Inputs

- ST-SKRIPT-41-01 B1-B6; ST-HULE-14-03 D1-D5; User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006), with explorer maps of Skriptoteket's paid AI call sites and capacity and of the HuleEdu LLM provider service the same day.
- `exam_answer_key_token_leases.py`, `digiexam_answer_key_token_lease.py`, `exam_answer_key_enrichment_attempts.py`, `exam_answer_key_provider_attempts.py`, `item_type_labeling.py`, `exam_workspace_docx_build_rounds.py`, `exam_content_tagging.py`, `openrouter/answer_key_chat_provider.py`, `di/exam_answer_key.py:114-143`, `di/exam_workspace.py:138-294`, `di/docx_conversion.py`, `config.py:330-360`.

## Core Vertical And Performance

The vertical is one answer-key suggestion: the provider sends its Responses body through the door client with the internal key, the teacher's user id and the exempt flag for admin users; the door's answer returns to the existing parsing; a limit 429 becomes the B4 note. Recorded replays keep working with the door client as the recording boundary. No performance change here.

Units: 1. door client and settings; 2. each exam provider through it, Luna 6 low; 3. removal of the lease, key settings and GLM failover with a migration; 4. guard test; 5. the limit note (C6: no app override control).

## Validation

- Focused tests: each exam provider sends through the door client with user id and exempt flag; a 429 per limit gives the B4 note and no retry; the scripts send the override only with their per-run flag and stop on a pool 429 without it; replays pass with no door call; the guard test fails on a direct OpenAI call.
- Vitest for the limit note. Lint and typecheck for touched domains; migration test.
- Staging walk: a signed-in admin's answer-key suggestion goes through the door.

## Stop Conditions

Stop and report if a recorded replay cannot be served at the door client boundary. Build and test every unit now; only the staging walk waits until the HuleEdu door is reachable from Skriptoteket staging and HuleEdu staging serves the door from real OpenAI (C4).

## Known Gap

Before the REP-0044 gate opens AI to teachers, close this gap: the door's `allow_paid_overage` skips only the pool check. In HuleEdu `services/llm_provider_service/openai_allowance_redis_scripts.py` RESERVE_SCRIPT (lines 45-61), `enforce` gates only the pool; the user-share and USD-ceiling checks still refuse a non-exempt caller even under `allow_paid_overage`. A started job of a non-exempt teacher can therefore still be refused mid-job, which C7 does not allow. Every AI user today is an admin sent exempt, so the gap is not reachable now. Out of scope here; do not work around the door. (Lead finding and orchestrator ruling, 2026-10-22.)

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | ST-SKRIPT-41-01 B1-B6 apply as written.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| C2  | One door client owns the internal key, the user id, the exempt flag and the override; providers keep their request bodies.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| C3  | Network: HuleEdu staging attaches `llm_provider_service` to `hule-network`, the shared cross-app network; Skriptoteket stays off HuleEdu's internal network. This task joins Skriptoteket's worker to `hule-network` (the web is already on it). One `HULEEDU_INTERNAL_API_KEY` goes into both staging `.env` files, set by the HuleEdu attach. Production needs the same attach when ST-SKRIPT-41-01 ships. (Mac orchestrator, 2026-10-22.)                                                                                                                                                                                                                                                                                                              |
| C4  | The staging walk uses real OpenAI: HuleEdu staging switches the door off its mock for the walk. (User, 2026-10-22, relayed by the Mac orchestrator.)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| C5  | The live scripts `exam_conversion_eval`, `item_type_labeler_live` and `labeling_feasibility` go through the door client and run only where the door is reachable; `with_hemma_answer_key.sh` and `run_labeling_feasibility_with_hemma_key.sh` are deleted. (User, 2026-10-22, relayed by the Hemma orchestrator.)                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| C6  | The paid-overage override is for agent-run tooling, not app users: no app control or route accepts it, and teachers and admins see only the B4 note. The live scripts and staging proof runs take an explicit per-run flag, off by default; without it a pool 429 stops the run with a message that paying overage needs the user's approval, and the agent reruns with the flag only on the user's yes. One approved run; nothing persists. Narrows ST-SKRIPT-41-01 B5's admin-control wording. (User, 2026-10-22, relayed by the Hemma orchestrator.)                                                                                                                                                                                                   |
| C7  | A started AI job finishes: a job is admitted when its first door call succeeds under `free_allowance_only`, and every later call of that job sends `allow_paid_overage`; a refusal before admission gives the B4 note, so only new jobs meet the limit. Each job's overage is the sum of `X-HuleEdu-Charge-USD-Micros` on its calls marked `X-HuleEdu-Charge-Kind: overage`; once it passes `LLM_JOB_OVERAGE_CAP_USD` (default 1.0) the job stops through the interrupted-job failure path, and no partial result is shown as complete. Automatic, no approval or UI control, nothing persists after the job. The charge headers come from a HuleEdu door change routed by the Hemma orchestrator. (User, 2026-10-22; orchestrator call (A), 2026-10-22.) |
| C8  | Exempt (admin and superuser) jobs have no per-job overage cap: the door sends no charge headers on exempt calls, so their overage is not counted. The cap applies to non-exempt users once the REP-0044 gate opens AI to them. A non-exempt call without charge headers counts no overage and logs `llm_door_charge_headers_missing`; no exam path streams, so no streamed answer goes uncharged. A local price estimate is ruled out. (User, 2026-10-21, relayed by the Hemma orchestrator.)                                                                                                                                                                                                                                                             |

## Progress

2026-10-21, implementation lead: units 1-5 are built on `codex/task-skript-41-01-03`. The staging walk (AC 4) and review have not happened yet.

- Unit 1, door client and settings: `e260e4fe8`. Admission, the per-job overage cap and the lease removal (migration `9f3c7a1b4e02`, job `ai_limit`): `cbb6e3b2d`.
- Unit 2, providers through the door on GPT-6 Luna low: the answer-key provider and the GLM failover removal in `e23b92be2`; the Decisions labeler, content tags and DOCX and content job limits in `d5abb3018`.
- Units 3 and 4, settings removal, compose wiring (the staging worker joins `huleedu-dev-hule-network`), the guard test and the scripts on the door: `c69e7441d`. The same commit adds `ai_limit` to the web contract and the 429 `AI_DAILY_LIMIT_REACHED` retry answer.
- Unit 5, the limit note in the exam workspace: `bafb8d40c`.
- Proof:
  - `pdm run typecheck`, `fe-type-check`, `fe-lint`, `check-migration-test-coverage` and `docs-validate` pass.
  - Docker integration passes: the migration test plus the DOCX background and DigiExam suggestion modules, 13 passed.
  - Focused unit tests pass: 2342 in curated apps, LLM and workers; 673 in web, architecture and config; 2282 exam-workspace Vitest.
  - `pdm run lint` passes after the consumer-root `.yamllint` turns off only line length; the other default yamllint rules still run on the compose files (orchestrator ruling, 2026-10-22).
  - Logs are in the lead's retained root, under `evidence/closeout-*.log`.
- Orchestrator confirmations (2026-10-22) of choices the work orders did not settle:
  1. A limit on any AI action disables every exam-workspace AI control for the page session, because one shared pool refuses them all.
  2. The guard test allowlists `scripts/llm_harness/inline_completion_harness.py`, script-editor tooling owned by TASK-SKRIPT-41-01-02.
  3. The live scripts exit with code 2 and the approval message on a pool refusal, and with code 1 naming the limit on any other limit; they send the caller as exempt.
  4. A DOCX job stopped by a door refusal keeps the user-facing limit note in `last_error`, and the job's first refusal wins.

2026-10-22, implementation lead: the review (`changes_requested`, F1-F6) is repaired in one round. F1-F3 go to one independent rereview; F4-F6 and the limit notes are admitted on focused proof.

- F1, the cap after each charge: `fb6c3aaef`. The client settles every door answer: a success admits the action, the overage charge is recorded, and the call that takes an app job past the $1 cap raises `AiJobOverageCapReached` itself.
- F2, a DOCX limit ends the job as a failure: `16446878a`. A door limit or the cap anywhere in a conversion fails the job with the limit note; published batches and teacher edits stay, and the job is never `SUCCEEDED` or published as final.
- F3, tooling overage only on approval: `fb6c3aaef` and `16446878a`. Tooling without `--allow-paid-overage` runs `FREE_ONLY` and never switches to paid overage; with the flag it runs `APPROVED_RUN`.
- F4: the eval sends a typed `AiDailyLimitReached` to the CLI exit handler (`16446878a`).
- F5: modules over 500 lines are split (the DOCX pipeline, the DOCX retry and `useExamWorkspaceConversion.ts`) in `16446878a`.
- F6: `Any`, `cast` and type assertions are removed from the new code and tests (`16446878a`, `ea597a597`).
- The limit notes follow `error.limit`: `user_share` says "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon."; `pool` and `usd_ceiling` say "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon." The answer-key profile id is now `openai-gpt-6-luna-answer-key` (`b76fb5c6e`).
- `origin/main` is merged in `188ebe30f`, `eb17850ed` and `cacc28e04`.
- Proof at `cacc28e04`, run after the merge:
  - `pdm run lint`, `typecheck`, `fe-lint`, `check-migration-test-coverage` and `docs-validate` pass.
  - Focused unit tests pass: 3576 in curated apps, LLM, workers, web, scripts, architecture and config, plus 2419 exam-workspace Vitest tests.
  - Docker integration passes 13 tests: the migration test plus the DOCX background and DigiExam suggestion modules.
  - Logs are in the lead's retained root, under `evidence/repair/`.
