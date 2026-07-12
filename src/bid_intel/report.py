from __future__ import annotations

from datetime import datetime
from pathlib import Path


def render_digest(rows: list[dict], generated_at: datetime | None = None) -> str:
    generated = generated_at or datetime.now().astimezone()
    lines = [
        "# OpenBid Intel 商机简报",
        "",
        f"生成时间：{generated.isoformat(timespec='minutes')}",
        f"候选商机：{len(rows)} 条",
        "",
    ]
    if not rows:
        lines.append("当前没有达到筛选阈值的公告。")
        return "\n".join(lines) + "\n"

    for index, row in enumerate(rows, 1):
        result = row["result"]
        budget = _money(row.get("budget_cny"))
        lines.extend([
            f"## {index}. [{row['level']} {row['score']}/100] {row['title']}",
            "",
            f"- 公告ID：`{row['id']}`",
            f"- 采购单位：{row.get('buyer') or '待确认'}",
            f"- 地区：{row.get('region') or '待确认'}",
            f"- 阶段：{row.get('stage') or '未知'}",
            f"- 预算：{budget}",
            f"- 发布时间：{row.get('published_at') or '待确认'}",
            f"- 截止时间：{row.get('deadline_at') or '待确认'}",
            f"- 匹配业务：{'、'.join(result.get('business_lines', [])) or '待人工判断'}",
            f"- 最新反馈：{row.get('latest_verdict') or '未反馈'}",
            "",
            "**推荐依据**",
        ])
        lines.extend([f"- {item}" for item in result.get("reasons", [])])
        lines.append("")
        lines.append("**风险与待确认项**")
        lines.extend([f"- {item}" for item in result.get("risks", [])] or ["- 暂无系统识别风险"])
        lines.append("")
        lines.append("**建议行动**")
        lines.extend([f"{i}. {item}" for i, item in enumerate(result.get("recommended_actions", []), 1)])
        lines.extend(["", f"原文：{row.get('url') or '无链接'}", ""])
    return "\n".join(lines)


def write_digest(path: str | Path, rows: list[dict]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_digest(rows), encoding="utf-8")
    return target


def _money(value: float | None) -> str:
    if value is None:
        return "待确认"
    if value >= 10000:
        return f"{value / 10000:,.1f} 万元"
    return f"{value:,.0f} 元"
