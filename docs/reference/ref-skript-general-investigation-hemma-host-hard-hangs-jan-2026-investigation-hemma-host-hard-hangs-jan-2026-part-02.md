---
type: reference
id: REF-SKRIPT-GENERAL-investigation-hemma-host-hard-hangs-jan-2026-PART-02
title: 'Investigation: hemma host hard hangs (Jan 2026) — part 02'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-investigation-hemma-host-hard-hangs-jan-2026
part: 2
---

- `rocm-smi` also warns that the GPU is in a low-power state and the power counter read can fail
  (`energy_count_secondary_die_check, Unexpected data received`) in this mode.
- `rocm-smi --showpagesinfo/--showretiredpages` currently prints no useful page-retirement data (empty sections).

### Source: Hypotheses (not yet proven)

- **H1: Hardware-level instability** (PSU, RAM, motherboard) causing hard lockups without clean logs.
- **H2: GPU/ROCm/driver wedge** (amdgpu under ROCm load) leading to a system-wide hang.
- **H3: Network stack / Wi‑Fi driver interaction** causing kernel deadlock (fits Incident A well, fits Incident B poorly).
- **H4: Runtime-PM suspend/resume + VRAM↔GTT migration storm** triggering a PCIe/IOMMU/bus-level wedge on this platform
  (old X370 BIOS/AGESA + RDNA4).

### Source: Next steps (recommended)

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

### Source: Incident: 2026-01-03 ~20:55 UTC freeze during Devstral Q8 test

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

### Source: Mitigation applied (post-incident): reboot-safe “GPU stays awake” clamp

Goal: reduce the probability of a deep host wedge during an uncontrolled runtime-PM suspend/resume transition and large
VRAM↔GTT migrations.

### Source: 1) Enforce a Vulkan-only trial window (Tabby disabled)

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

### Source: 2) Make “force GPU active” persistent at boot (systemd oneshot)

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

### Source: 3) Structured benchmark baseline (llama-bench, Vulkan)

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

### Source: 4) Canonical output-quality A/B (HTTP chat: review → diff)

Goal: keep a **reproducible “coding assistant” workload** (review + patch diff) and use it to choose the default model
for the Vulkan-only stability trial window. This is separate from “host wedge” root-cause, but it determines which model
we actually serve during the trial.

Protocol:

- Endpoint: `POST /v1/chat/completions` (non-streaming), against `llama-server-vulkan.service` on `:8082`
- Canonical payload: “CANONICAL BENCHMARK v3” (Step 1 = review, Step 2 = unified diff patch)
- Artifacts are stored **in-repo** for reproducibility:
  - `docs/reference/reports/artifacts/llama-canonical-chat-v3/`

### Source: Devstral Small 2 24B (Q8_0) — Vulkan

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

### Source: Qwen3-Coder 30B-A3B (Q4_K_M) — Vulkan

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

### Source: Appendix: raw data locations (do not commit secrets)

- Host log captures: `/root/logs/incident-*.log`
- This report intentionally does **not** include any Wi‑Fi credentials (and none should be added in future updates).

## Decisions And Interpretation

The source does not provide a separate decisions and interpretation section; no additional decisions and interpretation is recorded.
