import json
from pathlib import Path

_TASKS_FILE = Path(__file__).parent.parent / "tasks.json"


def load_tasks() -> dict[str, dict]:
    if not _TASKS_FILE.exists():
        return {}
    with open(_TASKS_FILE) as f:
        return json.load(f)


def save_tasks(tasks: dict[str, dict]) -> None:
    with open(_TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)
