"""
Convert pasted product copy into plain text.

Mohawk Medibles descriptions were imported from Wix/WooCommerce HTML.
HQ stores and edits them as shopper-facing prose, never as tags.
"""
from __future__ import annotations

import html as html_lib
import re

_TAG = re.compile(r"<[a-zA-Z][^>]*>", re.DOTALL)
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HR = re.compile(r"<hr\s*/?>", re.IGNORECASE)
_LI = re.compile(r"<li\b[^>]*>", re.IGNORECASE)
_BLOCK_CLOSE = re.compile(
    r"</(?:p|div|h[1-6]|li|ul|ol|tr|blockquote|section|article|header|footer)>",
    re.IGNORECASE,
)
_ALL_TAGS = re.compile(r"<[^>]+>")
_SPACES_BEFORE_NEWLINE = re.compile(r"[ \t]+\n")
_MANY_BLANK = re.compile(r"\n{3,}")
_MANY_SPACES = re.compile(r"[ \t]{2,}")


def looks_like_html(value: str | None) -> bool:
    return bool(_TAG.search(value or ""))


def html_to_plain_text(value: str | None) -> str:
    """Turn HTML (or mixed paste) into readable plain text."""
    text = str(value or "")
    if not text.strip():
        return ""
    if not looks_like_html(text):
        return text.strip()

    text = _BR.sub("\n", text)
    text = _HR.sub("\n\n", text)
    text = _LI.sub("- ", text)
    text = _BLOCK_CLOSE.sub("\n\n", text)
    text = _ALL_TAGS.sub("", text)
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = _SPACES_BEFORE_NEWLINE.sub("\n", text)
    text = _MANY_SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = _MANY_BLANK.sub("\n\n", text)
    return text.strip()


def as_plain_text(value: str | None) -> str:
    """Normalize any incoming description to plain text for storage and editing."""
    return html_to_plain_text(value)
