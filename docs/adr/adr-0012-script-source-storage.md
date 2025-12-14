---
type: adr
id: ADR-0012
title: "Hybrid storage: Source/Logs in DB, Artifacts on Disk"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-14
---

## Context

Tools require admin-authored Python logic with versioning. We need to store:
1.  **Source Code:** Versioned, auditable, text-based.
2.  **Run Metadata:** Status, timestamps, actor.
3.  **Run Output (Text):** stdout, stderr, HTML result (critical for UI rendering).
4.  **Run Artifacts (Binary):** Generated files (PDFs, CSVs, images) which can be large.

## Decision

Adopt a **Hybrid Storage Strategy**:

1.  **PostgreSQL (Text & Metadata)**:
    *   `tool_versions.source_code`: The python script.
    *   `tool_runs`: Metadata + **stdout, stderr, html_output**.
    *   *Rationale:* Keeps the "result page" rendering fast and atomic without filesystem hits. These text blobs are typically small (<1MB).

2.  **Filesystem (Binary Artifacts)**:
    *   Path: `/var/lib/skriptoteket/artifacts/{run_id}/{filename}`
    *   Referenced by: `tool_runs.artifacts_manifest` (JSON in DB).
    *   *Rationale:* Prevents DB bloat from large generated files.
    *   **Input files:** Treated as artifacts. Default retention differs by context:
        - Sandbox: input files are retained (short retention) for debugging.
        - Production: input files are not retained by default (deleted after execution) to reduce sensitive-data storage.

## Consequences

*   **Performance:** UI renders run results in a single DB query.
*   **Backups:** DB backup contains all *logic* and *logs*, but not binary artifacts (artifacts require separate FS backup).
*   **Complexity:** Runner must split output: capture text streams to memory (for DB), write files to disk (for artifact storage).
*   **Operations:** Requires a retention policy/cleanup task to prevent disk fill from artifacts.
