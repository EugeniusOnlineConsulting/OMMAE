"""
OMMAE Team Management agent.
Humans own membership and approvals. Ara only drafts tasks from live HQ work.
"""
from __future__ import annotations

import uuid
from typing import Any

from store import add_log, mutate, snapshot, utcnow


def list_members() -> list[dict[str, Any]]:
    members = list(snapshot().get("members", {}).values())
    members.sort(key=lambda item: item.get("name", ""))
    return members


def list_roles() -> list[dict[str, Any]]:
    roles = list(snapshot().get("roles", {}).values())
    counts: dict[str, int] = {}
    for member in list_members():
        role = (member.get("role") or "staff").lower()
        counts[role] = counts.get(role, 0) + 1
    for role in roles:
        role["memberCount"] = counts.get(role.get("id", ""), 0)
    return roles


def invite_member(name: str, email: str, role: str = "staff") -> dict[str, Any]:
    name = (name or "").strip()
    email = (email or "").strip().lower()
    if not name or "@" not in email:
        raise ValueError("name and email are required")
    member_id = f"member-{uuid.uuid4().hex[:8]}"
    record = {
        "id": member_id,
        "name": name,
        "email": email,
        "role": (role or "staff").lower(),
        "active": True,
        "lastActive": utcnow(),
        "createdAt": utcnow(),
    }

    def _write(data: dict[str, Any]) -> None:
        data.setdefault("members", {})[member_id] = record

    mutate(_write)
    add_log("team", f"Invited {record['name']} as {record['role']}.", actor="human")
    return record


def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    tasks = list(snapshot().get("tasks", {}).values())
    if status:
        tasks = [task for task in tasks if task.get("status") == status]
    tasks.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return tasks


def _add_task(data: dict[str, Any], title: str, description: str, assignee_id: str | None, priority: str) -> dict[str, Any]:
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    record = {
        "id": task_id,
        "title": title,
        "description": description,
        "assigneeId": assignee_id,
        "priority": priority,
        "status": "staged",
        "createdBy": "agent",
        "createdAt": utcnow(),
        "approvedAt": None,
    }
    data.setdefault("tasks", {})[task_id] = record
    return record


def propose_tasks() -> list[dict[str, Any]]:
    data = snapshot()
    created: list[dict[str, Any]] = []
    staged_videos = [v for v in data.get("videos", {}).values() if v.get("status") == "staged"]
    staged_leads = [lead for lead in data.get("leads", {}).values() if lead.get("status") == "staged"]
    approved_leads = [lead for lead in data.get("leads", {}).values() if lead.get("status") == "approved"]
    owner = next((m["id"] for m in data.get("members", {}).values() if m.get("role") == "owner"), None)
    manager = next((m["id"] for m in data.get("members", {}).values() if m.get("role") == "manager"), owner)

    def _write(bucket: dict[str, Any]) -> None:
        if staged_videos:
            created.append(
                _add_task(
                    bucket,
                    f"Review {len(staged_videos)} staged video(s)",
                    "Content is waiting in HQ staging. Approve, reject, or send back before anything posts.",
                    manager,
                    "high",
                )
            )
        if staged_leads:
            created.append(
                _add_task(
                    bucket,
                    f"Approve {len(staged_leads)} acquisition draft(s)",
                    "Ara drafted outreach. No email or affiliate contact goes out until a human signs it.",
                    owner,
                    "high",
                )
            )
        if approved_leads:
            created.append(
                _add_task(
                    bucket,
                    f"Work {len(approved_leads)} approved lead(s)",
                    "Outreach is cleared. Assign an owner and mark contacted after the human send.",
                    manager,
                    "medium",
                )
            )
        created.append(
            _add_task(
                bucket,
                "Daily compliance pass",
                "No medical claims in scripts, captions, or outreach. Keep Indigenous ownership language accurate.",
                manager,
                "medium",
            )
        )

    mutate(_write)
    add_log("team", f"Ara proposed {len(created)} team tasks. Waiting on human approval.")
    return created


def update_task(task_id: str, status: str, assignee_id: str | None = None) -> dict[str, Any] | None:
    updated: dict[str, Any] | None = None

    def _write(data: dict[str, Any]) -> None:
        nonlocal updated
        task = data.get("tasks", {}).get(task_id)
        if not task:
            return
        task["status"] = status
        if assignee_id:
            task["assigneeId"] = assignee_id
        if status == "approved":
            task["approvedAt"] = utcnow()
        updated = dict(task)

    mutate(_write)
    if updated:
        add_log("team", f"Task '{updated['title']}' marked {status}.", actor="human")
    return updated
