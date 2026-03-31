# Task Management System — Agent Guidelines

This file is the authoritative reference for all agents working in this repository.
Read it in full before writing any code.

---

## Table of Contents

1. [Project Architecture](#1-project-architecture)
2. [Tech Stack](#2-tech-stack)
3. [Backend Coding Standards](#3-backend-coding-standards)
4. [Frontend Coding Standards](#4-frontend-coding-standards)
5. [API Response Envelope](#5-api-response-envelope)
6. [Sub-Agent Roles](#6-sub-agent-roles)
7. [Patterns to Follow](#7-patterns-to-follow)
8. [Patterns to Avoid](#8-patterns-to-avoid)

---

## 1. Project Architecture

```
Task-Management-System/
├── backend/                  # FastAPI application
│   ├── api/
│   │   ├── main.py           # FastAPI app factory; mounts all routers under /api
│   │   ├── config.py         # Placeholder — reserved for future settings
│   │   ├── database.py       # Placeholder — reserved for future DB integration
│   │   ├── dependencies.py   # Placeholder — reserved for future auth/DI
│   │   ├── storage.py        # File-based persistence via tasks.json
│   │   ├── models/
│   │   │   └── task.py       # Pydantic models, enums, state-machine transitions
│   │   ├── routers/
│   │   │   └── tasks.py      # HTTP layer — thin delegation only, no business logic
│   │   └── services/
│   │       └── tasks.py      # All business logic: CRUD, filtering, state transitions
│   ├── tasks.json            # Runtime data store (git-ignored in production)
│   └── pyproject.toml        # Project metadata and dependencies
│
└── frontend/                 # Vite + React + TypeScript SPA
    ├── src/
    │   ├── api/
    │   │   └── tasks.ts      # Typed API client — all backend calls live here
    │   ├── App.tsx           # Root component
    │   └── main.tsx          # React entry point
    ├── index.html
    └── package.json
```

### Request / Response Flow

```
Browser → Vite dev server (port 5173)
       → FastAPI backend (port 8000) at /api/tasks/*
       → services/tasks.py (business logic)
       → storage.py (read/write tasks.json)
```

All API routes are mounted at the `/api` prefix.
The frontend base URL is controlled by `VITE_API_URL` (defaults to `http://localhost:8000`).
All `fetch` calls in `api/tasks.ts` must include the `/api` prefix, e.g. `/api/tasks/`.

### Task State Machine

```
todo  ──►  in-progress  ──►  done
```

Transitions are strictly one-directional and one-step-at-a-time.
No skipping (`todo → done`) and no reversals (`done → in-progress`).
This is enforced in `models/task.py` via `VALID_TRANSITIONS`.

---

## 2. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend language | Python 3.11+ | Use union syntax `X \| Y`, `match`, structural pattern matching |
| Backend framework | FastAPI 0.115+ | `fastapi[standard]` bundle (includes uvicorn, pydantic v2) |
| Data validation | Pydantic v2 | `model_dump(exclude_unset=True)` for partial updates |
| Persistence | JSON file (`tasks.json`) | `storage.py` — `load_tasks()` / `save_tasks()` |
| Frontend language | TypeScript 5.6+ | Strict mode; no `any` |
| Frontend framework | React 18 | Functional components only; no class components |
| Build tool | Vite 5 | Dev server on port 5173 |
| Data fetching | SWR 2 | Stale-while-revalidate; all remote state via SWR hooks |
| Styling | CSS Modules or plain CSS | No CSS-in-JS libraries |

---

## 3. Backend Coding Standards

### Project layout rules
- **Thin routers, fat services.** Routers do nothing except validate HTTP concerns (path params, query params, status codes) and delegate to the service layer. All business logic (filtering, state validation, 404 raising) belongs in `services/tasks.py`.
- New resource types each get their own module under `models/`, `routers/`, and `services/`.

### FastAPI conventions
- Use `async def` for all route handlers.
- Declare all path parameters with `Annotated[str, Path(...)]`.
- Declare all query parameters with `Annotated[X | None, Query(...)]`.
- Return `response_model=` on every route.
- Return `status_code=201` for `POST` creation routes; `status_code=204` for `DELETE` routes.
- Order static routes (`/stats`) **before** parameterised routes (`/{task_id}`) in the same router to avoid routing ambiguity.

### Pydantic v2
- Use `model_dump(exclude_unset=True)` for partial updates — never overwrite fields the caller did not send.
- Use `Field(min_length=1, max_length=200)` for user-supplied string fields.
- Use `str | None = None` for optional fields; never `Optional[str]`.

### API response envelope
Every endpoint **must** wrap its payload in the standard envelope (see §5).
The router returns the envelope dict; never return a raw model or a raw list.

### Error handling
- Raise `fastapi.HTTPException` with an appropriate `status_code` and a human-readable `detail` string.
- 404 for missing resources; 400 for invalid transitions or malformed input.
- Never let unhandled exceptions bubble to the client.

### Timestamps
- Always use `datetime.now(timezone.utc).isoformat()` — UTC only, no naive datetimes.

### Storage
- Every handler that mutates state must call `save_tasks()` before returning.
- `load_tasks()` returns a `dict[str, dict]` keyed by task ID (UUID4 string).
- Do not cache the in-memory dict between requests; always reload from disk.

---

## 4. Frontend Coding Standards

### Component rules
- Functional components only. No class components.
- Each component owns one responsibility. Split into smaller components early.
- Props must be fully typed with a TypeScript `interface` or `type` alias.

### Data fetching
- All server state must go through SWR hooks (`useSWR`, `useSWRMutation`).
- Do **not** use `useEffect` + `useState` for fetching remote data.
- The key passed to `useSWR` must match the cache key used everywhere that resource is used.
- Call `mutate()` after mutations to keep the cache coherent.

### API client (`src/api/tasks.ts`)
- All HTTP calls live in `api/tasks.ts`. Components never call `fetch` directly.
- The base URL prefix for all endpoints is `/api` (e.g. `/api/tasks/`, `/api/tasks/{id}`).
- The generic `request<T>()` helper handles JSON deserialisation, 204 No Content, and error propagation.
- The `data` field of the response envelope must be unwrapped inside `request<T>()` before returning to the caller.
- Mirror every backend Pydantic model as a TypeScript `interface`/`type`.

### TypeScript
- Enable `strict: true` in `tsconfig.app.json` (already set).
- No `any`. Use `unknown` and narrow with type guards where the shape is uncertain.
- Use `const` by default; `let` only when reassignment is necessary.

### Styling
- Use the existing `index.css` / `App.css` for global and component-level styles.
- Avoid inline `style={{}}` props except for truly dynamic values (e.g. calculated widths).

---

## 5. API Response Envelope

**Every** endpoint must return a JSON object with the following shape:

```json
{
  "success": true,
  "data": <payload>
}
```

On error, the envelope still applies:

```json
{
  "success": false,
  "data": null
}
```

FastAPI's `HTTPException` detail is surfaced in the standard error response body separately from the envelope.

### Backend implementation

Define a reusable generic wrapper in `api/models/task.py` (or a shared `api/models/common.py`):

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
```

Use it as the `response_model` on every route:

```python
@router.get("/", response_model=ApiResponse[list[TaskResponse]])
async def list_tasks(...) -> ApiResponse[list[TaskResponse]]:
    tasks = task_service.list_tasks(...)
    return ApiResponse(success=True, data=tasks)
```

For `DELETE` (204 No Content), return an empty body — the envelope does not apply.

### Frontend implementation

The `request<T>()` helper in `api/tasks.ts` must unwrap the envelope and return only `data`:

```typescript
interface Envelope<T> {
  success: boolean;
  data: T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (res.status === 204) return undefined as T;
  const envelope: Envelope<T> = await res.json();
  if (!envelope.success) throw new Error("Request failed");
  return envelope.data;
}
```

---

## 6. Sub-Agent Roles

### Backend Engineer
**Purpose:** Build and maintain all FastAPI backend code.

**Scope:**
- `backend/api/models/` — Pydantic models, enums, validators
- `backend/api/routers/` — HTTP route handlers
- `backend/api/services/` — business logic
- `backend/api/storage.py` — file persistence helpers
- `backend/api/main.py` — app factory and router registration

**Responsibilities:**
- Implement all endpoints wrapping responses in the `ApiResponse` envelope.
- Enforce the `VALID_TRANSITIONS` state machine.
- Keep routers thin — all logic goes in services.
- Raise correct `HTTPException` codes (400, 404, 422).
- Write `pyproject.toml` dependency entries for any new packages.

**Must not:** Touch `frontend/`, write raw SQL, or introduce external service dependencies without team discussion.

---

### Frontend Engineer
**Purpose:** Build and maintain the React + TypeScript UI.

**Scope:**
- `frontend/src/` — all React components, hooks, styles
- `frontend/src/api/tasks.ts` — API client
- `frontend/index.html`, `frontend/vite.config.ts`

**Responsibilities:**
- Wire SWR hooks to the API client functions.
- Unwrap the `ApiResponse` envelope inside `request<T>()` — components receive typed data directly.
- Build task list, task detail, create/edit forms, and stats views.
- Keep all remote state in SWR; use local `useState` only for ephemeral UI state (modal open, form draft).
- Ensure the `/api` prefix is present in every URL in `api/tasks.ts`.

**Must not:** Touch `backend/`, write business logic in components, or call `fetch` outside `api/tasks.ts`.

---

### Test Engineer
**Purpose:** Write and maintain automated tests for the entire system.

**Scope:**
- `backend/tests/` — pytest test suite
- `frontend/src/__tests__/` or `*.test.tsx` — Vitest unit/component tests

**Responsibilities:**
- Backend: use `fastapi.testclient.TestClient` (or `httpx.AsyncClient` for async) to test all routes.
- Test the happy path, all 4xx error cases, and each state machine transition (valid and invalid).
- Assert the `ApiResponse` envelope (`success`, `data`) on every response.
- Frontend: use Vitest + React Testing Library to test components in isolation; mock `api/tasks.ts` at the module boundary.
- Aim for 100% branch coverage on `services/tasks.py`.

**Must not:** Modify production source files; tests should only add files under `tests/` or `*.test.*` patterns.

---

## 7. Patterns to Follow

| Pattern | Rationale |
|---|---|
| **Thin router / fat service** | Keeps HTTP concerns separate from business logic; services are unit-testable without HTTP overhead. |
| **`ApiResponse` envelope on every route** | Uniform contract for the frontend; makes error propagation predictable. |
| **`exclude_unset=True` for partial updates** | Prevents overwriting fields the caller did not send; required for correct PATCH semantics. |
| **State machine via `VALID_TRANSITIONS`** | Centralised, auditable transition rules. Add new states by editing one dict. |
| **SWR for all remote state** | Avoids race conditions and stale data from manual `useEffect` patterns; built-in cache invalidation. |
| **Static routes before parameterised routes** | Prevents FastAPI from matching `/stats` as a task ID. Always declare `/stats` before `/{task_id}`. |
| **UTC ISO-8601 timestamps** | Timezone-safe; round-trips cleanly through JSON and Pydantic. |
| **`VITE_API_URL` environment variable** | Allows the frontend to target different backends (local, staging, production) without code changes. |
| **UUID4 for task IDs** | Collision-resistant, no sequencing dependency, safe to generate client-side if needed. |

---

## 8. Patterns to Avoid

| Anti-pattern | Why it's banned | Correct approach |
|---|---|---|
| **Business logic in routers** | Mixes concerns; untestable without spinning up HTTP. | Move all logic to the service layer. |
| **Raw list/model responses (no envelope)** | Breaks the frontend contract; makes it impossible to signal partial failure. | Always wrap in `ApiResponse(success=True, data=...)`. |
| **`useEffect` + `useState` for fetching** | Causes race conditions, duplicate requests, and stale state. | Use SWR hooks exclusively for server state. |
| **`fetch` calls outside `api/tasks.ts`** | Scatters network logic across the codebase; hard to mock in tests. | All HTTP calls go through the `api` object in `tasks.ts`. |
| **Missing `/api` prefix in frontend URLs** | Requests hit 404 because the backend mounts all routes under `/api`. | Use `${BASE}/api/tasks/` — never `/tasks/`. |
| **Naive datetimes** | Ambiguous timezone; breaks across DST boundaries and serialisations. | Always use `datetime.now(timezone.utc)`. |
| **Caching `load_tasks()` between requests** | File may be written by another process; stale reads cause data loss. | Call `load_tasks()` at the start of every handler. |
| **`Optional[X]` from `typing`** | Verbose legacy syntax. | Use `X | None` (Python 3.10+ built-in union). |
| **`any` in TypeScript** | Silences type errors; masks real bugs. | Use `unknown` and narrow, or define the type properly. |
| **Class components in React** | Lifecycle methods are error-prone and verbose. | Use functional components with hooks. |
| **Inline `style={{}}` for static values** | Defeats CSS caching; harder to theme. | Use CSS classes or CSS Modules. |
| **Skipping or reversing state transitions** | Breaks workflow integrity (e.g. re-opening a completed task). | Only allow transitions defined in `VALID_TRANSITIONS`. |
