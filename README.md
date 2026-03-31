# Task Management System

A full-stack task management web application built with FastAPI and React. Create, track, and manage tasks through a structured workflow with priority levels and real-time status visibility.

---

## Features

- **Task CRUD** — Create, view, edit, and delete tasks
- **State Machine Workflow** — Tasks move strictly through `todo → in-progress → done`
- **Priority Levels** — Assign `low`, `medium`, or `high` priority to each task
- **Filtering & Search** — Filter by status or priority; search by title and description
- **Dashboard Stats** — At-a-glance task counts grouped by status and priority
- **Toast Notifications** — Success and error feedback on every action

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI 0.115+, Pydantic v2 |
| Persistence | JSON file (`tasks.json`) |
| Frontend | React 18, TypeScript 5.6, Vite 5 |
| Data Fetching | SWR 2 |
| E2E Testing | Playwright |
| Backend Testing | pytest, httpx |

---

## Project Structure

```
Task-Management-System/
├── backend/
│   ├── api/
│   │   ├── main.py           # FastAPI app factory, CORS, router registration
│   │   ├── models/task.py    # Pydantic models, enums, state machine
│   │   ├── routers/tasks.py  # HTTP handlers (thin delegation only)
│   │   ├── services/tasks.py # All business logic (CRUD, filtering, transitions)
│   │   └── storage.py        # JSON file I/O (load_tasks / save_tasks)
│   ├── tasks.json            # Runtime data store
│   ├── pyproject.toml
│   └── tests/
│       ├── conftest.py
│       ├── test_api.py
│       └── test_storage.py
└── frontend/
    ├── src/
    │   ├── api/tasks.ts      # Typed API client — all HTTP calls
    │   ├── App.tsx           # Main dashboard view
    │   └── components/
    │       ├── TaskModal.tsx  # Create / edit dialog
    │       └── Toast.tsx      # Notification component
    ├── e2e/tasks.spec.ts     # Playwright E2E tests
    └── package.json
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
pip install -e ".[dev]"
fastapi dev api/main.py --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`.

### Running Both Together

1. Start the backend in one terminal: `fastapi dev api/main.py --port 8000`
2. Start the frontend in another: `npm run dev`
3. Open `http://localhost:5173`

---

## API Reference

All endpoints are mounted under `/api`. Every response (except `DELETE`) is wrapped in:

```json
{ "success": true, "data": <payload> }
```

| Method | Endpoint | Description | Status |
|---|---|---|---|
| `GET` | `/api/tasks/` | List tasks (optional `?status=` and `?priority=` filters) | 200 |
| `POST` | `/api/tasks/` | Create a new task | 201 |
| `GET` | `/api/tasks/stats` | Aggregate counts by status and priority | 200 |
| `GET` | `/api/tasks/{id}` | Get a single task | 200 |
| `PUT` | `/api/tasks/{id}` | Partially update a task | 200 |
| `DELETE` | `/api/tasks/{id}` | Delete a task | 204 |
| `POST` | `/api/tasks/{id}/complete` | Advance an `in-progress` task to `done` | 200 |

### Task Object

```json
{
  "id": "uuid4",
  "title": "My task",
  "description": "Optional description",
  "status": "todo | in-progress | done",
  "priority": "low | medium | high",
  "created_at": "2026-03-31T12:00:00+00:00",
  "updated_at": "2026-03-31T12:00:00+00:00"
}
```

### State Machine

```
todo  ──►  in-progress  ──►  done
```

Transitions are strictly one-directional and one-step-at-a-time. Skipping (`todo → done`) and reversals (`done → in-progress`) return `400 Bad Request`.

---

## Configuration

### Frontend environment variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

Create a `.env` file in `frontend/` to override:

```
VITE_API_URL=https://api.example.com
```

---

## Running Tests

### Backend

```bash
cd backend
pytest                                      # All tests
pytest -v                                   # Verbose output
pytest --cov=api --cov-report=html          # HTML coverage report
```

The test suite covers all endpoints including happy paths, 4xx error cases, and every valid/invalid state machine transition.

### Frontend E2E (Playwright)

```bash
cd frontend
npx playwright test
npx playwright test --headed               # With browser UI
npx playwright show-report                 # View last report
```
