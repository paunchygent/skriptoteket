# Docs Contract

Documentation in `docs/` is governed by a strict contract:

- **Allowed folders**: only the allowlist in `docs/_meta/docs-contract.yaml`
- **Naming + placement**: enforced by regex per document type
- **Frontmatter**: required for all docs except explicitly exempt files

Run `pdm run docs-validate` before opening a PR that changes documentation.
