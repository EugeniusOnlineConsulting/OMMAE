from product_copy import as_plain_text, html_to_plain_text, looks_like_html
from main import app


TOXIC_CHERRY_BOMB_HTML = """
<h2 class="PDq2pG_selectionAnchorContainer">🍒 🍇 Toxic Cherry Bomb – $40/OZ or $100/3OZ 💣 🍒</h2>
<p><strong>Balanced Hybrid – 50% Sativa / 50% Indica</strong><br />
<strong>THC: 22% – 28%</strong></p>
<hr />
<p class="PDq2pG_selectionAnchorContainer">A burst of <strong>sweet ripe cherries</strong> with grape on the finish.</p>
<p>Expect <strong>euphoria</strong> for social sessions, creative projects, or relaxing after a long day.</p>
"""


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_html_product_copy_becomes_plain_text():
    plain = html_to_plain_text(TOXIC_CHERRY_BOMB_HTML)
    assert "<h2" not in plain
    assert "PDq2pG_selectionAnchorContainer" not in plain
    assert "<strong>" not in plain
    assert "Toxic Cherry Bomb" in plain
    assert "Balanced Hybrid" in plain
    assert "sweet ripe cherries" in plain
    assert "euphoria" in plain
    assert looks_like_html(TOXIC_CHERRY_BOMB_HTML) is True
    assert looks_like_html(plain) is False
    assert as_plain_text("Already readable copy.") == "Already readable copy."


def test_products_are_saved_and_shown_as_plain_text():
    hq = client()
    created = hq.post(
        "/products",
        json={
            "client": "mohawkmedibles",
            "name": "Toxic Cherry Bomb",
            "shortDescription": "<p>Shoppers see this first.</p>",
            "longDescription": TOXIC_CHERRY_BOMB_HTML,
        },
    )
    payload = created.get_json()
    assert created.status_code == 200
    assert payload["success"] is True
    product = payload["product"]
    assert product["name"] == "Toxic Cherry Bomb"
    assert "<" not in product["shortDescription"]
    assert product["shortDescription"] == "Shoppers see this first."
    assert "<h2" not in product["longDescription"]
    assert "Toxic Cherry Bomb" in product["longDescription"]
    assert "PDq2pG_selectionAnchorContainer" not in product["longDescription"]

    listed = hq.get("/products?client=mohawk_medibles").get_json()
    assert listed["success"] is True
    assert len(listed["products"]) == 1
    assert listed["products"][0]["longDescription"] == product["longDescription"]

    via_action = hq.post(
        "/",
        json={
            "action": "products",
            "id": product["id"],
            "name": "Toxic Cherry Bomb",
            "longDescription": "<div>Updated with <em>plain</em> intent.</div>",
            "client": "mohawk_medibles",
        },
    ).get_json()
    assert via_action["success"] is True
    assert via_action["product"]["longDescription"] == "Updated with plain intent."

    missing = hq.post("/products", json={"client": "mohawk_medibles"})
    assert missing.status_code == 400

    deleted = hq.post("/products", json={"id": product["id"], "delete": True}).get_json()
    assert deleted["success"] is True
    remaining = hq.get("/products?client=mohawk_medibles").get_json()["products"]
    assert remaining == []


def test_admin_product_form_is_plain_text():
    page = client().get("/admin")
    html = page.get_data(as_text=True)
    assert "Products" in html
    assert "Long Description / product details." in html
    assert "Short description is what shoppers see first." in html
    assert "htmlToPlainText" in html
    assert "stripPastedHtml" in html
