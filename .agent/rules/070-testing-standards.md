---
id: "070-testing-standards"
type: "quality"
created: 2025-12-13
scope: "all"
---

# 070: Testing Standards

## 1. Test Organization

```text
tests/
├── unit/                    # Pure business logic tests
│   ├── domain/
│   │   ├── test_user_service.py
│   │   └── test_order_service.py
│   └── __init__.py
├── integration/             # Database + external services
│   ├── test_user_repository.py
│   └── test_order_flow.py
├── fixtures/                # Explicit fixture modules
│   ├── __init__.py
│   ├── user_fixtures.py
│   └── database_fixtures.py
└── conftest.py              # Minimal: only re-exports from fixtures/
```

## 2. No Conftest Magic

Fixtures **MUST** be explicit imports, not conftest discovery:

```python
# tests/conftest.py (minimal)
from tests.fixtures.user_fixtures import mock_user_repo, sample_user
from tests.fixtures.database_fixtures import test_engine, test_session

__all__ = ["mock_user_repo", "sample_user", "test_engine", "test_session"]
```

```python
# tests/fixtures/user_fixtures.py
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.protocols import UserRepositoryProtocol
from src.domain.users.models import User

@pytest.fixture
def mock_user_repo() -> AsyncMock:
    """Mock user repository for unit tests."""
    return AsyncMock(spec=UserRepositoryProtocol)

@pytest.fixture
def sample_user() -> User:
    """Sample user for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
    )
```

## 3. Protocol-Based Mocking

Always mock protocols, not implementations:

```python
# tests/unit/domain/test_user_service.py
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.protocols import UserRepositoryProtocol, EventPublisherProtocol
from src.domain.users.services import _create_user_impl
from src.domain.users.models import CreateUserDTO, User

@pytest.mark.asyncio
async def test_create_user_publishes_event():
    # Arrange
    mock_repo = AsyncMock(spec=UserRepositoryProtocol)
    mock_publisher = AsyncMock(spec=EventPublisherProtocol)

    created_user = User(id=uuid4(), email="new@example.com", name="New User")
    mock_repo.create.return_value = created_user

    # Act
    result = await _create_user_impl(
        repo=mock_repo,
        publisher=mock_publisher,
        data=CreateUserDTO(email="new@example.com", name="New User"),
        correlation_id=uuid4(),
    )

    # Assert
    assert result.email == "new@example.com"
    mock_repo.create.assert_called_once()
    mock_publisher.publish.assert_called_once()
```

## 4. Pure Implementation Testing

Extract pure functions for unit tests:

```python
# src/domain/users/services.py
async def _create_user_impl(
    repo: UserRepositoryProtocol,
    publisher: EventPublisherProtocol,
    data: CreateUserDTO,
    correlation_id: UUID,
) -> User:
    """Pure implementation for unit testing."""
    user = await repo.create(data)
    await publisher.publish(...)
    return user

class UserService(UserServiceProtocol):
    async def create(self, data: CreateUserDTO, correlation_id: UUID) -> User:
        return await _create_user_impl(
            self._repo, self._publisher, data, correlation_id
        )
```

Test `_create_user_impl` directly with mocked dependencies.

## 5. Integration Tests

Introduce integration tests after PostgreSQL repositories/models exist.

When ready, use testcontainers for database tests:

```python
# tests/integration/test_user_repository.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from src.infrastructure.models.user import Base
from src.domain.users.models import CreateUserDTO

@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture
async def test_engine(postgres_container):
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
def user_repo(test_engine) -> PostgreSQLUserRepository:
    return PostgreSQLUserRepository(test_engine)

@pytest.mark.asyncio
async def test_create_and_retrieve_user(user_repo):
    # Create
    user = await user_repo.create(
        CreateUserDTO(email="test@example.com", name="Test")
    )
    assert user.id is not None

    # Retrieve
    found = await user_repo.get_by_id(user.id)
    assert found is not None
    assert found.email == "test@example.com"
```

## 6. Test Constraints

| Constraint | Value |
|------------|-------|
| Max LoC per test file | <500 |
| Max timeout per test | 30s (60s for integration) |
| Max assertions per test | 3-5 |
| Test isolation | Tests must be independent |

## 7. Async Test Pattern

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

Configure in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## 8. Error Testing

```python
import pytest
from src.domain.errors import DomainError, ErrorCode

@pytest.mark.asyncio
async def test_raises_not_found_for_missing_user():
    mock_repo = AsyncMock(spec=UserRepositoryProtocol)
    mock_repo.get_by_id.return_value = None

    with pytest.raises(DomainError) as exc_info:
        await _get_user_impl(repo=mock_repo, user_id=uuid4())

    assert exc_info.value.code == ErrorCode.NOT_FOUND
```

## 9. Forbidden Test Patterns

| Pattern | Why | Alternative |
|---------|-----|-------------|
| `try/except pass` in tests | Hides failures | Let exceptions propagate |
| Mocking implementations | Couples to internals | Mock protocols |
| `@patch` decorator | Hidden dependencies | Constructor injection |
| Shared mutable state | Test interference | Fresh fixtures per test |
| `assert caplog.text` | Fragile string matching | Structured log assertions |
| Simplifying to pass | Hides bugs | Fix implementation |

## 10. Test Naming

```python
# Pattern: test_{method}_{scenario}_{expected_result}
def test_create_user_with_duplicate_email_raises_conflict(): ...
def test_get_user_when_not_exists_returns_none(): ...
def test_complete_order_when_cancelled_raises_business_error(): ...
```

## 11. Coverage Requirements

| Type | Coverage |
|------|----------|
| Domain services | >90% |
| Repositories | >80% |
| API routers | >70% |
| Overall | >80% |

Run with:

```bash
pytest --cov=src --cov-report=term-missing
```
