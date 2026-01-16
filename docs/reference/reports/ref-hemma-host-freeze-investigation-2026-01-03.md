---
type: reference
id: REF-hemma-host-freeze-investigation-2026-01-03
title: "Investigation: hemma host hard hangs (Jan 2026)"
status: active
owners: "agents"
created: 2026-01-03
updated: 2026-01-16
topic: "devops"
---

This report summarizes what we know so far about two **host-level hard hangs** on the hemma server that required
physical intervention.

**Important:** This report contains *sanitized* log excerpts. IPs, MACs, SSIDs, and local IPv6 addresses were redacted.

## Update (2026-01-13)

Hemma now runs llama.cpp via Docker using `llama-server-rocm.service` (container `llama-server-rocm`). References in
this report to `llama-server.service`, `llama-server-hip.service`, or `llama-server-vulkan.service` reflect the
historical state during Jan 2026 debugging and should not be re-enabled.

## Update (2026-01-16)

Hemma now uses `watchdog.stop_on_reboot=0` (normal + crash-kernel cmdlines) so the `sp5100_tco` hardware watchdog keeps
running across warm reboots (including the post-kdump SysRq reboot path). This reduces the chance that a wedge *during
reboot* requires a manual hard power cycle.

## Executive summary

- **Two incidents on 2026-01-02 (UTC)** ended with the host becoming unresponsive and requiring a reboot/power-cycle.
- The journal shows **no kernel panic, no OOM killer, and no obvious “smoking gun”** right before either hang.
- **Incident A (08:34 UTC)** correlates strongly with unexpected Wi‑Fi (`wlp5s0`) activity, flapping, and heavy
  `tailscaled` rebind churn.
- **Incident B (17:54 UTC)** has almost no log signal in the final minute (heartbeat `ok`, then silence), which is
  consistent with a deep host wedge where logs stop flushing.

## Timeline (UTC)

Derived from `journalctl --list-boots` on the host.

- **Incident A (hang):** 2026-01-02 **08:34:55** (boot `-2` ended)
- **Reboot after incident A:** 2026-01-02 **11:59:24** (boot `-1` started)
- **Incident B (hang):** 2026-01-02 **17:54:45** (boot `-1` ended)
- **Reboot after incident B (manual hard power cycle):** 2026-01-03 **10:39:34** (boot `0` started)

User-reported detail for Incident B: the host did not respond even to a physical case soft reset; a hard power cycle was
required.

## Current health (post-reboot)

As of 2026-01-03 12:07 UTC:

- `https://skriptoteket.hule.education/health` returns **200**.
- `skriptoteket-web`, `nginx-proxy`, and `shared-postgres` show **restart count 0** since the 2026-01-03 10:39 UTC boot.

## Hardware inventory (host snapshot)

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

## Known/likely compatibility risks from this inventory

### 1) Extremely old motherboard BIOS (2018)

This is the single biggest “known bad smell” in the hardware inventory: the PRIME X370-PRO has BIOS releases through at
least **2024-11-14**, with multiple entries explicitly mentioning **system stability improvements** and AGESA updates.

Practical implication: even if the immediate trigger is “GPU/ROCm”, an out-of-date AGESA/firmware can absolutely
contribute to PCIe/IOMMU edge cases (and make debugging harder).

### 2) RDNA4 + ROCm 7.1.1 + llama.cpp HIP backend

There is an open ROCm issue describing RDNA4 (`gfx1201` / Radeon AI PRO R9700) staying in a non-idle state after HIP
initialization under ROCm 7.1.1, while the Vulkan backend behaves correctly. This aligns with our observation that
`llama-server` can hold large amounts of VRAM even when “idle”.

This is not a proven root-cause for a hard host hang, but it does increase the prior probability that the HIP path is
still unstable on RDNA4 in this stack.

### 3) Display-core timeouts at boot (`optc401_disable_crtc`)

The recurring `REG_WAIT timeout ... optc401_disable_crtc` message we saw is in the amdgpu Display Core (DCN) pipeline.
This is an area with active patch discussions/upstream churn, which makes it a plausible suspect when combined with a
new GPU generation and out-of-tree driver stack.

## Memory check (post-reboot snapshot)

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

## Findings

### 1) Incident A: network churn + unexpected Wi‑Fi

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

### 2) Incident B: “silent” last minute

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

### 3) GPU / AI inference services are active (not proven causal)

During boot `-1` (the one that later hard-hung at 17:54 UTC), `llama-server` processed requests (example: logs at
2026-01-02 17:38 UTC), and the kernel logs include recurring `amdgpu` messages at boot.

We did not find a definitive GPU reset / kernel crash line right before the hang, but GPU/ROCm load remains a plausible
candidate for “host wedges without clean logs”.

## Automated incident capture (as of 2026-01-04)

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

## GPU load check (ROCm SMI snapshot)

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

## Vulkan A/B test status (current boot)

As of **2026-01-03 16:00 UTC**:

- `llama-server-vulkan.service` is **enabled + running** on `:8082`.
- `llama-server-hip.service` is **disabled + inactive**.
- `rocm-smi --showpids` reports **no KFD PIDs** (expected when avoiding the HIP/KFD compute path).
- Boot-time kernel logs still include:
  - `AMD-Vi: Event logged [INVALID_DEVICE_REQUEST ...]`
  - `REG_WAIT timeout ... optc401_disable_crtc`

### GPU power policy adjustment (during Vulkan trial)

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

### Inference check + context window A/B (Vulkan)

We ran a small inference request with the same prompt at two context sizes to observe latency and GPU memory behavior.

#### Baseline: `--ctx-size 8192`

- Request time (end-to-end): **~6.34s**
- Usage: `prompt_tokens=29`, `completion_tokens=81`
- During the request, sysfs reported the GPU waking and VRAM usage ramping to **~19.6 GB**, while GTT dropped to
  **~0.29 GB**. When the GPU returned to `runtime_status=suspended`, `mem_info_vram_used` dropped back to **~60 MB** and
  `mem_info_gtt_used` returned to **~16.6 GB**.

#### Change: `--ctx-size 16384` (double)

Applied at **2026-01-03 17:30 UTC** by updating and restarting `llama-server-vulkan.service`.

- Request time (same prompt as above): **~5.27s**
- Usage: `prompt_tokens=29`, `completion_tokens=81` (same as baseline)
- Peak VRAM during the request: **~20.4 GB** (about **+0.8 GB** vs 8192)

#### Longer output: `max_tokens=512` (ctx=16384)

With `--ctx-size 16384`, we ran an additional request with a longer completion:

- Request time (end-to-end): **~10.71s**
- Usage: `prompt_tokens=57`, `completion_tokens=512`
- GPU during the request: busy ~**85–87%**, VRAM plateaued at **~20.37 GB**

#### “Coding assistant” workflow (max_tokens=1024, ctx=16384)

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

### Memory + GPU snapshot (Vulkan mode)

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

### New low-level signal: UMC “hardware errors” spam when querying RAS (runtime-PM interaction)

On the current boot, querying `rocm-smi --showrasinfo` causes the kernel to emit messages like:

```text
amdgpu 0000:0b:00.0: 1048560 correctable hardware errors detected in umc block
amdgpu 0000:0b:00.0: 1048560 uncorrectable hardware errors detected in umc block
```

The reported count increases by exactly **1048560** per query (e.g. 1048560 → 2097120 → 3145680), which is consistent
with a **driver/tool reporting bug** rather than a real burst of ECC events, but we should treat it as a red flag until
confirmed.

#### Controlled test: keep GPU awake while querying RAS

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

- `rocm-smi` also warns that the GPU is in a low-power state and the power counter read can fail
  (`energy_count_secondary_die_check, Unexpected data received`) in this mode.
- `rocm-smi --showpagesinfo/--showretiredpages` currently prints no useful page-retirement data (empty sections).

## Hypotheses (not yet proven)

- **H1: Hardware-level instability** (PSU, RAM, motherboard) causing hard lockups without clean logs.
- **H2: GPU/ROCm/driver wedge** (amdgpu under ROCm load) leading to a system-wide hang.
- **H3: Network stack / Wi‑Fi driver interaction** causing kernel deadlock (fits Incident A well, fits Incident B poorly).
- **H4: Runtime-PM suspend/resume + VRAM↔GTT migration storm** triggering a PCIe/IOMMU/bus-level wedge on this platform
  (old X370 BIOS/AGESA + RDNA4).

## Next steps (recommended)

1. **Enable a real hardware watchdog** (DONE 2026-01-12; `sp5100_tco` + `health-watchdog.service`; updated 2026-01-16
   with `watchdog.stop_on_reboot=0`), so the host can reboot itself on deep hangs and reboot wedges.
2. **Run an A/B isolation trial** for 24–48h each:
   - A: stop/disable `llama-server` (and/or `tabby`) temporarily
   - B: re-enable one service at a time
   Track whether hangs recur.
3. **After next reboot following a hang**, immediately collect:
   - `journalctl --list-boots --no-pager | tail -10`
   - `journalctl -b -1 --no-pager | tail -300`
   - `journalctl -b -1 -k --no-pager | tail -300`
4. If hangs continue: schedule deeper hardware checks (memtest, PSU validation, reseat RAM/GPU, NVMe health beyond
   SMART “PASSED”).

## Incident: 2026-01-03 ~20:55 UTC freeze during Devstral Q8 test

- **Event:** Host became unresponsive during Devstral (24B Q8) inference testing; SSH timed out and the box required a
  hard power-cycle.
- **Workload preceding the freeze:** `llama-server-vulkan` was running the Devstral 24B Q8 model on `:8082`, and we
  executed the two-step “coding assistant” benchmark (review + diff) with `ctx=16384` via the curl+sysfs sampling
  script (same as the earlier Qwen3 test).
- **Flash-attention status:** **not enabled** (attempted to add `--flash-attn on`, but SSH timed out before any change
  or restart was applied).
- **Reboot time:** Boot `-1` ended at **2026-01-03 20:55:32 UTC**; new boot `0` started at **2026-01-03 20:58:46 UTC**.
- **Last confirmed command (pre-freeze):** `ssh -o ConnectTimeout=5 -o BatchMode=yes hemma "echo ok"` timed out.
- **First successful command after power-cycle:** `ssh -o ConnectTimeout=5 -o BatchMode=yes hemma "echo ok"` returned `ok`.

---

## Mitigation applied (post-incident): reboot-safe “GPU stays awake” clamp

Goal: reduce the probability of a deep host wedge during an uncontrolled runtime-PM suspend/resume transition and large
VRAM↔GTT migrations.

### 1) Enforce a Vulkan-only trial window (Tabby disabled)

Post-reboot we discovered that `tabby.service` has `Wants=llama-server.service` and can therefore start a ROCm/KFD-based
llama.cpp server even if `llama-server-hip.service` is disabled. This breaks the “Vulkan-only” assumption.

During the Vulkan stability trial window we disabled Tabby and ensured the ROCm/KFD `llama-server.service` was stopped:

```bash
ssh hemma "sudo systemctl disable --now tabby.service"
ssh hemma "sudo systemctl disable --now llama-server.service"
ssh hemma "sudo ss -ltnp | rg ':8082'"
ssh hemma "rocm-smi --showpids details"
```

Expected signals:

- `:8082` is bound only by `llama-server-vulkan.service`
- `rocm-smi --showpids details` prints `No KFD PIDs currently running`

### 2) Make “force GPU active” persistent at boot (systemd oneshot)

We previously observed that when the GPU is runtime-suspended in Vulkan mode, sysfs reports very low VRAM usage and very
high GTT usage (example snapshot earlier in this report). The working theory is that the idle→suspend→resume path plus
large memory migration is a plausible trigger for the “silent wedge”.

To reduce the chance of runtime suspend, we force:

- `/sys/bus/pci/devices/0000:0b:00.0/power/control=on`

and made it reboot-safe with a oneshot unit:

- Service: `/etc/systemd/system/amdgpu-force-active.service` (targets the PCI path
  `0000:0b:00.0` to avoid card index ambiguity)

Applied and enabled at **2026-01-03 22:38:41 UTC**.

Verification commands:

```bash
ssh hemma "sudo systemctl status --no-pager amdgpu-force-active.service"
ssh hemma "sudo sh -c 'cat /sys/bus/pci/devices/0000:0b:00.0/power/control; cat /sys/bus/pci/devices/0000:0b:00.0/power/runtime_status'"
```

Rollback:

```bash
ssh hemma "sudo systemctl disable --now amdgpu-force-active.service"
ssh hemma "sudo sh -c 'echo auto > /sys/bus/pci/devices/0000:0b:00.0/power/control'"
```

Notes:

- `rocm-smi` may still print a “low-power state” warning even when `runtime_status=active`; rely on sysfs for the
  authoritative runtime-PM state.

### 3) Structured benchmark baseline (llama-bench, Vulkan)

To capture a repeatable baseline independent of HTTP serving, we ran `llama-bench` against the same Devstral Q8 model
file using the Vulkan build on the host.

Commands (performed with a short `:8082` outage by stopping/starting `llama-server-vulkan.service`):

```bash
ssh hemma "sudo systemctl stop llama-server-vulkan.service"
ssh hemma "/home/paunchygent/llama.cpp/build-vulkan/bin/llama-bench -m /home/paunchygent/models/Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf -p 512 -n 128 -r 1 --no-warmup -t 8 -ngl 99 -dev Vulkan0 -o md"
ssh hemma "sudo systemctl start llama-server-vulkan.service"
ssh hemma "curl -s http://127.0.0.1:8082/health"
```

Result (exact `llama-bench` output lines):

```text
| mistral3 14B Q8_0              |  23.33 GiB |    23.57 B | Vulkan     |  99 | Vulkan0      |           pp512 |        366.65 ± 0.00 |
| mistral3 14B Q8_0              |  23.33 GiB |    23.57 B | Vulkan     |  99 | Vulkan0      |           tg128 |         19.97 ± 0.00 |

build: 0f89d2ecf (7585)
```

Notes:

- `llama-bench` labels the model as `mistral3 14B Q8_0` but reports `params=23.57 B` and uses the Devstral 24B Q8 file
  path; treat the throughput values as the baseline signal.
- After restarting `llama-server-vulkan.service`, `curl -s http://127.0.0.1:8082/health` returned `{"status":"ok"}`.

### 4) Canonical output-quality A/B (HTTP chat: review → diff)

Goal: keep a **reproducible “coding assistant” workload** (review + patch diff) and use it to choose the default model
for the Vulkan-only stability trial window. This is separate from “host wedge” root-cause, but it determines which model
we actually serve during the trial.

Protocol:

- Endpoint: `POST /v1/chat/completions` (non-streaming), against `llama-server-vulkan.service` on `:8082`
- Canonical payload: “CANONICAL BENCHMARK v3” (Step 1 = review, Step 2 = unified diff patch)
- Artifacts are stored **in-repo** for reproducibility:
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/`

#### Devstral Small 2 24B (Q8_0) — Vulkan

Run: 2026-01-04T00:10Z (UTC)

- Prompts:
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260104T001002Z/prompt1_review_v3.txt`
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260104T001002Z/prompt2_diff_v3.txt`
- Outputs:
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260104T001002Z/review.text`
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260104T001002Z/diff.text`
- Request payloads (settings):
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260104T001002Z/review.request.json`
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260104T001002Z/diff.request.json`

Summary: Devstral produced a **usable patch** that satisfied the constraints (Zip Slip block, chunked copy, added the two
tests, strict diff formatting).

#### Qwen3-Coder 30B-A3B (Q4_K_M) — Vulkan

Runs: 2026-01-04T00:32Z (UTC) and 2026-01-04T00:38Z (UTC)

1 “Recommended sampler” run (temperature=0.7)

- Outputs:
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-20260104T003257Z/review.text`
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-20260104T003257Z/diff.text`
- Request payloads (settings):
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-20260104T003257Z/review.request.json`
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-20260104T003257Z/diff.request.json`

2 Deterministic rerun (temperature=0.1)

- Outputs:
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-t0.1-20260104T003857Z/review.text`
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-t0.1-20260104T003857Z/diff.text`
- Request payloads (settings):
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-t0.1-20260104T003857Z/review.request.json`
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-qwen-t0.1-20260104T003857Z/diff.request.json`

Summary: in both runs, Qwen3-Coder produced a **non-usable patch**. The key failure is the Zip Slip “fix” pattern:
`Path(name).resolve()` makes the path absolute, so the subsequent `is_absolute()` check becomes true for essentially all
entries, effectively skipping extraction for normal files. Lowering temperature did not change this behavior.

Decision (current): keep `llama-server-vulkan.service` on **Devstral** for the canonical “review + diff” workflow until
Qwen3-Coder can produce correct diffs under a comparable instruct model + prompt template.

Operational note: the systemd unit `Description=` may drift (it currently mentions Qwen even when serving Devstral). For
truth, always check the served model id:

```bash
ssh hemma "curl -s http://127.0.0.1:8082/v1/models | jq -r '.data[0].id'"
```

## Appendix: raw data locations (do not commit secrets)

- Host log captures: `/root/logs/incident-*.log`
- This report intentionally does **not** include any Wi‑Fi credentials (and none should be added in future updates).
