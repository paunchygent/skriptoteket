---
type: task
id: TASK-SKRIPT-REP-0008-PART-01
title: Hemma incident log findings (2026-01-04 to 2026-01-06) — part 01
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: TASK-SKRIPT-REP-0008
part: 1
---

## Context

### Context

### Source: Source introduction

> Update (2026-01-13): Hemma now runs llama.cpp via Docker using `llama-server-rocm.service` (container
> `llama-server-rocm`). References to `llama-server-hip.service` / `llama-server-vulkan.service` in this PR are
> historical and should not be treated as current run instructions.

### Source: Problem

Hemma continues to hard-crash with forced power cycles after the prior report.
We need a consolidated, time-stamped summary of incident log findings to guide
next steps.

### Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

### Story Contract Slice

### Source: Goal

Document the incident log findings from 2026-01-04 through 2026-01-06, including
new patterns and crash windows, in a single PR record.

### Contract Inputs

### Source: Supporting reference

- `docs/reference/ref-hemma-critical-paths-2026-01-06.md` (critical paths,
  firewall, SSH, tailscale, app locations, and package inventory sources).

### Plan

### Source: Implementation plan

1) Keep this PR as the consolidated source for the Jan 4–6 incident findings.
2) Use these findings to guide the next diagnostic or mitigation experiment.

### Implementation Steps

The source records no separate implementation steps.

### Proof

### Source: Test plan

- `pdm run docs-validate`

### Validation

Validation follows the focused test and verification material recorded above.

### Stop Conditions

### Source: Non-goals

- Root-cause resolution or configuration changes.
- New automation or monitoring changes.

### Source: Rollback plan

- Remove this PR doc and its index entry.

### Lessons Learned

No separate lessons learned were recorded in the source snapshot.

### Notes

### Source: Crash/reboot windows (UTC)

Derived from `journalctl --list-boots` sections in the captured logs:

- 2026-01-04 15:57:36 → 2026-01-04 17:23:52
- 2026-01-04 17:42:32 → 2026-01-05 00:31:28
- 2026-01-05 00:32:05 → 2026-01-05 06:58:20
- 2026-01-05 10:29:56 → 2026-01-05 14:03:17
- 2026-01-05 14:33:08 → 2026-01-05 14:35:40 (short boot)
- 2026-01-05 14:50:47 → 2026-01-06 01:29:38
- 2026-01-06 02:07:30 → 2026-01-06 06:26:57
- 2026-01-06 06:27:44 → 2026-01-06 09:03:33
- 2026-01-06 09:14:48 → 2026-01-06 09:30:48 (short boot)

### Source: Correlation analysis (crash end ↔ nearest incident logs)

**Method:** For each crash end timestamp, identify the closest capture before
and after the crash by filename time. Then check each log for notable signals
and verify whether the log content is time-adjacent to the crash or primarily
boot-time output.

### 2026-01-04 17:23:52 crash

- **Last capture before crash:** `incident-20260104-153900-154030.log`
  (lag 1h44m). This capture is stale relative to the crash and does not contain
  notable signals.
- **First capture after crash:** `incident-20260104-180334.log`
  (lag 39m). No notable signals found in this capture.
- **Correlation strength:** weak (no near-crash coverage).

### 2026-01-05 00:31:28 crash

- **Last capture before crash:** `incident-20260105-002707.log`
  (lag 4m21s). Contains no notable signals.
- **First capture after crash:** `incident-20260105-003707.log`
  (lag 5m39s). Boot-time signals immediately after the crash:
  - 2026-01-05 00:32:05: `amdgpu [drm] REG_WAIT timeout ... optc401_disable_crtc`.
  - 2026-01-05 00:32:05: `AMD-Vi INVALID_DEVICE_REQUEST`.
  - 2026-01-05 00:32:06: `amdgpu-force-active` sysfs write I/O error.
  - 2026-01-05 00:32:06: `amdgpu-force-active.service` failed.
  - 2026-01-05 00:32:06–00:32:18: repeated `tailscaled` bootstrapDNS failures
    and `LinkChange: major, rebinding`.
  - 2026-01-05 00:32:05: `wlp5s0` interface rename (ath9k).
- **Same boot (earlier signal):** 2026-01-04 20:56:44 OOM kill captured in
  `incident-20260104-205954.log` (about 3h35m before the crash), including
  `tailscaled invoked oom-killer` and heavy memory pressure.
- **Correlation strength:** moderate (OOM within boot; strong post-crash boot
  errors).

### 2026-01-05 06:58:20 crash

- **Last capture before crash:** `incident-20260105-065819.log`
  (lag 1s, **empty file**).
- **First capture after crash:** `incident-20260105-103458.log`
  (lag 3h36m). Boot-time signals when the host came back:
  - 2026-01-05 10:29:56: `AMD-Vi INVALID_DEVICE_REQUEST`.
  - 2026-01-05 10:29:57: `amdgpu [drm] REG_WAIT timeout ... optc401_disable_crtc`.
  - 2026-01-05 10:29:58: `amdgpu-force-active` sysfs write I/O error.
  - 2026-01-05 10:29:58: `amdgpu-force-active.service` failed.
  - 2026-01-05 10:29:58–10:30:10: repeated `tailscaled` bootstrapDNS failures
    and `LinkChange: major, rebinding`.
  - 2026-01-05 10:29:57: `wlp5s0` interface rename (ath9k).
- **Correlation strength:** moderate (empty pre-crash capture; strong boot-time
  errors after recovery).

### 2026-01-05 14:03:17 crash

- **Last capture before crash:** `incident-20260105-140203.log`
  (lag 1m14s). No notable signals.
- **First capture after crash:** `incident-20260105-145549.log`
  (lag 52m32s). Boot-time signals:
  - 2026-01-05 14:50:49: `amdgpu-force-active` sysfs write I/O error.
  - 2026-01-05 14:50:49: `amdgpu-force-active.service` failed.
  - 2026-01-05 14:50:49–14:51:07: repeated `tailscaled` bootstrapDNS failures
    and `LinkChange: major, rebinding`.
  - 2026-01-05 14:50:48: `wlp5s0` interface rename (ath9k).
- **Correlation strength:** moderate (no near-crash signals; boot-time errors
  persist).

### 2026-01-05 14:35:40 crash (short boot)

- **Last capture before crash:** `incident-20260105-140203.log`
  (lag 33m37s). No notable signals.
- **First capture after crash:** `incident-20260105-145549.log`
  (lag 20m09s). Same boot-time errors as above (amdgpu-force-active I/O error,
  tailscaled bootstrapDNS failures, `wlp5s0`).
- **Correlation strength:** weak-to-moderate (short boot; no near-crash data).

### 2026-01-06 01:29:38 crash

- **Last capture before crash:** `incident-20260106-012620.log`
  (lag 3m18s). No notable signals.
- **First capture after crash:** `incident-20260106-021300.log`
  (lag 43m22s). Boot-time signals:
  - 2026-01-06 02:07:32: `amdgpu-force-active` sysfs write I/O error.
  - 2026-01-06 02:07:32: `amdgpu-force-active.service` failed.
  - 2026-01-06 02:07:34–02:07:40: repeated `tailscaled` bootstrapDNS failures
    and `LinkChange: major, rebinding`.
  - 2026-01-06 02:07:31: `wlp5s0` interface rename (ath9k).
- **Correlation strength:** moderate (boot-time errors persist).

### 2026-01-06 06:26:57 crash

- **Last capture before crash:** `incident-20260106-062318.log`
  (lag 3m39s). No notable signals.
- **First capture after crash:** `incident-20260106-063246.log`
  (lag 5m49s). Boot-time signals:
  - 2026-01-06 06:27:44: **MCE hardware errors** (`Machine check events logged`)
    with CPU bank details.
  - 2026-01-06 06:27:45: `amdgpu-force-active` sysfs write I/O error.
  - 2026-01-06 06:27:45: `amdgpu-force-active.service` failed.
  - 2026-01-06 06:27:46–06:27:53: repeated `tailscaled` bootstrapDNS failures
    and `LinkChange: major, rebinding`.
  - 2026-01-06 06:27:45: `wlp5s0` interface rename (ath9k).
- **Correlation strength:** strong (MCE errors immediately after crash).

### 2026-01-06 09:03:33 crash

- **Last capture before crash:** `incident-20260106-090000.log`
  (lag 3m33s). No notable signals.
- **First capture after crash:** `incident-20260106-091948.log`
  (lag 16m15s). Boot-time signals:
  - 2026-01-06 09:14:49: `amdgpu [drm] REG_WAIT timeout ... optc401_disable_crtc`.
  - 2026-01-06 09:14:50: `amdgpu-force-active` sysfs write I/O error.
  - 2026-01-06 09:14:50: `amdgpu-force-active.service` failed.
  - 2026-01-06 09:14:52–09:14:58: repeated `tailscaled` bootstrapDNS failures
    and `LinkChange: major, rebinding`.
  - 2026-01-06 09:14:49: `wlp5s0` interface rename (ath9k).
- **Correlation strength:** moderate (boot-time errors persist).

### 2026-01-06 09:30:48 crash (short boot)

- **Last capture before crash:** `incident-20260106-093048.log`
  (lag 0s). No notable signals within this capture.
- **First capture after crash:** none (same capture file).
- **Correlation strength:** weak (no signals in capture).

### Coverage gaps and limits

- Several near-crash captures contain only system state/hwmon sections and
  no log errors, so most signals come from **post-crash boot logs** rather than
  final-minute pre-crash output.
- The 2026-01-05 06:58 crash has an empty capture file 1s prior to reboot,
  indicating the capture process itself may fail during the hang.

### Post-reboot check (2026-01-06 10:38 UTC)

Reviewed the latest post-reboot captures (e.g. `incident-20260106-104321.log`)
after disabling `amdgpu-force-active.service`, `rocm-perf.service`, and removing
`amdgpu.runpm=0` from GRUB.

- **Persisting:** `amdgpu [drm] REG_WAIT timeout ... optc401_disable_crtc` at
  2026-01-06 10:38:01.
- **Not observed in 10:xx logs:** `amdgpu-force-active` I/O error, AMD-Vi
  `INVALID_DEVICE_REQUEST`, MCE hardware errors, or OOM killer events.

### Post-firmware reboot check (2026-01-06 11:10 UTC)

After upgrading `linux-firmware` and rebooting, verified kernel/module stack
and boot logs.

- **Platform:** Ubuntu 24.04.3 LTS (Noble), kernel `6.14.0-37-generic`.
- **Driver:** `amdgpu` DKMS module `6.16.6` loaded (kernel tainted by
  `amdkcl: module verification failed`).
- **ROCm:** `rocminfo` reports ROCk module 6.16.6; `rocm-smi` reports the GPU
  healthy (perf auto).
- **Persisting:** `amdgpu [drm] REG_WAIT timeout ... optc401_disable_crtc` at
  2026-01-06 11:10:54.
- **Persisting:** `amdgpu: SMU driver if version not matched` and `[drm] Cannot
  find any crtc or sizes` (headless display core).
- **Not observed:** `amdgpu-force-active` I/O errors, AMD-Vi
  `INVALID_DEVICE_REQUEST`, or MCE hardware errors (only
  `MCE: In-kernel MCE decoding enabled`).
- **Other boot notes:** `tsc: Fast TSC calibration failed` and normal IOMMU
  group initialization.

### Stack version mapping (AMDGPU 30.20.1 ↔ Radeon Software 25.30.1)

Installed package versions use the **30.20.1** numbering scheme even though the
release notes refer to **Radeon Software for Linux 25.30.1**. The host is
aligned to the 25.30.1/ROCm 7.1.1 bundle, but the Debian package versions and
repo paths are labeled differently:

- **Installed on host:** `amdgpu-install` `30.20.1.0.30200100-2255209.24.04`,
  `amdgpu-dkms` `1:6.16.6.30200100-2255209.24.04`, and the repos
  `https://repo.radeon.com/amdgpu/30.20.1/ubuntu` +
  `https://repo.radeon.com/graphics/7.1.1/ubuntu` +
  `https://repo.radeon.com/rocm/apt/7.1.1`.
- **Release notes label:** AMD’s release notes refer to **Radeon Software for
  Linux 25.30.1** (ROCm 7.1.1), which appears to correspond to the above
  **30.20.1** package line. Treat this as AMD’s internal packaging/version
  scheme rather than a mismatch in the installed stack.

### One-time 6.8 kernel boot attempt (2026-01-06 11:46 UTC)

Attempted a one-time boot into the GA kernel (`6.8.0-90-generic`) to approximate
the strict release-notes alignment without reimaging.

- **Booted kernel:** `6.8.0-90-generic` (GRUB one-time entry).
- **AMDGPU DKMS:** loaded (`6.16.6`), built for 6.8 via `dkms autoinstall`.
- **Failure:** `amdgpu: Fatal error during GPU init` and
  `amdgpu: probe of 0000:0b:00.0 failed with error -22`.
- **Impact:** `rocm-smi` showed no device in the concise GPU table.
- **Conclusion:** 6.8 kernel is not viable for the AI PRO R9700 with the
  current AMD DKMS stack; revert to the HWE kernel for GPU availability.

### Return to HWE kernel (2026-01-06 11:52 UTC)

Rebooted back to the default HWE kernel after the 6.8 failure.

- **Booted kernel:** `6.14.0-37-generic`.
- **ROCm/AMDGPU:** DKMS `6.16.6` loaded; `rocm-smi` shows the GPU.
- **Persisting boot messages:** `SMU driver if version not matched` and headless
  `[drm] Cannot find any crtc or sizes`.

### Source: GPU stability progress (current session)

### Decisions and actions taken

- **Strict release-notes alignment target:** Ubuntu **24.04.2** is the only OS
  listed without the “AMD Radeon series graphics products only” limitation for
  the AI PRO R9700. That makes a **24.04.2 reimage** the strictest alignment.
- **Pin/hold attempt (no reimage):** tried booting the GA kernel (6.8.0-90) with
  AMD DKMS. **Result:** GPU init failed (`amdgpu: Fatal error ... error -22`),
  so the GA kernel is **not viable** for this GPU stack.
- **Outcome:** revert to HWE kernel and proceed with reimage plan.

### Backup + reinstall preparation

- **Storage decision:** system SSDs are LVM‑spanned; do not split. Use HDD for
  backup + seed.
- **HDD repurpose:** wiped `/dev/sdd`, created two partitions:
  - `/dev/sdd1` FAT32 **CIDATA** (2GiB) mounted at `/mnt/seed` for autoinstall
    seed.
  - `/dev/sdd2` ext4 **BACKUP** mounted at `/mnt/backup`.
- **Autoinstall seed:** `/mnt/seed/user-data` + `/mnt/seed/meta-data` created
  with **all authorized SSH keys** (root + paunchygent) to ensure SSH access
  during install.
- **Full snapshot:** `/mnt/backup/hemma-root-20260106/` (~110G). Includes
  `dpkg-selections.txt`, `unit-files.txt`, `authorized_keys.txt`.
- **HWE holds:** `linux-generic-hwe-24.04`, `linux-image-generic-hwe-24.04`,
  `linux-headers-generic-hwe-24.04` are held to avoid drift while reimage is
  prepared.
- **SSH access without Tailscale:** UFW now allows `22/tcp` from Anywhere
  (IPv4 + IPv6) so SSH access does not depend on Tailscale during reimage.
- **Services paused:** All Docker containers (app + observability) stopped and
  left down until the reimage is complete.
- **Install USB prepared:** Ubuntu 24.04.2 live-server ISO written to
  `/dev/sde` (label: `Ubuntu-Server 24.04.2 LTS amd64`).

### Current plan (strict alignment)

1) **Reimage to Ubuntu 24.04.2 LTS** (headless autoinstall).
2) **Install AMD 25.30.1 + ROCm 7.1.1** using AMD’s Noble installer commands.
3) **Verify** GPU health and boot logs (amdgpu/IOMMU/MCE/reg_wait).
4) **Restore** configs + services from the backup snapshot.

### Restore progress (2026-01-06 to 2026-01-07, ongoing)

- **Reimage complete:** Ubuntu 24.04.2 LTS installed, kernel `6.8.0-90-generic`,
  hostname `paunchygentserver`.
- **Backup/seed mounted:** `/mnt/seed` (CIDATA) + `/mnt/backup` (BACKUP) restored
  configs, scripts, and repo state from `/mnt/backup/hemma-root-20260106/`.
- **SSH/Tailscale:** Tailscale state restored; MagicDNS access works. UFW now
  allows `22/tcp` only on `tailscale0` (no public/LAN SSH).
- **System services:** Restored systemd units + enabled timers
  (`ssh-watchdog`, `heartbeat-log`, `skriptoteket-incident-capture`,
  cleanup timers, `amdgpu-release-watch`).
- **Docker + core stacks:** Docker (snap) installed; infrastructure stack
  (nginx-proxy, acme-companion, shared-postgres) running; observability stack
  up (grafana/prometheus/jaeger/loki/promtail healthy).
- **ROCm install:** completed (installer rerun after hang + reboot). DKMS
  `amdgpu` version `6.16.6` loaded; `/opt/rocm/.info/version` reports `7.1.1`.
  `rocm-smi` + `rocminfo` both work after adding `paunchygent` to `render`.
- **Crash logs:** enabled pstore backend (`efi_pstore`) via
  `/etc/modules-load.d/pstore.conf`; `systemd-pstore` enabled (pstore mount
  present, currently empty).
- **Hostname + cron cleanup:** set hostname to `paunchygent-server` and
  defined `EXTRA_OPTS=` for `cron` to silence boot warnings.
- **llama.cpp (HIP default):** `llama-server-hip.service` enabled on boot with
  `Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf`; `llama-server-vulkan.service`
  disabled.
- **Public HTTPS restored:** router port forwarding for `80/443` updated to
  `192.168.0.9`; certs restored from backup snapshot to the nginx-proxy cert
  volume; nginx-proxy restarted; `https://skriptoteket.hule.education/healthz`
  reachable (acme-companion restarted to resume renewals).
- **Shared Postgres restored:** postgres data volume restored from backup
  snapshot; bootstrap user present; login verified from server.
- **Remaining:** confirm UI login from a browser, validate runner/tool execution,
  and re-check observability endpoints from outside the LAN.

### Autoinstall boot instructions (headless)

1) Boot the **Ubuntu 24.04.2 Server ISO** via USB or console.
2) At GRUB, press `e` and append one of:

```
autoinstall ds=nocloud
```

or (explicit seed device):

```
autoinstall ds=nocloud;s=/dev/disk/by-label/CIDATA/
```
