---
type: reference
id: REF-SKRIPT-GENERAL-ai-completion-architecture-technical-specification
title: AI Completion Architecture Technical Specification
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
  - REF-ai-completion-architecture
summary: AI Completion Architecture Technical Specification
---

## Overview

Technical architecture for the script editor's AI features (inline completions, chat, chat ops and edit). Every
model call goes through HuleEdu's LLM provider door. The reference is split into these ordered parts:

- [Part 01](ref-skript-general-ai-completion-architecture-technical-specification-ai-completion-architecture-technical-specification-part-01.md)
- [Part 02](ref-skript-general-ai-completion-architecture-technical-specification-ai-completion-architecture-technical-specification-part-02.md)

## Facts And Semantics

Door routing, request bodies, prompt budgeting, the API contract and the 429 limit behavior are in
[Part 01](ref-skript-general-ai-completion-architecture-technical-specification-ai-completion-architecture-technical-specification-part-01.md).
The CodeMirror extension, settings tables, security, files and testing are in
[Part 02](ref-skript-general-ai-completion-architecture-technical-specification-ai-completion-architecture-technical-specification-part-02.md).

## Decisions And Interpretation

Inline completion runs on `gpt-6-luna`, and chat, chat ops and edit run on `gpt-6.1-sol` at low reasoning, all through
the door with the teacher's user id. Part 02 lists the decisions.
