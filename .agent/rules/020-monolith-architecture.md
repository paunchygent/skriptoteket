---
id: "020-monolith-architecture"
type: "architecture"
created: 2025-12-13
scope: "all"
---

# 020: Monolith Layer Architecture

## 1. Directory Structure

```text
src/
├── app.py                    # FastAPI application factory
├── config.py                 # Pydantic Settings (env-based)
├── protocols.py              # ALL Protocol definitions
├── di.py                     # Dishka container setup
│
├── api/                      # HTTP Layer (thin)
│   ├── v1/
│   │   ├── __init__.py       # Router aggregation
│   │   ├── users.py          # User endpoints
│   │   └── orders.py         # Order endpoints
│   └── middleware/
│       ├── correlation.py    # Correlation ID injection
│       └── error_handler.py  # Global exception → response
│
├── web/                      # Server-rendered UI (thin)
│   ├── __init__.py           # Router aggregation
│   ├── pages/                # Page routes (HTML)
│   ├── partials/             # HTMX partial endpoints
│   ├── templates/            # Jinja2 templates
│   └── static/               # Static assets (CSS/JS)
│
├── domain/                   # Business Logic (pure)
│   ├── users/
│   │   ├── services.py       # Application services
│   │   ├── models.py         # Domain entities (Pydantic)
│   │   └── events.py         # Domain events
│   └── orders/
│       ├── services.py
│       ├── models.py
│       └── events.py
│
├── infrastructure/           # External Integrations
│   ├── repositories/
│   │   ├── user_repository.py
│   │   └── order_repository.py
│   ├── clients/              # External HTTP clients
│   │   └── payment_client.py
│   └── publishers/           # Kafka publishers
│       └── event_publisher.py
│
├── workers/                  # Kafka Consumers (optional)
│   ├── __init__.py
│   └── order_consumer.py
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

## 2. Layer Rules

### API Layer (`api/`)

- **Thin**: Validation, routing, response formatting only
- **No business logic**: Delegates to domain services
- **DTOs**: Pydantic models for request/response
- **Size**: <150 LoC per router file

```python
@router.post("/users", response_model=UserResponse)
@inject
async def create_user(
    request: CreateUserRequest,
    service: FromDishka[UserServiceProtocol],
) -> UserResponse:
    user = await service.create(request)
    return UserResponse.from_domain(user)
```

### Web Layer (`web/`)

- **Thin**: routing + template rendering only
- **No business logic**: calls application/domain handlers via protocols
- **HTMX-friendly**: partial endpoints return HTML fragments

```python
@router.get("/tools", response_class=HTMLResponse)
@inject
async def list_tools(
    request: Request,
    handler: FromDishka[ListToolsQueryHandlerProtocol],
):
    result = await handler.handle(ListToolsQuery())
    return templates.TemplateResponse(
        request=request,
        name="tools/index.html",
        context={"tools": result.tools},
    )
```

### Domain Layer (`domain/`)

- **Pure business logic**: No framework dependencies
- **Protocol dependencies**: Injected via constructor
- **Domain events**: Defined here, published via injected publisher
- **No I/O**: All I/O through injected protocols

```python
class UserService(UserServiceProtocol):
    def __init__(
        self,
        repo: UserRepositoryProtocol,
        publisher: EventPublisherProtocol,
    ):
        self._repo = repo
        self._publisher = publisher

    async def create(self, data: CreateUserDTO) -> User:
        user = await self._repo.create(data)
        await self._publisher.publish(UserCreatedEvent(user_id=user.id))
        return user
```

### Infrastructure Layer (`infrastructure/`)

- **Protocol implementations**: Repositories, clients, publishers
- **Framework-specific**: SQLAlchemy, aiohttp, aiokafka
- **Transactions**: Unit of Work owns session + commit/rollback; repositories receive a session and never commit
- **No business logic**: Data access and external calls only

## 3. Dependency Direction

```text
api/ ──depends on──▶ domain/ ◀──implements── infrastructure/
         │                           │
         └─────── protocols.py ◀─────┘
```

- **Domain**: Zero external dependencies (pure Python + Pydantic)
- **API**: Depends on domain protocols
- **Infrastructure**: Implements domain protocols

## 4. Cross-Cutting Files

| File | Purpose | Location |
|------|---------|----------|
| `protocols.py` | All Protocol definitions | `src/` root |
| `config.py` | Pydantic Settings | `src/` root |
| `di.py` | Dishka provider setup | `src/` root |
| `app.py` | FastAPI factory | `src/` root |

## 5. Forbidden Patterns

| Pattern | Why Forbidden |
|---------|---------------|
| Direct DB access in API | Violates layer separation |
| Business logic in routers | Domain logic belongs in domain/ |
| Infrastructure imports in domain | Domain must stay pure |
| Circular imports | Indicates architecture violation |
| God classes (>500 LoC) | Violates single responsibility |

## 6. Domain Boundaries

Each domain subdirectory (`domain/users/`, `domain/orders/`) is a bounded context:

- Has its own models, services, events
- Communicates with other domains via domain events
- Never imports directly from other domain subdirectories
