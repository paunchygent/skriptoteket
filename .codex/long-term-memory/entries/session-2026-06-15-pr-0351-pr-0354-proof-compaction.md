# 2026-06-15 PR-0351 through PR-0354 proof compaction

- Archived from `.codex/handoff.md` to keep the live handoff under 200 lines
  while preserving recent transcript-proof details.
- `PR-0351` focused verification:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with 31 tests.
- `PR-0351` focused frontend:
  `pdm run fe-test -- --run src/api/sirConvertGateway/transcriptClient.spec.ts src/api/sirConvertGateway/transcriptProgressParsers.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts`
  passed with 8 files / 44 tests.
- Shared frontend gates at that checkpoint:
  `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`.
- Local transcript live proof command:
  `pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --sir-convert-proof-lane hemma-remote-proof --sir-convert-gateway-backend-url http://host.docker.internal:28085 --sir-convert-producer-backend-url http://host.docker.internal:28085 --sir-convert-ready-url http://127.0.0.1:28085/readyz --gateway-signer-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --sir-convert-trusted-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --timeout-seconds 1200`.
- Retained transcript proof artifacts:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/proof-summary.json`,
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/backend-container.json`,
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/backend-live.log`,
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T030725Z/proof-summary.json`,
  `/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260614T191738Z/proof-summary.json`,
  `/home/paunchygent/apps/skriptoteket/.artifacts/pr-0352-native-proof-logs/20260614T191737Z/`,
  and `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T210105Z/proof-summary.json`.
- Deployment checkpoints archived from the live handoff:
  Sir Convert prod `159e82d5e674213ba58d5e2d959e8baba383dadb`,
  Skriptoteket prod `2fa27cfb85c8e64d9d0a9e9fb15c26091a09946e`,
  deploy log `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260614-191250.log`.
- `PR-0352` focused script verification:
  `pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py`
  passed with 20 tests after the red-first missing-module failure.
- `PR-0352` adjacent script bundle:
  `pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py`
  passed with 28 tests.
- `PR-0352` async formatter producer bundle:
  `pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py`
  passed with 18 tests.
- `PR-0352` static gates:
  `pdm run lint`, `pdm run typecheck`.
- `REV-PR-0352` approved after rerunning focused preflight, formatter, and Sir
  Convert recovery tests.
- `PR-0354` focused frontend:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts`
  passed with 5 files / 29 tests.
- `PR-0354` backend producer:
  `pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py`
  passed with 2 tests.
- `PR-0354` gates:
  `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`.
- `PR-0354` in-app browser proof used HuleEdu auth and the dev fixture
  `/apps/documents.conversion_hub/transcript/ui-fixtures/completed-export`.
  Retained artifacts: `.artifacts/pr-0354-transcript-ui-remediation/20260614T2104Z/`.
