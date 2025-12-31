---
type: runbook
id: RUN-gpu-ai-workloads
title: "Runbook: GPU AI Workloads (AMD Radeon AI PRO R9700)"
status: active
owners: "olof"
created: 2025-12-30
updated: 2025-12-30
system: "hemma.hule.education"
---

Operations guide for AI workloads on the AMD Radeon AI PRO R9700 (32GB VRAM, RDNA 4).

## Hardware Specifications

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

## Software Stack

| Component | Version | Path |
|-----------|---------|------|
| **Kernel** | 6.14.0-37-generic (HWE) | - |
| **Driver** | amdgpu 6.16.6 | - |
| **ROCm** | 7.1.1 | `/opt/rocm-7.1.1/` |
| **HIP** | 7.1.x | `/opt/rocm/bin/hipcc` |
| **MIOpen** | 3.5.1 | `/opt/rocm/bin/MIOpenDriver` |
| **MIGraphX** | - | `/opt/rocm/bin/migraphx-driver` |

## Quick Commands

### GPU Status

```bash
# Basic status (temp, power, clocks)
ssh hemma "rocm-smi"

# Detailed info
ssh hemma "rocm-smi --showallinfo"

# VRAM usage
ssh hemma "rocm-smi --showmeminfo vram"

# Temperature monitoring (watch)
ssh hemma "watch -n 1 rocm-smi --showtemp"

# Power consumption
ssh hemma "rocm-smi --showpower"

# ROCm agent info
ssh hemma "rocminfo"

# OpenCL info
ssh hemma "clinfo"
```

### Power Profiles

```bash
# Show available profiles
ssh hemma "rocm-smi --showprofile"

# Set COMPUTE profile (recommended for AI)
ssh hemma "sudo rocm-smi --setprofile COMPUTE"

# Reset to default
ssh hemma "sudo rocm-smi --setprofile BOOTUP DEFAULT"

# Available profiles:
# - COMPUTE: optimized for compute workloads
# - POWER SAVING: reduced power/thermals
# - VIDEO: video encode/decode
# - 3D FULL SCREEN: gaming
# - VR: virtual reality
# - BOOTUP DEFAULT: balanced
```

### Fan Control

```bash
# Show fan status
ssh hemma "rocm-smi --showfan"

# Set fan to percentage (0-255 or percentage)
ssh hemma "sudo rocm-smi --setfan 80"  # 80%

# Reset to auto
ssh hemma "sudo rocm-smi --resetfans"
```

## AI Framework Setup

### PyTorch with ROCm

```bash
# Create venv
ssh hemma "python3 -m venv ~/ai-env && source ~/ai-env/bin/activate"

# Install PyTorch ROCm (check pytorch.org for latest)
ssh hemma "source ~/ai-env/bin/activate && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2"

# Verify GPU detection
ssh hemma "source ~/ai-env/bin/activate && python -c 'import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))'"
```

### llama.cpp with ROCm

```bash
# Clone and build
ssh hemma "git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp"
ssh hemma "cd ~/llama.cpp && make clean && make GGML_HIP=1 -j$(nproc)"

# Verify build
ssh hemma "~/llama.cpp/llama-cli --version"

# Run inference (example)
ssh hemma "cd ~/llama.cpp && ./llama-cli -m models/model.gguf -p 'Hello' -n 50 --gpu-layers 99"
```

### Ollama with ROCm

```bash
# Install Ollama (auto-detects ROCm)
ssh hemma "curl -fsSL https://ollama.com/install.sh | sh"

# Pull a model
ssh hemma "ollama pull llama3.2:3b"

# Run with GPU
ssh hemma "ollama run llama3.2:3b"

# Check GPU usage during inference
ssh hemma "rocm-smi --showmeminfo vram"
```

### vLLM with ROCm

```bash
# Install vLLM ROCm
ssh hemma "source ~/ai-env/bin/activate && pip install vllm"

# Serve a model
ssh hemma "source ~/ai-env/bin/activate && python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3.2-3B --gpu-memory-utilization 0.9"
```

## VRAM Management

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
# Watch VRAM usage
ssh hemma "watch -n 0.5 'rocm-smi --showmeminfo vram'"

# Get current usage in GB
ssh hemma "rocm-smi --showmeminfo vram | grep Used | awk '{print \$6/1024/1024/1024 \" GB\"}'"
```

### Clear VRAM (if stuck)

```bash
# Kill GPU processes
ssh hemma "sudo fuser -k /dev/dri/renderD128"

# Or reset GPU (last resort)
ssh hemma "sudo rocm-smi --gpureset"
```

## Environment Variables

Add to `~/.bashrc` for optimal ROCm configuration:

```bash
# ROCm paths
export PATH="/opt/rocm/bin:$PATH"
export LD_LIBRARY_PATH="/opt/rocm/lib:$LD_LIBRARY_PATH"

# HIP settings
export HIP_VISIBLE_DEVICES=0
export HSA_OVERRIDE_GFX_VERSION=12.0.1  # Only if needed for compatibility

# PyTorch ROCm
export PYTORCH_ROCM_ARCH="gfx1201"

# Performance tuning
export GPU_MAX_HW_QUEUES=8
export AMD_SERIALIZE_KERNEL=3
export AMD_SERIALIZE_COPY=3

# MIOpen cache (speeds up repeated runs)
export MIOPEN_USER_DB_PATH="~/.config/miopen"
export MIOPEN_CACHE_DIR="~/.cache/miopen"

# Debug (enable if troubleshooting)
# export AMD_LOG_LEVEL=4
# export HIP_LAUNCH_BLOCKING=1
```

## Performance Tuning

### Set Performance Mode

```bash
# Set compute profile
ssh hemma "sudo rocm-smi --setprofile COMPUTE"

# Set performance level to high
ssh hemma "sudo rocm-smi --setperflevel high"

# Verify
ssh hemma "rocm-smi --showperflevel"
```

### Persistent Settings (systemd)

Create `/etc/systemd/system/rocm-perf.service`:

```ini
[Unit]
Description=Set ROCm GPU to compute profile
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/opt/rocm/bin/rocm-smi --setprofile COMPUTE
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
ssh hemma "sudo systemctl enable rocm-perf.service"
```

## Troubleshooting

### GPU Not Detected

```bash
# Check driver loaded
ssh hemma "lsmod | grep amdgpu"

# Check dmesg for errors
ssh hemma "dmesg | grep -i amdgpu | tail -20"

# Check PCIe device
ssh hemma "lspci | grep -i vga"

# Verify user in groups
ssh hemma "groups | grep -E 'render|video'"
```

### ROCm Errors

```bash
# Check HSA status
ssh hemma "rocminfo 2>&1 | head -20"

# Common error: HSA_STATUS_ERROR_OUT_OF_RESOURCES
# Fix: Set HSA_OVERRIDE_GFX_VERSION if architecture mismatch
ssh hemma "export HSA_OVERRIDE_GFX_VERSION=12.0.1 && rocminfo"
```

### PyTorch Not Using GPU

```bash
# Check CUDA (HIP) available
ssh hemma "source ~/ai-env/bin/activate && python -c 'import torch; print(torch.version.hip); print(torch.cuda.is_available())'"

# If False, check ROCm version compatibility with PyTorch wheel
# May need: export PYTORCH_ROCM_ARCH="gfx1201"
```

### High Temps / Throttling

```bash
# Check temp
ssh hemma "rocm-smi --showtemp"

# If junction > 100C, increase fan
ssh hemma "sudo rocm-smi --setfan 100"

# Or set power limit
ssh hemma "sudo rocm-smi --setpoweroverdrive 250"  # 250W limit
```

### DKMS Rebuild After Kernel Update

```bash
# If kernel updates break driver
ssh hemma "sudo dkms status"
ssh hemma "sudo dkms autoinstall"
ssh hemma "sudo reboot"
```

## Benchmarks

### Quick GPU Benchmark

```bash
# ROCm bandwidth test
ssh hemma "/opt/rocm/bin/rocm-bandwidth-test"

# HIP samples (if installed)
ssh hemma "/opt/rocm/hip/bin/hipDeviceQuery"
```

### AI Inference Benchmark (llama.cpp)

```bash
# Benchmark with a model
ssh hemma "cd ~/llama.cpp && ./llama-bench -m models/model.gguf -p 512 -n 128 -ngl 99"
```

## Maintenance

### Update ROCm

```bash
# Check current version
ssh hemma "cat /opt/rocm/.info/version"

# Update (download new amdgpu-install, then reinstall)
ssh hemma "sudo amdgpu-install --uninstall"
ssh hemma "wget https://repo.radeon.com/amdgpu-install/<version>/ubuntu/noble/amdgpu-install_<version>.deb"
ssh hemma "sudo apt install ./amdgpu-install_*.deb"
ssh hemma "sudo amdgpu-install -y --usecase=graphics,rocm"
ssh hemma "sudo reboot"
```

### Clean MIOpen Cache

```bash
# If MIOpen issues or after ROCm update
ssh hemma "rm -rf ~/.config/miopen ~/.cache/miopen"
```

## Docker Integration

GPU inference runs as systemd services on the host. Docker containers reach them via `host.docker.internal`.

### Container Access to Host GPU Services

Add to any compose file that needs GPU inference:

```yaml
services:
  my-service:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - LLM_BASE_URL=http://host.docker.internal:8082
```

### Verify Connectivity

```bash
# From inside a container
docker exec skriptoteket-web curl -s http://host.docker.internal:8082/health
# Expected: {"status":"ok"}

# Test completion
docker exec skriptoteket-web curl -s http://host.docker.internal:8082/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def hello", "n_predict": 10}'
```

### Port Reference

| Service      | Host Port | Container URL                       |
|--------------|-----------|-------------------------------------|
| llama-server | 8082      | `http://host.docker.internal:8082` |
| Tabby        | 8083      | `http://host.docker.internal:8083` |

## Remote Development (SSH Tunnel)

Access hemma's GPU from your local dev machine via SSH tunnel.

### Setup (macOS)

```bash
# Install autossh (once)
brew install autossh

# Start persistent tunnel (auto-reconnects)
autossh -M 0 -f -N -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" -L 8082:localhost:8082 hemma
```

### Verify

```bash
# Health check
curl http://localhost:8082/health
# Expected: {"status":"ok"}

# Test completion
curl -s http://localhost:8082/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def hello():", "n_predict": 20}'
```

### Manage Tunnel

```bash
# Check if running
pgrep -f "autossh.*8082" && echo "Running" || echo "Not running"

# Stop tunnel
pkill -f "autossh.*8082"

# Restart tunnel
autossh -M 0 -f -N -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" -L 8082:localhost:8082 hemma
```

### Use in Docker Compose

Local containers reach the tunnel via `host.docker.internal`:

```yaml
services:
  my-service:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - LLM_URL=http://host.docker.internal:8082
```

## References

- [ROCm Documentation](https://rocm.docs.amd.com/)
- [PyTorch ROCm](https://pytorch.org/get-started/locally/)
- [llama.cpp ROCm](https://github.com/ggerganov/llama.cpp#hiprocm)
- [AMD Radeon AI PRO R9700 Review](https://www.phoronix.com/review/amd-radeon-ai-pro-r9700)
