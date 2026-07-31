---
type: runbook
id: RUN-SKRIPT-runbook-gpu-ai-workloads-amd-radeon-ai-pro-r9700-PART-02
title: 'Runbook: GPU AI Workloads (AMD Radeon AI PRO R9700) — part 02'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: RUN-SKRIPT-runbook-gpu-ai-workloads-amd-radeon-ai-pro-r9700
part: 2
---

Purpose: model-level behavior check against Kodassistenten constraints (runner limits, UI payload contract,
toolkit usage, action/state flow). This runs **directly** against llama.cpp for stable prompts.

Harness docs:
- `scripts/ai_prompt_eval/README.md`

Fixture source:
- `docs/reference/reports/artifacts/llama-kodassistent-eval-v2/llama-kodassistent-eval-v2-20260131T150000Z/`

Run (example):

```bash
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label glm
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label devstral --output-dir <same-run-dir>
```

Outputs include `comparison.json` (usage/timing) and `validation.json` (pass/fail + reasons).
The harness runs two patch steps: `diff_tool` (tool.py only) and `diff_schema` (input_schema.json + usage).

Notes:
- By default the harness injects the Kodassistenten system prompt (editor_chat_v1). Use `--no-system` to disable.
- If system prompt composition fails due to missing dependencies, run via `pdm run python ...`.

### Source: Maintenance

### Update ROCm

```bash
### Check current version
ssh hemma "cat /opt/rocm/.info/version"

### Confirm supported flags/usecases (e.g. rocm, rocmdev, rocmdevtools)
ssh hemma "amdgpu-install --list-usecase"

### Stop GPU workloads before uninstall/reinstall
ssh hemma "sudo systemctl stop llama-server-rocm.service"

### Update (download new amdgpu-install, then reinstall)
ssh hemma "sudo amdgpu-install --uninstall"

### Download + install new amdgpu-install (example: ROCm 7.2 on Ubuntu 24.04 'noble')
ssh hemma "wget https://repo.radeon.com/amdgpu-install/7.2/ubuntu/noble/amdgpu-install_7.2.70200-1_all.deb"
ssh hemma "sudo apt install ./amdgpu-install_7.2.70200-1_all.deb"

### Install usecase (pick one):
### - Graphics + compute (Mesa + ROCm): graphics,rocm
### - Headless/compute (no Mesa): rocm
### Notes:
### - "Mesa graphics" == `graphics` (open source Mesa 3D + multimedia libs).
### - `workstation` is deprecated and maps to Mesa; prefer `graphics`.
ssh hemma "sudo amdgpu-install -y --usecase=graphics,rocm"
### ssh hemma "sudo amdgpu-install -y --usecase=rocm"
ssh hemma "sudo reboot"
```

Post-upgrade verification:

```bash
ssh hemma "cat /opt/rocm/.info/version"
ssh hemma "rocm-smi -V && rocm-smi --showproductname --showdriverversion"
ssh hemma "rocminfo | head -n 50"
ssh hemma "sudo systemctl status --no-pager llama-server-rocm.service | head -n 40"
ssh hemma "curl -fsS http://127.0.0.1:8082/health && echo"
```

### Clean MIOpen Cache

```bash
### If MIOpen issues or after ROCm update
ssh hemma "rm -rf ~/.config/miopen ~/.cache/miopen"
```

### Source: Docker Integration

llama.cpp inference runs in Docker (managed by systemd). Docker containers reach it via `host.docker.internal`.

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
### From inside a container
docker exec skriptoteket-web curl -s http://host.docker.internal:8082/health
### Expected: {"status":"ok"}

### Test completion
docker exec skriptoteket-web curl -s http://host.docker.internal:8082/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def hello", "n_predict": 10}'
```

### Port Reference

| Service      | Host Port | Container URL                       |
|--------------|-----------|-------------------------------------|
| llama-server | 8082      | `http://host.docker.internal:8082` |
| Tabby        | 8083      | `http://host.docker.internal:8083` |

### Source: Remote Development (SSH Tunnel)

Access hemma's GPU from your local dev machine via SSH tunnel.

### Prerequisites (macOS)

```bash
brew install autossh
```

### Tunnel Management Script

Install `~/bin/hemma-gpu-tunnel` for easy tunnel management:

Note: status checks use `nc` on the local port to avoid noisy `pgrep`/`sysmond` failures on macOS.

```bash
#!/bin/bash
### SSH tunnels to hemma GPU services (llama-server + Tabby)

LLAMA_PORT=8082
TABBY_PORT=8083
HOST=hemma
PID_DIR="${HOME}/.cache/hemma-gpu-tunnel"

mkdir -p "$PID_DIR"

start_tunnel() {
    local port=$1
    local name=$2
    local pid_file="${PID_DIR}/tunnel-${port}.pid"
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file" 2>/dev/null || true)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo "✓ ${name} tunnel already running (port ${port})"
            return
        fi
    fi

    autossh -M 0 -N \
        -o "ServerAliveInterval=30" \
        -o "ServerAliveCountMax=3" \
        -o "ExitOnForwardFailure=yes" \
        -L ${port}:localhost:${port} ${HOST} >/dev/null 2>&1 &
    echo $! > "$pid_file"
    echo "▶ Started ${name} tunnel (port ${port})"
}

stop_tunnel() {
    local port=$1
    local name=$2
    local pid_file="${PID_DIR}/tunnel-${port}.pid"
    local pid=""
    if [[ -f "$pid_file" ]]; then
        pid=$(cat "$pid_file" 2>/dev/null || true)
    fi

    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        rm -f "$pid_file"
        echo "■ Stopped ${name} tunnel"
        return
    fi

    rm -f "$pid_file"
    echo "  ${name} tunnel not running"
}

status() {
    echo "=== Hemma GPU Tunnels ==="
    for port in $LLAMA_PORT $TABBY_PORT; do
        if nc -z -w 1 localhost ${port} 2>/dev/null; then
            if curl -s --connect-timeout 2 http://localhost:${port}/health > /dev/null 2>&1 || \
               curl -s --connect-timeout 2 http://localhost:${port}/v1/health > /dev/null 2>&1; then
                echo "✓ Port ${port}: connected"
            else
                echo "? Port ${port}: port open, service unreachable"
            fi
        else
            echo "✗ Port ${port}: not running"
        fi
    done
}

case "${1:-start}" in
    start)
        start_tunnel $LLAMA_PORT "llama-server"
        start_tunnel $TABBY_PORT "tabby"
        ;;
    start-llama)
        start_tunnel $LLAMA_PORT "llama-server"
        ;;
    start-tabby)
        start_tunnel $TABBY_PORT "tabby"
        ;;
    stop-llama)
        stop_tunnel $LLAMA_PORT "llama-server"
        ;;
    stop-tabby)
        stop_tunnel $TABBY_PORT "tabby"
        ;;
    stop)
        stop_tunnel $LLAMA_PORT "llama-server"
        stop_tunnel $TABBY_PORT "tabby"
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $(basename $0) {start|start-llama|start-tabby|stop|stop-llama|stop-tabby|restart|status}"
        exit 1
        ;;
esac
```

Usage:

```bash
hemma-gpu-tunnel start        # start tunnels
hemma-gpu-tunnel start-llama  # start only llama tunnel (:8082)
hemma-gpu-tunnel start-tabby  # start only tabby tunnel (:8083)
hemma-gpu-tunnel stop         # stop tunnels
hemma-gpu-tunnel stop-llama   # stop only llama tunnel (:8082)
hemma-gpu-tunnel stop-tabby   # stop only tabby tunnel (:8083)
hemma-gpu-tunnel restart      # restart tunnels
hemma-gpu-tunnel status       # check status
```

### Auto-Start on Login (LaunchAgent)

Create `~/Library/LaunchAgents/com.hemma.gpu-tunnel.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hemma.gpu-tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/bin/hemma-gpu-tunnel</string>
        <string>start-llama</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/hemma-gpu-tunnel.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/hemma-gpu-tunnel.log</string>
</dict>
</plist>
```

Load:

```bash
launchctl load ~/Library/LaunchAgents/com.hemma.gpu-tunnel.plist
```

### Verify

```bash
### Health check
curl http://localhost:8082/health
### Expected: {"status":"ok"}

### Test chat completion (recommended for instruction-tuned models)
curl -s http://localhost:8082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Write a fibonacci function in Python"}], "max_tokens": 100}' | \
  jq -r '.choices[0].message.content'

### Test raw completion (for base models or text continuation)
curl -s http://localhost:8082/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "The capital of Sweden is", "n_predict": 10}' | \
  jq -r '.content'
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

### Source: References

- [ROCm Documentation](https://rocm.docs.amd.com/)
- [PyTorch ROCm](https://pytorch.org/get-started/locally/)
- [llama.cpp ROCm](https://github.com/ggerganov/llama.cpp#hiprocm)
- [AMD Radeon AI PRO R9700 Review](https://www.phoronix.com/review/amd-radeon-ai-pro-r9700)

## Expected Results

No separate source material was recorded for this section.

## Stop Conditions

### Source: Troubleshooting

### GPU Not Detected

```bash
### Check driver loaded
ssh hemma "lsmod | grep amdgpu"

### Check dmesg for errors
ssh hemma "dmesg | grep -i amdgpu | tail -20"

### Check PCIe device
ssh hemma "lspci | grep -i vga"

### Verify user in groups
ssh hemma "groups | grep -E 'render|video'"
```

### ROCm Errors

```bash
### Check HSA status
ssh hemma "rocminfo 2>&1 | head -20"

### Common error: HSA_STATUS_ERROR_OUT_OF_RESOURCES
### Fix: Set HSA_OVERRIDE_GFX_VERSION if architecture mismatch
ssh hemma "export HSA_OVERRIDE_GFX_VERSION=12.0.1 && rocminfo"
```

### PyTorch Not Using GPU

```bash
### Check CUDA (HIP) available
ssh hemma "source ~/ai-env/bin/activate && python -c 'import torch; print(torch.version.hip); print(torch.cuda.is_available())'"

### If False, check ROCm version compatibility with PyTorch wheel
### May need: export PYTORCH_ROCM_ARCH="gfx1201"
```

### High Temps / Throttling

```bash
### Check temp
ssh hemma "rocm-smi --showtemp"

### If junction > 100C, increase fan
ssh hemma "sudo rocm-smi --setfan 100"

### Or set power limit
ssh hemma "sudo rocm-smi --setpoweroverdrive 250"  # 250W limit
```

### DKMS Rebuild After Kernel Update
