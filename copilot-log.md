# Copilot Usage Log

## 1. Inline Suggestions- [file]: [comment typed] → [what Copilot generated]

### 1. backend/api/models/task.py

models/task.py — Domain models and state-machine definitions

Defines all Pydantic schemas used across the task management system:

  TaskStatus      — Enumeration of valid task lifecycle states: todo, in-progress, done.
  TaskPriority    — Enumeration of task urgency levels: low, medium, high.
  VALID_TRANSITIONS — Mapping that encodes the one-directional, one-step-at-a-time
                      state machine.  Only transitions listed here are permitted; any
                      attempt to skip or reverse a step is rejected at the service layer.
  TaskCreate      — Request body schema for creating a new task.
  TaskUpdate      — Partial-update schema (all fields optional); used with
                    model_dump(exclude_unset=True) so unset fields are never overwritten.
  TaskResponse    — Read schema returned to callers; includes server-generated fields
                    (id, created_at, updated_at).
  TaskStats       — Aggregated totals keyed by status and priority, used by GET /stats.**
""" 

```
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in-progress"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


VALID_TRANSITIONS = {
    TaskStatus.todo: {TaskStatus.in_progress, TaskStatus.done,TaskStatus.todo},
    TaskStatus.in_progress: {TaskStatus.done,TaskStatus.in_progress},
    TaskStatus.done: set(),
}   

class TaskBase(BaseModel):
    title: str = Field(..., example="Buy groceries")
    description: str | None = Field(None, example="Milk, eggs, bread")
    status: TaskStatus = Field(TaskStatus.todo, example="todo")
    priority: TaskPriority = Field(TaskPriority.medium, example="medium")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: str | None = Field(None, example="Buy groceries")
    description: str | None = Field(None, example="Milk, eggs, bread")
    status: TaskStatus | None = Field(None, example="todo")
    priority: TaskPriority | None = Field(None, example="medium")

class TaskResponse(TaskBase):
    id: str = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    created_at: str = Field(..., example="2024-01-01T12:00:00Z")
    updated_at: str = Field(..., example="2024-01-02T15:30:00Z")

class TaskStats(BaseModel):
    total: int = Field(..., example=42)
    by_status: dict[TaskStatus, int] = Field(..., example={"todo": 10, "in-progress": 20, "done": 12})
    by_priority: dict[TaskPriority, int] = Field(..., example={"low": 15, "medium": 20, "high": 7})
    
```

2.


### 2. backend/api/routers/tasks.py

"""
routers/tasks.py — HTTP route handlers for /api/tasks

This module is intentionally thin: each handler validates HTTP-level concerns
(path parameters, query parameters, status codes) and immediately delegates to
the service layer.  No business logic lives here.

Endpoints
---------
  GET    /tasks/stats              → TaskStats
      Aggregate counts by status and priority.  Declared before /{task_id} to
      prevent FastAPI from treating "stats" as a task UUID.

  GET    /tasks/                   → list[TaskResponse]
      List all tasks with optional ?status= and ?priority= query filters.

  POST   /tasks/              201  → TaskResponse
      Create a new task from the JSON request body.

  GET    /tasks/{task_id}          → TaskResponse
      Retrieve a single task by its UUID.

  PUT    /tasks/{task_id}          → TaskResponse
      Partially update a task's fields (title, description, status, priority).

  DELETE /tasks/{task_id}     204  → (no body)
      Permanently delete a task.

  POST   /tasks/{task_id}/complete → TaskResponse
      Convenience endpoint to advance a task to its next valid state.

"""



```
from ..models.task import TaskCreate, TaskPriority, TaskResponse, TaskStats, TaskStatus, TaskUpdate
from ..services import tasks as task_service
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/stats", response_model=TaskStats)
async def get_stats() -> TaskStats:
    return task_service.get_stats()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    status: Annotated[TaskStatus | None, Query(description="Filter by status")] = None,
    priority: Annotated[TaskPriority | None, Query(description="Filter by priority")] = None,
) -> list[TaskResponse]:
    return task_service.list_tasks(status, priority)


@router.post("/", status_code=http_status.HTTP_201_CREATED, response_model=TaskResponse)
async def create_task(data: TaskCreate) -> TaskResponse:
    return task_service.create_task(data)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: Annotated[str, Path(description="Task UUID")],
) -> TaskResponse:
    return task_service.get_task(task_id)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: Annotated[str, Path(description="Task UUID")],
    data: TaskUpdate,
) -> TaskResponse:
    return task_service.update_task(task_id, data)


@router.delete("/{task_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: Annotated[str, Path(description="Task UUID")],
) -> None:
    task_service.delete_task(task_id)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: Annotated[str, Path(description="Task UUID")],
) -> TaskResponse:
    return task_service.complete_task(task_id)


```

### 3. backend/api/services/tasks.py
"""
services/tasks.py — Business logic layer

This module owns all business rules for the task management system and is the
single authoritative source of truth for data mutations.  Routers are thin
delegates; every decision is made here.

Public interface
----------------
  list_tasks(status_filter, priority_filter)  → list[TaskResponse]
      Return all tasks, optionally filtered by status and/or priority.

  create_task(data: TaskCreate)               → TaskResponse
      Persist a new task with a UUID4 id and UTC timestamps, then return it.

  get_task(task_id)                           → TaskResponse
      Fetch a single task by id; raises HTTP 404 if not found.

  update_task(task_id, data: TaskUpdate)      → TaskResponse
      Apply a partial update.  Status changes are validated against
      VALID_TRANSITIONS; invalid transitions raise HTTP 400.

  delete_task(task_id)                        → None
      Remove a task permanently; raises HTTP 404 if not found.

  get_stats()                                 → TaskStats
      Aggregate task counts grouped by status and priority.

Storage contract
----------------
  load_tasks() is called at the start of every operation to avoid serving stale
  data.  save_tasks() is called after every mutation before the response is
  returned.
"""

```
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status

from ..models.task import (
    VALID_TRANSITIONS,
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStats,
    TaskStatus,
    TaskUpdate,
)
from ..storage import load_tasks, save_tasks


def _to_response(doc: dict) -> TaskResponse:
    return TaskResponse(
        id=doc["id"],
        title=doc["title"],
        description=doc.get("description"),
        status=doc["status"],
        priority=doc["priority"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def list_tasks(
    status_filter: TaskStatus | None = None,
    priority_filter: TaskPriority | None = None,
) -> list[TaskResponse]:
    tasks = load_tasks()
    result = list(tasks.values())
    if status_filter is not None:
        result = [t for t in result if t["status"] == status_filter.value]
    if priority_filter is not None:
        result = [t for t in result if t["priority"] == priority_filter.value]
    return [_to_response(t) for t in result]


def create_task(data: TaskCreate) -> TaskResponse:
    now = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())
    doc: dict = {
        "id": task_id,
        "title": data.title,
        "description": data.description,
        "status": data.status.value,
        "priority": data.priority.value,
        "created_at": now,
        "updated_at": now,
    }
    tasks = load_tasks()
    tasks[task_id] = doc
    save_tasks(tasks)
    return _to_response(doc)


def get_task(task_id: str) -> TaskResponse:
    tasks = load_tasks()
    doc = tasks.get(task_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(doc)


def update_task(task_id: str, data: TaskUpdate) -> TaskResponse:
    tasks = load_tasks()
    doc = tasks.get(task_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updates = data.model_dump(exclude_unset=True)

    if "status" in updates:
        new_status = TaskStatus(updates["status"])
        current_status = TaskStatus(doc["status"])
        if new_status not in VALID_TRANSITIONS[current_status]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition: '{current_status.value}' → '{new_status.value}'",
            )
        updates["status"] = new_status.value

    if "priority" in updates:
        updates["priority"] = TaskPriority(updates["priority"]).value

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    doc.update(updates)
    tasks[task_id] = doc
    save_tasks(tasks)
    return _to_response(doc)


def delete_task(task_id: str) -> None:
    tasks = load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    del tasks[task_id]
    save_tasks(tasks)


def complete_task(task_id: str) -> TaskResponse:
    tasks = load_tasks()
    doc = tasks.get(task_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    current_status = TaskStatus(doc["status"])
    if current_status != TaskStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task must be 'in-progress' to complete. Current status: '{current_status.value}'",
        )

    doc["status"] = TaskStatus.done.value
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = doc
    save_tasks(tasks)
    return _to_response(doc)


def get_stats() -> TaskStats:
    tasks = load_tasks()
    by_status: dict[str, int] = {s.value: 0 for s in TaskStatus}
    by_priority: dict[str, int] = {p.value: 0 for p in TaskPriority}
    for task in tasks.values():
        by_status[task["status"]] = by_status.get(task["status"], 0) + 1
        by_priority[task["priority"]] = by_priority.get(task["priority"], 0) + 1
    return TaskStats(by_status=by_status, by_priority=by_priority)

```

## 2. Agent Mode Prompts- [prompt] → [files changed / result]

## 3. Sub-Agent Usage- @ui-agent: [prompt] → [result]
- @backend-agent: [prompt] → [result]
- @testing-agent: [prompt] → [result]

## 4. Review Agent- Issues found: ...
- Fixes applied: ...

## 5. Skills- Skill: [name] | Prompt: [prompt] | Changes: [what improved]

## 6. Playwright MCP- Screenshot taken: yes/no
- E2E test generated: [filename]