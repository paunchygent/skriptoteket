---
type: reference
id: REF-hemma-host-freeze-stack-alignment-2026-01-03
title: "Follow-up: hemma host freeze stack alignment (Jan 2026)"
status: active
owners: "agents"
created: 2026-01-03
updated: 2026-01-03
topic: "devops"
links:
  - docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md
  - docs/reference/reports/ref-hemma-incident-log-2026-01-02-083355-083455.md
---

# Follow-up: hemma host freeze stack alignment (Jan 2026)

## Scope

This report consolidates the prior incident investigation and sanitized log capture with a concrete software/hardware
stack scan taken on 2026-01-03, then maps that stack to AMD/Ubuntu support matrices. It also records an ordered list
of remediation options from most likely to least likely to resolve the underlying host hangs.

## Inputs used

- `docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md`
- `docs/reference/reports/ref-hemma-incident-log-2026-01-02-083355-083455.md`
- On-host scan collected at **2026-01-03 12:08 UTC** (commands executed via SSH)

## Observed stack (2026-01-03 12:08 UTC)

- OS: Ubuntu 24.04.3 LTS (Noble Numbat)
- Kernel: 6.14.0-37-generic
- ROCm: 7.1.1 (`/opt/rocm/.info/version`)
- AMDGPU DKMS: 6.16.6 (from `amdgpu-install` 30.20.1.0)
- GPU PCI ID: `1002:7551` (rev c0), driver in use: `amdgpu`
- Headless status: all DP connectors report `disconnected`

## Support-matrix alignment summary

- Ubuntu 24.04.3 + ROCm 7.1.1 is listed as supported in AMD's Radeon/ROCm compatibility tables.
- AMDGPU 30.20.1 aligns with ROCm 7.1.x per the AMD kernel/user-space compatibility matrix.
- No explicit mismatch appears between the installed driver, ROCm version, and OS release.

Note: AMD marks Ubuntu 24.04.3 support as preliminary when using the 24.04.2 installer. That means the stack is
supported but may still contain early-release regressions.

## Driver source check (local DKMS)

The installed AMDGPU DKMS source under `/usr/src/amdgpu-6.16.6-2255209.24.04/amd/display/` already contains the
`optc401_disable_crtc` wait logic. This confirms the display-core wait patch is present, so the observed
`REG_WAIT timeout ... optc401_disable_crtc` log line indicates a timeout despite the guard, not a missing patch.

## Risk signals relevant to the hangs

- **Incident A** aligns with Wi-Fi churn and tailscale rebinding loops (see the sanitized incident log report).
- **Incident B** shows a silent last minute before logging stops, consistent with a kernel or driver wedge.
- The kernel log message `REG_WAIT timeout ... optc401_disable_crtc` points to a DCN (display core) stall path even
  on a headless host, which can still execute display-core code paths.
- Llama/ROCm workloads on RDNA4 (gfx1201/R9700) have active issue reports in public trackers and are not explicitly
  listed in AMD's llama.cpp compatibility tables for ROCm 7.1.1.

## Ordered remediation options (most likely to least likely to fix root cause)

1) **Disable HIP workloads temporarily**
   - Stop `llama-server` and `tabby` for 24-48h to isolate ROCm/HIP as the trigger.
   - If workload must remain, prefer llama.cpp Vulkan backend or reduce HIP-specific features.

2) **Move to a newer 6.14 HWE point release**
   - If 6.14.0-38/39 is available, take it to pick up amdgpu/DCN backports that did not land in 6.14.0-37.

3) **Align to a ROCm version explicitly supported by AMD for llama.cpp**
   - Consider ROCm 7.0.x or 6.4.x (per AMD's llama.cpp compatibility table) if the workload depends on HIP.

4) **Disable display core on a headless server**
   - Use kernel param `amdgpu.dc=0` to bypass DCN, as a targeted mitigation for `optc401_disable_crtc` timeouts.

5) **IOMMU mitigations (diagnostic only)**
   - Test `iommu=pt` or `amd_iommu=off` if `AMD-Vi INVALID_DEVICE_REQUEST` events continue and above steps fail.

6) **Hardware validation**
   - PSU, RAM, GPU seating, or PCIe slot checks only after the software/driver isolation steps.

## Suggested next evidence to collect

If another hang occurs, capture immediately after reboot:

- `journalctl --list-boots --no-pager | tail -10`
- `journalctl -b -1 --no-pager | tail -300`
- `journalctl -b -1 -k --no-pager | tail -300`

These should be saved under `/root/logs/incident-*.log` and referenced in a follow-up report.

## References

- Prior investigation summary: `docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md`
- Sanitized log window: `docs/reference/reports/ref-hemma-incident-log-2026-01-02-083355-083455.md`
