from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "spm", "from"}


def normalize_text(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.lower())


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in _TRACKING_KEYS]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(sorted(query)), ""))


def notice_fingerprint(title: str, buyer: str, project_id: str, url: str) -> str:
    if project_id:
        material = f"project:{normalize_text(project_id)}"
    else:
        normalized_url = canonical_url(url)
        if normalized_url:
            material = f"url:{normalized_url}"
        else:
            material = f"text:{normalize_text(title)}|{normalize_text(buyer)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
