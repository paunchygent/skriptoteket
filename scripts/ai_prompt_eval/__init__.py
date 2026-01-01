"""AI prompt evaluation harness (dev tooling).

This package is intentionally dev-only:
- It talks to a live backend over HTTP (session cookie + CSRF).
- It writes metadata-only artifacts under `.artifacts/ai-prompt-eval/`.
"""
