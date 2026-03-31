"""
conftest.py — shared pytest fixtures for the backend test suite.

Strategy
--------
All tests that exercise the HTTP layer use the `client` fixture, which wires
a FastAPI TestClient to an in-memory task store (a plain dict).  The real
tasks.json file is never touched during tests.

Patching is performed at the import site used by the service layer:
    api.services.tasks.load_tasks
    api.services.tasks.save_tasks
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_task_doc(
    *,
    task_id: str = "00000000-0000-0000-0000-000000000001",
    title: str = "Test task",
    description: str | None = None,
    status: str = "todo",
    priority: str = "medium",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": task_id,
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store() -> dict[str, Any]:
    """An empty in-memory task store shared by load/save mocks."""
    return {}


@pytest.fixture
def client(store: dict[str, Any]):
    """
    FastAPI TestClient backed by a mocked in-memory store.

    Both load_tasks and save_tasks are patched so that:
    - load_tasks() returns a shallow copy of `store` (prevents aliasing bugs)
    - save_tasks(tasks) replaces the entire `store` contents (handles deletions)
    """

    def _load() -> dict[str, Any]:
        return dict(store)

    def _save(tasks: dict[str, Any]) -> None:
        store.clear()
        store.update(tasks)

    with patch("api.services.tasks.load_tasks", side_effect=_load), \
         patch("api.services.tasks.save_tasks", side_effect=_save):
        yield TestClient(app)
