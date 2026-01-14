---
type: review
id: REV-EPIC-08
title: "Review: PR-0031 Editor AI patch-only edit-ops alignment"
status: approved
owners: "agents"
created: 2026-01-14
updated: 2026-01-14
reviewer: "lead-developer"
epic: EPIC-08
adrs:
  - ADR-0051
stories:
  - ST-08-24
  - ST-08-28
---

## TL;DR

Edit-ops v2 is implemented (ST-08-24) and we added capture-on-error (ST-08-28), but real-world failures show two
workflow gaps:

1) The model often emits malformed unified diffs (most commonly incorrect `@@ -a,b +c,d @@` counts) and we currently
   surface this as a generic “Patchen kunde inte appliceras”.
2) Correlation-ids are not stable end-to-end across `edit-ops` → `preview` → `apply`, so the correlation-id shown in the
   UI is not the one you can use to locate captures/logs for preview/apply failures.

PR-0031 proposes a patch-only alignment + diff hygiene + correlation propagation cleanup so edit-ops feels like a modern
AI IDE workflow without cursor/selection targeting.

## Scope

- In scope:
  - Validate PR-0031 plan and ensure it matches current canonical decisions (ADR-0051 + ST-08-24/ST-08-28).
  - Review failure evidence (captures + logs) and confirm the proposed mitigations address root causes.
- Out of scope:
  - New editing capabilities (semantic refactors, multi-file ops in a single diff, partial apply).
  - Provider/model changes (prompt + diff engine behavior only).

## Artifacts to review

**Primary**

- `docs/backlog/prs/pr-0031-editor-ai-edit-ops-patch-only-alignment.md`
- `.artifacts/llm-captures/edit_ops_preview_failure/*/capture.json` (malformed diff examples)

**Decision / intent**

- `docs/adr/adr-0051-chat-first-ai-editing.md`
- `docs/backlog/stories/story-08-24-ai-edit-ops-anchor-patch-v2.md`
- `docs/backlog/stories/story-08-28-ai-chat-ops-response-capture-on-error.md`

**Implementation entry points**

- Backend:
  - `src/skriptoteket/application/editor/edit_ops_handler.py`
  - `src/skriptoteket/application/editor/edit_ops_preview_handler.py`
  - `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`
  - `src/skriptoteket/infrastructure/editor/unified_diff_applier.py`
  - `src/skriptoteket/web/middleware/correlation.py`
  - `src/skriptoteket/infrastructure/llm/capture_store.py`
- Frontend:
  - `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`
  - `frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.ts`

## Review checklist

- [x] PR-0031 acceptance criteria are correct, testable, and aligned with ADR-0051 intent.
- [x] Prompt changes are unambiguous: patch-only output; no cursor/selection targeting requirements.
- [x] Proposed backend diff hygiene is safe: rejects dangerous cases; repairs only mechanical mistakes; preserves
      deterministic apply/undo semantics.
- [x] Correlation propagation plan ensures a single id is visible + usable for debugging across generation/preview/apply.
- [x] Failure modes become diagnosable (captures contain enough context; user-visible messages are actionable).
- [x] No violations of architecture rules (thin web layer; protocol-first DI; UoW owns transactions; no prompt/code
      content in normal logs).

## Verification (when PR-0031 is implemented)

- `pdm run lint`
- `pdm run typecheck`
- `pdm run test`
- Manual dev:
  - Edit-ops request without selecting text → preview renders → apply works → undo works.
  - Force a malformed hunk header (via capture replay) → backend repairs or fails with a specific message.
  - Confirm same `X-Correlation-ID` shows up for edit-ops generation, preview, and apply.

## Output

- Verdict: `approved`

## Review Feedback

The plan to align on **patch-only edit ops** is approved and strongly recommended. The failure evidence confirms that malformed unified diffs (specifically incorrect hunk header counts) are the primary cause of regeneration loops, and the proposed hybrid repair strategy in `unified_diff_applier.py` is the correct mitigation.

### Required Actions (Done)

- **ADR-0051 Updated**: The ADR has been updated to reflect the "patch-only" alignment for v2, removing "Anchor" targeting from the primary flow to avoid ambiguity and hallucinations.

### Implementation Notes

- Ensure `X-Correlation-ID` plumbing is verified end-to-end in the frontend (`useEditorEditOps.ts`).
- The backend diff repair logic should log a specific metadata flag (e.g. `rewrote_hunk_counts=True`) so we can track how often the model is getting it wrong vs right.
