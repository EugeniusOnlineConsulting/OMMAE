"""
OMMAE HQ API — Mohawk Medibles command center.

Agent drafts work. Humans approve it. Nothing posts or outreaches without a person in the loop.
Supports both path routes (/generate-video) and the admin action contract (?action=videos).
"""
from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))

import functions_framework
from flask import Flask, jsonify, request, send_from_directory

import acquisition
import gloris
import team_ops
from store import add_log, mutate, snapshot, utcnow

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "CT96S5RC77U74JDR24HG")

ADMIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "admin"))
DEFAULT_CLIENT = "mohawk_medibles"

app = Flask(__name__)


def cors_headers() -> dict[str, str]:
    origin = request.headers.get("Origin", "*")
    return {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Credentials": "false",
    }


def ok(payload: dict, status: int = 200):
    return jsonify(payload), status, cors_headers()


def normalize_client(value: str | None) -> str:
    raw = (value or DEFAULT_CLIENT).strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "mohawkmedibles": DEFAULT_CLIENT,
        "mohawk_medibles": DEFAULT_CLIENT,
        "mohawk": DEFAULT_CLIENT,
        "spiritfire": "spirit_fire",
        "spiritfiretobacco": "spirit_fire",
        "spirit_fire_tobacco": "spirit_fire",
        "spirit_fire": "spirit_fire",
    }
    return aliases.get(raw, raw or DEFAULT_CLIENT)


def generate_audio_elevenlabs(text: str, output_path: str):
    import requests

    if not ELEVENLABS_API_KEY:
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.85,
            "style": 0.6,
            "use_speaker_boost": True,
        },
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        if response.status_code == 200:
            with open(output_path, "wb") as handle:
                handle.write(response.content)
            return output_path
    except Exception as exc:
        print(f"ElevenLabs error: {exc}")
    return None


EUGENE_VOICE_PROMPT = """You are writing a 30-second video script for Mohawk Medibles, an indigenous cannabis wellness brand.
Voice: EUGENE - authentic, warm, real. Rules:
- Short sentences. Punchy. Human.
- Use "Look," "I get it," "Here's the thing"
- No corporate jargon. No medical claims.
- Under 80 words (30 seconds spoken)
Topic: {topic}
Write ONLY the script words."""


def generate_script_gemini(topic: str) -> str:
    fallback = (
        f"Look. {topic.split()[0].capitalize()} isn't complicated. "
        "We're just trying to help you feel better. The natural way. "
        "Mohawk Medibles. Real wellness. Real simple. Check us out."
    )
    if not GEMINI_API_KEY:
        return fallback
    try:
        import google.generativeai as genai

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(EUGENE_VOICE_PROMPT.format(topic=topic))
        return response.text.strip().replace('"', "").replace("*", "")
    except Exception:
        return "Look. Wellness shouldn't be complicated. Mohawk Medibles. We keep it simple. We keep it real."


def public_video(video: dict) -> dict:
    created = video.get("createdAt") or video.get("created_at") or utcnow()
    return {
        "id": video["videoId"],
        "videoId": video["videoId"],
        "client": video.get("client", DEFAULT_CLIENT),
        "topic": video.get("topic", ""),
        "script": video.get("script", ""),
        "status": video.get("status", "staged"),
        "audioUrl": video.get("audioUrl"),
        "videoUrl": video.get("videoUrl"),
        "video_url": video.get("videoUrl"),
        "driveUrl": video.get("driveUrl"),
        "thumbnail": video.get("thumbnail") or "",
        "duration": video.get("duration") or "0:30",
        "realGeneration": bool(video.get("realGeneration")),
        "createdAt": created,
        "created_at": created,
        "approvedAt": video.get("approvedAt"),
        "postedAt": video.get("postedAt"),
        "postResult": video.get("postResult"),
    }


def list_videos(client: str | None = None, status: str | None = None) -> list[dict]:
    videos = [public_video(item) for item in snapshot().get("videos", {}).values()]
    if client:
        videos = [item for item in videos if item.get("client") == client]
    if status:
        allowed = {status}
        if status == "approved":
            allowed.add("posted")
            allowed.add("queued")
        videos = [item for item in videos if item.get("status") in allowed]
    videos.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return videos


def create_video_response(client: str, topic: str, use_real_tts: bool = True) -> dict:
    video_id = f"video-{uuid.uuid4().hex[:8]}"
    script = generate_script_gemini(topic)
    audio_path = f"/tmp/{video_id}_audio.mp3"
    real_generation = False
    if use_real_tts and ELEVENLABS_API_KEY:
        if generate_audio_elevenlabs(script, audio_path):
            real_generation = True
    video_data = {
        "videoId": video_id,
        "client": client,
        "topic": topic,
        "script": script,
        "audioUrl": f"/staging/{client}/{video_id}.mp3" if real_generation else None,
        "videoUrl": f"/staging/{client}/{video_id}.mp4",
        "driveUrl": f"https://drive.google.com/file/d/{video_id}/view",
        "thumbnail": "",
        "duration": "0:30",
        "realGeneration": real_generation,
        "status": "staged",
        "createdAt": utcnow(),
        "approvedAt": None,
        "postedAt": None,
        "postResult": None,
    }

    def _write(data: dict) -> None:
        data.setdefault("videos", {})[video_id] = video_data

    mutate(_write)
    add_log("content", f"Staged video {video_id} on '{topic}'. Waiting on human approval.")
    try:
        from ara_notifications import content_ready

        content_ready(topic)
    except Exception:
        pass
    return video_data


def update_video_status(video_id: str, status: str) -> dict | None:
    updated = None

    def _write(data: dict) -> None:
        nonlocal updated
        video = data.get("videos", {}).get(video_id)
        if not video:
            return
        video["status"] = status
        if status == "approved":
            video["approvedAt"] = utcnow()
        if status in {"posted", "queued"}:
            video["postedAt"] = utcnow()
        updated = dict(video)

    mutate(_write)
    if updated:
        add_log("content", f"Video {video_id} marked {status}.", actor="human")
    return updated


def post_video(video_id: str) -> tuple[dict | None, str]:
    video = snapshot().get("videos", {}).get(video_id)
    if not video:
        return None, "Video not found"
    if video.get("status") not in {"approved", "queued"}:
        return None, "Video must be approved before posting"

    caption = video.get("script") or video.get("topic") or "Mohawk Medibles"
    hashtags = ["mohawkmedibles", "cannabis", "indigenous", "wellness"]
    result = {
        "success": False,
        "platforms_posted": 0,
        "message": "Social credentials are not configured. Video queued for posting.",
    }
    try:
        import asyncio
        from social_poster import post_now

        result = asyncio.run(
            post_now(video.get("videoUrl") or "", caption, hashtags)
        )
    except Exception as exc:
        result = {"success": False, "error": str(exc), "platforms_posted": 0}

    posted = bool(result.get("success")) and int(result.get("platforms_posted") or 0) > 0
    status = "posted" if posted else "queued"

    def _write(data: dict) -> None:
        item = data.get("videos", {}).get(video_id)
        if not item:
            return
        item["status"] = status
        item["postedAt"] = utcnow()
        item["postResult"] = result

    mutate(_write)
    add_log("content", f"Video {video_id} {status}. {result.get('message', '')}", actor="human")
    if posted:
        try:
            from ara_notifications import posted as notify_posted

            notify_posted(int(result.get("platforms_posted") or 0), ["Instagram", "TikTok", "YouTube"])
        except Exception:
            pass
    updated = snapshot().get("videos", {}).get(video_id)
    return updated, status


def json_body() -> dict:
    return request.get_json(silent=True) or {}


def query_action() -> str:
    body = json_body()
    return (
        request.args.get("action")
        or body.get("action")
        or ""
    ).strip()


@app.after_request
def add_cors(response):
    for key, value in cors_headers().items():
        response.headers[key] = value
    return response


@app.route("/", methods=["GET", "POST", "OPTIONS"])
def root():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    action = query_action()
    if action:
        return handle_action(action)
    data = snapshot()
    return ok(
        {
            "status": "operational",
            "version": "0.2.0",
            "message": "OMMAE HQ — agent drafts, humans approve",
            "services": {
                "gemini": "ready" if GEMINI_API_KEY else "not_configured",
                "elevenlabs": "ready" if ELEVENLABS_API_KEY else "not_configured",
            },
            "counts": {
                "videos": len(data.get("videos", {})),
                "leads": len(data.get("leads", {})),
                "tasks": len(data.get("tasks", {})),
                "members": len(data.get("members", {})),
                "incidents": len(data.get("incidents", {})),
            },
        }
    )


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    return ok({"status": "healthy", "version": "0.2.0"})


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


@app.route("/admin")
@app.route("/admin/")
@app.route("/hq")
def admin_page():
    return send_from_directory(ADMIN_DIR, "index.html")


@app.route("/generate-video", methods=["GET", "POST", "OPTIONS"])
def generate_video_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    if request.method == "GET":
        return ok({"message": "POST with {client, topic}"})
    return handle_generate_video()


@app.route("/list-staging", methods=["GET", "OPTIONS"])
def list_staging_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    client = normalize_client(request.args.get("client"))
    return ok({"client": client, "videos": list_videos(client=client, status="staged")})


@app.route("/videos", methods=["GET", "OPTIONS"])
def videos_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    client = normalize_client(request.args.get("client"))
    return ok({"success": True, "client": client, "videos": list_videos(client=client)})


@app.route("/approve", methods=["POST", "OPTIONS"])
def approve_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    video_id = json_body().get("videoId")
    video = update_video_status(video_id, "approved") if video_id else None
    if not video:
        return ok({"success": False, "error": "Video not found"}, 404)
    return ok({"success": True, "videoId": video_id, "status": "approved"})


@app.route("/reject", methods=["POST", "OPTIONS"])
def reject_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    video_id = json_body().get("videoId")
    video = update_video_status(video_id, "rejected") if video_id else None
    if not video:
        return ok({"success": False, "error": "Video not found"}, 404)
    return ok({"success": True, "videoId": video_id, "status": "rejected"})


@app.route("/leads", methods=["GET", "POST", "OPTIONS"])
def leads_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    client = normalize_client(request.args.get("client") or json_body().get("client"))
    if request.method == "POST":
        leads = acquisition.propose_leads(client=client, topic=json_body().get("topic") or "cannabis wellness")
        return ok({"success": True, "leads": leads})
    return ok({"success": True, "leads": acquisition.list_leads(client=client)})


@app.route("/team", methods=["GET", "POST", "OPTIONS"])
def team_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    if request.method == "POST":
        body = json_body()
        if not body.get("name") or not body.get("email"):
            return ok({"success": False, "error": "name and email are required"}, 400)
        try:
            member = team_ops.invite_member(body["name"], body["email"], body.get("role") or "staff")
        except ValueError as exc:
            return ok({"success": False, "error": str(exc)}, 400)
        return ok({"success": True, "member": member})
    return ok({"success": True, "members": team_ops.list_members(), "roles": team_ops.list_roles()})


@app.route("/tasks", methods=["GET", "POST", "OPTIONS"])
def tasks_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    if request.method == "POST":
        tasks = team_ops.propose_tasks()
        return ok({"success": True, "tasks": tasks})
    return ok({"success": True, "tasks": team_ops.list_tasks()})


@app.route("/logs", methods=["GET", "OPTIONS"])
def logs_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    return ok({"success": True, "logs": snapshot().get("logs", [])[:100]})


@app.route("/incidents", methods=["GET", "POST", "OPTIONS"])
def incidents_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    if request.method == "POST":
        body = json_body()
        error_text = body.get("error") or body.get("text") or ""
        if not error_text.strip():
            return ok({"success": False, "error": "error text is required"}, 400)
        incident = gloris.ingest_incident(
            error_text,
            source=body.get("source") or "operator",
            site=body.get("site"),
            task_id=body.get("taskId") or body.get("task_id"),
        )
        return ok({"success": True, "incident": incident, "bridge": gloris.cursor_bridge_payload(incident)})
    return ok({"success": True, "incidents": gloris.list_incidents()})


@app.route("/bridge", methods=["GET", "OPTIONS"])
@app.route("/bridge/next", methods=["GET", "OPTIONS"])
def bridge_route():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    job = gloris.next_bridge_job()
    return ok({"success": True, "job": job, "jobs": gloris.list_bridge_jobs(request.args.get("status"))})


def handle_generate_video():
    body = json_body()
    client = normalize_client(body.get("client") or request.args.get("client"))
    topic = body.get("topic") or "Indigenous Cannabis Wellness"
    video = create_video_response(client, topic)
    return ok(
        {
            "success": True,
            "videoId": video["videoId"],
            "script": video["script"],
            "driveUrl": video["driveUrl"],
            "realGeneration": video["realGeneration"],
            "status": "staged",
            "video": public_video(video),
        }
    )


def handle_video_status():
    body = json_body()
    video_id = body.get("videoId") or body.get("video_id")
    status = (body.get("status") or "").strip().lower()
    if not video_id:
        return ok({"success": False, "error": "videoId is required"}, 400)
    if status == "posted":
        video, resolved = post_video(video_id)
        if not video:
            return ok({"success": False, "error": resolved}, 404)
        return ok({"success": True, "videoId": video_id, "status": resolved, "video": public_video(video)})
    if status not in {"approved", "rejected", "staged"}:
        return ok({"success": False, "error": "Unknown status"}, 400)
    video = update_video_status(video_id, status)
    if not video:
        return ok({"success": False, "error": "Video not found"}, 404)
    return ok({"success": True, "videoId": video_id, "status": status, "video": public_video(video)})


def handle_lead_status():
    body = json_body()
    lead_id = body.get("leadId") or body.get("lead_id")
    status = (body.get("status") or "").strip().lower()
    assigned_to = body.get("assignedTo") or body.get("assigned_to")
    if status not in {"approved", "rejected", "contacted", "staged"}:
        return ok({"success": False, "error": "Unknown lead status"}, 400)
    lead = acquisition.update_lead(lead_id, status, assigned_to)
    if not lead:
        return ok({"success": False, "error": "Lead not found"}, 404)
    return ok({"success": True, "lead": lead})


def handle_task_status():
    body = json_body()
    task_id = body.get("taskId") or body.get("task_id")
    status = (body.get("status") or "").strip().lower()
    assignee_id = body.get("assigneeId") or body.get("assignee_id")
    if status not in {"approved", "rejected", "in_progress", "done", "staged"}:
        return ok({"success": False, "error": "Unknown task status"}, 400)
    task = team_ops.update_task(task_id, status, assignee_id)
    if not task:
        return ok({"success": False, "error": "Task not found"}, 404)
    return ok({"success": True, "task": task})


def handle_action(action: str):
    action = action.strip().lower()
    if action in {"videos", "list-staging"}:
        client = normalize_client(request.args.get("client") or json_body().get("client"))
        return ok({"success": True, "client": client, "videos": list_videos(client=client)})
    if action in {"generate-video", "generate_video"}:
        return handle_generate_video()
    if action in {"video", "video-status"}:
        return handle_video_status()
    if action in {"leads"}:
        if request.method == "POST" and json_body().get("status"):
            return handle_lead_status()
        if request.method == "POST":
            client = normalize_client(json_body().get("client"))
            leads = acquisition.propose_leads(client=client, topic=json_body().get("topic") or "cannabis wellness")
            return ok({"success": True, "leads": leads})
        client = normalize_client(request.args.get("client"))
        return ok({"success": True, "leads": acquisition.list_leads(client=client)})
    if action in {"lead"}:
        return handle_lead_status()
    if action in {"team"}:
        if request.method == "POST":
            body = json_body()
            try:
                member = team_ops.invite_member(body.get("name", ""), body.get("email", ""), body.get("role") or "staff")
            except ValueError as exc:
                return ok({"success": False, "error": str(exc)}, 400)
            return ok({"success": True, "member": member})
        return ok({"success": True, "members": team_ops.list_members(), "roles": team_ops.list_roles()})
    if action in {"tasks"}:
        if request.method == "POST" and not json_body().get("status"):
            return ok({"success": True, "tasks": team_ops.propose_tasks()})
        return ok({"success": True, "tasks": team_ops.list_tasks()})
    if action in {"task"}:
        return handle_task_status()
    if action in {"incident"}:
        body = json_body()
        status = (body.get("status") or "").strip().lower()
        incident_id = body.get("incidentId") or body.get("incident_id")
        if status not in {"approved", "rejected", "resolved", "staged"}:
            return ok({"success": False, "error": "Unknown incident status"}, 400)
        incident = gloris.update_incident(incident_id, status)
        if not incident:
            return ok({"success": False, "error": "Incident not found"}, 404)
        return ok({"success": True, "incident": incident})
    if action in {"incidents", "gloris"}:
        if request.method == "POST":
            body = json_body()
            text = body.get("error") or body.get("text") or ""
            if not str(text).strip():
                return ok({"success": False, "error": "error text is required"}, 400)
            incident = gloris.ingest_incident(
                text,
                source=body.get("source") or "operator",
                site=body.get("site"),
                task_id=body.get("taskId"),
            )
            return ok({"success": True, "incident": incident})
        return ok({"success": True, "incidents": gloris.list_incidents()})
    if action in {"bridge"}:
        return ok({"success": True, "job": gloris.next_bridge_job(), "jobs": gloris.list_bridge_jobs()})
    if action in {"logs"}:
        return ok({"success": True, "logs": snapshot().get("logs", [])[:100]})
    return ok({"success": False, "error": f"Unknown action: {action}"}, 404)


@functions_framework.http
def main(request):  # noqa: ARG001 — Cloud Functions entry
    with app.request_context(request.environ):
        return app.full_dispatch_request()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
