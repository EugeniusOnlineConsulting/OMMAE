from gloris import (
    buggy_create_product_params,
    create_product_params,
    ingest_incident,
    redact,
)
from main import app


PRODUCT_ERROR = (
    "Could not create product: Failed query: insert into 'products' "
    "(id, name, slug, categoryId, price, cost, inStock, stockQuantity, imageUrl, image_alt, status) "
    "values (default, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
    "params: BC FF, bc-ff, 1, 39.99, 32.19, true, 50, draft"
)

PREMIUM_ERROR = (
    "mhq-20260825T163053Z-5dbae2e5 stopped safely: RuntimeError: Codex premium lane failed "
    "(exit 1): Incorrect API key provided: sk-proj-FAKESECRETKEYVALUEHERE. "
    "auth error: 401, auth error code: invalid_api_key. "
    "No local/API fallback was used, and nothing was pushed, merged, deployed, deleted, "
    "or changed in customer data."
)


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_image_params_are_always_bound():
    payload = {
        "name": "BC FF",
        "slug": "bc-ff",
        "categoryId": 1,
        "price": 39.99,
        "cost": 32.19,
        "inStock": True,
        "stockQuantity": 50,
        "status": "draft",
    }
    broken = buggy_create_product_params(payload)
    fixed = create_product_params(payload)
    assert len(broken) == 8
    assert len(fixed) == 10
    assert fixed[7] is None
    assert fixed[8] == "BC FF"
    assert fixed[9] == "draft"


def test_gloris_diagnoses_product_insert_without_openai():
    hq = client()
    result = hq.post("/incidents", json={"error": PRODUCT_ERROR, "site": "spiritfiretobacco.com"}).get_json()
    assert result["success"] is True
    incident = result["incident"]
    assert incident["status"] == "staged"
    assert incident["diagnosis"]["playbook"] == "spiritfire_product_insert"
    assert incident["diagnosis"]["placeholders"] == 10
    assert incident["diagnosis"]["paramCount"] == 8
    assert incident["premium"]["fallback"] == "local"
    assert "imageUrl" in incident["diagnosis"]["fix"]
    bridge = result["bridge"]
    assert bridge["kind"] == "cursor_bridge"
    assert bridge["hitl"] == "approve_before_deploy"


def test_gloris_falls_back_when_premium_lane_401s(monkeypatch):
    monkeypatch.setenv("GLORIS_FORCE_PREMIUM_FAIL", "1")
    incident = ingest_incident(PREMIUM_ERROR, source="gloris", task_id="mhq-20260825T163053Z-5dbae2e5")
    assert incident["premium"]["used"] is True
    assert incident["premium"]["ok"] is False
    assert incident["premium"]["fallback"] == "local"
    assert incident["diagnosis"]["playbook"] == "gloris_premium_fallback"
    assert "sk-proj-FAKESECRETKEYVALUEHERE" not in incident["error"]
    assert "sk-***REDACTED***" in incident["error"]


def test_secrets_are_redacted():
    assert "abcdefgh" not in redact("key sk-proj-abcdefghijklmnop leaked")
    assert "sk-***REDACTED***" in redact("sk-proj-abcdefghijklmnop")


def test_cursor_bridge_hitl_approve():
    hq = client()
    created = hq.post("/incidents", json={"error": PRODUCT_ERROR}).get_json()["incident"]
    listed = hq.get("/incidents").get_json()["incidents"]
    assert any(item["id"] == created["id"] for item in listed)
    approved = hq.post("/", json={"action": "incident", "incidentId": created["id"], "status": "approved"}).get_json()
    assert approved["incident"]["status"] == "approved"
    job = hq.get("/bridge/next").get_json()["job"]
    assert job["incidentId"] == created["id"]
    assert job["status"] == "approved"
    assert job["payload"]["operator"] == "gloris"


def test_propose_tasks_includes_gloris_incidents():
    hq = client()
    hq.post("/incidents", json={"error": PRODUCT_ERROR})
    tasks = hq.post("/tasks", json={}).get_json()["tasks"]
    titles = [task["title"] for task in tasks]
    assert any("Gloris incident" in title for title in titles)
