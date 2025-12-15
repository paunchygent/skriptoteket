# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).

## Snapshot

- Date: 2025-12-15
- Branch / commit: `main` (HEAD `c448ee8`, dirty working tree)
- Goal of the session: Implement ST-04-02 Docker runner execution end-to-end (protocol + infra + config + DI + tests + docs).

## What changed

- Runner protocol boundary + execution models:
  - `src/skriptoteket/protocols/runner.py`
  - `src/skriptoteket/domain/scripting/execution.py`
- Runner image + contract implementation:
  - `Dockerfile.runner` (venv built in builder stage; runtime runs `python` directly as non-root)
  - `runner/_runner.py` (writes `/work/result.json` + artifacts under `/work/output/`)
- Docker SDK runner + artifacts:
  - `src/skriptoteket/infrastructure/runner/docker_runner.py` (read-only rootfs, per-run `/work` volume, `/tmp` tmpfs, archive seed/extract)
  - `src/skriptoteket/infrastructure/runner/artifact_manager.py`, `path_safety.py`, `result_contract.py`, `retention.py`
- Application use-case boundary:
  - `src/skriptoteket/application/scripting/handlers/execute_tool_version.py` (+ protocol in `src/skriptoteket/protocols/scripting.py`)
- Config/DI wiring:
  - `src/skriptoteket/config.py`, `src/skriptoteket/di.py`
- Compose + ops:
  - `compose.dev.yaml` (dev docker.sock mount + local artifacts)
  - `compose.runner.yaml` (production/homeserver opt-in docker.sock mount)
  - `src/skriptoteket/cli/main.py` (adds `pdm run artifacts-prune`)
- Docs updates:
  - `docs/backlog/stories/story-04-02-docker-runner-execution.md` (now documents `/work` volume note)
  - `docs/adr/adr-0013-execution-ephemeral-docker.md` (adds note: archive APIs + tmpfs limitation)
  - `docs/reference/ref-scripting-api-contracts.md` (adds `SERVICE_UNAVAILABLE` mapping)

## Decisions (and links)

- Testing approach: Option A (unit tests + manual smoke run).
- Runner deps policy: parity with app runtime deps; no dynamic installs (changes = PR + rebuild/redeploy).
- Backpressure semantics: `ErrorCode.SERVICE_UNAVAILABLE` maps to HTTP 503 (“Runner is at capacity; retry.”).
- docker.sock mount:
  - Dev: allowed via `compose.dev.yaml`
  - Production/homeserver: opt-in via `compose.runner.yaml`
- Filesystem decision: keep `read_only=True`; `/work` uses a per-run Docker volume (rw), `/tmp` is tmpfs.
  - Rationale: `get_archive`/`docker cp` is unreliable for `tmpfs` mounts on some engines.
- Retention default: `ARTIFACTS_RETENTION_DAYS=7` + cron-friendly prune command.

## How to run / verify

- Build runner image (ran): `docker build -f Dockerfile.runner -t skriptoteket-runner:latest .`
- Quality (ran): `pdm run docs-validate && pdm run test`
- Manual runner smoke (ran):
  - Ran a small local harness that instantiates `DockerToolRunner` and executes a draft `ToolVersion` in SANDBOX.
  - Observed `status=succeeded`, `html_output` returned, and artifact `output/hello.txt` persisted under the artifacts root.

## Known issues / risks

- `/work` per-run volume does not have a portable per-run size cap (unlike tmpfs); a buggy/malicious script can fill disk.
- docker.sock mount expands blast radius if the app container is compromised (keep production opt-in and hardened).

## Next steps (recommended order)

1. Mark ST-04-02 as done once merged/committed and runner image build is in deployment pipeline.
2. Implement ST-04-03 admin editor UI + sandbox execution.
3. Consider adding artifact size caps (max bytes per file/total) and/or operational disk quotas.

## Notes

- Do not include secrets/tokens in this file.
