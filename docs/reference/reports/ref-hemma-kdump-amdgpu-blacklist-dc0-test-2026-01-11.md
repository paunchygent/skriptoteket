---
type: reference
id: REF-hemma-kdump-amdgpu-blacklist-dc0-test-2026-01-11
title: "Reference: hemma kdump AMDGPU blacklist + DC-off test (2026-01-11)"
status: active
owners: "agents"
created: 2026-01-11
topic: "devops"
---

## Overview

Stabilization steps after an AMDGPU display-path WARN panic:

- Prevent the crash kernel from loading AMDGPU (reduces kdump hang risk).
- Add a one-time GRUB entry to test `amdgpu.dc=0` without changing the default boot.

## Actions

- Kdump crash-kernel blacklist:
  - Set `KDUMP_CMDLINE_APPEND="... modprobe.blacklist=amdgpu"` in `/etc/default/kdump-tools`.
  - Reloaded kdump kernel: `sudo kdump-config unload && sudo kdump-config load`.
  - Verified with `sudo kdump-config show` (kexec cmdline includes `modprobe.blacklist=amdgpu`).
- GRUB test entry:
  - Added `Ubuntu (safe)` + `Ubuntu (dc=0 test)` entries in `/etc/grub.d/40_custom`.
  - Regenerated GRUB: `sudo update-grub`.
  - One-time test boot: `sudo grub-reboot "Ubuntu (dc=0 test)" && sudo reboot`.

## Evidence (2026-01-11)

- `/proc/cmdline` includes `amdgpu.dc=0` after the one-time boot.
- Host reachable via SSH; local display shows static after early boot (expected with DC disabled).

## Post-crash checklist (kdump + DC-off test)

Run these after the next crash/reboot to capture evidence quickly.

```bash
# Boot timeline + last boot log windows
ssh hemma "journalctl --list-boots | tail -n 10"
ssh hemma "journalctl -b -1 --no-pager | tail -n 300"
ssh hemma "journalctl -b -1 -k --no-pager | tail -n 300"

# Kdump artifacts
ssh hemma "ls -lah /var/crash | tail -n 20"
ssh hemma "sudo ls -lah /var/crash/$(date -u +%Y%m%d)* 2>/dev/null || true"
ssh hemma "sudo journalctl -b -1 -u kdump-tools-dump.service --no-pager"

# Crash kernel config sanity
ssh hemma "sudo kdump-config show | sed -n '1,120p'"

# pstore (if any)
ssh hemma "sudo ls -la /sys/fs/pstore"
ssh hemma "sudo ls -la /var/lib/systemd/pstore"

# Confirm DC-off (if still in effect)
ssh hemma "cat /proc/cmdline | rg amdgpu.dc=0"
```

## Recovery

- Normal reboot returns to the default boot entry (no `amdgpu.dc=0`).
- Explicit safe boot (one-time): `sudo grub-reboot "Ubuntu (safe)" && sudo reboot`.

## Related

- Runbook: `docs/runbooks/runbook-home-server.md` (Crash Capture Hardening + DC-off test).
- Prior context: `docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md`.
- Root-cause alignment notes: `docs/reference/reports/ref-hemma-host-freeze-stack-alignment-2026-01-03.md`.
