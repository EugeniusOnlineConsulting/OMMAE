from main import app


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_health_and_root():
    hq = client()
    health = hq.get("/health").get_json()
    assert health["status"] == "healthy"
    root = hq.get("/").get_json()
    assert root["status"] == "operational"
    assert root["counts"]["members"] >= 3


def test_admin_hq_is_served():
    page = client().get("/admin")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Acquisition" in html
    assert "Propose Tasks" in html
    assert "Invite member" in html


def test_content_hitl_generate_approve_reject_and_queue_post():
    hq = client()
    generated = hq.post(
        "/generate-video",
        json={"client": "mohawkmedibles", "topic": "Indigenous wellness"},
    ).get_json()
    assert generated["success"] is True
    assert generated["status"] == "staged"
    video_id = generated["videoId"]
    assert "Look" in generated["script"] or "wellness" in generated["script"].lower()

    listed = hq.get("/videos?client=mohawk_medibles").get_json()
    assert any(item["id"] == video_id for item in listed["videos"])
    staged = hq.get("/list-staging?client=mohawkmedibles").get_json()
    assert any(item["videoId"] == video_id for item in staged["videos"])

    approved = hq.post("/", json={"action": "video", "video_id": video_id, "status": "approved"}).get_json()
    assert approved["success"] is True
    assert approved["status"] == "approved"

    posted = hq.post("/", json={"action": "video", "video_id": video_id, "status": "posted"}).get_json()
    assert posted["success"] is True
    assert posted["status"] == "queued"

    other = hq.post("/generate-video", json={"client": "mohawk_medibles", "topic": "Community"}).get_json()
    rejected = hq.post("/reject", json={"videoId": other["videoId"]}).get_json()
    assert rejected["status"] == "rejected"


def test_action_query_lists_videos():
    hq = client()
    hq.post("/", json={"action": "generate-video", "topic": "Delivery"})
    data = hq.get("/?action=videos&client=mohawk_medibles").get_json()
    assert data["success"] is True
    assert len(data["videos"]) == 1


def test_acquisition_hitl_draft_approve_contact_reject():
    hq = client()
    drafted = hq.post("/leads", json={"client": "mohawk_medibles"}).get_json()
    assert drafted["success"] is True
    assert len(drafted["leads"]) == 4
    assert all(lead["status"] == "staged" for lead in drafted["leads"])
    assert all(lead["outreach"] for lead in drafted["leads"])

    lead_id = drafted["leads"][0]["id"]
    approved = hq.post("/", json={"action": "lead", "leadId": lead_id, "status": "approved"}).get_json()
    assert approved["lead"]["status"] == "approved"
    contacted = hq.post("/", json={"action": "lead", "leadId": lead_id, "status": "contacted"}).get_json()
    assert contacted["lead"]["status"] == "contacted"

    other_id = drafted["leads"][1]["id"]
    rejected = hq.post("/", json={"action": "lead", "leadId": other_id, "status": "rejected"}).get_json()
    assert rejected["lead"]["status"] == "rejected"

    remaining = hq.get("/leads?client=mohawk_medibles").get_json()["leads"]
    statuses = {item["id"]: item["status"] for item in remaining}
    assert statuses[lead_id] == "contacted"
    assert statuses[other_id] == "rejected"


def test_team_invite_and_agent_task_hitl():
    hq = client()
    missing = hq.post("/team", json={"name": "No Email"})
    assert missing.status_code == 400

    invited = hq.post(
        "/team",
        json={"name": "Jordan Staff", "email": "jordan@mohawkmedibles.ca", "role": "staff"},
    ).get_json()
    assert invited["success"] is True
    assert invited["member"]["email"] == "jordan@mohawkmedibles.ca"

    roster = hq.get("/team").get_json()
    assert any(member["email"] == "jordan@mohawkmedibles.ca" for member in roster["members"])
    assert any(role["id"] == "manager" for role in roster["roles"])

    hq.post("/leads", json={"client": "mohawk_medibles"})
    proposed = hq.post("/tasks", json={}).get_json()
    assert proposed["success"] is True
    assert len(proposed["tasks"]) >= 2
    assert all(task["status"] == "staged" for task in proposed["tasks"])

    task_id = proposed["tasks"][0]["id"]
    approved = hq.post("/", json={"action": "task", "taskId": task_id, "status": "approved"}).get_json()
    assert approved["task"]["status"] == "approved"
    done = hq.post("/", json={"action": "task", "taskId": task_id, "status": "done"}).get_json()
    assert done["task"]["status"] == "done"


def test_logs_record_hitl_activity():
    hq = client()
    hq.post("/generate-video", json={"topic": "Wellness"})
    hq.post("/leads", json={})
    logs = hq.get("/logs").get_json()["logs"]
    kinds = {entry["type"] for entry in logs}
    assert "content" in kinds
    assert "acquisition" in kinds
