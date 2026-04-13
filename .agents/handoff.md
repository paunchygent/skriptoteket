# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history into repo long-term memory at `docs/reference/ref-development-changelog.md` first.
## Snapshot
- Date: 2026-04-13
- Branch: `main` + local changes
- Current lane: `ST-28-12`, `PR-0261`, and `PR-0262` are done locally and verified. `PR-0254`
  is the next auth-cutover proof lane.
- Production: Full Vue SPA.
- Handoff compaction moved the older auth-cutover verification ledger into
  `docs/reference/ref-development-changelog.md`.
## Status
- `PR-0261` implemented direct HuleEdu action anchors/auto-handoff for login, registration,
  forgot-password, reset completion, and email verification, plus the hidden no-side-effect
  diagnostics route `GET /api/v1/diagnostics/huleedu-internal-identity`.
- HuleEdu reran `TASK-0327` live apply against that route and retained final `status=ok` provider
  proof:
  `/Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json`.
- HuleEdu runner now accepts the approved sanitized diagnostics shape without requiring raw
  signed-context email or raw `realm_subject_id` in retained signed-context proof.
- `PR-0262` consumes the HuleEdu artifact as upstream provider evidence instead of re-driving the
  real-inbox lifecycle.
- `PR-0262` validates upstream direct-action/session/signed-context evidence, then proves
  Skriptoteket callback continuation, local projection, local role observation, live diagnostics,
  and redaction.
- Retained PR-0262 manifest:
  `.artifacts/playwright-pr-0262-real-lifecycle/local-nonprod/20260413T132801Z/manifest.redacted.json`.
- Shared temporary Playwright backend/Vite helpers now support free backend ports and Vite proxy
  wiring so targeted PR proofs do not collide with the long-running Docker dev stack on 8000/5173.
- `ST-28-12` is done; final cross-app Docker/operator proof remains in `ST-28-04` / `PR-0254`.
## Verification
- `pdm run db-upgrade` (pass).
- `pdm run docs-validate` (pass before final handoff compaction; rerun after final docs edits).
- `pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py
  tests/unit/web/test_profile_app_continuation_api.py` (pass; 11 tests).
- `pdm run pr-0262-real-lifecycle --huleedu-artifact
  /Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json
  --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod` (pass).
- Manifest inspection: upstream status `ok`, browser callback final path `/editor`, local role
  `contributor`, and all redaction booleans pass; raw proof email/subject/CSRF/context markers
  were absent from the retained manifest.
- `pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py
  tests/unit/web/test_huleedu_identity_context_probe_api.py
  tests/unit/web/test_profile_app_continuation_api.py
  tests/unit/web/test_profile_app_continuation_context_api.py` (pass; 38 tests).
- `pdm run pr-0261-auth-action-matrix` (pass after free-port helper update).
- `pdm run typecheck` (pass).
## How to Run
```bash
pdm run docs-validate
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run pr-0261-auth-action-matrix
pdm run pr-0262-real-lifecycle --huleedu-artifact /Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod
pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py tests/unit/web/test_huleedu_identity_context_probe_api.py tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_context_api.py
```
## Known Issues / Risks
- `PR-0254` still owns the final Docker/operator cross-app proof; run it through the HuleEdu
  `TASK-0325` local Gateway lane, not public production with loopback return origins.
- Do not reintroduce app-local browser auth, browser-to-Identity calls, raw signed-context echo
  routes, or retained token/session artifacts.
- The PR-0262 proof uses transient raw session subject/email from the HuleEdu artifact only to seed
  and verify local projection; retained Skriptoteket artifacts must stay sanitized.
## Next Steps
- Finish final close-out gates for these local changes: `pdm run fe-type-check`, `pdm run fe-lint`,
  `pdm run lint`, `pdm run docs-validate`, and `git diff --check`.
- Then execute `ST-28-04` / `PR-0254` as the final cross-app auth cutover proof.
- Follow with `ST-28-10` auth outcome observability for gateway/session, realm, lifecycle,
  projection, and local RBAC outcomes.
