"""
test_api.py — Integration tests for all /api/tasks/* endpoints.

Covers
------
  GET    /api/tasks/              list tasks (no filter, status filter, priority filter, combined)
  POST   /api/tasks/              create task (valid, missing title, bad enum values)
  GET    /api/tasks/stats         stats aggregation (known bug: missing `total` → 500)
  GET    /api/tasks/{id}          get single task (found / not found)
  PUT    /api/tasks/{id}          partial update (title, status transitions, priority, not found)
  DELETE /api/tasks/{id}          delete (success 204 / not found 404)
  POST   /api/tasks/{id}/complete complete task (from in-progress / invalid states / not found)

Each test follows Arrange → Act → Assert.
"""
from __future__ import annotations

from typing import Any

import pytest

from .conftest import make_task_doc


# ===========================================================================
# GET /api/tasks/  — list tasks
# ===========================================================================

class TestListTasks:
    def test_empty_store_returns_empty_list(self, client, store):
        response = client.get("/api/tasks/")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_tasks(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", title="Task 1")
        store["id-2"] = make_task_doc(task_id="id-2", title="Task 2")

        response = client.get("/api/tasks/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {t["title"] for t in data}
        assert titles == {"Task 1", "Task 2"}

    def test_filter_by_status(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", title="Todo task", status="todo")
        store["id-2"] = make_task_doc(task_id="id-2", title="Done task", status="done")

        response = client.get("/api/tasks/?status=todo")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Todo task"

    def test_filter_by_priority(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", title="High priority", priority="high")
        store["id-2"] = make_task_doc(task_id="id-2", title="Low priority", priority="low")

        response = client.get("/api/tasks/?priority=high")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "High priority"

    def test_filter_by_status_and_priority(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="todo", priority="high")
        store["id-2"] = make_task_doc(task_id="id-2", status="todo", priority="low")
        store["id-3"] = make_task_doc(task_id="id-3", status="done", priority="high")

        response = client.get("/api/tasks/?status=todo&priority=high")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "id-1"

    def test_filter_by_invalid_status_returns_422(self, client, store):
        response = client.get("/api/tasks/?status=invalid")
        assert response.status_code == 422

    def test_filter_by_invalid_priority_returns_422(self, client, store):
        response = client.get("/api/tasks/?priority=urgent")
        assert response.status_code == 422

    def test_filter_no_matches_returns_empty_list(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="todo")

        response = client.get("/api/tasks/?status=done")
        assert response.status_code == 200
        assert response.json() == []


# ===========================================================================
# POST /api/tasks/  — create task
# ===========================================================================

class TestCreateTask:
    def test_create_task_minimal_returns_201(self, client, store):
        response = client.post("/api/tasks/", json={"title": "Buy milk"})
        assert response.status_code == 201

    def test_create_task_minimal_defaults(self, client, store):
        response = client.post("/api/tasks/", json={"title": "Buy milk"})
        data = response.json()
        assert data["title"] == "Buy milk"
        assert data["status"] == "todo"
        assert data["priority"] == "medium"
        assert data["description"] is None

    def test_create_task_all_fields(self, client, store):
        payload = {
            "title": "Deploy service",
            "description": "Deploy to production server",
            "status": "in-progress",
            "priority": "high",
        }
        response = client.post("/api/tasks/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Deploy service"
        assert data["description"] == "Deploy to production server"
        assert data["status"] == "in-progress"
        assert data["priority"] == "high"

    def test_create_task_assigns_uuid_id(self, client, store):
        response = client.post("/api/tasks/", json={"title": "Check UUID"})
        data = response.json()
        assert "id" in data
        assert len(data["id"]) == 36  # UUID4 format

    def test_create_task_assigns_timestamps(self, client, store):
        response = client.post("/api/tasks/", json={"title": "Check timestamps"})
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] == data["updated_at"]

    def test_create_task_persists_to_store(self, client, store):
        client.post("/api/tasks/", json={"title": "Persistent task"})
        assert len(store) == 1

    def test_create_task_missing_title_returns_422(self, client, store):
        response = client.post("/api/tasks/", json={"description": "no title"})
        assert response.status_code == 422

    def test_create_task_empty_body_returns_422(self, client, store):
        response = client.post("/api/tasks/", json={})
        assert response.status_code == 422

    def test_create_task_invalid_status_returns_422(self, client, store):
        response = client.post("/api/tasks/", json={"title": "T", "status": "cancelled"})
        assert response.status_code == 422

    def test_create_task_invalid_priority_returns_422(self, client, store):
        response = client.post("/api/tasks/", json={"title": "T", "priority": "critical"})
        assert response.status_code == 422

    def test_create_multiple_tasks_each_gets_unique_id(self, client, store):
        r1 = client.post("/api/tasks/", json={"title": "Task A"})
        r2 = client.post("/api/tasks/", json={"title": "Task B"})
        assert r1.json()["id"] != r2.json()["id"]


# ===========================================================================
# GET /api/tasks/stats  — aggregated stats
# ===========================================================================

class TestGetStats:
    def test_stats_empty_store_returns_zeros(self, client, store):
        response = client.get("/api/tasks/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["by_status"]["todo"] == 0
        assert data["by_status"]["in-progress"] == 0
        assert data["by_status"]["done"] == 0

    def test_stats_with_tasks_aggregates_correctly(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="todo", priority="high")
        store["id-2"] = make_task_doc(task_id="id-2", status="done", priority="low")
        response = client.get("/api/tasks/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["by_status"]["todo"] == 1
        assert data["by_status"]["done"] == 1
        assert data["by_priority"]["high"] == 1
        assert data["by_priority"]["low"] == 1


# ===========================================================================
# GET /api/tasks/{task_id}  — get single task
# ===========================================================================

class TestGetTask:
    def test_get_existing_task(self, client, store):
        store["abc-123"] = make_task_doc(task_id="abc-123", title="Find me")
        response = client.get("/api/tasks/abc-123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "abc-123"
        assert data["title"] == "Find me"

    def test_get_task_returns_all_fields(self, client, store):
        store["abc-123"] = make_task_doc(
            task_id="abc-123",
            title="Full task",
            description="Some desc",
            status="in-progress",
            priority="high",
        )
        response = client.get("/api/tasks/abc-123")
        data = response.json()
        assert data["description"] == "Some desc"
        assert data["status"] == "in-progress"
        assert data["priority"] == "high"
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_nonexistent_task_returns_404(self, client, store):
        response = client.get("/api/tasks/does-not-exist")
        assert response.status_code == 404

    def test_get_task_404_detail(self, client, store):
        response = client.get("/api/tasks/ghost")
        assert response.json()["detail"] == "Task not found"


# ===========================================================================
# PUT /api/tasks/{task_id}  — partial update
# ===========================================================================

class TestUpdateTask:
    def test_update_title(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", title="Old title")
        response = client.put("/api/tasks/id-1", json={"title": "New title"})
        assert response.status_code == 200
        assert response.json()["title"] == "New title"

    def test_update_description(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        response = client.put("/api/tasks/id-1", json={"description": "Added desc"})
        assert response.status_code == 200
        assert response.json()["description"] == "Added desc"

    def test_update_priority(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", priority="low")
        response = client.put("/api/tasks/id-1", json={"priority": "high"})
        assert response.status_code == 200
        assert response.json()["priority"] == "high"

    def test_update_advances_timestamp(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        original_updated_at = store["id-1"]["updated_at"]
        response = client.put("/api/tasks/id-1", json={"title": "Changed"})
        assert response.json()["updated_at"] >= original_updated_at

    def test_update_does_not_overwrite_unset_fields(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", title="Keep me", priority="high")
        # Only update title
        client.put("/api/tasks/id-1", json={"title": "New title"})
        assert store["id-1"]["priority"] == "high"

    # --- Status transitions ---

    def test_status_transition_todo_to_in_progress(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="todo")
        response = client.put("/api/tasks/id-1", json={"status": "in-progress"})
        assert response.status_code == 200
        assert response.json()["status"] == "in-progress"

    def test_status_transition_in_progress_to_done(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="in-progress")
        response = client.put("/api/tasks/id-1", json={"status": "done"})
        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_status_transition_todo_to_done_not_allowed(self, client, store):
        # Skipping in-progress is forbidden per the strict one-step state machine.
        store["id-1"] = make_task_doc(task_id="id-1", status="todo")
        response = client.put("/api/tasks/id-1", json={"status": "done"})
        assert response.status_code == 400

    def test_status_transition_same_state_todo_returns_400(self, client, store):
        # Self-transitions are not listed in VALID_TRANSITIONS.
        store["id-1"] = make_task_doc(task_id="id-1", status="todo")
        response = client.put("/api/tasks/id-1", json={"status": "todo"})
        assert response.status_code == 400

    def test_invalid_transition_done_to_todo_returns_400(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="done")
        response = client.put("/api/tasks/id-1", json={"status": "todo"})
        assert response.status_code == 400

    def test_invalid_transition_done_to_in_progress_returns_400(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="done")
        response = client.put("/api/tasks/id-1", json={"status": "in-progress"})
        assert response.status_code == 400

    def test_invalid_transition_detail_message(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="done")
        response = client.put("/api/tasks/id-1", json={"status": "todo"})
        detail = response.json()["detail"]
        assert "Invalid status transition" in detail
        assert "done" in detail

    def test_update_nonexistent_task_returns_404(self, client, store):
        response = client.put("/api/tasks/ghost", json={"title": "Nope"})
        assert response.status_code == 404

    def test_update_invalid_status_value_returns_422(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        response = client.put("/api/tasks/id-1", json={"status": "cancelled"})
        assert response.status_code == 422

    def test_update_invalid_priority_value_returns_422(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        response = client.put("/api/tasks/id-1", json={"priority": "critical"})
        assert response.status_code == 422

    def test_update_empty_body_makes_no_change(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", title="Original")
        client.put("/api/tasks/id-1", json={})
        assert store["id-1"]["title"] == "Original"


# ===========================================================================
# DELETE /api/tasks/{task_id}  — delete task
# ===========================================================================

class TestDeleteTask:
    def test_delete_existing_task_returns_204(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        response = client.delete("/api/tasks/id-1")
        assert response.status_code == 204

    def test_delete_removes_task_from_store(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        client.delete("/api/tasks/id-1")
        assert "id-1" not in store

    def test_delete_204_has_no_body(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        response = client.delete("/api/tasks/id-1")
        assert response.content == b""

    def test_delete_nonexistent_task_returns_404(self, client, store):
        response = client.delete("/api/tasks/ghost")
        assert response.status_code == 404

    def test_delete_nonexistent_task_detail(self, client, store):
        response = client.delete("/api/tasks/ghost")
        assert response.json()["detail"] == "Task not found"

    def test_delete_only_removes_target_task(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1")
        store["id-2"] = make_task_doc(task_id="id-2")
        client.delete("/api/tasks/id-1")
        assert "id-2" in store
        assert "id-1" not in store


# ===========================================================================
# POST /api/tasks/{task_id}/complete  — complete task
# ===========================================================================

class TestCompleteTask:
    def test_complete_in_progress_task_returns_200(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="in-progress")
        response = client.post("/api/tasks/id-1/complete")
        assert response.status_code == 200

    def test_complete_sets_status_to_done(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="in-progress")
        response = client.post("/api/tasks/id-1/complete")
        assert response.json()["status"] == "done"

    def test_complete_updates_updated_at(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="in-progress")
        original_updated_at = store["id-1"]["updated_at"]
        response = client.post("/api/tasks/id-1/complete")
        assert response.json()["updated_at"] >= original_updated_at

    def test_complete_from_todo_returns_400(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="todo")
        response = client.post("/api/tasks/id-1/complete")
        assert response.status_code == 400

    def test_complete_from_todo_detail_message(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="todo")
        response = client.post("/api/tasks/id-1/complete")
        detail = response.json()["detail"]
        assert "in-progress" in detail

    def test_complete_from_done_returns_400(self, client, store):
        store["id-1"] = make_task_doc(task_id="id-1", status="done")
        response = client.post("/api/tasks/id-1/complete")
        assert response.status_code == 400

    def test_complete_nonexistent_task_returns_404(self, client, store):
        response = client.post("/api/tasks/ghost/complete")
        assert response.status_code == 404

    def test_complete_nonexistent_task_detail(self, client, store):
        response = client.post("/api/tasks/ghost/complete")
        assert response.json()["detail"] == "Task not found"
