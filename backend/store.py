"""
OMMAE HQ persistence.
JSON file store so staging, leads, team, and logs survive process restarts.
"""
from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

DEFAULT_STORE_PATH = os.environ.get(
    "OMMAE_STORE_PATH",
    os.path.join(os.path.dirname(__file__), "data", "ommae.json"),
)

_lock = threading.RLock()
_cache: dict[str, Any] | None = None
_store_path = DEFAULT_STORE_PATH


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty() -> dict[str, Any]:
    return {
        "videos": {},
        "leads": {},
        "members": {},
        "roles": {},
        "tasks": {},
        "logs": [],
    }


def _seed(data: dict[str, Any]) -> dict[str, Any]:
    if not data.get("members"):
        data["members"] = {
            "member-eugene": {
                "id": "member-eugene",
                "name": "Eugene Agyemang",
                "email": "eugene@mohawkmedibles.ca",
                "role": "owner",
                "active": True,
                "lastActive": utcnow(),
                "createdAt": utcnow(),
            },
            "member-ara": {
                "id": "member-ara",
                "name": "Ara",
                "email": "ara@ommae.local",
                "role": "agent",
                "active": True,
                "lastActive": utcnow(),
                "createdAt": utcnow(),
            },
            "member-ops": {
                "id": "member-ops",
                "name": "HQ Operations",
                "email": "ops@mohawkmedibles.ca",
                "role": "manager",
                "active": True,
                "lastActive": utcnow(),
                "createdAt": utcnow(),
            },
        }
    if not data.get("roles"):
        data["roles"] = {
            "owner": {
                "id": "owner",
                "name": "Owner",
                "description": "Full HQ access, approvals, and posting",
                "permissions": ["approve", "post", "invite", "assign", "outreach"],
                "memberCount": 1,
            },
            "manager": {
                "id": "manager",
                "name": "Manager",
                "description": "Review staged work and assign team tasks",
                "permissions": ["approve", "assign", "outreach"],
                "memberCount": 1,
            },
            "agent": {
                "id": "agent",
                "name": "Agent",
                "description": "Drafts content, leads, and tasks for human approval",
                "permissions": ["draft"],
                "memberCount": 1,
            },
            "staff": {
                "id": "staff",
                "name": "Staff",
                "description": "Execute approved tasks",
                "permissions": ["execute"],
                "memberCount": 0,
            },
        }
    data.setdefault("videos", {})
    data.setdefault("leads", {})
    data.setdefault("tasks", {})
    data.setdefault("logs", [])
    return data


def configure(path: str | None = None) -> None:
    global _store_path, _cache
    with _lock:
        if path:
            _store_path = path
        _cache = None


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _load_unlocked() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    if os.path.exists(_store_path):
        try:
            with open(_store_path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if not isinstance(raw, dict):
                raw = _empty()
        except (json.JSONDecodeError, OSError):
            raw = _empty()
    else:
        raw = _empty()
    _cache = _seed(raw)
    return _cache


def _save_unlocked() -> None:
    if _cache is None:
        return
    _ensure_dir(_store_path)
    tmp_path = f"{_store_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(_cache, handle, indent=2)
    os.replace(tmp_path, _store_path)


def snapshot() -> dict[str, Any]:
    with _lock:
        return deepcopy(_load_unlocked())


def mutate(mutator) -> dict[str, Any]:
    with _lock:
        data = _load_unlocked()
        mutator(data)
        _save_unlocked()
        return deepcopy(data)


def reset(path: str | None = None) -> None:
    configure(path)
    with _lock:
        global _cache
        _cache = _seed(_empty())
        _save_unlocked()


def add_log(kind: str, message: str, actor: str = "Ara") -> dict[str, Any]:
    entry = {
        "id": f"log-{len(snapshot().get('logs', [])) + 1:05d}",
        "type": kind,
        "message": message,
        "actor": actor,
        "createdAt": utcnow(),
    }

    def _append(data: dict[str, Any]) -> None:
        data.setdefault("logs", [])
        entry["id"] = f"log-{len(data['logs']) + 1:05d}"
        data["logs"].insert(0, entry)
        data["logs"] = data["logs"][:200]

    mutate(_append)
    return entry
