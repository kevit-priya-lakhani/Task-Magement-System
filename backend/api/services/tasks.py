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
    """Convert a raw storage document to a TaskResponse schema.

    Args:
        doc: Dictionary loaded from storage containing raw task fields.

    Returns:
        A TaskResponse instance populated from the storage document.
    """
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
    """Return all tasks, optionally filtered by status and/or priority.

    Args:
        status_filter: When provided, only tasks with this status are returned.
        priority_filter: When provided, only tasks with this priority are returned.

    Returns:
        A list of TaskResponse objects matching the given filters.
    """
    tasks = load_tasks()
    result = list(tasks.values())
    if status_filter is not None:
        result = [t for t in result if t["status"] == status_filter.value]
    if priority_filter is not None:
        result = [t for t in result if t["priority"] == priority_filter.value]
    return [_to_response(t) for t in result]


def create_task(data: TaskCreate) -> TaskResponse:
    """Create and persist a new task.

    Args:
        data: Validated task creation payload.

    Returns:
        The newly created TaskResponse with a generated UUID id and UTC timestamps.
    """
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
    """Retrieve a single task by its ID.

    Args:
        task_id: UUID4 string identifying the task.

    Returns:
        A TaskResponse with the task data.

    Raises:
        HTTPException: 404 if no task with that ID exists.
    """
    tasks = load_tasks()
    doc = tasks.get(task_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(doc)


def update_task(task_id: str, data: TaskUpdate) -> TaskResponse:
    """Apply a partial update to an existing task.

    Args:
        task_id: UUID4 string identifying the task.
        data: Partial update payload; only fields present in the request are applied.

    Returns:
        The updated TaskResponse.

    Raises:
        HTTPException: 404 if no task with that ID exists.
        HTTPException: 400 if the requested status transition is not permitted.
    """
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
    """Permanently remove a task from storage.

    Args:
        task_id: UUID4 string identifying the task.

    Raises:
        HTTPException: 404 if no task with that ID exists.
    """
    tasks = load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    del tasks[task_id]
    save_tasks(tasks)


def complete_task(task_id: str) -> TaskResponse:
    """Advance a task in 'in-progress' state to 'done'.

    Args:
        task_id: UUID4 string identifying the task.

    Returns:
        The updated TaskResponse with status set to 'done'.

    Raises:
        HTTPException: 404 if no task with that ID exists.
        HTTPException: 400 if the task is not currently 'in-progress'.
    """
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
    """Aggregate task counts grouped by status and priority.

    Returns:
        A TaskStats instance with total count and breakdowns by status and priority.
    """
    tasks = load_tasks()
    by_status: dict[str, int] = {s.value: 0 for s in TaskStatus}
    by_priority: dict[str, int] = {p.value: 0 for p in TaskPriority}
    for task in tasks.values():
        by_status[task["status"]] = by_status.get(task["status"], 0) + 1
        by_priority[task["priority"]] = by_priority.get(task["priority"], 0) + 1
    return TaskStats(total=sum(by_status.values()), by_status=by_status, by_priority=by_priority)

