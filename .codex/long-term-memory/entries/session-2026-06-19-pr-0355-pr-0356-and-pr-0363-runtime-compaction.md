# Session Memory: PR-0355/PR-0356 Proof And PR-0363 Runtime Breadcrumb

Created: 2026-06-19

This entry preserves durable context compacted out of `.codex/handoff.md`.

## PR-0355

- `PR-0355` was completed, reviewed, pushed to `main`, and deployed at
  `fe56307c`.
- Scope: transcript cancel slot and rail remediation. It reserved the
  `Avbryt` row above `Starta transkribering`, removed the checkbox-like
  square icon, updated empty upload copy, and retained local remote-proof E2E
  evidence.
- Review:
  `docs/backlog/reviews/review-pr-0355-transcript-cancel-slot-rail-remediation.md`
  is approved.
- Focused checks included transcript rail/shell frontend tests,
  `pdm run fe-type-check`, and `pdm run docs-validate`.
- Live proof artifact:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json`.

## PR-0356

- `PR-0356` was completed, reviewed, pushed to `main`, and deployed at
  `fe56307c`.
- Scope: authenticated Exam Converter source-only intake and owned-format
  exports. The implementation removed early PDF/QTI target controls,
  removed `graded_result_pdf` from authenticated submit/retry requests, and
  preserved source `.dxe` state on invalid replacement attempts.
- Review:
  `docs/backlog/reviews/review-pr-0356-source-only-intake-export-owned-formats.md`
  is approved after the browser-proof and invalid-replacement follow-ups.
- Green frontend/request-context bundle passed with 7 files / 55 tests.
- Additional gates passed: `pdm run fe-type-check`, `pdm run fe-lint`, and
  `pdm run fe-build`.
- Authenticated fixture proof:
  `pdm run python -m scripts.playwright_pr_0356_source_only_fixture_proof --base-url http://127.0.0.1:5173 --dotenv .env`.
- Proof artifact:
  `.artifacts/playwright-pr-0356-source-only-fixture-proof/20260614T233419Z/manifest.redacted.json`.

## Hemma Deploy And Transcript Follow-Ups

- Hemma deploy for `fe56307c` passed from
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260615-154707.log`.
- Hemma deploy for `ddd2bcf1` passed from
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260615-163905.log`.
- Final native Hemma production transcript proof passed at:
  `/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260615T164255Z/proof-summary.json`.
- The proof retained `service-monitoring.json` plus service logs for
  Skriptoteket, HuleEdu, and Sir Convert.
- The real production blocker before the final pass was Sir Convert runtime
  availability: Gateway `/sir-convert` returned `502` until
  `sir_convert_a_lot_prod` was started and resolvable.

## PR-0363 Local Runtime Lesson

- Gateway-backed protected browser proof for Skriptoteket must use the Docker
  `skriptoteket_web` service attached to `hule-network` with alias
  `skriptoteket-web`.
- Host Uvicorn can answer host health checks but is the wrong runtime for this
  proof lane because HuleEdu Gateway resolves
  `API_GATEWAY_SKRIPTOTEKET_BACKEND_URL=http://skriptoteket-web:8000`.
- The local Docker Desktop issue encountered during PR-0363 proof was a stale
  Docker Desktop host-port proxy on `:8080` plus stale container/network state.
  Restarting Docker Desktop and recreating the affected HuleEdu services
  restored Gateway health.
