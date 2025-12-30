---
type: runbook
id: RUN-tabby-codemirror
title: "Runbook: Tabby + CodeMirror 6 AI Code Completion"
status: active
owners: "olof"
created: 2025-12-30
updated: 2025-12-30
system: "hemma.hule.education"
links: ["RUN-gpu-ai-workloads"]
---

Self-hosted AI code completion using Tabby with CodeMirror 6 frontend, powered by Qwen 3 on AMD ROCm.

## Architecture

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CodeMirror 6   │────▶│  Tabby Server   │────▶│  llama.cpp      │
│  (Web Frontend) │     │  :8083          │     │  :8082 (ROCm)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
   /v1/completions          HTTP proxy           Qwen3-Coder-30B-A3B
```

**Components:**

- **llama.cpp**: Model inference with ROCm GPU acceleration (port 8082)
- **Tabby**: API orchestration, prompt templating, context management (port 8083)
- **CodeMirror 6**: Ghost-text inline completions in browser

## Current Model: Qwen3-Coder-30B-A3B (MoE)

**Active configuration on hemma.hule.education:**

| Property | Value |
|----------|-------|
| **Model** | `qwen3-coder-30b-a3b-q4_k_m.gguf` |
| **Architecture** | MoE (Mixture of Experts) |
| **Total Params** | 30.5B |
| **Active Params** | 3.3B per token |
| **Experts** | 128 total, 8 active |
| **Quantization** | Q4_K_M |
| **VRAM Usage** | ~18.5 GB |
| **Context Length** | 262K (native), 8192 (configured) |
| **Port** | 8082 |

## Model Selection (32GB VRAM)

| Model | Quant | VRAM | Speed | Quality | Recommended |
|-------|-------|------|-------|---------|-------------|
| **Qwen3-Coder-30B-A3B** | Q4_K_M | ~18.5 GB | Fast (MoE) | Great | **Current** |
| Qwen3-Coder-30B-A3B | Q5_K_M | ~21.7 GB | Fast (MoE) | Better | Alternative |
| Qwen2.5-Coder-32B | Q4 | ~18 GB | Medium | Great | Dense alternative |

**Why MoE?** The 30B-A3B model has 30B total params but only 3.3B active per token (8 of 128 experts). This gives 30B-quality outputs with 3B-like inference speed.

## Setup

### Step 1: Download Model

```bash
# SSH to server
ssh hemma

# Create models directory
mkdir -p ~/models
cd ~/models

# Download Qwen3-Coder-30B-A3B (MoE - recommended)
# 30.5B total params, only 3.3B active per token = fast inference
wget https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/resolve/main/qwen3-coder-30b-a3b-q4_k_m.gguf

# Alternative: Qwen2.5-Coder-32B (dense model, slower but good quality)
# wget https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/qwen2.5-coder-32b-instruct-q4_k_m.gguf
```

### Step 2: Build llama.cpp with ROCm

**Note:** llama.cpp now requires CMake (Makefile is deprecated).

```bash
ssh hemma

# Install build dependencies
sudo apt install -y cmake build-essential libcurl4-openssl-dev

# Clone llama.cpp
git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp
cd ~/llama.cpp

# Build with ROCm/HIP support using CMake
# IMPORTANT: -DGGML_HIP_FA=OFF disables flash attention which crashes on gfx1201 (RDNA 4)
cmake -B build \
  -DGGML_HIP=ON \
  -DGGML_HIP_FA=OFF \
  -DGGML_CURL=ON \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j$(nproc)

# Verify build (binary is in build/bin/)
./build/bin/llama-server --version
```

### Step 3: Create llama.cpp Service

Create systemd service for llama.cpp server:

```bash
ssh hemma "sudo tee /etc/systemd/system/llama-server.service" << 'EOF'
[Unit]
Description=llama.cpp Server (ROCm) - Qwen3-Coder-30B-A3B
After=network.target

[Service]
Type=simple
User=paunchygent
WorkingDirectory=/home/paunchygent/llama.cpp
Environment="HSA_OVERRIDE_GFX_VERSION=12.0.1"
ExecStart=/home/paunchygent/llama.cpp/build/bin/llama-server \
    --model /home/paunchygent/models/qwen3-coder-30b-a3b-q4_k_m.gguf \
    --host 127.0.0.1 \
    --port 8082 \
    --ctx-size 8192 \
    --n-gpu-layers 99 \
    --threads 8 \
    --parallel 2
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
ssh hemma "sudo systemctl daemon-reload && sudo systemctl enable llama-server && sudo systemctl start llama-server"

# Check status
ssh hemma "sudo systemctl status llama-server"

# View logs
ssh hemma "journalctl -u llama-server -f"
```

### Step 4: Install Tabby Server

```bash
ssh hemma

# Download latest Tabby binary
cd /tmp
curl -L -o tabby.tar.gz https://github.com/TabbyML/tabby/releases/latest/download/tabby_x86_64-manylinux_2_28.tar.gz
tar -xzf tabby.tar.gz

# Install binaries (Tabby requires bundled llama-server for embeddings)
sudo cp tabby_x86_64-manylinux_2_28/tabby /usr/local/bin/
sudo cp tabby_x86_64-manylinux_2_28/llama-server /usr/local/bin/
sudo chmod +x /usr/local/bin/tabby /usr/local/bin/llama-server

# Verify
tabby --version
```

### Step 5: Configure Tabby

Create Tabby config to use llama.cpp backend:

```bash
ssh hemma 'mkdir -p ~/.tabby && cat > ~/.tabby/config.toml << '\''EOF'\''
# Tabby Configuration
# Uses llama.cpp backend (ROCm) for model inference

[model.completion.http]
kind = "llama.cpp/completion"
api_endpoint = "http://127.0.0.1:8082"
# Qwen FIM (fill-in-middle) prompt template
prompt_template = "<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"

[model.chat.http]
kind = "openai/chat"
api_endpoint = "http://127.0.0.1:8082/v1"
model_name = "qwen3-coder-30b-a3b"

# Optional: Add repositories for context
# [[repositories]]
# name = "skriptoteket"
# git_url = "file:///home/paunchygent/apps/skriptoteket"
EOF'
```

### Step 6: Create Tabby Service

**Note:** Using `--no-webserver` disables authentication and web UI, serving only the completion API.

```bash
ssh hemma 'sudo tee /etc/systemd/system/tabby.service << '\''EOF'\''
[Unit]
Description=Tabby AI Code Completion Server
After=network.target llama-server.service
Wants=llama-server.service

[Service]
Type=simple
User=paunchygent
Environment="TABBY_ROOT=/home/paunchygent/.tabby"
ExecStart=/usr/local/bin/tabby serve --port 8083 --no-webserver
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'
```

Enable and start:

```bash
ssh hemma "sudo systemctl daemon-reload && sudo systemctl enable tabby && sudo systemctl start tabby"

# Verify
ssh hemma "curl -s http://localhost:8083/v1/health | jq ."
```

### Step 7: Test Completion API

```bash
# Test code completion
ssh hemma 'curl -s http://localhost:8083/v1/completions \
  -H "Content-Type: application/json" \
  -d "{\"language\": \"python\", \"segments\": {\"prefix\": \"def fibonacci(n):\\n    \", \"suffix\": \"\"}}" | jq .'

# Expected response:
# {
#   "id": "cmpl-...",
#   "choices": [{ "index": 0, "text": "if n <= 1:\n        return n\n    ..." }]
# }
```

### Step 8: Expose via Reverse Proxy (Optional)

Add to nginx-proxy for external access:

```bash
# Add to compose or nginx config
# VIRTUAL_HOST=tabby.hemma.hule.education
# Proxy to localhost:8083
```

## CodeMirror 6 Integration

### API Client

```typescript
// lib/tabby-client.ts

interface TabbyCompletionRequest {
  language: string;
  segments: {
    prefix: string;
    suffix: string;
  };
}

interface TabbyCompletionResponse {
  id: string;
  choices: Array<{
    index: number;
    text: string;
  }>;
}

export async function fetchTabbyCompletion(
  endpoint: string,
  prefix: string,
  suffix: string,
  language: string,
  signal?: AbortSignal
): Promise<string | null> {
  try {
    const response = await fetch(`${endpoint}/v1/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // "Authorization": "Bearer YOUR_TOKEN"  // if auth enabled
      },
      body: JSON.stringify({
        language,
        segments: { prefix, suffix },
      } satisfies TabbyCompletionRequest),
      signal,
    });

    if (!response.ok) {
      console.error(`Tabby error: ${response.status}`);
      return null;
    }

    const data: TabbyCompletionResponse = await response.json();
    return data.choices?.[0]?.text || null;
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") return null;
    console.error("Tabby completion failed:", e);
    return null;
  }
}
```

### CodeMirror Extension

```typescript
// lib/tabby-codemirror.ts

import {
  EditorView,
  Decoration,
  DecorationSet,
  WidgetType,
  keymap,
} from "@codemirror/view";
import {
  StateField,
  StateEffect,
  Extension,
  Prec,
} from "@codemirror/state";
import { fetchTabbyCompletion } from "./tabby-client";

// Effects
const setSuggestion = StateEffect.define<{ text: string; pos: number } | null>();

// Ghost text widget
class GhostTextWidget extends WidgetType {
  constructor(readonly text: string) {
    super();
  }

  toDOM(): HTMLElement {
    const span = document.createElement("span");
    span.className = "cm-ghost-text";
    span.textContent = this.text;
    return span;
  }

  eq(other: GhostTextWidget): boolean {
    return this.text === other.text;
  }
}

// State field for suggestion
const suggestionField = StateField.define<{ text: string; pos: number } | null>({
  create: () => null,

  update(value, tr) {
    // Clear on document change or selection change
    if (tr.docChanged || tr.selection) {
      value = null;
    }

    for (const effect of tr.effects) {
      if (effect.is(setSuggestion)) {
        value = effect.value;
      }
    }

    return value;
  },

  provide: (field) =>
    EditorView.decorations.from(field, (suggestion) => {
      if (!suggestion) return Decoration.none;

      return Decoration.set([
        Decoration.widget({
          widget: new GhostTextWidget(suggestion.text),
          side: 1,
        }).range(suggestion.pos),
      ]);
    }),
});

// Configuration
export interface TabbyConfig {
  endpoint: string;
  language: string;
  delay?: number;
  maxCompletionLength?: number;
}

// Main extension
export function tabbyCompletion(config: TabbyConfig): Extension {
  const {
    endpoint,
    language,
    delay = 400,
    maxCompletionLength = 500,
  } = config;

  let timeout: ReturnType<typeof setTimeout> | null = null;
  let abortController: AbortController | null = null;

  const plugin = EditorView.updateListener.of((update) => {
    // Only trigger on document changes
    if (!update.docChanged) return;

    // Cancel pending request
    if (timeout) clearTimeout(timeout);
    if (abortController) abortController.abort();

    // Clear current suggestion
    update.view.dispatch({
      effects: setSuggestion.of(null),
    });

    // Debounce new request
    timeout = setTimeout(async () => {
      const state = update.view.state;
      const pos = state.selection.main.head;
      const doc = state.doc.toString();
      const prefix = doc.slice(0, pos);
      const suffix = doc.slice(pos);

      // Skip if cursor at start or very short prefix
      if (prefix.length < 3) return;

      abortController = new AbortController();

      const completion = await fetchTabbyCompletion(
        endpoint,
        prefix,
        suffix,
        language,
        abortController.signal
      );

      if (completion && completion.length <= maxCompletionLength) {
        // Verify cursor hasn't moved
        const currentPos = update.view.state.selection.main.head;
        if (currentPos === pos) {
          update.view.dispatch({
            effects: setSuggestion.of({ text: completion, pos }),
          });
        }
      }
    }, delay);
  });

  // Keybindings (high precedence to override defaults)
  const completionKeymap = Prec.highest(
    keymap.of([
      {
        key: "Tab",
        run: (view) => {
          const suggestion = view.state.field(suggestionField);
          if (!suggestion) return false;

          view.dispatch({
            changes: { from: suggestion.pos, insert: suggestion.text },
            effects: setSuggestion.of(null),
            selection: { anchor: suggestion.pos + suggestion.text.length },
          });
          return true;
        },
      },
      {
        key: "Escape",
        run: (view) => {
          const suggestion = view.state.field(suggestionField);
          if (!suggestion) return false;

          view.dispatch({ effects: setSuggestion.of(null) });
          return true;
        },
      },
      {
        // Accept word-by-word with Ctrl+Right
        key: "Ctrl-ArrowRight",
        mac: "Cmd-ArrowRight",
        run: (view) => {
          const suggestion = view.state.field(suggestionField);
          if (!suggestion) return false;

          // Find next word boundary
          const match = suggestion.text.match(/^\S*\s*/);
          const word = match ? match[0] : suggestion.text;

          view.dispatch({
            changes: { from: suggestion.pos, insert: word },
            effects: setSuggestion.of(
              word.length < suggestion.text.length
                ? { text: suggestion.text.slice(word.length), pos: suggestion.pos + word.length }
                : null
            ),
            selection: { anchor: suggestion.pos + word.length },
          });
          return true;
        },
      },
    ])
  );

  return [suggestionField, plugin, completionKeymap];
}
```

### CSS Styles

```css
/* Ghost text styling */
.cm-ghost-text {
  color: var(--color-text-muted, #6b7280);
  opacity: 0.6;
  font-style: italic;
  pointer-events: none;
  user-select: none;
}

/* Optional: animate appearance */
.cm-ghost-text {
  animation: ghost-fade-in 0.15s ease-out;
}

@keyframes ghost-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 0.6;
  }
}
```

### Usage Example

```typescript
import { EditorView, basicSetup } from "codemirror";
import { python } from "@codemirror/lang-python";
import { tabbyCompletion } from "./lib/tabby-codemirror";

const editor = new EditorView({
  parent: document.getElementById("editor")!,
  extensions: [
    basicSetup,
    python(),
    tabbyCompletion({
      endpoint: "https://tabby.hemma.hule.education", // or http://localhost:8083
      language: "python",
      delay: 400,
    }),
  ],
});
```

## Operations

### Quick Health Check

```bash
# Check service status
ssh hemma "sudo systemctl status llama-server --no-pager"

# Test health endpoint
ssh hemma "curl -s http://localhost:8082/health"
# Expected: {"status":"ok"}

# Check VRAM usage
ssh hemma "rocm-smi --showmeminfo vram | grep Used"
# Expected: ~18.5 GB for Qwen3-Coder-30B-A3B Q4_K_M

# Test inference
ssh hemma 'curl -s http://localhost:8082/completion \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"def fibonacci(n):\", \"n_predict\": 50}" | jq -r .content'
```

### Start/Stop Services

```bash
# Start both services
ssh hemma "sudo systemctl start llama-server tabby"

# Stop both services
ssh hemma "sudo systemctl stop tabby llama-server"

# Restart (e.g., after model change)
ssh hemma "sudo systemctl restart llama-server && sleep 5 && sudo systemctl restart tabby"
```

### Monitor Performance

```bash
# Watch GPU usage during inference
ssh hemma "watch -n 1 rocm-smi"

# Check llama.cpp logs
ssh hemma "journalctl -u llama-server -f"

# Check Tabby logs
ssh hemma "journalctl -u tabby -f"

# Test completion API directly
ssh hemma 'curl -X POST http://localhost:8083/v1/completions \
  -H "Content-Type: application/json" \
  -d "{\"language\": \"python\", \"segments\": {\"prefix\": \"def hello(name):\\n    \", \"suffix\": \"\"}}"'
```

### Switch Models

```bash
# 1. Stop services
ssh hemma "sudo systemctl stop tabby llama-server"

# 2. Edit llama-server.service to change --model path
ssh hemma "sudo nano /etc/systemd/system/llama-server.service"

# 3. Reload and restart
ssh hemma "sudo systemctl daemon-reload && sudo systemctl start llama-server tabby"
```

### VRAM Monitoring

```bash
# Check VRAM usage
ssh hemma "rocm-smi --showmeminfo vram"

# Expected for Qwen 32B Q4: ~18-20 GB during inference
```

## Troubleshooting

### llama.cpp Won't Start

```bash
# Check logs
ssh hemma "journalctl -u llama-server -n 50"

# Common issues:
# - Model path wrong
# - VRAM insufficient (reduce --ctx-size or use smaller quant)
# - ROCm not detecting GPU (check HSA_OVERRIDE_GFX_VERSION)
```

### Build Crashes on RDNA 4 (gfx1201)

If the ROCm compiler (clang) crashes during build with segfault errors in flash attention files:

```text
clang++: error: clang frontend command failed due to signal
File: fattn-tile-instance-*.cu
```

**Fix:** Rebuild with flash attention disabled:

```bash
cd ~/llama.cpp
rm -rf build
cmake -B build -DGGML_HIP=ON -DGGML_HIP_FA=OFF -DGGML_CURL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j$(nproc)
```

This is a known issue with ROCm 7.1 and RDNA 4. Flash attention may be supported in future ROCm versions.

### Tabby Returns Empty Completions

```bash
# Test llama.cpp directly
ssh hemma 'curl http://localhost:8082/completion \
  -d "{\"prompt\": \"def hello\"}" \
  -H "Content-Type: application/json"'

# If llama.cpp works but Tabby doesn't, check prompt_template in config.toml
```

### High Latency

- Reduce `--ctx-size` (e.g., 4096 instead of 8192)
- Use Q4 quantization instead of Q8
- Increase `--threads` if CPU-bound
- Check if GPU is throttling: `rocm-smi --showtemp`

### CodeMirror Ghost Text Not Showing

- Check browser console for fetch errors
- Verify CORS headers if Tabby on different origin
- Check network tab for 401/403 (auth issues)

## Performance Tuning

### llama.cpp Server Options

```bash
# Optimized for latency
--ctx-size 4096        # Smaller context = faster
--n-gpu-layers 99      # All layers on GPU
--threads 8            # Match physical cores
--parallel 2           # Concurrent requests
--cont-batching        # Better throughput
# NOTE: --flash-attn crashes on RDNA 4 (gfx1201), disabled via -DGGML_HIP_FA=OFF at build time

# Optimized for quality
--ctx-size 16384       # Larger context
--temp 0.2             # Lower temperature for code
--top-p 0.9            # Nucleus sampling
```

### Tabby Completion Tuning

Adjust in CodeMirror config:

```typescript
tabbyCompletion({
  endpoint: "...",
  language: "python",
  delay: 300,              // Lower = more responsive, more requests
  maxCompletionLength: 200 // Limit long completions
})
```

## Known Issues & Lessons Learned

### Port Conflicts on hemma.hule.education

| Port | Service | Notes |
|------|---------|-------|
| 8080 | node | Pre-existing service |
| 8081 | Apache httpd | Pre-existing service |
| 8082 | llama-server | Our ROCm inference server |
| 8083 | Tabby | Our completion proxy |
| 30888 | llama-server (Tabby) | Tabby's internal embedding server (CPU) |

### RDNA 4 (gfx1201) Flash Attention Crash

ROCm 7.1.1's clang compiler crashes when building flash attention kernels for gfx1201. The workaround is to disable flash attention at build time with `-DGGML_HIP_FA=OFF`. This may be fixed in future ROCm releases.

### llama.cpp Makefile Deprecated

As of late 2024, llama.cpp requires CMake builds. The old `make GGML_HIP=1` approach no longer works. Use the CMake workflow documented in Step 2.

### Tabby Authentication

Tabby v0.31+ has authentication enabled by default. For local/personal use without user management, use the `--no-webserver` flag which:

- Disables the web UI entirely
- Removes authentication requirements
- Serves only the `/v1/completions` and `/v1/chat/completions` APIs

For production deployments with multiple users, omit this flag and set up the first admin user via the web UI.

### Tabby Requires Bundled llama-server

Even when using an external HTTP backend (like our ROCm llama-server), Tabby still requires its bundled `llama-server` binary in the same directory. This is used internally for:

- Text embeddings (Nomic-Embed-Text model)
- Repository indexing features

The bundled llama-server runs on CPU and doesn't conflict with our GPU-accelerated llama-server.

## References

- [Tabby Documentation](https://tabby.tabbyml.com/docs/)
- [llama.cpp Server](https://github.com/ggerganov/llama.cpp/tree/master/examples/server)
- [CodeMirror 6 Decorations](https://codemirror.net/docs/ref/#view.Decoration)
- [Qwen Models](https://huggingface.co/Qwen)
- [Using Tabby without authentication](https://github.com/TabbyML/tabby/issues/3236)
