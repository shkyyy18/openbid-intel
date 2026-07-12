from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def render_dashboard(rows: list[dict], generated_at: datetime | None = None, title: str = "OpenBid Intel") -> str:
    generated = generated_at or datetime.now().astimezone()
    total_budget = sum(float(row.get("budget_cny") or 0) for row in rows)
    average_score = round(sum(int(row.get("score") or 0) for row in rows) / len(rows)) if rows else 0
    stages = sorted({str(row.get("stage") or "Unknown") for row in rows})
    regions = sorted({str(row.get("region") or "Unknown") for row in rows})
    lines = sorted({line for row in rows for line in row.get("result", {}).get("business_lines", [])})
    cards = "\n".join(_render_card(row) for row in rows)
    empty_class = "" if rows else " visible"

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{_escape(title)} - Opportunity Dashboard</title>
<style>
:root {{ --bg:#07111f; --panel:#0d1b2d; --text:#eaf2ff; --muted:#91a6c3; --line:#203754; --cyan:#42d9ff; --violet:#9b7bff; --green:#4ee1a0; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; color:var(--text); background:radial-gradient(circle at 15% -10%,#17345b 0,transparent 38%),radial-gradient(circle at 95% 5%,#2a1b55 0,transparent 34%),var(--bg); font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
a {{ color:inherit; }}
.shell {{ width:min(1420px,calc(100% - 32px)); margin:0 auto; padding:36px 0 60px; }}
.hero {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:24px; }}
.eyebrow {{ color:var(--cyan); font-weight:800; letter-spacing:.16em; text-transform:uppercase; font-size:11px; }}
h1 {{ margin:6px 0 4px; font-size:clamp(28px,4vw,48px); line-height:1.05; letter-spacing:-.04em; }}
.subtitle,.generated {{ color:var(--muted); }}
.generated {{ text-align:right; white-space:nowrap; }}
.stats {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:20px 0; }}
.stat {{ padding:18px; border:1px solid var(--line); border-radius:18px; background:linear-gradient(145deg,rgba(18,35,58,.96),rgba(10,24,42,.9)); box-shadow:0 14px 40px rgba(0,0,0,.18); }}
.stat-label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.stat-value {{ margin-top:6px; font-size:25px; font-weight:800; letter-spacing:-.03em; }}
.filters {{ position:sticky; top:10px; z-index:4; display:grid; grid-template-columns:minmax(220px,2fr) repeat(3,minmax(130px,1fr)); gap:10px; padding:12px; margin:18px 0; border:1px solid var(--line); border-radius:18px; background:rgba(7,17,31,.88); backdrop-filter:blur(18px); }}
input,select {{ width:100%; border:1px solid var(--line); border-radius:12px; padding:11px 12px; color:var(--text); background:#0b192a; outline:none; }}
input:focus,select:focus {{ border-color:var(--cyan); box-shadow:0 0 0 3px rgba(66,217,255,.12); }}
.toolbar {{ display:flex; justify-content:space-between; align-items:center; margin:18px 2px 10px; color:var(--muted); }}
.grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
.card {{ border:1px solid var(--line); border-radius:20px; padding:20px; background:linear-gradient(145deg,rgba(18,35,58,.94),rgba(10,23,39,.94)); box-shadow:0 18px 50px rgba(0,0,0,.18); transition:transform .18s ease,border-color .18s ease; }}
.card:hover {{ transform:translateY(-2px); border-color:#355a84; }}
.card[hidden] {{ display:none; }}
.card-top {{ display:flex; justify-content:space-between; gap:18px; align-items:flex-start; }}
.score {{ flex:0 0 66px; height:66px; border-radius:18px; display:grid; place-items:center; background:linear-gradient(145deg,var(--cyan),var(--violet)); color:#04101c; font-size:24px; font-weight:900; box-shadow:0 8px 26px rgba(66,217,255,.2); }}
.card h2 {{ margin:0 0 7px; font-size:18px; line-height:1.3; letter-spacing:-.015em; }}
.meta {{ color:var(--muted); font-size:13px; }}
.tags {{ display:flex; flex-wrap:wrap; gap:7px; margin:15px 0; }}
.tag {{ border:1px solid #2a4668; border-radius:999px; padding:4px 9px; color:#bcd0ea; background:#0a192b; font-size:12px; }}
.tag.level {{ border-color:rgba(78,225,160,.35); color:var(--green); }}
.facts {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; margin:14px 0; }}
.fact {{ padding:10px 12px; border-radius:12px; background:rgba(5,15,27,.55); }}
.fact span {{ display:block; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.06em; }}
.fact strong {{ display:block; margin-top:3px; overflow-wrap:anywhere; }}
.reasons {{ margin:14px 0 0; padding:0 0 0 18px; color:#c8d8ec; }}
.reasons li {{ margin:4px 0; }}
details {{ margin-top:13px; border-top:1px solid var(--line); padding-top:12px; }}
summary {{ cursor:pointer; color:var(--cyan); font-weight:700; }}
.actions {{ margin:10px 0 0; padding-left:20px; color:#c8d8ec; }}
.original {{ display:inline-flex; margin-top:16px; text-decoration:none; font-weight:800; color:var(--cyan); }}
.original:hover {{ text-decoration:underline; }}
.empty {{ display:none; padding:50px; text-align:center; border:1px dashed var(--line); border-radius:20px; color:var(--muted); }}
.empty.visible {{ display:block; }}
.footer {{ margin-top:28px; color:var(--muted); font-size:12px; text-align:center; }}
@media (max-width:900px) {{ .stats {{ grid-template-columns:repeat(2,1fr); }} .filters {{ grid-template-columns:1fr 1fr; }} .grid {{ grid-template-columns:1fr; }} }}
@media (max-width:580px) {{ .shell {{ width:min(100% - 20px,1420px); padding-top:22px; }} .hero {{ display:block; }} .generated {{ text-align:left; margin-top:12px; }} .stats,.filters {{ grid-template-columns:1fr; }} .facts {{ grid-template-columns:1fr; }} }}
@media print {{ body {{ background:white; color:#111; }} .shell {{ width:100%; padding:0; }} .filters,.footer {{ display:none; }} .card,.stat {{ break-inside:avoid; box-shadow:none; color:#111; background:white; }} .meta,.subtitle,.generated,.toolbar,.fact span {{ color:#555; }} }}
</style>
</head>
<body>
<main class="shell">
<section class="hero">
  <div><div class="eyebrow">Local-first procurement intelligence</div><h1>{_escape(title)}</h1><div class="subtitle">Ranked opportunities with explainable scores and direct source links.</div></div>
  <div class="generated">Generated {_escape(generated.isoformat(timespec="minutes"))}</div>
</section>
<section class="stats">
  <div class="stat"><div class="stat-label">Visible opportunities</div><div class="stat-value" id="visibleStat">{len(rows)}</div></div>
  <div class="stat"><div class="stat-label">Average score</div><div class="stat-value">{average_score}</div></div>
  <div class="stat"><div class="stat-label">Pipeline budget</div><div class="stat-value">{_money(total_budget)}</div></div>
  <div class="stat"><div class="stat-label">Top score</div><div class="stat-value">{max((int(row.get("score") or 0) for row in rows), default=0)}</div></div>
</section>
<section class="filters" aria-label="Opportunity filters">
  <input id="search" type="search" placeholder="Search title, buyer, source, reasons..." aria-label="Search opportunities">
  {_select("stage", "All stages", stages)}
  {_select("region", "All regions", regions)}
  {_select("line", "All business lines", lines)}
</section>
<div class="toolbar"><span><strong id="visibleCount">{len(rows)}</strong> opportunities shown</span><span>Sorted by score</span></div>
<section class="grid" id="cards">{cards}</section>
<div class="empty{empty_class}" id="empty">No opportunities match the current filters.</div>
<footer class="footer">Generated locally by OpenBid Intel. Verify all details on the official notice page before acting.</footer>
</main>
<script>
(() => {{
  const cards = [...document.querySelectorAll('.card')];
  const inputs = ['search','stage','region','line'].map(id => document.getElementById(id));
  const apply = () => {{
    const q = document.getElementById('search').value.trim().toLowerCase();
    const stage = document.getElementById('stage').value;
    const region = document.getElementById('region').value;
    const line = document.getElementById('line').value;
    let visible = 0;
    for (const card of cards) {{
      const show = (!q || card.dataset.search.includes(q)) && (!stage || card.dataset.stage === stage) && (!region || card.dataset.region === region) && (!line || card.dataset.lines.split('|').includes(line));
      card.hidden = !show;
      if (show) visible++;
    }}
    document.getElementById('visibleCount').textContent = visible;
    document.getElementById('visibleStat').textContent = visible;
    document.getElementById('empty').classList.toggle('visible', visible === 0);
  }};
  inputs.forEach(input => input.addEventListener('input', apply));
}})();
</script>
</body>
</html>
'''


def write_dashboard(path: str | Path, rows: list[dict], title: str = "OpenBid Intel") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(rows, title=title), encoding="utf-8")
    return target


def _render_card(row: dict) -> str:
    result = row.get("result") or {}
    business_lines = [str(item) for item in result.get("business_lines", [])]
    reasons = [str(item) for item in result.get("reasons", [])][:4]
    actions = [str(item) for item in result.get("recommended_actions", [])]
    search = " ".join([
        str(row.get("title") or ""), str(row.get("buyer") or ""), str(row.get("source") or ""),
        str(row.get("region") or ""), str(row.get("stage") or ""), " ".join(business_lines), " ".join(reasons),
    ]).lower()
    stage = str(row.get("stage") or "Unknown")
    region = str(row.get("region") or "Unknown")
    tags = [f'<span class="tag level">{_escape(row.get("level") or "Scored")}</span>']
    tags.extend(f'<span class="tag">{_escape(item)}</span>' for item in business_lines)
    reason_html = "".join(f"<li>{_escape(item)}</li>" for item in reasons) or "<li>No scoring reasons recorded.</li>"
    action_html = "".join(f"<li>{_escape(item)}</li>" for item in actions) or "<li>Review the official notice and assign an owner.</li>"
    url = _safe_url(row.get("url"))
    title = _escape(row.get("title") or "Untitled opportunity")
    buyer = _escape(row.get("buyer") or "Unknown buyer")
    source = _escape(row.get("source") or "Unknown source")
    return f'''<article class="card" data-search="{_escape(search)}" data-stage="{_escape(stage)}" data-region="{_escape(region)}" data-lines="{_escape('|'.join(business_lines))}">
  <div class="card-top"><div><h2>{title}</h2><div class="meta">{buyer} - {source}</div></div><div class="score" title="Opportunity score">{int(row.get("score") or 0)}</div></div>
  <div class="tags">{''.join(tags)}</div>
  <div class="facts">
    <div class="fact"><span>Budget</span><strong>{_money(row.get("budget_cny"))}</strong></div>
    <div class="fact"><span>Deadline</span><strong>{_escape(row.get("deadline_at") or "Not specified")}</strong></div>
    <div class="fact"><span>Stage</span><strong>{_escape(stage)}</strong></div>
    <div class="fact"><span>Region</span><strong>{_escape(region)}</strong></div>
  </div>
  <ul class="reasons">{reason_html}</ul>
  <details><summary>Recommended actions</summary><ol class="actions">{action_html}</ol></details>
  <a class="original" href="{_escape(url)}" target="_blank" rel="noopener noreferrer">Open official notice -></a>
</article>'''


def _select(element_id: str, label: str, values: list[str]) -> str:
    options = "".join(f'<option value="{_escape(value)}">{_escape(value)}</option>' for value in values)
    return f'<select id="{element_id}" aria-label="{_escape(label)}"><option value="">{_escape(label)}</option>{options}</select>'


def _safe_url(value: object) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else "#"


def _money(value: object) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        return "Not specified"
    if amount <= 0:
        return "Not specified"
    if amount >= 100_000_000:
        return f"CNY {amount / 1_000_000_000:,.2f}B"
    if amount >= 1_000_000:
        return f"CNY {amount / 1_000_000:,.2f}M"
    if amount >= 1_000:
        return f"CNY {amount / 1_000:,.1f}K"
    return f"CNY {amount:,.0f}"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
