---
type: reference
id: REF-SKRIPT-GENERAL-investigation-hemma-host-hard-hangs-jan-2026-PART-01
title: 'Investigation: hemma host hard hangs (Jan 2026) — part 01'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-investigation-hemma-host-hard-hangs-jan-2026
part: 1
---

## Overview

The source does not provide a separate overview section; no additional overview is recorded.

## Facts And Semantics

### Source: Findings



### Source: Update (2026-01-13)

Hemma now runs llama.cpp via Docker using `llama-server-rocm.service` (container `llama-server-rocm`). References in
this report to `llama-server.service`, `llama-server-hip.service`, or `llama-server-vulkan.service` reflect the
historical state during Jan 2026 debugging and should not be re-enabled.

### Source: Update (2026-01-16)

Hemma now uses `watchdog.stop_on_reboot=0` (normal + crash-kernel cmdlines) so the `sp5100_tco` hardware watchdog keeps
running across warm reboots (including the post-kdump SysRq reboot path). This reduces the chance that a wedge *during
reboot* requires a manual hard power cycle.

### Source: Executive summary

- **Two incidents on 2026-01-02 (UTC)** ended with the host becoming unresponsive and requiring a reboot/power-cycle.
- The journal shows **no kernel panic, no OOM killer, and no obvious “smoking gun”** right before either hang.
- **Incident A (08:34 UTC)** correlates strongly with unexpected Wi‑Fi (`wlp5s0`) activity, flapping, and heavy
  `tailscaled` rebind churn.
- **Incident B (17:54 UTC)** has almost no log signal in the final minute (heartbeat `ok`, then silence), which is
  consistent with a deep host wedge where logs stop flushing.

### Source: Timeline (UTC)

Derived from `journalctl --list-boots` on the host.

- **Incident A (hang):** 2026-01-02 **08:34:55** (boot `-2` ended)
- **Reboot after incident A:** 2026-01-02 **11:59:24** (boot `-1` started)
- **Incident B (hang):** 2026-01-02 **17:54:45** (boot `-1` ended)
- **Reboot after incident B (manual hard power cycle):** 2026-01-03 **10:39:34** (boot `0` started)

User-reported detail for Incident B: the host did not respond even to a physical case soft reset; a hard power cycle was
required.

### Source: Current health (post-reboot)

As of 2026-01-03 12:07 UTC:

- `https://skriptoteket.hule.education/health` returns **200**.
- `skriptoteket-web`, `nginx-proxy`, and `shared-postgres` show **restart count 0** since the 2026-01-03 10:39 UTC boot.

### Source: Hardware inventory (host snapshot)

Collected from `dmidecode`, `lscpu`, and `lspci` on 2026-01-03.

- Motherboard: **ASUS PRIME X370-PRO** (X370 chipset)
- BIOS: **American Megatrends Inc. 3803** (2018-01-22)
- CPU: **AMD Ryzen 7 1700** (8C/16T, AM4)
- RAM: **32 GB DDR4** (4×8 GB), Corsair kit **CMK16GX4M2B3000C15**
- GPU: **AMD Radeon AI PRO R9700** (`gfx1201`, PCI ID `1002:7551`)
  - Host link: **PCIe 3.0 x16** (`8GT/s (downgraded), Width x16`) via a PCIe switch
  - Resizable BAR capability present; current BAR0 is **256 MB** (not “large BAR”)
- Network:
  - Intel **I211** (wired)
  - Qualcomm Atheros **AR93xx** (Wi‑Fi, `wlp5s0`)
- Storage (SATA):
  - 2× Samsung SSD 850 (465 GB)
  - 1× Seagate HDD 4 TB
  - 1× Seagate HDD 2 TB

### Source: Known/likely compatibility risks from this inventory



### Source: 1) Extremely old motherboard BIOS (2018)

This is the single biggest “known bad smell” in the hardware inventory: the PRIME X370-PRO has BIOS releases through at
least **2024-11-14**, with multiple entries explicitly mentioning **system stability improvements** and AGESA updates.

Practical implication: even if the immediate trigger is “GPU/ROCm”, an out-of-date AGESA/firmware can absolutely
contribute to PCIe/IOMMU edge cases (and make debugging harder).

### Source: 2) RDNA4 + ROCm 7.1.1 + llama.cpp HIP backend

There is an open ROCm issue describing RDNA4 (`gfx1201` / Radeon AI PRO R9700) staying in a non-idle state after HIP
initialization under ROCm 7.1.1, while the Vulkan backend behaves correctly. This aligns with our observation that
`llama-server` can hold large amounts of VRAM even when “idle”.

This is not a proven root-cause for a hard host hang, but it does increase the prior probability that the HIP path is
still unstable on RDNA4 in this stack.

### Source: 3) Display-core timeouts at boot (`optc401_disable_crtc`)

The recurring `REG_WAIT timeout ... optc401_disable_crtc` message we saw is in the amdgpu Display Core (DCN) pipeline.
This is an area with active patch discussions/upstream churn, which makes it a plausible suspect when combined with a
new GPU generation and out-of-tree driver stack.

### Source: Memory check (post-reboot snapshot)

Snapshot taken on the host at **2026-01-03 12:18 UTC**.

```text
$ free -h
               total        used        free      shared  buff/cache   available
Mem:            31Gi       2.3Gi       9.5Gi        69Mi        20Gi        29Gi
Swap:          8.0Gi          0B       8.0Gi

$ cat /proc/pressure/memory
some avg10=0.00 avg60=0.00 avg300=0.00 total=21
full avg10=0.00 avg60=0.00 avg300=0.00 total=21
```

Notes:

- No OOM killer lines were found in the previous boot journal (`-b -1`).
- No MCE/EDAC “Hardware Error” lines were found in the previous boot journal (`-b -1`) beyond normal initialization.

### Source: 1) Incident A: network churn + unexpected Wi‑Fi

The “last-minute” capture (08:33:55–08:34:54) shows:

- `wlp5s0` repeatedly associating/disassociating due to `DISASSOC_AP_BUSY`.
- `tailscaled` repeatedly logging `LinkChange: major, rebinding` and updating routes/DNS (with many `[RATELIMIT]` lines).
- `ssh-watchdog` observed `wlp5s0 is UP (expected down)`.

This log capture is included in full (sanitized) in:

- `docs/reference/reports/ref-hemma-incident-log-2026-01-02-083355-083455.md`

We also see that later that day (2026-01-02 ~13:29 UTC), Wi‑Fi was explicitly torn down:

- `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` exists (`network: {config: disabled}`) and has mtime
  **2026-01-02 13:29 UTC**.
- After that point, system logs show `netplan-wpa-wlp5s0.service` stopping and `systemd-networkd` unmanaging `wlp5s0`.
- On the current boot (2026-01-03), `wlp5s0` is **DOWN**.

### Source: 2) Incident B: “silent” last minute

The last minute before the journal stops (17:53:30–17:55:30) contains only routine firewall blocks and the heartbeat:

```text
Jan 02 17:53:42 paunchygentserver kernel: [UFW BLOCK] IN=enp7s0 OUT= MAC=<mac_redacted> SRC=<ip_redacted> DST=<ip_redacted> LEN=394 TOS=0x00 PREC=0x00 TTL=64 ID=50216 DF PROTO=UDP SPT=48434 DPT=55211 LEN=374
Jan 02 17:54:04 paunchygentserver kernel: [UFW BLOCK] IN=enp7s0 OUT= MAC=<mac_redacted> SRC=<ip_redacted> DST=<ip_redacted> LEN=466 TOS=0x00 PREC=0x00 TTL=64 ID=55418 DF PROTO=UDP SPT=52114 DPT=56430 LEN=446
Jan 02 17:54:27 paunchygentserver kernel: [UFW BLOCK] IN=enp7s0 OUT= MAC=<mac_redacted> SRC=<ip_redacted> DST=<ip_redacted> LEN=466 TOS=0x00 PREC=0x00 TTL=64 ID=65259 DF PROTO=UDP SPT=42915 DPT=36198 LEN=446
Jan 02 17:54:38 paunchygentserver systemd[1]: Starting heartbeat-log.service - Heartbeat log entry...
Jan 02 17:54:38 paunchygentserver heartbeat[148288]: ok
Jan 02 17:54:38 paunchygentserver systemd[1]: heartbeat-log.service: Deactivated successfully.
Jan 02 17:54:38 paunchygentserver systemd[1]: Finished heartbeat-log.service - Heartbeat log entry.
Jan 02 17:54:45 paunchygentserver kernel: [UFW BLOCK] IN=enp7s0 OUT= MAC=<mac_redacted> SRC=<ip_redacted> DST=<ip_redacted> LEN=36 TOS=0x00 PREC=0xC0 TTL=1 ID=65356 DF PROTO=2
```

No obvious crash indicator appears in this window.

### Source: 3) GPU / AI inference services are active (not proven causal)

During boot `-1` (the one that later hard-hung at 17:54 UTC), `llama-server` processed requests (example: logs at
2026-01-02 17:38 UTC), and the kernel logs include recurring `amdgpu` messages at boot.

We did not find a definitive GPU reset / kernel crash line right before the hang, but GPU/ROCm load remains a plausible
candidate for “host wedges without clean logs”.

### Source: Automated incident capture (as of 2026-01-04)

To preserve crash-adjacent context (system + kernel logs + GPU state), we now capture rolling incident snapshots on the
host:

- Script: `/usr/local/bin/skriptoteket-incident-capture.sh`
- Systemd: `skriptoteket-incident-capture.service` + `skriptoteket-incident-capture.timer`
- Output: `/root/logs/incident-*.log`
- Defaults: every 5 minutes, 10-minute window, 7-day retention
- Captures: system + kernel logs, llama/tabby service logs, GPU runtime state, `rocm-smi` power/temps/clocks, and
  `/sys/class/hwmon` snapshot (uses `sensors` if installed).
- Threshold warnings are logged in each capture and can be tuned via env:
  `INCIDENT_GPU_EDGE_WARN_C`, `INCIDENT_GPU_JUNCTION_WARN_C`, `INCIDENT_GPU_MEM_WARN_C`,
  `INCIDENT_GPU_PPT_WARN_W`, `INCIDENT_CPU_TCTL_WARN_C`.

This is intended to retain the last few minutes of activity even if the kernel ring buffer or journald does not flush
cleanly during a hard hang.

### Source: GPU load check (ROCm SMI snapshot)

Snapshot taken on the host at **2026-01-03 12:18 UTC**.

```text
$ rocm-smi --showuse --showtemp --showpower --showmemuse --showfan --showclocks --showvoltage
GPU[0] : Temperature (Sensor edge) (C): 38.0
GPU[0] : Temperature (Sensor junction) (C): 40.0
GPU[0] : Temperature (Sensor memory) (C): 42.0
GPU[0] : Average Graphics Package Power (W): 43.0
GPU[0] : GPU use (%): 3
GPU[0] : GPU Memory Allocated (VRAM%): 61

$ rocm-smi --showmeminfo vram
GPU[0] : VRAM Total Memory (B): 32061259776
GPU[0] : VRAM Total Used Memory (B): 19853647872

$ rocm-smi --showpids details
PID  PROCESS NAME  GPU  VRAM USED      SDMA USED  CU OCCUPANCY
1372 llama-server  1    19783208960    0          UNKNOWN
```

Interpretation:

- The GPU was mostly idle in this snapshot (3% busy), but `llama-server` had ~19.8 GB VRAM allocated, which explains the
  ~61% VRAM usage at “idle”.

RAS/ECC counters (same boot):

```text
$ rocm-smi --showrasinfo
Block  Status   Correctable  Uncorrectable
UMC    ENABLED           0              0
DF     ENABLED
```

### Source: Vulkan A/B test status (current boot)

As of **2026-01-03 16:00 UTC**:

- `llama-server-vulkan.service` is **enabled + running** on `:8082`.
- `llama-server-hip.service` is **disabled + inactive**.
- `rocm-smi --showpids` reports **no KFD PIDs** (expected when avoiding the HIP/KFD compute path).
- Boot-time kernel logs still include:
  - `AMD-Vi: Event logged [INVALID_DEVICE_REQUEST ...]`
  - `REG_WAIT timeout ... optc401_disable_crtc`

### Source: GPU power policy adjustment (during Vulkan trial)

To reduce forced high clocks while continuing the Vulkan A/B stability trial, we changed the host GPU setting:

- `power_dpm_force_performance_level`: `high` → `auto`
- Left `pp_power_profile_mode` as `COMPUTE*` (unchanged)

Applied at **2026-01-03 16:38 UTC** (host time):

```bash
ssh hemma 'sudo sh -c "
  echo on > /sys/class/drm/card1/device/power/control
  echo auto > /sys/class/drm/card1/device/power_dpm_force_performance_level
  echo auto > /sys/class/drm/card1/device/power/control
"'
```

### Source: Inference check + context window A/B (Vulkan)

We ran a small inference request with the same prompt at two context sizes to observe latency and GPU memory behavior.

### Source: Baseline: `--ctx-size 8192`

- Request time (end-to-end): **~6.34s**
- Usage: `prompt_tokens=29`, `completion_tokens=81`
- During the request, sysfs reported the GPU waking and VRAM usage ramping to **~19.6 GB**, while GTT dropped to
  **~0.29 GB**. When the GPU returned to `runtime_status=suspended`, `mem_info_vram_used` dropped back to **~60 MB** and
  `mem_info_gtt_used` returned to **~16.6 GB**.

### Source: Change: `--ctx-size 16384` (double)

Applied at **2026-01-03 17:30 UTC** by updating and restarting `llama-server-vulkan.service`.

- Request time (same prompt as above): **~5.27s**
- Usage: `prompt_tokens=29`, `completion_tokens=81` (same as baseline)
- Peak VRAM during the request: **~20.4 GB** (about **+0.8 GB** vs 8192)

### Source: Longer output: `max_tokens=512` (ctx=16384)

With `--ctx-size 16384`, we ran an additional request with a longer completion:

- Request time (end-to-end): **~10.71s**
- Usage: `prompt_tokens=57`, `completion_tokens=512`
- GPU during the request: busy ~**85–87%**, VRAM plateaued at **~20.37 GB**

### Source: “Coding assistant” workflow (max_tokens=1024, ctx=16384)

We simulated a common coding-assistant flow: send a script, get a review, then request a patch diff.

Step 1 (review):

- Request time (end-to-end): **~14.55s**
- Usage: `prompt_tokens=1218`, `completion_tokens=509`
- GPU during the request: VRAM plateaued at **~20.40 GB**
- Note: before the request (GPU runtime-suspended), sysfs showed **GTT used ~16.65 GB**, which corresponds to a large
  chunk of host RAM appearing “used” in `free -h`. Once the GPU resumed for compute, GTT dropped to **~0.29 GB**.

Step 2 (diff):

- Request time (end-to-end): **~15.56s**
- Usage: `prompt_tokens=1184`, `completion_tokens=1024` (hit max_tokens)
- GPU during the request: VRAM plateaued at **~20.40 GB**, GTT stayed **~0.30 GB**

RAM note: model load for `--ctx-size 16384` showed a temporary high memory peak in systemd (`peak: 15.0G`), and the host
later showed non-zero swap use (example snapshot: `Swap: ... 144Mi used`). This isn’t necessarily a problem by itself, but
it increases memory pressure and is worth tracking if hangs recur.

### Source: Memory + GPU snapshot (Vulkan mode)

Snapshot taken on the host at **2026-01-03 16:10 UTC**.

Memory:

```text
$ free -h
               total        used        free      shared  buff/cache   available
Mem:            31Gi        20Gi       6.2Gi        22Mi       4.8Gi        10Gi
Swap:          8.0Gi       256Ki       8.0Gi

$ swapon --show
NAME      TYPE SIZE USED PRIO
/swap.img file   8G 256K   -2
```

GPU:

```text
$ rocm-smi --showuse --showtemp --showpower --showmemuse --showpids details
WARNING: AMD GPU device(s) is/are in a low-power state. Check power control/runtime_status
...
GPU[0] : GPU use (%): 0
GPU[0] : GPU Memory Allocated (VRAM%): 0
...
No KFD PIDs currently running
```

Relevant sysfs (bytes unless stated):

```text
/sys/class/drm/card1/device/mem_info_vram_total=32061259776
/sys/class/drm/card1/device/mem_info_vram_used=59895808
/sys/class/drm/card1/device/mem_info_vis_vram_total=268435456
/sys/class/drm/card1/device/mem_info_vis_vram_used=3272704
/sys/class/drm/card1/device/mem_info_gtt_total=16790835200
/sys/class/drm/card1/device/mem_info_gtt_used=16642551808
/sys/class/drm/card1/device/power/runtime_status=suspended
/sys/class/drm/card1/device/power/control=auto
```

Interpretation:

- In Vulkan mode, `rocm-smi` does not show per-process VRAM allocations (no HIP/KFD processes), but the kernel sysfs
  memory counters still show a small amount of VRAM in use and a very large amount of GTT mapped.
- The GPU runtime-PM state being `suspended` matters for interpreting some ROCm SMI/RAS outputs (see next section).

### Source: New low-level signal: UMC “hardware errors” spam when querying RAS (runtime-PM interaction)

On the current boot, querying `rocm-smi --showrasinfo` causes the kernel to emit messages like:

```text
amdgpu 0000:0b:00.0: 1048560 correctable hardware errors detected in umc block
amdgpu 0000:0b:00.0: 1048560 uncorrectable hardware errors detected in umc block
```

The reported count increases by exactly **1048560** per query (e.g. 1048560 → 2097120 → 3145680), which is consistent
with a **driver/tool reporting bug** rather than a real burst of ECC events, but we should treat it as a red flag until
confirmed.

### Source: Controlled test: keep GPU awake while querying RAS

We performed a single controlled query with the GPU forced to `runtime_status=active`:

```text
$ sudo sh -c "echo on > /sys/class/drm/card1/device/power/control"
$ cat /sys/class/drm/card1/device/power/runtime_status
active

$ rocm-smi --showrasinfo
UMC ENABLED correctable=4194240 uncorrectable=4194240

$ sudo journalctl -k -b --since "2026-01-03T16:11:36+00:00" | rg "umc block"
(no matches)
```

Result: with the GPU kept awake, `rocm-smi --showrasinfo` did **not** produce new `umc block` kernel spam and the
reported counter did **not** jump by the fixed 1048560 step.

Working hypothesis: the “error count jump + kernel spam” is triggered by querying RAS while the GPU is runtime-suspended
(`power/runtime_status=suspended`), and the counter value is not reliable in that state.

Notes:
