# Next Session Instruction Prompt Template

Use this when the user asks for a next-session handoff or a message to a new
developer/agent.

Rules:

- Address the recipient as **you**.
- Include concrete file references, commands, verification state, and blockers.
- Do not assume the reader saw the prior chat.
- Do not include secrets, tokens, passwords, or private credentials.
- Do not edit this template to store session state. Generate the handoff as a
  chat message.

## Prompt Shape

You are working in the Skriptoteket repo.

Start by reading:

1. `AGENTS.md`
1. `.codex/handoff.md`
1. the task-relevant skill
1. `.codex/rules/000-rule-index.md` only if repo rules are needed
1. `docs/index.md` for durable docs discovery

Current task:

- Backlog item:
- Goal:
- Current branch/state:
- Files or areas already touched:
- Decisions already made:
- Known blockers or risks:

Required context:

- Product/domain context:
- Architecture constraints:
- Relevant docs/runbooks:
- Relevant skills:
- Relevant rules:

Implementation expectations:

- Keep changes scoped to the named backlog item.
- Follow DDD/Clean Architecture boundaries.
- Keep modules under the repo file-size limits.
- Update docs/backlog and `.codex/handoff.md` when status, scope, or
  verification state changes.
- Run the task-relevant validation gates and record exact results.

Close-out:

- Summarize what changed.
- List verification commands and results.
- Note any residual risks.
- Produce a fresh next-session handoff only if the work is not complete.
