# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history to `.codex/long-term-memory/entries/` first.
## Snapshot
- Date: 2026-06-14.
- Branch: `main` after merging `codex/skriptoteket-pr-0350-product-owned-transcript-replay-export`;
  the PR branch was fast-forwarded to `14f4b3af930b02f7b587b0b87c168418730fd28f`.
- Sir Convert `task-363` is complete, reviewed, deployed, and consumed by
  Skriptoteket. Producer contract revision:
  `4b09baa989d38f582573a810f045e50c676139a9`.
- Skriptoteket `PR-0350` is implemented, reviewed, merged, pushed, and deployed.
  It removes the browser-owned formatter replay saga and replaces it with
  product-owned `POST/GET /formatter-exports` state over saved transcripts.
- Production wiring fix `14f4b3af` makes Hemma use internal Sir Convert base
  `http://sir_convert_a_lot_prod:8085`; `https://convert.hule.education` is a
  reserved public edge and returned `421` during the first live proof attempt.
- Prior PR-0310 through PR-0342 history lives in
  `.codex/long-term-memory/entries/session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history.md`,
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0325-pr-0326-exam-converter-history.md`,
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0326-through-pr-0331-ai-facit-review-history.md`, and
  `.codex/long-term-memory/entries/session-2026-06-12-pr-0332-through-pr-0342-correction-transcript-history.md`.
## Status
- `REV-PR-0350` is approved:
  `docs/backlog/reviews/review-pr-0350-product-owned-transcript-replay-export-boundary.md`.
- `PR-0350` code replaced browser replay prepare/submit/poll/download/base64/
  complete with backend-owned Sir Convert replay submission, manifest/artifact
  verification, persisted product export state, and Swedish pending/running/
  succeeded/failed UI.
- Old browser saga clients/tests were deleted or rewritten. Browser traffic now
  calls Skriptoteket product endpoints only for formatter exports.
- `ST-21-08` and `PR-0349` are now closeout-ready from the transcript parity
  perspective; update durable docs before starting unrelated ST-21 work.
## Verification
- Feature commit: `ae70ddbdc6f7c586374b7d1bda59e95e454b4eff`.
- Merge commit: `6378fe3d2978eedd541eccd9471bc14ea8e19fd6`.
- Production URL fix: `14f4b3af930b02f7b587b0b87c168418730fd28f`.
- Hemma deploy passed for `6378fe3d`; first PR-0349 live proof then failed at
  product export because public `convert.hule.education` returned `421`.
- Hemma `.env` was corrected to
  `SIR_CONVERT_A_LOT_V2_BASE_URL=http://sir_convert_a_lot_prod:8085`.
- Hemma redeploy passed for `14f4b3af`; log:
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260614-030634.log`.
- Final live proof passed through HuleEdu browser-session ceremony:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T030725Z/proof-summary.json`.
- Final proof showed upload cancel feedback, running progress, durable transcript
  save, two speaker overlays, product export success with four artifacts,
  overlay labels present in TXT/MD/VTT/SRT downloads, fallback labels absent,
  and Mina filer save of `transkript-a35745cd.txt`.
- Sir Convert downstream-consumption docs were also committed and redeployed at
  `147479fdf92d5ec4c1891403c5986ef0a48d8292`; deploy verification passed with
  remote/service revision parity.
- Green local gates: focused backend pytest, focused Vitest, migration
  idempotency for `f4c8e2a6b9d1`, `pdm run db-upgrade`, `pdm run lint`,
  `pdm run typecheck`, `pdm run fe-type-check`, `pdm run fe-lint`,
  `pdm run fe-build`, `pdm run docs-validate`, `pdm run handoff-validate`,
  and `git diff --check`.
## How to Run
```bash
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run fe-test -- --run src/api/conversionHubTranscriptFormatterExports.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts
pdm run fe-gen-api-types
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
pdm run hemma-deploy
pdm run hemma-deploy-monitor -- /home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-YYYYMMDD-HHMMSS.log
set -euo pipefail
CREDS_JSON="$(cd /Users/olofs_mba/Documents/Repos/huleedu && pdm run run-local-pdm run-hemma -- bash scripts/hemma/fetch_bootstrap_browser_credentials.sh)"
export PLAYWRIGHT_EMAIL="$(printf '%s' "$CREDS_JSON" | jq -r '.BOOTSTRAP_SUPERUSER_EMAIL')"
export PLAYWRIGHT_PASSWORD="$(printf '%s' "$CREDS_JSON" | jq -r '.BOOTSTRAP_SUPERUSER_PASSWORD')"
pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url https://skriptoteket.hule.education --dotenv .env.prod-smoke --timeout-seconds 1200
```
## Known Issues / Risks
- `.env.prod-smoke` credentials are stale; use the HuleEdu Hemma credential
  helper for live browser proof and do not print secret values.
- Production formatter export must not use `https://convert.hule.education` as
  server-side producer base; that public edge is reserved/fail-closed.
- Keep transcript formatter/export follow-ups product-owned: saved canonical
  `transcript_json`, saved overlays, accepted Sir Convert artifacts, no browser
  submit/poll/download/base64/complete saga.
## Next Steps
- No PR-0350/ST-21-08 closeout work remains after committing and redeploying
  this handoff/docs evidence. Continue with the next governed backlog item.
