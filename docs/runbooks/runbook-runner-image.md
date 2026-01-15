---
type: runbook
id: RUN-runner-image
title: "Runbook: Runner image build + contract smoke test"
status: active
owners: "agents"
created: 2025-12-24
system: "skriptoteket-runner"
links: ["ADR-0013", "ADR-0015", "REF-ai-script-generation-kb", "REF-tool-editor-framework-codemap"]
---

## When to use this runbook

Use this runbook when you need to:
- Rebuild or deploy a new `skriptoteket-runner` image (new libs, security updates, contract changes).
- Debug tool runs that fail due to runner contract drift.
- Validate app → runner contract changes (e.g. `SKRIPTOTEKET_INPUT_DIR` + `SKRIPTOTEKET_INPUT_MANIFEST`,
  `SKRIPTOTEKET_MEMORY_PATH` / `/work/memory.json`).

## Prerequisites

- Docker daemon access on the target host.
- The web app has access to `/var/run/docker.sock` (required to start runner containers).
- `RUNNER_IMAGE` is set to the intended tag (default: `skriptoteket-runner:latest`).

Reference: `docs/reference/ref-ai-script-generation-kb.md`.

## Procedures

### 1) Build the runner image (local)

```bash
# Build runner image
docker build -f Dockerfile.runner -t skriptoteket-runner:latest .
```

### 2) Build the runner image (home server / production)

The runner is built but not run as a long-lived service. The web app starts runner containers dynamically.

```bash
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml --profile build-only build runner"
```

### 3) Smoke test the contract (local dev)

1. Run quality gate:
```bash
pdm run precommit-run
```

2. If verifying memory injection end-to-end:
   - Ensure the backend and SPA are running (`pdm run dev` + `pdm run fe-dev`).
   - Save tool settings in the Tool Run view (⚙ Settings), then run the tool.
   - In the tool script, read `SKRIPTOTEKET_MEMORY_PATH` and access `memory["settings"]` (see `docs/reference/ref-ai-script-generation-kb.md`).

3. If verifying multi-file input end-to-end:
   - Upload **multiple** files in the Tool Run view.
   - In the tool script, discover inputs via `SKRIPTOTEKET_INPUT_MANIFEST` and/or list files under
     `SKRIPTOTEKET_INPUT_DIR` (see `docs/reference/ref-ai-script-generation-kb.md`).

## Troubleshooting

### Tool runs fail to start runner containers

- Verify web container has Docker socket mounted:
  - Dev compose: `compose.dev.yaml`
  - Prod compose: `compose.prod.yaml`
- Verify `RUNNER_IMAGE` points to an image that exists on the Docker host.

### Settings are not applied in the runner

- Confirm `SKRIPTOTEKET_MEMORY_PATH` is present in the runner environment (see `docs/reference/ref-ai-script-generation-kb.md`).
- Ensure the tool script reads `memory.json` (scripts do not receive settings via function args).
