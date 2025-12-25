---
type: story
id: ST-12-06
title: "Session file cleanup policies and admin tooling"
status: ready
owners: "agents"
created: 2025-12-25
epic: "EPIC-12"
acceptance_criteria:
  - "Given session files older than 24 hours, when the cleanup job runs, then expired files are deleted."
  - "Given an admin wants to clear session storage, when they run the CLI command, then all session files are cleared."
  - "Given session storage usage, when an admin checks metrics, then Prometheus exposes session_files_total_bytes and session_files_count."
dependencies: ["ST-12-05"]
ui_impact: "No"
data_impact: "No"
---

## Context

Session file storage needs cleanup policies to prevent unbounded growth.

## Implementation plan

1) TTL-based cleanup

   - Track `last_accessed_at` per session directory
   - Cleanup job removes sessions not accessed in 24 hours

2) CLI tooling

   - `pdm run cleanup-session-files` - run cleanup manually
   - `pdm run clear-all-session-files` - admin tool to clear all (with confirmation)

3) Observability

   - Prometheus metrics: `skriptoteket_session_files_bytes_total`, `skriptoteket_session_files_count`
   - Log cleanup operations with session counts and bytes freed

4) Documentation

   - Add to runbook: session file storage location, cleanup schedule, manual intervention
