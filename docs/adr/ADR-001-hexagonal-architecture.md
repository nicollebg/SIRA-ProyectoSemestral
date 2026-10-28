# ADR-001: Adopt Hexagonal Architecture (Ports & Adapters) with DDD Bounded Contexts

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** SIRA project team (Taller de Programación 2026-262)

## Context

SIRA (Academic Registration System) started as a Streamlit application where `app.py`
(UI), `services.py` (business logic, ~1,300 lines) and SQLAlchemy models were tightly coupled.
This caused three problems:

1. Business rules could only be tested against a real database.
2. Adding external data sources (datos.gov.co, DANE/DIVIPOLA) would have mixed HTTP code,
   retries and analytics into `services.py`.
3. The business logic depended directly on frameworks (Streamlit, SQLAlchemy, requests).

## Decision

We refactor incrementally into four layers with dependencies pointing **inward only**:

| Layer | Folder | Responsibility |
|---|---|---|
| Domain | `domain/` | Pure entities, errors and **ports** (abstract interfaces). No framework imports. |
| Application | `application/` | Use cases (`CatalogService`, `EnrollmentService`, `OpenDataService`) with **constructor dependency injection**. |
| Infrastructure | `infrastructure/` | **Adapters**: SQLAlchemy reader, legacy enrollment gateway, Socrata HTTP client, circuit breaker + retry, DuckDB analytics. |
| API / Entry | `api/` | Composition root (`container.py`) and Streamlit pages. |

### Bounded contexts (DDD)

1. **Enrollment** – groups, seats, enrollments, waitlists (core domain; transactional locking).
2. **Identity & Access** – authentication and roles (student / coordinator).
3. **Operational Metrics** – performance metrics and the concurrency simulator for the coordinator.
4. **Open Data & Analytics** – external Colombian public data (MEN/SNIES institutions and DANE DIVIPOLA codes via datos.gov.co) analysed with DuckDB.

### Resilience for external APIs

Each API client is wrapped with a **circuit breaker** (CLOSED → OPEN → HALF_OPEN) and
**retry with exponential backoff** (0.5 s, 1 s, 2 s, …). If one API is down, the other
keeps working (graceful degradation).

### Migration strategy

`LegacyEnrollmentGateway` wraps the existing, tested `services.inscribir_estudiante`
(strangler pattern), so the proven row-locking logic is reused while the rest of `services.py`
is migrated behind ports one use case at a time.

## Consequences

**Positive**
- Use cases are unit-testable with mocks (no DB, no network): see `tests/test_services_with_mocks.py`.
- Swapping MySQL, an HTTP API or DuckDB only requires a new adapter.
- Failures of external APIs do not break enrollment.

**Negative / trade-offs**
- More files and indirection for a small application.
- Temporary duplication: `services.py` and the new use cases coexist until the migration ends.
- Dataset schemas from datos.gov.co can change; analytics queries discover columns dynamically to reduce breakage.

## Alternatives considered

- **Keep the layered monolith (`app.py` + `services.py`)** – rejected: not testable in isolation.
- **Full rewrite at once** – rejected: high risk of breaking the concurrency-safe enrollment logic.
