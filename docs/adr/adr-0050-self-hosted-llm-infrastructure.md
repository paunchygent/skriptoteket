---
type: adr
id: ADR-0050
title: "Self-hosted LLM infrastructure for AI code completion"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-30
supersedes: []
---

## Context

ADR-0043 specifies an OpenAI-compatible backend proxy for AI inline completions. That ADR focuses on the
application-layer protocol and CodeMirror integration. This ADR documents the **infrastructure decision**: which
model to run and how to host it.

### Requirements

- Local/self-hosted inference for privacy and cost control
- Sufficient quality for code completion (FIM / fill-in-middle)
- Runs on available hardware: AMD Radeon AI PRO R9700 (32GB VRAM, RDNA 4, gfx1201)
- OpenAI-compatible API for integration with Tabby and future CodeMirror ghost-text
- Low operational complexity (systemd services, no Kubernetes)

### Hardware Available

| Component    | Spec                                      |
|--------------|-------------------------------------------|
| GPU          | AMD Radeon AI PRO R9700 (RDNA 4, gfx1201) |
| VRAM         | 32 GB GDDR6                               |
| Driver/Stack | ROCm 7.1.1, kernel 6.14 HWE               |
| Server       | hemma.hule.education (Ubuntu 24.04)       |

### Options Considered

| Option                       | VRAM   | Quality         | Speed     | Notes                                    |
|------------------------------|--------|-----------------|-----------|------------------------------------------|
| Qwen2.5-Coder-32B Q4         | ~18 GB | Excellent       | Slow      | Dense model, full 32B active per token   |
| Qwen3-Coder-30B-A3B Q4_K_M   | ~18 GB | Excellent       | Fast      | MoE: 30B total, 3.3B active (8/128)      |
| CodeLlama-34B Q4             | ~20 GB | Good            | Slow      | Older, less instruction-following        |
| DeepSeek-Coder-33B Q4        | ~20 GB | Good            | Slow      | Strong but slower than MoE               |
| Smaller models (7B-13B)      | ~4-8GB | Moderate        | Very fast | Quality trade-off for code completion    |

### Why Tabby?

Tabby provides:

- FIM prompt templating for code completion
- OpenAI-compatible `/v1/completions` API
- Repository indexing for context (future use)
- Proxies to external llama.cpp for GPU inference

Alternative considered: direct llama.cpp API. Rejected because Tabby's FIM templating and
repository indexing features add value for code completion use cases.

## Decision

Use **Qwen3-Coder-30B-A3B** (MoE architecture) with **Tabby** proxying to **llama.cpp** (ROCm).

### Architecture

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CodeMirror 6   │────▶│  Tabby Server   │────▶│  llama.cpp      │
│  (Frontend)     │     │  :8083          │     │  :8082 (ROCm)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
   /v1/completions         FIM templating        Qwen3-Coder-30B-A3B
```

### Model Choice Rationale

Qwen3-Coder-30B-A3B uses Mixture-of-Experts (MoE):

- **30.5B total parameters** for quality
- **3.3B active per token** (8 of 128 experts) for speed
- Inference speed comparable to a 3B dense model
- Quality comparable to a 30B dense model
- Fits comfortably in 32GB VRAM with Q4_K_M quantization (~18.5 GB)

### Service Configuration

| Service      | Port  | Binary/Config                                         |
|--------------|-------|-------------------------------------------------------|
| llama-server | 8082  | `/home/paunchygent/llama.cpp/build/bin/llama-server`  |
| tabby        | 8083  | `/usr/local/bin/tabby serve --port 8083 --no-webserver` |

Both run as systemd services (`llama-server.service`, `tabby.service`).

### Build Notes (RDNA 4 / gfx1201)

llama.cpp must be built with flash attention disabled due to ROCm 7.1.1 compiler crash:

```bash
cmake -B build -DGGML_HIP=ON -DGGML_HIP_FA=OFF -DGGML_CURL=ON -DCMAKE_BUILD_TYPE=Release
```

## Consequences

### Positive

- **Privacy**: All inference runs on-premises; no code sent to external APIs
- **Cost**: Zero per-token costs after initial setup
- **Speed**: MoE architecture provides fast inference (~1-2s for typical completions)
- **Quality**: 30B-class model quality for code completion
- **Flexibility**: Can swap models by changing llama-server config

### Negative

- **Maintenance**: Self-hosted infrastructure requires updates (ROCm, llama.cpp, Tabby)
- **Single point of failure**: One GPU server; no redundancy
- **RDNA 4 early adoption**: Flash attention disabled; may improve in future ROCm versions

### Mitigations

- Runbooks document maintenance procedures: `docs/runbooks/runbook-gpu-ai-workloads.md`,
  `docs/runbooks/runbook-tabby-codemirror.md`
- Systemd services auto-restart on failure
- Health check: `curl http://localhost:8083/v1/health`

## References

- [ADR-0043: AI-assisted inline completions](adr-0043-ai-completion-integration.md) - Application layer design
- [ADR-0035: Script editor intelligence](adr-0035-script-editor-intelligence-architecture.md) - CodeMirror architecture
- [EPIC-08: Contextual help and onboarding](../backlog/epics/epic-08-contextual-help-and-onboarding.md)
- [ST-08-14: AI inline completions](../backlog/stories/story-08-14-ai-inline-completions.md)
- [Runbook: GPU AI Workloads](../runbooks/runbook-gpu-ai-workloads.md)
- [Runbook: Tabby + CodeMirror](../runbooks/runbook-tabby-codemirror.md)
- [Qwen3-Coder-30B-A3B model](https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF)
