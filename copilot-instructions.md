# Copilot Instructions

These instructions apply to all code generated or modified in this repository.
Follow every rule below unless the user explicitly overrides it for a specific task.

---

## 1. Docstrings and JSDoc on All Public Functions

### Python (backend)
- Every public function, method, and class in `backend/` must have a docstring.
- Use the Google-style docstring format.
- Include `Args:`, `Returns:`, and `Raises:` sections whenever they apply.
- One-liner docstrings are acceptable only for trivially self-evident helpers.

```python
def get_task(task_id: str) -> TaskResponse:
    """Retrieve a single task by its ID.

    Args:
        task_id: UUID4 string identifying the task.

    Returns:
        A TaskResponse with the task data.

    Raises:
        HTTPException: 404 if no task with that ID exists.
    """
```

### TypeScript / React (frontend)
- Every exported function, React component, and custom hook in `frontend/src/` must have a JSDoc comment.
- Document `@param`, `@returns`, and `@throws` where relevant.
- For React components, describe the component's purpose and its props.

```typescript
/**
 * Fetches the full task list from the backend and returns typed data.
 *
 * @returns Promise resolving to an array of Task objects.
 * @throws {Error} When the API response signals failure.
 */
export async function fetchTasks(): Promise<Task[]> { ... }
```

---

## 2. Input Validation on Every POST / PUT Route

### Backend
- All `POST` and `PUT` request bodies must be validated through a Pydantic model.
- String fields that are user-supplied must declare `Field(min_length=1, max_length=200)`.
- Enum fields must use Python `Enum` types — never accept raw strings and branch on them.
- Perform semantic validation (e.g. valid state transitions, referenced IDs exist) in the service layer and raise `HTTPException(400)` on failure.
- Never trust that optional fields are absent — use `model_dump(exclude_unset=True)` for partial updates.

```python
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    status: TaskStatus = TaskStatus.TODO
```

### Frontend
- Validate forms client-side before submitting (non-empty required fields, max lengths).
- Display inline field-level error messages; do not rely solely on backend 422 responses.
- Disable the submit button while a mutation is in flight to prevent double-submission.

---

## 3. Correct HTTP Status Codes

Always return the most precise status code. The mapping below is mandatory:

| Situation | Code |
|---|---|
| Successful resource creation (`POST`) | `201 Created` |
| Successful deletion (`DELETE`) | `204 No Content` |
| Successful read or update | `200 OK` |
| Missing resource | `404 Not Found` |
| Invalid input / bad transition | `400 Bad Request` |
| Schema / type validation failure (Pydantic) | `422 Unprocessable Entity` (FastAPI default) |
| Unexpected server error | `500 Internal Server Error` |

- Never return `200` for creations — use `201`.
- Never return `200` for deletions — use `204` (no body).
- Do not swallow errors and return `200` with a success flag set to `false`; use the appropriate 4xx/5xx code.
- Use `response_model` and `status_code` on every route decorator:

```python
@router.post("/", response_model=ApiResponse[TaskResponse], status_code=201)
@router.delete("/{task_id}", status_code=204)
```

---

## 4. No Empty Catch Blocks

### Python
- Never write a bare `except: pass` or `except Exception: pass`.
- If an exception is intentionally suppressed, add a comment explaining why.
- Re-raise or convert all caught exceptions to an appropriate `HTTPException`.

```python
# BAD
try:
    data = load_tasks()
except Exception:
    pass

# GOOD
try:
    data = load_tasks()
except OSError as exc:
    raise HTTPException(status_code=500, detail="Storage unavailable") from exc
```

### TypeScript
- Never write an empty `catch` block or one that only does `catch (e) {}`.
- Always log the error and surface it to the user via state or a notification.
- In SWR, use the `onError` callback or the returned `error` value — do not swallow it.

```typescript
// BAD
try {
  await createTask(payload);
} catch (_) {}

// GOOD
try {
  await createTask(payload);
} catch (err) {
  console.error("createTask failed:", err);
  setError(err instanceof Error ? err.message : "Unknown error");
}
```

---

## 5. Frontend Loading States and Error Handling

- Every data-fetching SWR hook must handle three states explicitly: **loading**, **error**, and **success**.
- Render a visible loading indicator (spinner, skeleton, or disabled state) while `isLoading` / `isValidating` is true.
- Render a user-readable error message when the `error` value is set — never silently fail.
- Mutation functions (create, update, delete) must:
  1. Set a loading/submitting flag on start.
  2. Clear the flag in a `finally` block (or equivalent).
  3. Show a success notification on completion.
  4. Show an error notification on failure with a human-readable message.
- Do not use `useEffect` + `useState` for remote data; use SWR exclusively.

```tsx
const { data: tasks, error, isLoading } = useSWR<Task[]>("/api/tasks/", fetchTasks);

if (isLoading) return <Spinner />;
if (error) return <ErrorBanner message={error.message} />;
```

---

## 6. Test Coverage > 80 %

### Backend (pytest)
- All code under `backend/api/services/` must reach **> 80 % branch coverage**.
- Use `fastapi.testclient.TestClient` for route-level integration tests.
- Required test cases for every endpoint:
  - Happy path (valid input → expected response and status code).
  - Missing resource (→ 404).
  - Invalid input / bad transition (→ 400 or 422).
- Every `VALID_TRANSITIONS` edge (valid and invalid) must have a dedicated test.
- Assert the `ApiResponse` envelope (`success`, `data`) on every response, not just the HTTP status.
- Run coverage with: `pytest --cov=api --cov-report=term-missing --cov-fail-under=80`

### Frontend (Vitest + React Testing Library)
- All components and hooks under `frontend/src/` must reach **> 80 % line/branch coverage**.
- Mock `api/tasks.ts` at the module boundary — never make real network calls in tests.
- Required test cases for every component:
  - Renders the loading state.
  - Renders the error state.
  - Renders data correctly on success.
  - User interactions (click, submit) trigger the correct API calls.
- Run coverage with: `vitest run --coverage`

### General
- Tests live in `backend/tests/` and `frontend/src/__tests__/` (or co-located `*.test.tsx` files).
- Do not modify production source files from inside test files.
- New features are not considered complete until tests are written and coverage stays above 80 %.
