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

