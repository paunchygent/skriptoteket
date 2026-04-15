# Architect Review: ST-08-10 Script Editor Intelligence

## Context Package

**File**: `repomix-st08-10-editor-intelligence-architecture.xml` (22K tokens)

## Objective

Design a CodeMirror 6 extension suite that provides in-editor intelligence for Skriptoteket tool script authors. The goal is **discoverability** - helping authors find available helpers and catch errors before running.

## Background

Skriptoteket runs Python scripts in isolated Docker containers. Scripts must follow a specific contract:

```python
def run_tool(input_path: str, output_dir: str) -> str | dict:
    # Process input, write artifacts to output_dir
    return {"outputs": [...], "next_actions": [...], "state": None}
```

Two helper modules are available inside the container:
- `pdf_helper.save_as_pdf(html, output_dir, filename)` - HTML to PDF rendering
- `tool_errors.ToolUserError` - Clean user-facing error messages

**Problem**: Authors don't know these helpers exist. The KB documentation isn't surfaced in the editor.

## Research Questions

### 1. CodeMirror 6 Architecture

- How do `@codemirror/autocomplete`, `@codemirror/lint`, and tooltip extensions compose?
- What's the performance model for linting? (debounce, incremental, full-doc?)
- Can we share state between completions/lint/hover (e.g., parsed AST)?

### 2. Python Analysis in Browser

- Is there a lightweight Python parser for JS/TS? (tree-sitter-python? Lezer grammar?)
- Or should we use regex-based pattern matching for simplicity?
- What's the trade-off between accuracy and complexity?

### 3. Lint Rule Implementation

Review the KB (`ref-ai-script-generation-kb.md`) and propose implementation approach for:

| Rule Category | Example | Detection Method |
|---------------|---------|------------------|
| Entrypoint | Missing `def run_tool` | Regex or AST |
| Contract | `outputs` not a list | Regex on return statements |
| Security | Using `requests` | Import statement scan |
| Best practices | Missing `encoding=` | Function call pattern |

### 4. Completion Source Design

- Static completions (imports, contract keys) vs dynamic (context-aware)?
- How to trigger import completions on `from ` prefix?
- Should we complete inside dict literals for contract keys?

### 5. Hover Documentation

- What tooltip API does CodeMirror 6 provide?
- How to detect hover target (function name, import)?
- Inline Swedish docs or link to external KB?

## Deliverables

1. **Technical Design Document** answering the research questions
2. **Extension Architecture** - how the 3 extensions compose
3. **Lint Rules Specification** - detection patterns for each rule
4. **Risk Assessment** - complexity, performance, maintenance concerns
5. **Implementation Recommendation** - phased approach if needed

## Constraints

- **No external services** - all analysis must run in-browser
- **Swedish UI** - lint messages and hover docs in Swedish
- **Performance** - must not lag the editor on large scripts (500+ lines)
- **Maintainability** - rules should be easy to add/modify as KB evolves

## Files to Study

From the repomix package:

| File | Purpose |
|------|---------|
| `story-08-10-script-editor-intelligence.md` | Feature requirements |
| `ref-ai-script-generation-kb.md` | **Source of truth** for all lint rules |
| `CodeMirrorEditor.vue` | Current CM6 setup (extensions, keymaps) |
| `useScriptEditor.ts` | Editor state management pattern |
| `_runner.py` | Runner contract implementation |
| `pdf_helper.py`, `tool_errors.py` | Helpers to document in hover |

## Success Criteria

An architect reviewing this should be able to:

1. Understand what we're building and why
2. Evaluate technical approaches for Python analysis
3. Propose a concrete extension architecture
4. Identify risks and complexity hotspots
5. Recommend a phased implementation plan

## Notes

- The lint rules in ST-08-10 are comprehensive but can be prioritized
- Phase 1 could focus on: import completions + missing entrypoint lint + hover docs
- Phase 2: contract validation + security warnings
- Phase 3: best practices (lower severity, nice-to-have)
