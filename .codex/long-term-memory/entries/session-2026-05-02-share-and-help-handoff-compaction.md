---
type: agent_session_long_term_memory_entry
id: skriptoteket-session-2026-05-02-share-and-help-handoff-compaction
status: active
created: '2026-05-02'
last_updated: '2026-05-02'
---

# 2026-05-02 Handoff Compaction

## Scope

This entry preserves non-current session history compacted out of
`.codex/handoff.md` while the live handoff was refocused on `ST-26-07` /
`PR-0277`.

## Durable Notes

- `ST-32-08` / `PR-0270` landing authenticated-value copy refresh closed with
  Alternative B and `docs/reference/ref-public-landing-copy-lock.md`.
- Production auth-route remediation fixed the stale
  `/auth/provisioning-required?from=/` continuation loop and recorded that
  protected Skriptoteket app APIs must use the HuleEdu Gateway edge
  `https://api.hule.education/api/...`.
- Production signed-context trust wiring now mounts/forwards the Gateway public
  key and verifies it in
  `scripts/hemma_deploy_and_verify_seating_export.sh`.
- `TASK-0042` added the `.codex/long-term-memory/entries/` layout and removed
  the extra template file.
- `ST-08-35` / `PR-0271` shipped SPA help completion with route/topic catalog
  coverage, Swedish copy corrections, help drawer style cleanup, micro-help,
  and public/auth-aware Klassrumskartan help copy.
- `ST-26-06` share-link work closed `PR-0273`, `PR-0275`, and `PR-0276`:
  public guest share/revoke behavior, popover/bottom-sheet management, static
  spatial share rendering, grouping share layout, share chrome/PDF follow-up,
  and the retained `REV-PR-0276` fixes.
- `PR-0278` print/PDF redesign proof remains at
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/proof.json`.
- `EPIC-36` proposed the next scoped-sharing direction in
  `docs/reference/ref-klassrumskartan-scoped-sharing-and-import-direction-2026-05-01.md`.

## Validation Context

The live handoff should keep only current blockers, current verification, and
next closeout steps. Use governed docs and this entry for the older historical
details listed above.
