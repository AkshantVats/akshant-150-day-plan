"""Single source for calendar day and per-day status in the 150-day plan."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
CURRENT_DAY_PATH = DATA / "current-day.json"
PLAN_PATH = DATA / "plan.json"


def load_current_day() -> int:
    if CURRENT_DAY_PATH.exists():
        raw = json.loads(CURRENT_DAY_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "current_day" in raw:
            return int(raw["current_day"])
        if isinstance(raw, int):
            return raw
    if PLAN_PATH.exists():
        raw = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "current_day" in raw:
            return int(raw["current_day"])
    return 0


def save_current_day(day: int) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    CURRENT_DAY_PATH.write_text(
        json.dumps({"current_day": day}, indent=2) + "\n",
        encoding="utf-8",
    )


def load_saved_statuses() -> dict[int, str]:
    if not PLAN_PATH.exists():
        return {}
    raw = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    days = raw.get("days", raw if isinstance(raw, list) else [])
    return {int(d["day"]): d.get("status", "pending") for d in days if "day" in d}


def resolve_status(day: int, current_day: int, saved: str | None = None) -> str:
    if saved == "done":
        return "done"
    if day < current_day:
        return "done"
    if day == current_day:
        return "today" if saved != "done" else "done"
    return "pending"


def apply_statuses(
    days: list[dict],
    current_day: int | None = None,
    saved_by_day: dict[int, str] | None = None,
) -> list[dict]:
    current_day = load_current_day() if current_day is None else current_day
    saved_by_day = load_saved_statuses() if saved_by_day is None else saved_by_day
    out: list[dict] = []
    for d in days:
        day_num = int(d["day"])
        st = resolve_status(day_num, current_day, saved_by_day.get(day_num))
        out.append({**d, "status": st})
    return out
