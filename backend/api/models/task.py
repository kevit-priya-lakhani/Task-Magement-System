from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in-progress"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# Valid one-step forward transitions (no skipping, no reversals)
VALID_TRANSITIONS: dict["TaskStatus", set["TaskStatus"]] = {
    TaskStatus.todo: {TaskStatus.in_progress},
    TaskStatus.in_progress: {TaskStatus.done},
    TaskStatus.done: set(),
}


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime


class TaskStats(BaseModel):
    by_status: dict[str, int]
    by_priority: dict[str, int]
