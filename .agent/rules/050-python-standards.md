---
id: "050-python-standards"
type: "implementation"
created: 2025-12-13
scope: "all"
---

# 050: Python Coding Standards

## 1. File Size Limits

| Metric | Limit |
|--------|-------|
| Lines per file | <400-500 LoC |
| Lines per function | <50 |
| Lines per class | <200 |

Exceeding limits forces decomposition.

## 2. Formatting (Ruff)

```bash
# Format
ruff format .

# Lint with auto-fix
ruff check --fix .
```

### Style Rules

- **Line length**: 100 characters
- **Quotes**: Double quotes
- **Indent**: 4 spaces
- **Trailing commas**: Required in multi-line structures

```python
# Correct
result = {
    "key": "value",
    "another": "value",
}

# Incorrect
result = {
    'key': 'value',
    'another': 'value'
}
```

## 3. Typing Requirements

All public functions **MUST** have type hints:

```python
# Correct
async def get_user(user_id: UUID) -> User | None:
    ...

# Incorrect (missing types)
async def get_user(user_id):
    ...
```

### Common Type Patterns

```python
from typing import Protocol, TypeVar, Generic
from uuid import UUID
from collections.abc import Sequence, Mapping

# Optional (use | None, not Optional)
def find(id: UUID) -> User | None: ...

# Collections
def process(items: list[Item]) -> dict[str, Result]: ...

# Generics
T = TypeVar("T")
class Repository(Generic[T], Protocol):
    async def get(self, id: UUID) -> T | None: ...

# Callable
from collections.abc import Callable, Awaitable
Handler = Callable[[Request], Awaitable[Response]]
```

## 4. Import Organization

```python
# Standard library
from datetime import datetime
from uuid import UUID

# Third-party
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

# Local (absolute from src/)
from src.protocols import UserRepositoryProtocol
from src.domain.users.models import User
```

**Rules**:

- Absolute imports only (never relative across modules)
- Group: stdlib → third-party → local
- One import per line for clarity (or grouped with parentheses)

## 5. Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Module | snake_case | `user_service.py` |
| Class | PascalCase | `UserService` |
| Function | snake_case | `get_user_by_id` |
| Variable | snake_case | `user_count` |
| Constant | UPPER_SNAKE | `MAX_RETRIES` |
| Protocol | PascalCase + Protocol | `UserRepositoryProtocol` |
| Private | _prefix | `_internal_method` |

## 6. Docstrings

Use Google style for public APIs:

```python
async def create_user(
    self,
    data: CreateUserDTO,
    correlation_id: UUID,
) -> User:
    """Create a new user and publish creation event.

    Args:
        data: User creation data.
        correlation_id: Request correlation ID for tracing.

    Returns:
        The created user entity.

    Raises:
        DomainError: If user with email already exists (DUPLICATE_ENTRY).
    """
```

Docstrings required for:

- Public classes
- Public methods
- Module-level functions
- Complex private functions

## 7. Comments

```python
# Good: Explains WHY
# Use semaphore to prevent overwhelming the payment API (rate limit: 10 RPS)
semaphore = asyncio.Semaphore(10)

# Bad: Explains WHAT (obvious from code)
# Create a semaphore with value 10
semaphore = asyncio.Semaphore(10)
```

## 8. Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()

class User(BaseModel):
    id: UUID
    email: str
    name: str

    model_config = {"from_attributes": True}  # ORM mode
```

## 9. Async/Await

```python
# Correct: async function for I/O
async def fetch_user(user_id: UUID) -> User:
    return await repo.get_by_id(user_id)

# Correct: sync function for pure computation
def calculate_score(results: list[Result]) -> float:
    return sum(r.value for r in results) / len(results)

# Incorrect: unnecessary async
async def format_name(first: str, last: str) -> str:  # No I/O!
    return f"{first} {last}"
```

## 10. Exception Handling

```python
# Good: Specific exception, proper handling
try:
    user = await repo.get_by_id(user_id)
except IntegrityError as e:
    raise DomainError(
        code=ErrorCode.DATABASE_ERROR,
        message="Database error",
        details={"error": str(e)},
    ) from e

# Bad: Bare except
try:
    user = await repo.get_by_id(user_id)
except:  # FORBIDDEN
    pass

# Bad: Catching too broadly
try:
    user = await repo.get_by_id(user_id)
except Exception:  # Too broad without re-raise
    return None
```

## 11. Forbidden Patterns

| Pattern | Alternative |
|---------|-------------|
| `from x import *` | Explicit imports |
| `try/except pass` | Handle or re-raise |
| `type: ignore` without reason | Fix the type issue |
| Magic numbers | Named constants |
| Mutable default args | `field(default_factory=...)` |
| Global mutable state | DI injection |
