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
summary: Authoritative unit files live on the server under `/etc/systemd/system/`.
  Use `sudo systemctl cat <unit>` to view the current source when troubleshooting.
---

## Overview

Authoritative unit files live on the server under `/etc/systemd/system/`. Use `sudo systemctl cat <unit>` to view the
current source when troubleshooting.

## Facts And Semantics

### Source: Sandbox Snapshot Cleanup (DB)

Unit files (hemma):

- `/etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.service`
- `/etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.timer`

```ini
### /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.service
[Unit]
Description=Skriptoteket sandbox snapshot cleanup
Requires=snap.docker.dockerd.service
After=snap.docker.dockerd.service

[Service]
Type=oneshot
ExecStart=/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-sandbox-snapshots
```

```ini
### /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.timer
[Unit]
Description=Run sandbox snapshot cleanup hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

### Source: Login Events Cleanup (DB)

Unit files (hemma):

- `/etc/systemd/system/skriptoteket-login-events-cleanup.service`
- `/etc/systemd/system/skriptoteket-login-events-cleanup.timer`

```ini
### /etc/systemd/system/skriptoteket-login-events-cleanup.service
[Unit]
Description=Skriptoteket login events cleanup
Requires=snap.docker.dockerd.service
After=snap.docker.dockerd.service

[Service]
Type=oneshot
ExecStart=/snap/bin/docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli cleanup-login-events
```

```ini
### /etc/systemd/system/skriptoteket-login-events-cleanup.timer
[Unit]
Description=Run login events cleanup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

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
