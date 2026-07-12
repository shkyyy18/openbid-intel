import base64
import hashlib
import hmac
import json

from bid_intel.notifier import render_feishu_digest, send_feishu_text


def test_render_feishu_digest():
    rows = [{
        "id": 1, "title": "天线测试", "level": "重点", "score": 90,
        "buyer": "某研究院", "region": "北京", "budget_cny": 3_000_000,
        "stage": "招标公告", "deadline_at": "2026-08-01", "url": "https://example.com",
        "result": {"reasons": ["命中核心需求：天线测量系统"]},
    }]
    text = render_feishu_digest(rows)
    assert "重点候选 1 条" in text
    assert "300.0万元" in text
    assert "公告ID：1" in text


def test_feishu_signature_payload(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self): return b'{"StatusCode":0}'

    def fake_open(request, timeout=0):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    monkeypatch.setattr("time.time", lambda: 1000)
    send_feishu_text("hello", "https://example.invalid/hook", "secret")
    expected = base64.b64encode(hmac.new(b"1000\nsecret", digestmod=hashlib.sha256).digest()).decode("ascii")
    assert captured["payload"]["timestamp"] == "1000"
    assert captured["payload"]["sign"] == expected
