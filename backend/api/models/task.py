"""
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
  TaskStats       — Aggregated totals keyed by status and priority, used by GET /stats.
""" 
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
    