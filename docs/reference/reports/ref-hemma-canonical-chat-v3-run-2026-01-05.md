---
type: reference
id: REF-hemma-canonical-chat-v3-run-2026-01-05
title: "Canonical chat v3 run (Devstral, runpm=0) - 2026-01-05"
status: active
owners: "agents"
created: 2026-01-05
updated: 2026-01-05
topic: "devops"
links:
  - docs/reference/reports/ref-hemma-runpm0-before-after-2026-01-05.md
  - docs/reference/reports/ref-hemma-perflevel-auto-vs-high-2026-01-05.md
  - docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md
---

Controlled inference run using the canonical chat v3 prompts after enabling `amdgpu.runpm=0`.

## Run details

- Timestamp (artifact id): **2026-01-05T01:19:23Z**
- Model: **Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf** (current model only; no Qwen3)
- Endpoint: `http://127.0.0.1:8082/v1/chat/completions` (llama-server-vulkan)
- Prompts: canonical v3 (review + diff)

Artifacts:

- `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260105T011923Z/`
  - Requests: `review.request.json`, `diff.request.json`
  - Responses: `review.response.json`, `diff.response.json`
  - Extracted text: `review.text`, `diff.text`
  - State snapshots: `review.before.txt`, `review.after.txt`, `diff.before.txt`, `diff.after.txt`
  - Sensors: `rocm-smi.txt`, `sensors.txt`, `pm_info.txt`, `power_state.txt`

## Timing (approx, from before/after snapshots)

- Review: **~45s** (01:20:14 → 01:20:59 UTC)
- Diff: **~57s** (01:21:22 → 01:22:19 UTC)

## Power state at capture time

From `power_state.txt`:

- `runpm=0`
- `power.control=on`
- `power.runtime_status=active`
- `perflevel=high`

## Sensors (post-run, idle)

From `rocm-smi.txt` and `sensors.txt`:

- GPU edge/junction/mem: **32°C / 33°C / 60°C**
- GPU PPT (rocm-smi): **~40 W**
- Fan: **~1984 RPM (20%)**
- Clocks: **SCLK 0 MHz**, **MCLK 1124 MHz**, **FCLK 2400 MHz**, **SOC 1371 MHz**
- CPU Tctl: **~37°C**

Note: `sensors` reported PPT as **1000 mW** (1 W), which conflicts with rocm-smi (~40 W). This appears to be a
sensor reporting quirk; treat rocm-smi as the authoritative power reading for now.

## Observations

- The GPU remained in an idle/parked core state (SCLK 0 MHz) with high VRAM allocation (~27.4 GB).
- Low-power warnings still appear in rocm-smi even with `runpm=0` and `perflevel=high`.

## Follow-up: during-load telemetry capture

We reran the canonical v3 review + diff with **during-load** telemetry sampling (rocm-smi every ~2s)
while keeping the same model and power settings.

- Timestamp (artifact id): **2026-01-05T01:29:47Z**
- Model: **Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf** (current model only)
- Sampling: `rocm-smi --showuse --showmemuse --showpower --showtemp --showfan --showclocks --showvoltage`

Artifacts:

- `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260105T012947Z/`
  - Requests: `review.request.json`, `diff.request.json`
  - Responses: `review.response.json`, `diff.response.json`
  - Extracted text: `review.text`, `diff.text`
  - State snapshots: `review.before.txt`, `review.after.txt`, `diff.before.txt`, `diff.after.txt`
  - Telemetry: `review.telemetry.txt`, `diff.telemetry.txt`
  - Sensors: `sensors.txt`, `power_state.txt`

### During-load telemetry summary (rocm-smi samples)

Review telemetry (`review.telemetry.txt`, 60 samples, ~2s cadence):

- Window: **01:30:51 → 01:32:58 UTC**
- PPT: **38–177 W**
- Edge temp: **29–39°C**
- Junction temp: **29–45°C**
- Memory temp: **32–50°C**
- GPU use: **0–100%**
- VRAM allocation: **85%** (flat)
- SCLK: **0–2335 MHz**
- MCLK/FCLK: **1124 MHz / 2400 MHz** (flat)

Diff telemetry (`diff.telemetry.txt`, 60 samples, ~2s cadence):

- Window: **01:33:24 → 01:35:31 UTC**
- PPT: **39–171 W**
- Edge temp: **31–45°C**
- Junction temp: **31–51°C**
- Memory temp: **40–56°C**
- GPU use: **0–100%**
- VRAM allocation: **85%** (flat)
- SCLK: **0–2350 MHz**
- MCLK/FCLK: **1124 MHz / 2400 MHz** (flat)
