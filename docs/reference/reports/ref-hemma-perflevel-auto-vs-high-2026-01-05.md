---
type: reference
id: REF-hemma-perflevel-auto-vs-high-2026-01-05
title: "GPU perflevel auto vs high (runpm=0) snapshot (hemma, 2026-01-05)"
status: active
owners: "agents"
created: 2026-01-05
updated: 2026-01-05
topic: "devops"
links:
  - docs/reference/reports/ref-hemma-runpm0-before-after-2026-01-05.md
  - docs/runbooks/runbook-gpu-ai-workloads.md
---

This note captures a quick A/B of **perflevel high vs auto** on hemma after enabling
`amdgpu.runpm=0`. The goal was to see how DPM constraints affect idle power state
reporting and clocks.

## Context

- `amdgpu.runpm=0` is active (runtime PM disabled).
- `rocm-perf.service` sets profile **COMPUTE** and perflevel **high** at boot.

## Snapshot comparison (idle)

| Metric | perflevel high | perflevel auto |
| --- | --- | --- |
| rocm-smi perflevel | high | auto |
| power_dpm_force_performance_level | high | auto |
| GPU use | 0% | 0% |
| VRAM allocated | 85% | 85% |
| SCLK | 0 MHz | 0 MHz |
| FCLK | 2400 MHz | 582 MHz |
| MCLK | 1124 MHz | 96 MHz |
| SOCCLK | 1371 MHz | 417 MHz |
| PPT (rocm-smi) | 43 W | 10 W |
| Low-power warning | yes | yes |
| amdgpu_pm_info MCLK | 1124 MHz | 96 MHz |
| amdgpu_pm_info SCLK | 0 MHz | 0 MHz |

## Observations

- perflevel **auto** substantially reduces memory/SoC clocks and idle power, but the
  low-power warning persists and SCLK remains parked at 0 MHz.
- perflevel **high** keeps higher clocks and ~4x the idle power draw in this snapshot,
  without changing the low-power warning.

## State after test

- perflevel reverted to **high** (to match `rocm-perf.service`).
