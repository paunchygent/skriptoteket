---
type: task
id: TASK-SKRIPT-40-04-19
title: Two tabs that each hold an exam lock stop invalidating each other's CSRF token on every renew
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - With two tabs each holding an exam lock, lock renews pass on the first try with no CSRF 403; a stale or mismatched CSRF token gets a message that says so instead of 'CSRF token required'
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user filed this follow-up on 2026-10-20 after the Mac's step 5 re-walk of the 40-04 gap lane (TASK-SKRIPT-40-04-14). The user moved it to `ready` on 2026-10-21 ("Build it now").

Observed on staging at main f84eb85d (Mac .artifacts/staging-walk-e4d15c4a/walk-record.md, last section): while two tabs each hold an exam lock, every 5 s lock renew in both tabs gets 403 "CSRF token required for browser session write" and then 200 about 200 ms later, without end. Every 403 request carried the X-CSRF-Token header (length 43) and the huleedu_csrf cookie was set, so the token was stale or mismatched, not missing. With one tab holding a lock, renews passed on the first try. Most likely cause (hypothesis): each tab's token recovery rotates the shared token and invalidates the other tab's cached copy.

Behaviour:

1. Two tabs that each hold an exam lock renew with no CSRF 403 on the first try.
2. A browser-session write with a stale or mismatched CSRF token gets a 403 whose message says the token is stale or does not match, not that it is required.

## Contract Inputs

- The lead names the root cause with evidence before any fix: where the token is rotated, and where each tab caches it.
- HuleEdu owns the shared browser-session login and its CSRF cookie. If the fix belongs in HuleEdu, the lead stops and reports.

## Core Vertical And Performance

One two-tab lock renew on staging, recorded with the X-CSRF-Token header and the cookie on each request, as in the Mac's re-walk.

## Validation

- A fail-first test reproduces two tabs invalidating each other's token.
- Focused backend and frontend checks for the touched files.
- The Mac re-walks two tabs each holding a lock and records no 403 on renew.

## Stop Conditions

- The fix needs a change in HuleEdu's shared session or CSRF contract.
- The fix would weaken CSRF protection.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                        |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Under the user's edge-case rule (2026-10-20) this is not a data-safety defect: no edit is lost, and each renew recovers. It is filed because lock traffic doubles and the lock depends on the recovery succeeding every 5 s. |
| D2  | CSRF protection stays as strong as today: no exemption for lock routes, and no client retry added to hide the 403.                                                                                                           |
| D3  | The fix makes the tabs share one valid token or stop rotating it on recovery; the lead chooses which from the root cause.                                                                                                    |
| D4  | Ready by user decision 2026-10-21 ("Build it now", relayed by the Mac orchestrator). The lead starts after the TASK-SKRIPT-40-04-21 F1 repair merges, because both change the exam lock and replacement paths.               |

## Progress

### 2026-10-21 (Hemma orchestrator)

- The user moved the task from `proposed` to `ready` ("Build it now"). It is sequenced after the TASK-SKRIPT-40-04-21 merge (D4).
