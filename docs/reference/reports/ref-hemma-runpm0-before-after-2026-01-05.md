---
type: reference
id: REF-hemma-runpm0-before-after-2026-01-05
title: "runpm=0 before/after snapshot (hemma, 2026-01-05)"
status: active
owners: "agents"
created: 2026-01-05
updated: 2026-01-05
topic: "devops"
links:
  - docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md
  - docs/reference/reports/ref-hemma-host-freeze-stack-alignment-2026-01-03.md
---

This note compares the incident capture snapshots **before** and **after** applying the kernel parameter
`amdgpu.runpm=0` on the hemma host.

## Source logs

- Pre-change: `/root/logs/incident-20260105-002707.log` (boot without `amdgpu.runpm=0`)
- Post-change: `/root/logs/incident-20260105-003707.log` (boot with `amdgpu.runpm=0`)

## Snapshot comparison (idle)

| Metric | Pre (no runpm=0) | Post (runpm=0) |
| --- | --- | --- |
| Kernel cmdline | (no `amdgpu.runpm=0`) | `amdgpu.runpm=0` present |
| runtime_status | `active` | `active` |
| GPU use | 0% | 0% |
| VRAM allocated | 85% | 85% |
| SCLK | 0 MHz | 0 MHz |
| MCLK | 1124 MHz | 1124 MHz |
| PCIe link | 8.0 GT/s x16 | 8.0 GT/s x16 |
| rocm-smi warning | low-power state | low-power state |
| GPU edge temp | 29°C | 29°C |
| GPU junction temp | 29°C | 30°C |
| GPU mem temp | 30°C | 34°C |
| PPT (capture summary) | 40 W | 39 W |
| PPT (rocm-smi) | 42 W | 40 W |

## Observations

- `amdgpu.runpm=0` is active post-change, but the **low-power warning persists** and the GPU remains in an
  idle/parked state (`SCLK 0 MHz`) with **high VRAM allocation**.
- No meaningful thermal or power shift is visible in these two idle snapshots.
