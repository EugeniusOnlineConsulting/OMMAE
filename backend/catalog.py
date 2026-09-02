"""
Mohawk Medibles product copy in HQ.

Staff type short and long descriptions as plain text. HTML pasted from
Wix or WooCommerce is stripped on save so the admin never stores tags.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from product_copy import as_plain_text
from store import add_log, mutate, snapshot, utcnow

_SLUG_SAFE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    slug = _SLUG_SAFE.sub("-", (name or "").strip().lower()).strip("-")
    return slug or "product"


def list_products(client: str | None = None) -> list[dict[str, Any]]:
    products = list(snapshot().get("products", {}).values())
    if client:
        products = [item for item in products if item.get("client") == client]
    products.sort(key=lambda item: item.get("updatedAt") or item.get("createdAt") or "", reverse=True)
    return [public_product(item) for item in products]


def get_product(product_id: str) -> dict[str, Any] | None:
    product = snapshot().get("products", {}).get(product_id)
    return public_product(product) if product else None


def public_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": product["id"],
        "client": product.get("client", "mohawk_medibles"),
        "name": product.get("name", ""),
        "slug": product.get("slug", ""),
        "shortDescription": as_plain_text(product.get("shortDescription")),
        "longDescription": as_plain_text(product.get("longDescription")),
        "status": product.get("status", "draft"),
        "createdAt": product.get("createdAt"),
        "updatedAt": product.get("updatedAt"),
    }


def upsert_product(
    *,
    name: str,
    client: str = "mohawk_medibles",
    short_description: str = "",
    long_description: str = "",
    product_id: str | None = None,
    slug: str | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")

    short_text = as_plain_text(short_description)
    long_text = as_plain_text(long_description)
    status = (status or "draft").strip().lower()
    if status not in {"draft", "active"}:
        status = "draft"

    existing = snapshot().get("products", {}).get(product_id) if product_id else None
    record_id = product_id if existing else f"product-{uuid.uuid4().hex[:8]}"
    created_at = existing.get("createdAt") if existing else utcnow()
    record = {
        "id": record_id,
        "client": client,
        "name": name,
        "slug": (slug or "").strip() or _slugify(name),
        "shortDescription": short_text,
        "longDescription": long_text,
        "status": status,
        "createdAt": created_at,
        "updatedAt": utcnow(),
    }

    def _write(data: dict[str, Any]) -> None:
        data.setdefault("products", {})[record_id] = record

    mutate(_write)
    verb = "Updated" if existing else "Saved"
    add_log("catalog", f"{verb} product copy for '{name}' as plain text.", actor="human")
    return public_product(record)


def delete_product(product_id: str) -> bool:
    removed = {"ok": False, "name": ""}

    def _write(data: dict[str, Any]) -> None:
        product = data.get("products", {}).pop(product_id, None)
        if product:
            removed["ok"] = True
            removed["name"] = product.get("name") or product_id

    mutate(_write)
    if removed["ok"]:
        add_log("catalog", f"Removed product '{removed['name']}'.", actor="human")
    return removed["ok"]
