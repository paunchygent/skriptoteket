# Historical documentation validator

This directory preserves the legacy Skriptoteket documentation validator as a
read-only historical inspection tool. It selects only records whose paths and
identifiers still match `docs/_meta/docs-contract.yaml`.

The shared `repository-governance` commands are the sole authority for current
documents, generated indexes, hooks, and lifecycle operations. This validator
has no PDM binding, pre-commit hook, CI gate, index generator, or mutation path.

Run it manually from the repository root only when historical evidence needs
inspection:

```text
pdm run python -m scripts.historical_docs.validate_historical_docs
```
