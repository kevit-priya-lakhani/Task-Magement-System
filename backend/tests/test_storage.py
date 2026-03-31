"""
test_storage.py — Unit tests for api/storage.py.

These tests use a temporary file so neither tasks.json nor any mock is needed.
Covers:
  - load_tasks() when the file does not exist  → returns {}
  - load_tasks() when the file exists          → returns parsed dict
  - save_tasks() / load_tasks() round-trip     → data survives serialisation
  - save_tasks() overwrites previous content   → no stale data
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import api.storage as storage_module
from api.storage import load_tasks, save_tasks


@pytest.fixture
def tmp_tasks_file(tmp_path: Path):
    """
    Redirect the storage module's internal _TASKS_FILE to a temp location
    for the duration of each test, then restore the original.
    """
    temp_file = tmp_path / "tasks.json"
    with patch.object(storage_module, "_TASKS_FILE", temp_file):
        yield temp_file


# ===========================================================================
# load_tasks
# ===========================================================================

class TestLoadTasks:
    def test_returns_empty_dict_when_file_missing(self, tmp_tasks_file):
        assert not tmp_tasks_file.exists()
        result = load_tasks()
        assert result == {}

    def test_returns_parsed_dict_when_file_exists(self, tmp_tasks_file):
        data = {
            "id-1": {
                "id": "id-1",
                "title": "Sample",
                "description": None,
                "status": "todo",
                "priority": "medium",
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-01T00:00:00+00:00",
            }
        }
        tmp_tasks_file.write_text(json.dumps(data))
        result = load_tasks()
        assert result == data

    def test_returns_dict_type(self, tmp_tasks_file):
        tmp_tasks_file.write_text("{}")
        result = load_tasks()
        assert isinstance(result, dict)

    def test_loads_multiple_tasks(self, tmp_tasks_file):
        data = {
            "id-1": {"id": "id-1", "title": "T1"},
            "id-2": {"id": "id-2", "title": "T2"},
        }
        tmp_tasks_file.write_text(json.dumps(data))
        result = load_tasks()
        assert len(result) == 2
        assert "id-1" in result
        assert "id-2" in result


# ===========================================================================
# save_tasks
# ===========================================================================

class TestSaveTasks:
    def test_creates_file_if_not_present(self, tmp_tasks_file):
        assert not tmp_tasks_file.exists()
        save_tasks({"id-1": {"id": "id-1", "title": "New"}})
        assert tmp_tasks_file.exists()

    def test_saved_data_is_valid_json(self, tmp_tasks_file):
        save_tasks({"id-1": {"id": "id-1", "title": "New"}})
        content = tmp_tasks_file.read_text()
        parsed = json.loads(content)  # must not raise
        assert isinstance(parsed, dict)

    def test_save_and_load_roundtrip(self, tmp_tasks_file):
        original = {
            "id-1": {
                "id": "id-1",
                "title": "Round-trip task",
                "description": "desc",
                "status": "in-progress",
                "priority": "high",
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-02T00:00:00+00:00",
            }
        }
        save_tasks(original)
        result = load_tasks()
        assert result == original

    def test_save_overwrites_previous_content(self, tmp_tasks_file):
        save_tasks({"id-1": {"id": "id-1", "title": "First"}})
        save_tasks({"id-2": {"id": "id-2", "title": "Second"}})
        result = load_tasks()
        assert "id-1" not in result
        assert "id-2" in result

    def test_save_empty_dict(self, tmp_tasks_file):
        save_tasks({})
        result = load_tasks()
        assert result == {}


# ===========================================================================
# Round-trip via service-level operations (covers delete path)
# ===========================================================================

class TestSaveLoadDeletePattern:
    def test_removing_key_and_saving_removes_from_file(self, tmp_tasks_file):
        tasks = {
            "id-1": {"id": "id-1", "title": "Keep"},
            "id-2": {"id": "id-2", "title": "Remove"},
        }
        save_tasks(tasks)
        loaded = load_tasks()
        del loaded["id-2"]
        save_tasks(loaded)

        final = load_tasks()
        assert "id-1" in final
        assert "id-2" not in final
