---
type: reference
id: REF-SKRIPT-GENERAL-compatibility-notes-amd-radeon-ai-pro-r9700-on-prime-x370-pro-hemma
title: 'Compatibility notes: AMD Radeon AI PRO R9700 on PRIME X370-PRO (hemma)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-hemma-gpu-compatibility-notes-2026-01-05
summary: 'Compatibility notes: AMD Radeon AI PRO R9700 on PRIME X370-PRO (hemma)'
---

## Overview

This note consolidates compatibility signals for the **AMD Radeon AI PRO R9700** on the **ASUS PRIME X370-PRO**
motherboard (hemma), plus adjacent external reports that may explain instability patterns.


From the 2026-01-03 inventory:

- Motherboard: **ASUS PRIME X370-PRO** (X370)
- BIOS: **AMI 3803 (2018-01-22)**
- CPU: **Ryzen 7 1700**
- GPU: **AMD Radeon AI PRO R9700** (`gfx1201`, PCI ID `1002:7551`)
  - Host link: **PCIe 3.0 x16** (8 GT/s, downgraded) via a PCIe switch
  - Resizable BAR capability present; **BAR0 = 256 MB** (no large BAR)

## Facts And Semantics

No separate facts and semantics is stated in the source.

### Source: Internal compatibility signals (known risks)


These are *not proven conflicts*, but they are higher-probability contributors:

1) **Very old BIOS/AGESA (2018)** on X370 can increase the risk of PCIe/IOMMU edge cases with a new-gen GPU.
2) **RDNA4 + ROCm 7.1.1 + llama.cpp HIP** has open instability reports for RDNA4 (`gfx1201`).
3) **Display-core timeout logs** (`optc401_disable_crtc`) point to a DCN stall path, even on headless hosts.
4) **PCIe downgrade** (4.0 card on a 3.0 platform) is normal but reduces headroom for PCIe/IOMMU quirks.

Source detail: see linked investigation and stack-alignment reports.

### Source: External signals (adjacent, not proof)


These do **not** describe PRIME X370-PRO + R9700 directly, but they show RDNA4 or amdgpu issues that can look
similar (GPU hangs at idle, suspend/resume wedges, power-state transitions):

- RDNA4 (GFX12) GPUs have documented **random GPU hangs** tied to HiZ/HiS, with driver workarounds landed in Mesa.
  - Reference: Phoronix summary of the RADV workaround (April 2025).
- amdgpu has multiple long-running **suspend/resume freeze** reports across kernels and GPU generations.
  - Example: Ubuntu Launchpad bug #1917674 (amdgpu resume freeze).

These are best read as **“similar symptom class”** rather than direct evidence of a hardware incompatibility.

### Source: What we did not find


- No explicit ASUS GPU incompatibility/QVL list for PRIME X370-PRO.
- No official vendor note declaring R9700 conflicts with X370 boards.

### Source: Implications for troubleshooting


1) Firmware/AGESA age is still the strongest **platform risk factor**.
2) RDNA4 driver maturity and power-state transitions remain high-probability **software risk factors**.
3) Treat external reports as **adjacent evidence** to help prioritize safe experiments (GFXOFF, runtime PM,
   kernel/driver updates) before hardware replacement.

### Source: References


- Phoronix: "RADV Implements RDNA4 HiZ/HiS Workaround To Fix Random GPU Hangs"
  (https://www.phoronix.com/news/Mesa-RDNA4-HiZ-HiS)
- Ubuntu Launchpad bug #1917674: "amdgpu resume from suspend freeze"
  (https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1917674)

## Decisions And Interpretation

No separate decisions and interpretation is stated in the source.
