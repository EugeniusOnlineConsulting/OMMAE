"""
OMMAE Client Acquisition agent.
Drafts partnership, affiliate, collab, and win-back leads for human approval.
Nothing is contacted until a human approves the outreach.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from store import add_log, mutate, utcnow

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

DEFAULT_LEADS = [
    {
        "name": "Northern Sage Wellness Co-op",
        "channel": "wholesale",
        "email": "partnerships@example-coop.invalid",
        "region": "Ontario",
        "score": 86,
        "why": "Indigenous-owned wellness retailer looking for a sovereign supply partner.",
        "outreach": (
            "Look — we are not another catalogue brand. Mohawk Medibles is Indigenous-owned, "
            "ships Canada-wide from Tyendinaga, and we keep the story honest. Want a wholesale "
            "menu and a 15-minute intro this week?"
        ),
    },
    {
        "name": "Lake & Cedar Affiliates",
        "channel": "affiliate",
        "email": "hello@example-affiliates.invalid",
        "region": "Canada-wide",
        "score": 74,
        "why": "Content creators already talking about mail-order cannabis wellness.",
        "outreach": (
            "We run a real affiliate desk, not a coupon dump. If your audience cares about "
            "quality and Indigenous ownership, we will send a tracked link, creative, and a "
            "human to approve every public claim."
        ),
    },
    {
        "name": "Tyendinaga Community Newsletter",
        "channel": "community",
        "email": "editor@example-community.invalid",
        "region": "Tyendinaga Mohawk Territory",
        "score": 91,
        "why": "Local trust channel. Highest conversion when the message stays human.",
        "outreach": (
            "We would like to sponsor a community wellness note — no medical claims, no hype. "
            "Just who we are, where we ship from, and how neighbours can reach the store."
        ),
    },
    {
        "name": "Dormant buyers — 90 day silence",
        "channel": "winback",
        "email": "crm-segment@mohawkmedibles.ca",
        "region": "Existing customers",
        "score": 68,
        "why": "Repeat rate drops after one order. Needs a human-approved win-back, not a blast.",
        "outreach": (
            "It has been a while. New arrivals are up, packing is still discreet, and we did "
            "not sell your inbox to anyone. Here is a quiet invite back — only if HQ approves."
        ),
    },
]


def _draft_with_gemini(lead: dict[str, Any], client: str, topic: str) -> str:
    if not GEMINI_API_KEY:
        return lead["outreach"]
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"Write a short, warm outreach note for {client}. "
            f"Audience: {lead['name']} ({lead['channel']}). Topic: {topic}. "
            "No medical claims. No hype. Under 70 words. Return only the note."
        )
        text = model.generate_content(prompt).text.strip().replace("*", "")
        return text or lead["outreach"]
    except Exception:
        return lead["outreach"]


def propose_leads(client: str = "mohawk_medibles", topic: str = "cannabis wellness", count: int = 4) -> list[dict[str, Any]]:
    templates = DEFAULT_LEADS[: max(1, min(count, len(DEFAULT_LEADS)))]
    created: list[dict[str, Any]] = []
    for template in templates:
        lead_id = f"lead-{uuid.uuid4().hex[:8]}"
        created.append(
            {
                "id": lead_id,
                "client": client,
                "name": template["name"],
                "channel": template["channel"],
                "email": template["email"],
                "region": template["region"],
                "score": template["score"],
                "why": template["why"],
                "outreach": _draft_with_gemini(template, client, topic),
                "status": "staged",
                "assignedTo": None,
                "createdAt": utcnow(),
                "approvedAt": None,
                "contactedAt": None,
                "createdBy": "agent",
            }
        )

    def _write(data: dict[str, Any]) -> None:
        bucket = data.setdefault("leads", {})
        for record in created:
            bucket[record["id"]] = record

    mutate(_write)
    add_log(
        "acquisition",
        f"Ara staged {len(created)} acquisition leads for {client}. Waiting on human approval.",
    )
    return created


def list_leads(client: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    from store import snapshot

    leads = list(snapshot().get("leads", {}).values())
    if client:
        leads = [lead for lead in leads if lead.get("client") == client]
    if status:
        leads = [lead for lead in leads if lead.get("status") == status]
    leads.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return leads


def update_lead(lead_id: str, status: str, assigned_to: str | None = None) -> dict[str, Any] | None:
    updated: dict[str, Any] | None = None

    def _write(data: dict[str, Any]) -> None:
        nonlocal updated
        lead = data.get("leads", {}).get(lead_id)
        if not lead:
            return
        lead["status"] = status
        if assigned_to:
            lead["assignedTo"] = assigned_to
        if status == "approved":
            lead["approvedAt"] = utcnow()
        if status == "contacted":
            lead["contactedAt"] = utcnow()
        updated = dict(lead)

    mutate(_write)
    if updated:
        add_log("acquisition", f"Lead {updated['name']} marked {status}.", actor="human")
    return updated
