---
type: adr
id: ADR-0013
title: "Execute tool scripts via sibling runner containers (docker.sock + Docker SDK)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-14
---

## Context

The Skriptoteket application itself runs in a Docker container. It needs to spawn *ephemeral* containers to execute untrusted/admin-authored tool scripts safely.
Binding host paths (`-v /host/path:/container/path`) is unreliable because the app container does not know the host's filesystem layout.
Mounting `docker.sock` is powerful: if the app is compromised, an attacker may control containers on the host.

## Decision

**Sibling Container Model (Docker-outside-of-Docker):**

1.  **Socket Access:** The app container mounts `/var/run/docker.sock`.
2.  **I/O Strategy:**
    *   **Input:** App injects the script + input file via Docker Engine archive copy APIs (`put_archive`) into `/work` (a per-run Docker volume).
    *   **Execution:** Runner container executes with network isolation and resource limits.
    *   **Output:** App retrieves logs and artifacts via Docker Engine APIs (`container.logs()`, `get_archive`) and persists artifacts to disk.
    *   **Cleanup:** App explicitly removes the container and temporary volumes.
    *   **Filesystem:** Runner root filesystem is read-only; `/work` is a per-run volume (rw) and `/tmp` is a tmpfs mount.
        *   Note: some Docker engines do not support `get_archive`/`docker cp` for files stored on `tmpfs` mounts, so
            `/work` must be a volume to keep the archive-copy strategy.

**Security Constraints:**
*   Runner containers MUST NOT have access to the docker socket.
*   Runner containers MUST run as non-root user.
*   Runner containers MUST drop dangerous capabilities (`--cap-drop ALL`).
*   Runner containers SHOULD use `--security-opt no-new-privileges` and a strict `--pids-limit`.

## Repository Implementation Notes (Compose)

- The privileged `/var/run/docker.sock` mount is **opt-in** for production/homeserver deployments via
  `compose.runner.yaml` (keeps base `compose.yaml` unprivileged by default).
- For local development, `compose.dev.yaml` mounts `/var/run/docker.sock` to allow end-to-end runner testing.

## Consequences

*   **Deployment:** Requires `docker.sock` mount for the main app container.
*   **Implementation:** Use the Python Docker SDK (no Docker CLI required in the app container) for container lifecycle and file transfer.
*   **Robustness:** Works regardless of where the app container is hosted, as long as it has access to a Docker engine.
*   **Security:** The `docker.sock` mount expands blast radius; consider a dedicated runner service/host in the future and keep the app surface minimal and hardened.
