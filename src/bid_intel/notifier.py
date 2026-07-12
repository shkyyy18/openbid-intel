from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    source = Path(path)
    if not source.exists():
        return
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def send_feishu_text(text: str, webhook_url: str | None = None, secret: str | None = None) -> dict:
    load_dotenv()
    url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL", "")
    signing_secret = secret if secret is not None else os.getenv("FEISHU_WEBHOOK_SECRET", "")
    if not url:
        raise ValueError("未配置 FEISHU_WEBHOOK_URL")
    payload: dict[str, object] = {"msg_type": "text", "content": {"text": text}}
    if signing_secret:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{signing_secret}".encode("utf-8")
        signature = base64.b64encode(hmac.new(string_to_sign, digestmod=hashlib.sha256).digest()).decode("ascii")
        payload.update({"timestamp": timestamp, "sign": signature})
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"飞书 Webhook HTTP {exc.code}") from exc
    if result.get("StatusCode", result.get("code", 0)) not in (0, None):
        raise RuntimeError(f"飞书推送失败: {result}")
    return result


def render_feishu_digest(rows: list[dict], max_chars: int = 18000) -> str:
    lines = [f"OpenBid Intel 商机日报｜重点候选 {len(rows)} 条"]
    for index, row in enumerate(rows, 1):
        result = row["result"]
        reasons = result.get("reasons", [])
        reason = reasons[0] if reasons else "待人工判断"
        budget = "待确认" if row.get("budget_cny") is None else f"{row['budget_cny'] / 10000:,.1f}万元"
        lines.extend([
            "",
            f"{index}. [{row['level']} {row['score']}] {row['title']}",
            f"采购人：{row.get('buyer') or '待确认'}｜地区：{row.get('region') or '待确认'}｜预算：{budget}",
            f"阶段：{row.get('stage') or '未知'}｜截止：{row.get('deadline_at') or '待确认'}",
            f"依据：{reason}",
            f"公告ID：{row['id']}｜{row.get('url') or ''}",
        ])
        if sum(len(line) + 1 for line in lines) > max_chars:
            lines.append("\n其余候选请查看本地 Markdown 日报。")
            break
    return "\n".join(lines)
