---
id: "010-foundational-principles"
type: "architecture"
created: 2025-12-13
scope: "all"
---

# 010: Foundational Principles

## 1. Philosophy

This application follows:
- **DDD**: Domain-Driven Design with clear bounded contexts
- **Clean Architecture**: Dependencies point inward (domain has no external dependencies)
- **SOLID**: Single responsibility, dependency inversion, interface segregation
- **YAGNI**: No speculative abstractions; solve today's problems

## 2. Zero Tolerance for "Vibe Coding"

"Vibe coding" (intuition-based implementation, undocumented shortcuts) is **FORBIDDEN**.

- Every change follows established patterns
- No makeshift solutions or "temporary" hacks
- No legacy support or compatibility shims: do the full refactor (delete old paths) instead of workarounds
- If a pattern doesn't exist, propose it first
- Deviant code **MUST** be refactored immediately

## 3. Protocol-First Development

All dependencies are defined as `typing.Protocol` interfaces:

```python
# Correct: depend on protocol
class UserService:
    def __init__(self, repo: UserRepositoryProtocol): ...

# Forbidden: depend on implementation
class UserService:
    def __init__(self, repo: PostgreSQLUserRepository): ...
```

Benefits:
- Testability via protocol mocks
- Swappable implementations
- Clear contracts between layers

## 4. Understand Before Implementing

Before coding, you **MUST** understand:
1. Task requirements and acceptance criteria
2. Relevant architectural rules
3. Existing patterns in the codebase
4. Contracts (Pydantic models, event schemas) involved

If unclear, seek clarification **before** implementation.

## 5. File Size Limits

**<400-500 LoC hard limit per file** (including tests).

Forces:
- Single responsibility
- Decomposition into focused modules
- Readable, maintainable code

## 6. Leave Code Cleaner

Every commit should leave the codebase cleaner:
- Fix adjacent code smells when touching a file
- Update outdated patterns to current standards
- Remove dead code and unused imports

---

**Compliance is mandatory. These principles are non-negotiable.**
