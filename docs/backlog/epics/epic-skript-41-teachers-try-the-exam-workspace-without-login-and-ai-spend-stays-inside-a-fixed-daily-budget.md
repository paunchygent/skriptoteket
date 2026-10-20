---
type: epic
id: EPIC-SKRIPT-41
title: Teachers try the exam workspace without login and AI spend stays inside a fixed
  daily budget
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: active
closeout_review:
  record: inline
  status: not_started
outcome: Teachers can convert and edit exams in the public workspace without login
  and without AI, and every paid AI call stays inside one fixed daily budget
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Capability Contract

Skriptoteket's public offer is the exam workspace itself: a guest imports a QTI package or starts a blank exam, edits it in the same editor signed-in teachers use, and exports every format that costs no AI (QTI, print PDF, DOCX and the fallback Exam.net PDF). Signing in adds Mina filer and AI help. The sales argument is control and ownership of a fixed exam, not AI. Paid AI is never reachable without login (E1).

Every paid AI call goes through the HuleEdu LLM provider service's metered OpenAI door (ST-HULE-14-03), which reserves each call once against the shared UTC-day pools, the teacher's share and Skriptoteket's USD ceiling (E2-E4). Skriptoteket keeps its own prompts and schemas and holds no OpenAI key. Skriptoteket and the door serve 10,000 users and 1,000 concurrent calls (E6). DigiExam conversion is part of the exam app behind login (E5).

Non-goals: public AI (any later public AI is off by default and limited to one conversion, an item cap and one suggestion); textbook-grounded item generation (EPIC-SKRIPT-22); lifting the admin-only AI gate of TASK-SKRIPT-REP-0044, which is a separate user decision after both stories ship.

## Contract Inputs

- User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006), with explorer maps of Skriptoteket's paid AI call sites and capacity and of the HuleEdu LLM provider service the same day.
- ST-HULE-14-03 and TASK-HULE-14-03-01 in the HuleEdu repository (the metered door).
- TASK-SKRIPT-REP-0044 (paid AI admin-only until this epic ships); ADR-SKRIPT-0085 (public conversion exception); ST-SKRIPT-39-07 S8 and TASK-SKRIPT-39-07-03 R4 (the guest converter's later decision, taken here).
- EPIC-SKRIPT-22 (textbook corpus, linked for later grounding).

## Stories

| Story | Delivers |
| ----- | -------- |
| ST-SKRIPT-41-01 | Every paid call through the LLM provider door, the script editor on Sol 6.1 low, and capacity for 1,000 concurrent calls |
| ST-SKRIPT-41-02 | QTI import, the public workspace without login, and removal of the guest DigiExam line |

The two stories are built in parallel (user 2026-10-18).

## Verification

Each story's verification holds; a staging walk proves a guest QTI import, edit and export without login and a signed-in teacher meeting the daily limit note.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| E1  | No unauthenticated route reaches a paid AI provider. |
| E2  | Every paid AI call goes through the HuleEdu LLM provider door over `hule-network` with the internal key; Skriptoteket holds no OpenAI key and keeps no token ledger of its own. |
| E3  | The door's pools apply per UTC day, resetting at UTC midnight: 10,000,000 tokens for small models (Luna, Terra) and 1,000,000 tokens for full models (Sol). Each teacher may use 10% of the small pool and 1% of the full pool per day, and Skriptoteket's exam app stops at $1 per UTC day at OpenAI list prices. |
| E4  | Admin and staging test users meet only the pools. When a pool is exhausted, a call proceeds only with an explicit one-call paid-overage override that a person approves; agents running tests stop and ask the user. Deterministic fixture and corpus runs replay recordings and never call the door. |
| E5  | DigiExam conversion lives only in the exam workspace behind login; the public guest DigiExam line is removed; the guest converter's URL opens the public workspace. |
| E6  | Skriptoteket and the door serve 10,000 users and 1,000 concurrent AI calls, slowing down with a try-again answer instead of failing. |
