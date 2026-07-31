---
type: task
id: TASK-SKRIPT-REP-0008-PART-02
title: Hemma incident log findings (2026-01-04 to 2026-01-06) — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: TASK-SKRIPT-REP-0008
part: 2
---

This forces cloud-init to load the autoinstall seed from `/dev/sdd1` (label
`CIDATA`) and enables SSH immediately.

### Source: Follow-up actions after the window (2026-01-07)

These changes were applied after the 2026-01-04 → 2026-01-06 incident window to
improve crash capture and reduce future ambiguity. They are not part of the
findings above.

- Crash capture hardening applied (sysctl panic-on-oops, `log_buf_len=4M`,
  kdump enabled, netconsole to `192.168.0.11:6666`); see
  `docs/runbooks/runbook-home-server.md`.
- AMDGPU hang mitigation flags enabled on hemma (`amdgpu.cwsr_enable=0`,
  `amdgpu.mcbp=0`, `amdgpu.runpm=0`); see
  `docs/reference/reports/ref-hemma-host-freeze-stack-alignment-2026-01-03.md`.
- Post-change baseline capture: `/root/logs/incident-20260107-191503.log`.

### Source: Plan A: Align to AMD 24.04.3 HWE + ROCm 7.1.1 (recommended)

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

### Plan Document Review

No separate plan document review was recorded in the source snapshot.

### Implementation Review

### Source: Findings (from /root/logs/incident-*.log)

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

## Impact And Escalation

The migrated source records no separate statement for this section.

## Decision And Assumption Ledger

The migrated source records no separate statement for this section.

## Plan

The migrated source records no separate statement for this section.

## Implementation Steps

The migrated source records no separate statement for this section.

## Proof

The migrated source records no separate statement for this section.

## Validation

The migrated source records no separate statement for this section.

## Stop Conditions

The migrated source records no separate statement for this section.

## Lessons Learned

The migrated source records no separate statement for this section.

## Notes

The migrated source records no separate statement for this section.

## Readiness

The migrated source records no separate statement for this section.

## Closeout

The migrated source records no separate statement for this section.
