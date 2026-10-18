---
type: task
id: TASK-SKRIPT-41-01-03
title: Exam AI calls go through the LLM provider door and the local token ledger is
  removed
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
- A door limit 429 shows the limit note with no toast; admin users are sent exempt; the paid-overage override is one call at a time
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

Units: 1. door client and settings; 2. each exam provider through it, Luna 6 low; 3. removal of the lease, key settings and GLM failover with a migration; 4. guard test; 5. limit note and the admin override control.

## Validation

- Focused tests: each exam provider sends through the door client with user id and exempt flag; a 429 per limit gives the B4 note and no retry; the override is sent only for the one call it was approved for; replays pass with no door call; the guard test fails on a direct OpenAI call.
- Vitest for the limit note and override control. Lint and typecheck for touched domains; migration test.
- Staging walk: a signed-in admin's answer-key suggestion goes through the door.

## Stop Conditions

Stop and report if TASK-HULE-14-03-01 is not deployed for staging, or if a recorded replay cannot be served at the door client boundary.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| C1  | ST-SKRIPT-41-01 B1-B6 apply as written. |
| C2  | One door client owns the internal key, the user id, the exempt flag and the override; providers keep their request bodies. |
