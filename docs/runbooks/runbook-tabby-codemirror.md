---
type: runbook
id: RUN-tabby-codemirror
title: "Runbook: AI Code Completion Services"
status: active
owners: "olof"
created: 2025-12-30
updated: 2025-12-30
system: "hemma.hule.education"
links: ["RUN-gpu-ai-workloads", "REF-ai-completion-architecture"]
---

Operations runbook for AI code completion services (llama.cpp + Tabby) on hemma.hule.education.

For architecture, models, and integration details, see
[ref-ai-completion-architecture.md](../reference/ref-ai-completion-architecture.md).

---

## Services Overview

| Service | Port | Purpose | Systemd Unit |
| ------- | ---- | ------- | ------------ |
| llama-server | 8082 | ROCm GPU inference | `llama-server.service` |
| Tabby | 8083 | Completion API proxy | `tabby.service` |

**Current model:** Qwen3-Coder-30B-A3B (Q4_K_M, ~18.5 GB VRAM)

---

## Health Checks

### Quick Status

```bash
# Service status
ssh hemma "sudo systemctl status llama-server tabby --no-pager | head -30"

# Tabby health endpoint
ssh hemma "curl -s http://localhost:8083/v1/health | jq .model"
# Expected: "Remote"

# llama.cpp health
ssh hemma "curl -s http://localhost:8082/health"
# Expected: {"status":"ok"}
```

### VRAM Check

```bash
ssh hemma "rocm-smi --showmeminfo vram | grep Used"
# Expected: ~18.5 GB for Qwen3-Coder-30B-A3B Q4_K_M
```

### Test Completion

```bash
ssh hemma 'curl -s http://localhost:8083/v1/completions \
  -H "Content-Type: application/json" \
  -d "{\"language\": \"python\", \"segments\": {\"prefix\": \"def fib(n):\\n    \", \"suffix\": \"\"}}" | jq .choices[0].text'
```

---

## Start/Stop/Restart

### Start Services

```bash
ssh hemma "sudo systemctl start llama-server tabby"
```

### Stop Services

```bash
ssh hemma "sudo systemctl stop tabby llama-server"
```

### Restart Services

```bash
# After config change or model swap
ssh hemma "sudo systemctl restart llama-server && sleep 5 && sudo systemctl restart tabby"
```

### Reload After Service File Edit

```bash
ssh hemma "sudo systemctl daemon-reload"
```

---

## View Logs

```bash
# llama-server logs
ssh hemma "journalctl -u llama-server -f"

# Tabby logs
ssh hemma "journalctl -u tabby -f"

# Last 50 lines
ssh hemma "journalctl -u llama-server -n 50 --no-pager"
```

---

## Switch Models

1. Stop services:

   ```bash
   ssh hemma "sudo systemctl stop tabby llama-server"
   ```

2. Download new model (if needed):

   ```bash
   ssh hemma "cd ~/models && wget <model-url>"
   ```

3. Edit llama-server.service to change `--model` path:

   ```bash
   ssh hemma "sudo nano /etc/systemd/system/llama-server.service"
   ```

4. Reload and restart:

   ```bash
   ssh hemma "sudo systemctl daemon-reload && sudo systemctl start llama-server tabby"
   ```

5. Verify:

   ```bash
   ssh hemma "curl -s http://localhost:8083/v1/health | jq ."
   ```

---

## Monitor GPU

```bash
# Watch GPU usage during inference
ssh hemma "watch -n 1 rocm-smi"

# Check temperature
ssh hemma "rocm-smi --showtemp"
```

---

## Troubleshooting

### llama-server Won't Start

```bash
ssh hemma "journalctl -u llama-server -n 50"
```

Common causes:

- Model path incorrect in service file
- VRAM insufficient (reduce `--ctx-size` or use smaller quant)
- ROCm not detecting GPU (check `HSA_OVERRIDE_GFX_VERSION=12.0.1`)

### Tabby Returns Empty Completions

1. Test llama.cpp directly:

   ```bash
   ssh hemma 'curl http://localhost:8082/completion \
     -d "{\"prompt\": \"def hello\"}" \
     -H "Content-Type: application/json"'
   ```

2. If llama.cpp works but Tabby doesn't, check `~/.tabby/config.toml`

### High Latency

- Reduce `--ctx-size` (e.g., 4096 instead of 8192)
- Check GPU throttling: `rocm-smi --showtemp`
- Increase `--threads` if CPU-bound

### 401 Unauthorized from Tabby

Tabby v0.31+ has auth enabled by default. Use `--no-webserver` flag to disable.

---

## Known Issues

### RDNA 4 Flash Attention Crash

ROCm 7.1.1 clang crashes on gfx1201 flash attention. Build with `-DGGML_HIP_FA=OFF`.

### Port Conflicts

| Port | Service | Notes |
| ---- | ------- | ----- |
| 8080 | node | Pre-existing |
| 8081 | Apache httpd | Pre-existing |
| 8082 | llama-server | AI inference |
| 8083 | Tabby | Completion API |
| 30888 | llama-server (Tabby) | Internal embeddings |

### Tabby Requires Bundled llama-server

Even with external HTTP backend, Tabby needs its bundled llama-server for embeddings. Copy from tarball to `/usr/local/bin/`.

---

## Service Files

### llama-server.service

Location: `/etc/systemd/system/llama-server.service`

Key parameters:

- `--model`: Path to GGUF file
- `--port 8082`: API port
- `--ctx-size 8192`: Context window
- `--n-gpu-layers 99`: Offload all to GPU
- `HSA_OVERRIDE_GFX_VERSION=12.0.1`: RDNA 4 compatibility

### tabby.service

Location: `/etc/systemd/system/tabby.service`

Key parameters:

- `--port 8083`: API port
- `--no-webserver`: Disable auth and web UI

### Tabby Config

Location: `~/.tabby/config.toml`

```toml
[model.completion.http]
kind = "llama.cpp/completion"
api_endpoint = "http://127.0.0.1:8082"
prompt_template = "<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"

[model.chat.http]
kind = "openai/chat"
api_endpoint = "http://127.0.0.1:8082/v1"
model_name = "qwen3-coder-30b-a3b"
```

---

## References

- [ref-ai-completion-architecture.md](../reference/ref-ai-completion-architecture.md) - Architecture and integration
- [ADR-0050](../adr/adr-0050-self-hosted-llm-infrastructure.md) - Infrastructure decisions
- [runbook-gpu-ai-workloads.md](runbook-gpu-ai-workloads.md) - GPU operations
