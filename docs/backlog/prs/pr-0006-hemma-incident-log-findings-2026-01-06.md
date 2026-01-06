---
type: pr
id: PR-0006
title: "Hemma incident log findings (2026-01-04 to 2026-01-06)"
status: ready
owners: "agents"
created: 2026-01-06
updated: 2026-01-06
stories: []
tags: ["devops", "incident", "ops"]
acceptance_criteria:
  - "Findings from incident logs between 2026-01-04 and 2026-01-06 are documented
     with timestamps and log references."
  - "New patterns vs prior incidents are called out (amdgpu-force-active I/O
     errors, AMD-Vi invalid device requests, MCE hardware errors)."
  - "Crash/reboot windows are summarized from journalctl list-boots output."
---

## Problem

Hemma continues to hard-crash with forced power cycles after the prior report.
We need a consolidated, time-stamped summary of incident log findings to guide
next steps.

## Goal

Document the incident log findings from 2026-01-04 through 2026-01-06, including
new patterns and crash windows, in a single PR record.

## Non-goals

- Root-cause resolution or configuration changes.
- New automation or monitoring changes.

## Findings (from /root/logs/incident-*.log)

### New or notable signals since the prior report

- **amdgpu-force-active sysfs write failures**
  - `/bin/sh: 1: echo: echo: I/O error` while starting
    `amdgpu-force-active.service` (force GPU active state).
  - Seen at boot times: 2026-01-04 20:20:07, 2026-01-05 00:32:06, 10:29:58,
    14:50:49, 2026-01-06 02:07:32, 06:27:45, 09:14:50.
  - Example logs:
    - `incident-20260104-202734.log`
    - `incident-20260105-003707.log`
    - `incident-20260105-103458.log`
    - `incident-20260105-145549.log`
    - `incident-20260106-021300.log`
    - `incident-20260106-063246.log`
    - `incident-20260106-091948.log`

- **AMD-Vi IOMMU invalid device requests**
  - `iommu ivhd0: AMD-Vi: Event logged [INVALID_DEVICE_REQUEST ...]` at boot.
  - Observed at 2026-01-05 00:32:05 and 10:29:56.
  - Example logs:
    - `incident-20260105-003707.log`
    - `incident-20260105-103458.log`

- **MCE hardware errors (new)**
  - `mce: [Hardware Error]: Machine check events logged` with CPU bank details.
  - Observed at 2026-01-06 06:27:44.
  - Example log:
    - `incident-20260106-063246.log`

### Continuing signals

- **amdgpu display-core timeouts**
  - `amdgpu: [drm] REG_WAIT timeout ... optc401_disable_crtc` persists across
    multiple boots (2026-01-05 00:32/10:29/13:16 and 2026-01-06 09:14).
  - Example logs:
    - `incident-20260105-003707.log`
    - `incident-20260105-103458.log`
    - `incident-20260105-132343.log`
    - `incident-20260105-131753.log`
    - `incident-20260106-091948.log`

- **Memory pressure / OOM**
  - 2026-01-04 20:56:44: `tailscaled` invoked OOM killer; large `sh` process
    (~30 GB RSS) killed; journald flushing under memory pressure.
  - Example logs:
    - `incident-20260104-205954.log`
    - `incident-20260104-210504.log`

- **Tailscale network/DNS instability**
  - DNS/control-plane failures and “network is unreachable” errors around
    2026-01-05 17:44–17:50.
  - Example log:
    - `incident-20260105-174533.log`

- **Capture anomaly**
  - `incident-20260105-065819.log` is 0 bytes and timestamped one second before
    reboot at 06:58:20, consistent with capture dying during the crash.

## Crash/reboot windows (UTC)

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

## Correlation analysis (crash end ↔ nearest incident logs)

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

## Implementation plan

1) Keep this PR as the consolidated source for the Jan 4–6 incident findings.
2) Use these findings to guide the next diagnostic or mitigation experiment.

## Test plan

- `pdm run docs-validate`

## Rollback plan

- Remove this PR doc and its index entry.

## Plan A: Align to AMD 24.04.3 HWE + ROCm 7.1.1 (recommended)

**Rationale (officially aligned stack):**

- AMD’s 25.30.1 release notes explicitly list the Ubuntu 24.04.3 HWE installer
  and mention preliminary 24.04.4 HWE support via the 24.04.3 HWE installer.
  ([AMD 25.30.1 release notes](https://www.amd.com/en/resources/support-articles/release-notes/RN-AMDGPU-UNIFIED-LINUX-25-30-1.html))
- AMD’s 25.10.1 release notes list Ubuntu 24.04.2 HWE installers (older than
  the host’s current 24.04.3 HWE). ([AMD 25.10.1 release notes](https://www.amd.com/en/resources/support-articles/release-notes/RN-AMDGPU-UNIFIED-LINUX-25-10-1.html))
- The R9700 driver page publishes the ROCm 7.1.1 Noble commands for Ubuntu
  24.04.3 HWE, matching the current host. ([R9700 drivers page](https://www.amd.com/en/support/downloads/drivers.html/graphics/radeon-ai-pro/radeon-ai-pro-r9000-series/amd-radeon-ai-pro-r9700.html))
- GPU firmware blobs are managed by Ubuntu’s `linux-firmware` package and should
  stay updated via Noble updates. ([Ubuntu `linux-firmware` package](https://www.ubuntuupdates.org/package/core/noble/main/updates/linux-firmware))

### Steps

1) **Inventory current stack (before changes)**
   - `uname -r`
   - `modinfo amdgpu | grep -E 'version|srcversion'`
   - `dpkg -l | rg -i 'amdgpu|rocm|mesa'`
   - `ls /lib/modules/$(uname -r)/updates/dkms/`

2) **Remove conflicting AMD DKMS/ROCm packages**
   - Use AMD’s uninstall path or apt purge for any installed DKMS + ROCm
     packages after confirming what is currently installed.

3) **Install AMD’s official Noble 24.04.3 HWE ROCm stack**

```bash
sudo apt update
wget https://repo.radeon.com/amdgpu-install/7.1.1/ubuntu/noble/amdgpu-install_7.1.1.70101-1_all.deb
sudo apt install ./amdgpu-install_7.1.1.70101-1_all.deb
sudo amdgpu-install -y --usecase=graphics,rocm
sudo usermod -a -G render,video $LOGNAME
sudo reboot
```

4) **Update firmware**

```bash
sudo apt update
sudo apt install --only-upgrade linux-firmware
```

5) **Verify after reboot**

```bash
uname -r
modinfo amdgpu | grep -E 'version|srcversion'
rocminfo 2>/dev/null | head
rocm-smi 2>/dev/null | head
dmesg | grep -iE 'amdgpu|firmware|iommu|mce|reg_wait' | tail -n 50
```
