---
type: reference
id: REF-SKRIPT-GENERAL-reference-home-server-cleanup-timers
title: 'Reference: Home Server Cleanup Timers'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
  - REF-home-server-cleanup-timers
summary: The tracked installer owns the two current Skriptoteket cleanup timer pairs.
---

## Overview

The repository sources below are the durable definition of Skriptoteket cleanup
units. For the deployed bytes while troubleshooting, inspect the installed unit
with `sudo systemctl cat <unit>`.

## Facts And Semantics

### Tracked Sources And Installation

The tracked wrapper is
`scripts/hemma_cleanup_if_running.sh`, installed as
`/usr/local/libexec/skriptoteket-cleanup-if-running`.

The four tracked unit sources and their installed destinations are:

- `systemd/skriptoteket-session-files-cleanup.service` ->
  `/etc/systemd/system/skriptoteket-session-files-cleanup.service`
- `systemd/skriptoteket-session-files-cleanup.timer` ->
  `/etc/systemd/system/skriptoteket-session-files-cleanup.timer`
- `systemd/skriptoteket-sandbox-snapshots-cleanup.service` ->
  `/etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.service`
- `systemd/skriptoteket-sandbox-snapshots-cleanup.timer` ->
  `/etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.timer`

From the repository root, install or update only the wrapper and these four
destinations with:

```bash
sudo bash scripts/install_hemma_cleanup_units.sh
```

The installer runs `systemctl daemon-reload` and preserves the enabled/disabled
and active/inactive state of both timers. It does not enable or start a timer.

### Current Hourly Cleanup Pairs

The session-files pair runs `cleanup-session-files` through the wrapper:

- `skriptoteket-session-files-cleanup.service`
- `skriptoteket-session-files-cleanup.timer`

The sandbox-snapshots pair runs `cleanup-sandbox-snapshots` through the wrapper:

- `skriptoteket-sandbox-snapshots-cleanup.service`
- `skriptoteket-sandbox-snapshots-cleanup.timer`

Both timers use the hourly schedule. The retained 2026-08-28 baseline recorded
both as enabled and active before this update; inspect current state rather than
treating that baseline as live status.

### Journal Interpretation

The wrapper gives the service and journal one of three truthful outcomes:

- When `skriptoteket-web` is running, it invokes the selected cleanup command
  unchanged. Cleanup success is a successful service run; any cleanup-command
  failure remains non-zero with its diagnostic visible.
- When the exact container query proves the application is absent or stopped,
  the service succeeds intentionally and records
  `Cleanup skipped: state=absent` or `Cleanup skipped: state=stopped`.
- Docker access, container-state inspection, or cleanup failure is a real
  non-zero service failure. Read its original diagnostic with `journalctl`.

### Source: Host Log Cleanup (Incident + SMART)

Unit files (hemma):

- `/etc/systemd/system/cleanup-smart-logs.service`
- `/etc/systemd/system/cleanup-smart-logs.timer`

View with:

```bash
ssh hemma "sudo systemctl cat cleanup-smart-logs.timer"
ssh hemma "sudo systemctl cat cleanup-smart-logs.service"
```

## Decisions And Interpretation

The source contains no separate decision ledger; interpretation remains bounded by the recorded source material.
