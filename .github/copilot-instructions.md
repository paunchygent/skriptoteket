# Repository instructions for Copilot

Follow `AGENTS.md`.

Documentation contract:
- MUST follow `docs/_meta/docs-contract.yaml`
- MUST NOT create new parent folders under `docs/` without updating the contract
- MUST include YAML frontmatter for docs (unless exempt)
- MUST follow naming regex and id-from-filename rules per document type

Before proposing or committing docs changes:
- Run: `pdm run docs-validate`

