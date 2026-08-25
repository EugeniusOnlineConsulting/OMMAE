"""
Gloris — HQ operator for realtime incidents.
Premium lanes (Codex/OpenAI) are optional. Local diagnosis always runs.
Nothing is deployed until a human approves the Cursor Bridge job.
"""
from __future__ import annotations

import os
import re
import uuid
from typing import Any

from store import add_log, mutate, snapshot, utcnow

SECRET_RE = re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{8,}")


def redact(text: str) -> str:
    return SECRET_RE.sub("sk-***REDACTED***", text or "")


def count_placeholders(sql: str) -> int:
    return len(re.findall(r"\?", sql or ""))


def parse_params(blob: str) -> list[str]:
    match = re.search(r"params:\s*(.*)$", blob or "", re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    raw = match.group(1).strip().rstrip(".")
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    parts = [part.strip().strip("'\"") for part in re.split(r",\s*", raw) if part.strip()]
    return parts


CREATE_PRODUCT_FIELDS = [
    "name",
    "slug",
    "categoryId",
    "price",
    "cost",
    "inStock",
    "stockQuantity",
    "imageUrl",
    "image_alt",
    "status",
]


def create_product_params(payload: dict[str, Any]) -> list[Any]:
    """Always bind optional image fields so placeholders and params stay aligned."""
    return [
        payload.get("name"),
        payload.get("slug"),
        payload.get("categoryId"),
        payload.get("price"),
        payload.get("cost"),
        payload.get("inStock", True),
        payload.get("stockQuantity", 0),
        payload.get("imageUrl") if payload.get("imageUrl") not in (None, "") else None,
        payload.get("image_alt") or payload.get("name") or "",
        payload.get("status") or "draft",
    ]


def buggy_create_product_params(payload: dict[str, Any]) -> list[Any]:
    """Reproduces the Spirit Fire bug: skip empty image fields but leave SQL placeholders."""
    params = [
        payload.get("name"),
        payload.get("slug"),
        payload.get("categoryId"),
        payload.get("price"),
        payload.get("cost"),
        payload.get("inStock", True),
        payload.get("stockQuantity", 0),
    ]
    if payload.get("imageUrl"):
        params.append(payload.get("imageUrl"))
    if payload.get("image_alt"):
        params.append(payload.get("image_alt"))
    params.append(payload.get("status") or "draft")
    return params


def diagnose_sql_mismatch(error_text: str) -> dict[str, Any] | None:
    text = redact(error_text)
    lowered = text.lower()
    if "could not create product" not in lowered and "insert into" not in lowered:
        return None
    if "products" not in lowered:
        return None
    placeholders = count_placeholders(text)
    params = parse_params(text)
    missing_images = "imageurl" in lowered.replace("_", "") or "image_alt" in lowered
    if placeholders and params and placeholders != len(params):
        missing = placeholders - len(params)
        return {
            "playbook": "spiritfire_product_insert",
            "title": "Product insert parameter mismatch",
            "site": "spiritfiretobacco.com",
            "severity": "high",
            "placeholders": placeholders,
            "paramCount": len(params),
            "missing": missing,
            "summary": (
                f"INSERT into products has {placeholders} placeholders but {len(params)} bound params. "
                "imageUrl and image_alt stay in the SQL when no image is uploaded, then status shifts left."
            ),
            "fix": (
                "Always push imageUrl and image_alt onto the params array (null/empty string is fine). "
                "Do not omit optional image values while leaving `?` in the VALUES clause."
            ),
            "patch": SPIRITFIRE_PATCH,
            "cursorPrompt": (
                "On spiritfiretobacco.com admin product create, the products INSERT uses 10 bound fields "
                "(name, slug, categoryId, price, cost, inStock, stockQuantity, imageUrl, image_alt, status) "
                "but only 8 params are passed when image fields are empty. Align params with placeholders. "
                "Do not deploy until HQ human approval."
            ),
        }
    if missing_images and "failed query" in lowered:
        return {
            "playbook": "spiritfire_product_insert",
            "title": "Product insert parameter mismatch",
            "site": "spiritfiretobacco.com",
            "severity": "high",
            "summary": "Product create failed on products INSERT. Likely optional image params dropped.",
            "fix": "Always bind imageUrl and image_alt.",
            "patch": SPIRITFIRE_PATCH,
            "cursorPrompt": "Fix products INSERT param alignment for optional imageUrl/image_alt.",
        }
    return None


def diagnose_premium_failure(error_text: str) -> dict[str, Any] | None:
    text = redact(error_text)
    lowered = text.lower()
    if "codex premium lane failed" not in lowered and "invalid_api_key" not in lowered and "401 unauthorized" not in lowered:
        return None
    return {
        "playbook": "gloris_premium_fallback",
        "title": "Gloris premium lane 401 — local fallback required",
        "site": "ommae-hq",
        "severity": "high",
        "summary": (
            "Codex/OpenAI returned invalid_api_key. Task stopped with no local fallback, "
            "so no customer data changed. HQ must diagnose locally and open a Cursor Bridge job."
        ),
        "fix": (
            "Catch premium-lane 401/network failures, run local playbooks, and stage a Cursor Bridge "
            "job for human approval. Never halt the incident because OpenAI is down."
        ),
        "patch": None,
        "cursorPrompt": "Use OMMAE HQ local Gloris diagnosis. Do not block on Codex.",
    }


SPIRITFIRE_PATCH = """// Always bind optional image columns. Empty is null — never drop the param.
const params = [
  name,
  slug,
  categoryId,
  price,
  cost,
  inStock,
  stockQuantity,
  imageUrl ?? null,
  imageAlt ?? name ?? null,
  status ?? 'draft',
];
// placeholders in SQL must equal params.length (10)
"""


def local_diagnose(error_text: str) -> dict[str, Any]:
    for detector in (diagnose_sql_mismatch, diagnose_premium_failure):
        hit = detector(error_text)
        if hit:
            return hit
    return {
        "playbook": "generic",
        "title": "Unclassified incident",
        "site": "unknown",
        "severity": "medium",
        "summary": "No playbook matched. Staged for human review with Cursor Bridge.",
        "fix": "Inspect the error in HQ and assign an owner.",
        "patch": None,
        "cursorPrompt": redact(error_text)[:1500],
    }


def try_premium_lane(error_text: str) -> dict[str, Any]:
    """Optional Codex/OpenAI lane. Any failure falls back locally — never abort the incident."""
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CODEX_API_KEY") or ""
    force_fail = os.environ.get("GLORIS_FORCE_PREMIUM_FAIL") == "1"
    if not key and not force_fail:
        return {"used": False, "ok": False, "reason": "no_premium_key", "fallback": "local"}
    if force_fail or key.endswith("wtEA"):
        return {
            "used": True,
            "ok": False,
            "reason": "premium_401_invalid_api_key",
            "fallback": "local",
        }
    if os.environ.get("GLORIS_PREMIUM") != "1":
        return {"used": False, "ok": False, "reason": "premium_disabled", "fallback": "local"}
    try:
        import requests

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Diagnose this production error. Be concise."},
                    {"role": "user", "content": redact(error_text)[:4000]},
                ],
                "max_tokens": 400,
            },
            timeout=20,
        )
        if response.status_code >= 400:
            return {
                "used": True,
                "ok": False,
                "reason": f"premium_{response.status_code}",
                "fallback": "local",
            }
        return {"used": True, "ok": True, "reason": "premium_ok", "fallback": None}
    except Exception as exc:
        return {"used": True, "ok": False, "reason": f"premium_error:{exc}", "fallback": "local"}


def cursor_bridge_payload(incident: dict[str, Any]) -> dict[str, Any]:
    diagnosis = incident.get("diagnosis") or {}
    return {
        "kind": "cursor_bridge",
        "hq": "ommae",
        "operator": "gloris",
        "incidentId": incident.get("id"),
        "taskId": incident.get("taskId"),
        "site": diagnosis.get("site"),
        "playbook": diagnosis.get("playbook"),
        "summary": diagnosis.get("summary"),
        "fix": diagnosis.get("fix"),
        "patch": diagnosis.get("patch"),
        "prompt": diagnosis.get("cursorPrompt"),
        "hitl": "approve_before_deploy",
        "createdAt": incident.get("createdAt"),
    }


def ingest_incident(error_text: str, source: str = "operator", site: str | None = None, task_id: str | None = None) -> dict[str, Any]:
    redacted = redact(error_text)
    premium = try_premium_lane(redacted)
    diagnosis = local_diagnose(redacted)
    if site:
        diagnosis["site"] = site
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    record = {
        "id": incident_id,
        "taskId": task_id,
        "source": source,
        "site": diagnosis.get("site") or site or "unknown",
        "error": redacted[:8000],
        "status": "staged",
        "diagnosis": diagnosis,
        "premium": premium,
        "createdBy": "gloris",
        "createdAt": utcnow(),
        "approvedAt": None,
    }

    def _write(data: dict[str, Any]) -> None:
        data.setdefault("incidents", {})[incident_id] = record
        job_id = f"bridge-{uuid.uuid4().hex[:8]}"
        job = {
            "id": job_id,
            "incidentId": incident_id,
            "status": "staged",
            "payload": cursor_bridge_payload(record),
            "createdAt": utcnow(),
        }
        data.setdefault("bridgeJobs", {})[job_id] = job
        record["bridgeJobId"] = job_id

    mutate(_write)
    add_log(
        "gloris",
        f"Gloris staged incident {incident_id} via {diagnosis.get('playbook')} "
        f"(premium={premium.get('reason')}, fallback={premium.get('fallback')}).",
        actor="Gloris",
    )
    return snapshot().get("incidents", {}).get(incident_id) or record


def list_incidents(status: str | None = None) -> list[dict[str, Any]]:
    items = list(snapshot().get("incidents", {}).values())
    if status:
        items = [item for item in items if item.get("status") == status]
    items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return items


def update_incident(incident_id: str, status: str) -> dict[str, Any] | None:
    updated = None

    def _write(data: dict[str, Any]) -> None:
        nonlocal updated
        item = data.get("incidents", {}).get(incident_id)
        if not item:
            return
        item["status"] = status
        if status == "approved":
            item["approvedAt"] = utcnow()
        job_id = item.get("bridgeJobId")
        if job_id and job_id in data.get("bridgeJobs", {}):
            data["bridgeJobs"][job_id]["status"] = "approved" if status == "approved" else status
        updated = dict(item)

    mutate(_write)
    if updated:
        add_log("gloris", f"Incident {incident_id} marked {status}.", actor="human")
    return updated


def list_bridge_jobs(status: str | None = "staged") -> list[dict[str, Any]]:
    jobs = list(snapshot().get("bridgeJobs", {}).values())
    if status:
        jobs = [job for job in jobs if job.get("status") == status]
    jobs.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return jobs


def next_bridge_job() -> dict[str, Any] | None:
    jobs = list_bridge_jobs("approved")
    if jobs:
        return jobs[0]
    staged = list_bridge_jobs("staged")
    return staged[0] if staged else None
