---
type: runbook
id: RUN-SKRIPT-runbook-gpu-ai-workloads-amd-radeon-ai-pro-r9700-PART-01
title: 'Runbook: GPU AI Workloads (AMD Radeon AI PRO R9700) — part 01'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: RUN-SKRIPT-runbook-gpu-ai-workloads-amd-radeon-ai-pro-r9700
part: 1
---

## Trigger

### Source: Source introduction

Operations guide for AI workloads on the AMD Radeon AI PRO R9700 (32GB VRAM, RDNA 4).

## Preconditions

### Source: Environment Variables

Add to `~/.bashrc` for optimal ROCm configuration:

```bash
### ROCm paths
export PATH="/opt/rocm/bin:$PATH"
export LD_LIBRARY_PATH="/opt/rocm/lib:$LD_LIBRARY_PATH"

### HIP settings
export HIP_VISIBLE_DEVICES=0
export HSA_OVERRIDE_GFX_VERSION=12.0.1  # Only if needed for compatibility

### PyTorch ROCm
export PYTORCH_ROCM_ARCH="gfx1201"

### Performance tuning
export GPU_MAX_HW_QUEUES=8
export AMD_SERIALIZE_KERNEL=3
export AMD_SERIALIZE_COPY=3

### MIOpen cache (speeds up repeated runs)
export MIOPEN_USER_DB_PATH="~/.config/miopen"
export MIOPEN_CACHE_DIR="~/.cache/miopen"

### Debug (enable if troubleshooting)
### export AMD_LOG_LEVEL=4
### export HIP_LAUNCH_BLOCKING=1
```

## Steps

### Source: Storage Tiers

- `/srv/scratch` = fast SSD work tier for Docker root, BuildKit cache,
  HF/model caches, and active generated artifacts.
- `/srv/storage` = large HDD bulk-data tier for raw corpora and cold retained
  datasets.
- `/` must not be the long-term home for Docker persistent state or large GPU
  artifact trees.

### Source: Hardware Specifications

| Component | Value |
|-----------|-------|
| **GPU** | AMD Radeon AI PRO R9700 |
| **Architecture** | RDNA 4 (gfx1201) |
| **VRAM** | 32 GB GDDR6 |
| **Compute Units** | 64 |
| **SIMDs per CU** | 2 |
| **Max Clock** | 2350 MHz |
| **TDP** | 300W |
| **AI Accelerators** | 128 |
| **Peak FP16** | 96 TFLOPS |
| **INT4 Sparse** | 1531 TOPS |
| **L2 Cache** | 8 MB |
| **L3 Cache** | 64 MB (Infinity Cache) |
| **PCIe** | 4.0 x16 |

### Source: Software Stack

| Component | Version | Path |
|-----------|---------|------|
| **Kernel** | 6.14.0-37-generic (HWE) | - |
| **Driver** | amdgpu 6.16.13 | - |
| **ROCm** | 7.2.0 | `/opt/rocm-7.2.0/` |
| **HIP** | 7.2.x | `/opt/rocm/bin/hipcc` |
| **MIOpen** | 3.5.1 | `/opt/rocm/bin/MIOpenDriver` |
| **MIGraphX** | - | `/opt/rocm/bin/migraphx-driver` |

### Source: Support Baseline (ROCm System Requirements)

ROCm system requirements footnote for Radeon PRO / Radeon GPUs (verbatim excerpt):
> "only support Ubuntu 24.04.3, Ubuntu 22.04.5, RHEL 10.1, and RHEL 9.7."

Notes:
- Treat Ubuntu 24.04.2 as installer media only; target the Ubuntu 24.04.3 runtime baseline with HWE 6.14.x.
- Source: ROCm system requirements (Linux), 2026-01-05.

### Source: Quick Commands

### GPU Status

```bash
### Basic status (temp, power, clocks)
ssh hemma "rocm-smi"

### Detailed info
ssh hemma "rocm-smi --showallinfo"

### VRAM usage
ssh hemma "rocm-smi --showmeminfo vram"

### Temperature monitoring (watch)
ssh hemma "watch -n 1 rocm-smi --showtemp"

### Power consumption
ssh hemma "rocm-smi --showpower"

### ROCm agent info
ssh hemma "rocminfo"

### OpenCL info
ssh hemma "clinfo"
```

### Power Profiles

```bash
### Show available profiles
ssh hemma "rocm-smi --showprofile"

### Set COMPUTE profile (recommended for AI)
ssh hemma "sudo rocm-smi --setprofile COMPUTE"

### Reset to default
ssh hemma "sudo rocm-smi --setprofile BOOTUP DEFAULT"

### Available profiles:
### - COMPUTE: optimized for compute workloads
### - POWER SAVING: reduced power/thermals
### - VIDEO: video encode/decode
### - 3D FULL SCREEN: gaming
### - VR: virtual reality
### - BOOTUP DEFAULT: balanced
```

### Fan Control

```bash
### Show fan status
ssh hemma "rocm-smi --showfan"

### Set fan to percentage (0-255 or percentage)
ssh hemma "sudo rocm-smi --setfan 80"  # 80%

### Reset to auto
ssh hemma "sudo rocm-smi --resetfans"
```

### Source: AI Framework Setup

### PyTorch with ROCm

```bash
### Create venv
ssh hemma "python3 -m venv ~/ai-env && source ~/ai-env/bin/activate"

### Install PyTorch ROCm (check pytorch.org for latest)
ssh hemma "source ~/ai-env/bin/activate && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2"

### Verify GPU detection
ssh hemma "source ~/ai-env/bin/activate && python -c 'import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))'"
```

### llama.cpp server (Docker, ROCm) — canonical on hemma

On `hemma`, llama.cpp is run via Docker and managed by a systemd wrapper unit. This is the **only supported**
runtime path for llama.cpp on this host (ROCm + llama.cpp recommended operations). Do not run or enable legacy
host-binary llama-server units.

- Systemd unit: `llama-server-rocm.service`
- Container: `llama-server-rocm` (image `llama.cpp-rocm:7.2.0`)
- Endpoint: `http://127.0.0.1:8082` (`/health`, `/v1/*`)

#### Image build (ROCm 7.2)

`llama.cpp-rocm:7.2.0` is built locally on `hemma` from AMD's ROCm base image and ROCm fork of llama.cpp:

- Dockerfile: `/home/paunchygent/llama.cpp-rocm/Dockerfile`
- Base image: `rocm/dev-ubuntu-24.04:7.2-complete`
- Source: `https://github.com/ROCm/llama.cpp` (pinned via `LLAMA_CPP_COMMIT`)

Rebuild (pull base + rebuild local image) and restart:

```bash
ssh hemma "cd /home/paunchygent/llama.cpp-rocm && sudo docker build --pull -t llama.cpp-rocm:7.2.0 ."
ssh hemma "sudo systemctl restart llama-server-rocm.service"
```

#### Current settings (as of 2026-01-13)

- `--ctx-size 32768`
- `--parallel 2` → effective per-slot context is `n_ctx_seq = 16384`

#### Quick checks

```bash
ssh hemma "sudo systemctl status --no-pager llama-server-rocm.service | head -n 60"
ssh hemma "curl -s http://127.0.0.1:8082/health"
ssh hemma "sudo journalctl -u llama-server-rocm.service -n 200 --no-pager"
```

#### Change model/context (safe workflow)

1. Edit the unit: `ssh hemma "sudo nano /etc/systemd/system/llama-server-rocm.service"`
2. Apply: `ssh hemma "sudo systemctl daemon-reload && sudo systemctl restart llama-server-rocm.service"`
3. Verify effective context (note `n_ctx_seq` when `--parallel > 1`):

```bash
ssh hemma "sudo journalctl -u llama-server-rocm.service -n 200 --no-pager | grep -E 'n_ctx =|n_ctx_seq =|KV buffer size'"
```

#### Safety: keep legacy units disabled/masked

These units are retired and must remain disabled/masked:

- `llama-server.service`
- `llama-server-hip.service`
- `llama-server-vulkan.service`

Optional hardening (prevents accidental enable/start):

```bash
ssh hemma "sudo systemctl disable --now llama-server.service llama-server-hip.service llama-server-vulkan.service"
ssh hemma "sudo systemctl mask llama-server.service llama-server-hip.service llama-server-vulkan.service"
```

### Ollama with ROCm

```bash
### Install Ollama (auto-detects ROCm)
ssh hemma "curl -fsSL https://ollama.com/install.sh | sh"

### Pull a model
ssh hemma "ollama pull llama3.2:3b"

### Run with GPU
ssh hemma "ollama run llama3.2:3b"

### Check GPU usage during inference
ssh hemma "rocm-smi --showmeminfo vram"
```

### vLLM with ROCm

```bash
### Install vLLM ROCm
ssh hemma "source ~/ai-env/bin/activate && pip install vllm"

### Serve a model
ssh hemma "source ~/ai-env/bin/activate && python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3.2-3B --gpu-memory-utilization 0.9"
```

### Source: VRAM Management

### Model Size Guidelines (32GB VRAM)

| Model Size | Quantization | VRAM Usage | Fits? |
|------------|--------------|------------|-------|
| 7B | FP16 | ~14 GB | Yes |
| 7B | Q8 | ~7 GB | Yes |
| 7B | Q4 | ~4 GB | Yes |
| 13B | FP16 | ~26 GB | Yes |
| 13B | Q8 | ~13 GB | Yes |
| 13B | Q4 | ~7 GB | Yes |
| 30B | FP16 | ~60 GB | No |
| 30B | Q8 | ~30 GB | Tight |
| 30B | Q4 | ~16 GB | Yes |
| 70B | Q4 | ~35 GB | No |

### Monitor VRAM During Inference

```bash
### Watch VRAM usage
ssh hemma "watch -n 0.5 'rocm-smi --showmeminfo vram'"

### Get current usage in GB
ssh hemma "rocm-smi --showmeminfo vram | grep Used | awk '{print \$6/1024/1024/1024 \" GB\"}'"
```

### Clear VRAM (if stuck)

```bash
### Kill GPU processes
ssh hemma "sudo fuser -k /dev/dri/renderD128"

### Or reset GPU (last resort)
ssh hemma "sudo rocm-smi --gpureset"
```

### Source: Performance Tuning

### Set Performance Mode

```bash
### Set compute profile
ssh hemma "sudo rocm-smi --setprofile COMPUTE"

### Set performance level to high
ssh hemma "sudo rocm-smi --setperflevel high"

### Verify
ssh hemma "rocm-smi --showperflevel"
```

### Persistent Settings (systemd)

GPU settings persist across reboots via `/etc/systemd/system/rocm-perf.service`:

```ini
[Unit]
Description=Set ROCm GPU to compute profile
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/opt/rocm/bin/rocm-smi --setprofile COMPUTE
ExecStartPost=/opt/rocm/bin/rocm-smi --setperflevel high
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
ssh hemma "sudo systemctl daemon-reload && sudo systemctl enable --now rocm-perf.service"
```

Verify:

```bash
ssh hemma "systemctl status rocm-perf.service"
```

### Source: Benchmarks

### Quick GPU Benchmark

```bash
### ROCm bandwidth test
ssh hemma "/opt/rocm/bin/rocm-bandwidth-test"

### HIP samples (if installed)
ssh hemma "/opt/rocm/hip/bin/hipDeviceQuery"
```

### AI Inference Smoke (llama.cpp)

```bash
### Health
ssh hemma "curl -s http://127.0.0.1:8082/health"

### Quick generation smoke (non-OpenAI endpoint)
ssh hemma 'curl -s http://127.0.0.1:8082/completion \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"def hello(name):\\n    \", \"n_predict\": 32}"'
```

### Canonical Chat Burn (llama.cpp service)

Use the canonical chat fixtures to stress the live `llama-server-rocm.service`
for 10 minutes (review + diff requests). This is the preferred stability burn
when netconsole is enabled.

```bash
### Ensure llama-server is running (port 8082)
ssh hemma "sudo systemctl status llama-server-rocm.service --no-pager | head -n 20"

### Run the 10-minute burn (logs to /root/logs/)
ssh hemma "cd ~/apps/skriptoteket && sudo python3 scripts/ai_prompt_eval/llama_canonical_chat_burn.py \
  --duration-seconds 600 --workers 8 --log-dir /root/logs"
```

Log format includes progress every 30s and a final summary (p50/p95/p99).
The fixture source is
`docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260105T012947Z/`.

### Kodassistenten Eval (llama.cpp behavior + compliance)
