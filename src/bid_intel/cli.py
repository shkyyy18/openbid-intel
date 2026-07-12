from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .collectors import collect_sources
from .config_validation import validate_config
from .competitive import (
    analyze_awards, build_relationships, load_profile, render_competitor_report, resolve_buyer_aliases,
    summarize_suppliers, write_competitor_report,
)
from .dashboard import write_dashboard
from .doctor import run_doctor
from .exports import write_crm_csv
from .importers import load_notices
from .matcher import Matcher
from .notifier import load_dotenv, render_feishu_digest, send_feishu_text
from .profiles import list_profiles, write_profile
from .report import render_digest, write_digest
from .release import run_release_check
from .storage import Store

DEFAULT_DB = Path("data/bids.db")
DEFAULT_PROFILE = Path("config/profile.json")
DEFAULT_SOURCES = Path("config/sources.json")
VERDICTS = ("相关", "不相关", "已跟进", "放弃", "已投标", "中标", "失标")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenBid Intel - local-first procurement intelligence")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite 数据库路径")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE), help="企业匹配画像 JSON")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES), help="数据来源配置 JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    import_cmd = sub.add_parser("import", help="导入 JSON/JSONL/CSV 公告")
    import_cmd.add_argument("path")
    import_cmd.add_argument("--mapping", help="JSON file mapping canonical fields to source column names")
    import_cmd.add_argument("--score", action="store_true", help="导入后立即评分")

    collect = sub.add_parser("collect", help="从配置的公开来源采集公告")
    collect.add_argument("--no-details", action="store_true", help="只采集列表，不打开候选详情")
    collect.add_argument("--max-details", type=int, help="本次最多读取的详情页数量")
    collect.add_argument("--score", action="store_true", help="采集后对新公告评分")
    collect.add_argument("--max-pages", type=int, help="\u6bcf\u4e2a\u6765\u6e90\u6700\u591a\u56de\u6eaf\u9875\u6570")
    collect.add_argument("--history-days", type=int, help="\u53ea\u4fdd\u7559\u6700\u8fd1\u591a\u5c11\u5929\u516c\u544a")

    score_cmd = sub.add_parser("score", help="对公告评分")
    score_cmd.add_argument("--all", action="store_true", help="重新评分全部公告")

    digest = sub.add_parser("digest", help="生成商机日报")
    digest.add_argument("--min-score", type=int, default=30)
    digest.add_argument("--limit", type=int, default=20)
    digest.add_argument("--output", help="写入 Markdown 文件；不指定则输出到终端")

    dashboard = sub.add_parser("dashboard", help="generate a self-contained HTML opportunity dashboard")
    dashboard.add_argument("--min-score", type=int, default=30)
    dashboard.add_argument("--limit", type=int, default=200)
    dashboard.add_argument("--output", default="reports/dashboard.html")
    dashboard.add_argument("--title", default="OpenBid Intel")

    export = sub.add_parser("export", help="export qualified opportunities to an Excel-friendly CSV")
    export.add_argument("--min-score", type=int, default=50)
    export.add_argument("--limit", type=int, default=1000)
    export.add_argument("--output", default="reports/opportunities.csv")

    push = sub.add_parser("push", help="将商机日报推送到飞书群机器人")
    push.add_argument("--min-score", type=int, default=50)
    push.add_argument("--limit", type=int, default=15)

    daily = sub.add_parser("daily", help="采集、评分、生成日报并推送")
    daily.add_argument("--min-score", type=int, default=50)
    daily.add_argument("--limit", type=int, default=15)
    daily.add_argument("--output-dir", default="reports")
    daily.add_argument("--max-details", type=int)
    daily.add_argument("--no-details", action="store_true")
    daily.add_argument("--no-push", action="store_true")
    daily.add_argument("--max-pages", type=int, help="\u6bcf\u4e2a\u6765\u6e90\u6700\u591a\u56de\u6eaf\u9875\u6570")
    daily.add_argument("--history-days", type=int, help="\u53ea\u4fdd\u7559\u6700\u8fd1\u591a\u5c11\u5929\u516c\u544a")

    feedback = sub.add_parser("feedback", help="记录销售反馈")
    feedback.add_argument("notice_id", type=int)
    feedback.add_argument("verdict", choices=VERDICTS)
    feedback.add_argument("--note", default="")

    competitors = sub.add_parser("competitors", help="\u751f\u6210\u5386\u53f2\u4e2d\u6807\u4f9b\u5e94\u5546\u4e0e\u7ade\u4e89\u60c5\u62a5\u62a5\u544a")
    competitors.add_argument("--buyer", default="", help="\u6309\u91c7\u8d2d\u5355\u4f4d\u5173\u952e\u8bcd\u7b5b\u9009")
    competitors.add_argument("--limit", type=int, default=30, help="\u4f9b\u5e94\u5546\u6392\u884c\u6570\u91cf")
    competitors.add_argument("--history-limit", type=int, default=100, help="\u4e2d\u6807\u660e\u7ec6\u6570\u91cf")
    competitors.add_argument("--output", help="\u5199\u5165 Markdown \u6587\u4ef6")
    competitors.add_argument("--product-line", default="", help="\u6309\u4ea7\u54c1\u7ebf ID \u6216\u540d\u79f0\u7b5b\u9009")
    competitors.add_argument("--include-unrelated", action="store_true", help="include award notices that do not match the active profile")

    intelligence = sub.add_parser("intelligence", help="\u5386\u53f2\u91c7\u96c6\u3001\u8bc4\u5206\u5e76\u751f\u6210\u5b8c\u6574\u9500\u552e\u4e0e\u7ade\u4e89\u60c5\u62a5\u5305")
    intelligence.add_argument("--max-pages", type=int, default=10)
    intelligence.add_argument("--history-days", type=int, default=180)
    intelligence.add_argument("--max-details", type=int, default=100)
    intelligence.add_argument("--min-score", type=int, default=50)
    intelligence.add_argument("--limit", type=int, default=30)
    intelligence.add_argument("--history-limit", type=int, default=10000)
    intelligence.add_argument("--output-dir", default="reports/intelligence")
    intelligence.add_argument("--no-details", action="store_true")
    intelligence.add_argument("--no-push", action="store_true")

    sub.add_parser("quality", help="\u663e\u793a\u91c7\u96c6\u548c\u5b57\u6bb5\u5b8c\u6574\u5ea6\u7edf\u8ba1")
    sub.add_parser("stats", help="显示数据库统计")
    runs = sub.add_parser("runs", help="显示最近采集运行记录")
    runs.add_argument("--limit", type=int, default=20)
    sub.add_parser("doctor", help="检查配置、数据库和推送环境")
    release_check = sub.add_parser("release-check", help="run offline repository and configuration checks")
    release_check.add_argument("--root", default=".", help="repository root")

    validate = sub.add_parser("validate-config", help="validate profile and source JSON against bundled schemas")
    validate.add_argument("--only", choices=("profile", "sources"), help="validate only one configuration file")

    sub.add_parser("profiles", help="list built-in industry profile packs")
    init_profile = sub.add_parser("init-profile", help="create an editable profile from a built-in pack")
    init_profile.add_argument("preset", help="profile pack ID; run profiles to list choices")
    init_profile.add_argument("--output", default="config/profile.local.json")
    init_profile.add_argument("--force", action="store_true", help="replace an existing output file")

    demo = sub.add_parser("demo", help="导入样例、评分并生成报告")
    demo.add_argument("--sample", default="samples/demo_notices.json")
    demo.add_argument("--output", default="reports/demo_digest.md")
    demo.add_argument("--dashboard-output", default="reports/demo_dashboard.html")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "release-check":
        ok, checks = run_release_check(args.root, args.db, args.profile, args.sources)
        for check in checks:
            print(f"[{check['status'].upper()}] {check['check']}: {check['detail']}")
        return 0 if ok else 1

    if args.command == "validate-config":
        targets = [("profile", args.profile), ("sources", args.sources)]
        if args.only:
            targets = [item for item in targets if item[0] == args.only]
        failed = False
        for kind, path in targets:
            errors = validate_config(path, kind)
            if errors:
                failed = True
                print(f"[ERROR] {kind}: {path}")
                for error in errors:
                    print(f"  - {error}")
            else:
                print(f"[OK] {kind}: {path}")
        return 1 if failed else 0

    if args.command == "profiles":
        for row in list_profiles():
            print(f"{row['id']:<24} {row['title']} - {row['description']}")
        return 0

    if args.command == "init-profile":
        try:
            target = write_profile(args.preset, args.output, force=args.force)
        except (FileExistsError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Created {target}. Use it with --profile {target}")
        return 0

    store = Store(args.db)

    if args.command == "import":
        imported, updated = _import(store, args.path, args.mapping)
        print(f"导入完成：新增 {imported}，更新 {updated}")
        if args.score:
            print(f"评分完成：{_score(store, args.profile, all_notices=False)} 条")
        return 0

    if args.command == "collect":
        summary = _collect(store, args.sources, not args.no_details, args.max_details, args.max_pages, args.history_days)
        _print_collection(summary)
        if args.score:
            print(f"评分完成：{_score(store, args.profile, all_notices=False)} 条")
        return 1 if summary["failed_sources"] else 0

    if args.command == "score":
        count = _score(store, args.profile, all_notices=args.all)
        print(f"评分完成：{count} 条")
        return 0

    if args.command == "digest":
        rows = store.ranked(limit=args.limit, min_score=args.min_score)
        if args.output:
            target = write_digest(args.output, rows)
            print(f"已生成：{target}")
        else:
            print(render_digest(rows), end="")
        return 0

    if args.command == "dashboard":
        rows = store.ranked(limit=args.limit, min_score=args.min_score)
        target = write_dashboard(args.output, rows, title=args.title)
        print(f"Dashboard generated: {target} ({len(rows)} opportunities)")
        return 0

    if args.command == "export":
        rows = store.ranked(limit=args.limit, min_score=args.min_score)
        target = write_crm_csv(args.output, rows)
        print(f"Exported {len(rows)} opportunities: {target}")
        return 0

    if args.command == "push":
        rows = store.ranked(limit=args.limit, min_score=args.min_score)
        send_feishu_text(render_feishu_digest(rows))
        print(f"飞书推送成功：{len(rows)} 条")
        return 0

    if args.command == "daily":
        summary = _collect(store, args.sources, not args.no_details, args.max_details, args.max_pages, args.history_days)
        scored = _score(store, args.profile, all_notices=False)
        rows = store.ranked(limit=args.limit, min_score=args.min_score)
        stamp = datetime.now().astimezone().strftime("%Y%m%d")
        target = write_digest(Path(args.output_dir) / f"digest_{stamp}.md", rows)
        pushed = False
        load_dotenv()
        if not args.no_push and os.getenv("FEISHU_WEBHOOK_URL"):
            send_feishu_text(render_feishu_digest(rows))
            pushed = True
        _print_collection(summary)
        print(f"评分 {scored} 条；日报 {target}；飞书推送：{'成功' if pushed else '跳过'}")
        return 1 if summary["failed_sources"] else 0

    if args.command == "feedback":
        store.add_feedback(args.notice_id, args.verdict, args.note)
        print(f"已记录公告 {args.notice_id}：{args.verdict}")
        return 0

    if args.command == "competitors":
        profile = load_profile(args.profile)
        buyer_label, buyer_aliases = resolve_buyer_aliases(profile, args.buyer)
        raw_history = store.award_history(limit=args.history_limit, buyer_queries=buyer_aliases)
        history = analyze_awards(raw_history, profile, relevant_only=not args.include_unrelated, product_line=args.product_line)
        summary = summarize_suppliers(history, limit=args.limit)
        relationships = build_relationships(history)
        report_kwargs = {"relationships": relationships, "relevant_only": not args.include_unrelated, "product_line": args.product_line}
        if args.output:
            target = write_competitor_report(args.output, summary, history, buyer_label, **report_kwargs)
            print(f"\u5df2\u751f\u6210\uff1a{target}\uff1b\u4f9b\u5e94\u5546 {len(summary)} \u5bb6\uff1b\u76f8\u5173\u516c\u544a {len(history)} \u6761")
        else:
            print(render_competitor_report(summary, history, buyer_label, **report_kwargs), end="")
        return 0

    if args.command == "intelligence":
        return _run_intelligence(store, args)

    if args.command == "quality":
        print(json.dumps(_quality_snapshot(store, load_profile(args.profile)), ensure_ascii=False, indent=2))
        return 0

    if args.command == "stats":
        print(json.dumps(store.stats(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "runs":
        print(json.dumps(store.recent_collection_runs(args.limit), ensure_ascii=False, indent=2))
        return 0

    if args.command == "doctor":
        ok, checks = run_doctor(args.db, args.profile, args.sources)
        for check in checks:
            print(f"[{check['status'].upper()}] {check['check']}: {check['detail']}")
        return 0 if ok else 1

    if args.command == "demo":
        imported, updated = _import(store, args.sample)
        count = _score(store, args.profile, all_notices=True)
        rows = store.ranked(limit=20, min_score=0)
        target = write_digest(args.output, rows)
        dashboard_target = write_dashboard(args.dashboard_output, rows, title="OpenBid Intel Demo")
        print(f"Demo complete: {imported} new, {updated} updated, {count} scored; digest {target}; dashboard {dashboard_target}")
        return 0

    return 2


def _import(store: Store, path: str, mapping_path: str | None = None) -> tuple[int, int]:
    return _upsert_notices(store, load_notices(path, mapping_path))


def _upsert_notices(store: Store, notices) -> tuple[int, int]:
    imported = updated = 0
    for notice in notices:
        if not notice.title or not notice.published_at:
            raise ValueError("公告必须包含 title 和 published_at")
        _, created = store.upsert_notice(notice)
        if created:
            imported += 1
        else:
            updated += 1
    return imported, updated


def _collect(
    store: Store, sources_path: str, fetch_details: bool, max_details: int | None,
    max_pages: int | None = None, history_days: int | None = None,
) -> dict:
    totals = {"fetched": 0, "imported": 0, "updated": 0, "failed_sources": 0, "sources": []}
    batch_started = datetime.now().astimezone().isoformat(timespec="seconds")
    for result in collect_sources(
        sources_path, fetch_details=fetch_details, max_details=max_details,
        max_pages=max_pages, history_days=history_days,
    ):
        started = batch_started
        finished = datetime.now().astimezone().isoformat(timespec="seconds")
        imported = updated = 0
        status = "error" if result.error else "ok"
        if not result.error:
            imported, updated = _upsert_notices(store, result.notices)
        else:
            totals["failed_sources"] += 1
        store.add_collection_run(result.source_id, result.source_name, status, result.fetched, imported, updated, result.error or result.warning, started, finished)
        totals["fetched"] += result.fetched
        totals["imported"] += imported
        totals["updated"] += updated
        totals["sources"].append({"name": result.source_name, "status": status, "fetched": result.fetched, "imported": imported, "updated": updated, "error": result.error, "warning": result.warning})
    return totals


def _print_collection(summary: dict) -> None:
    for source in summary["sources"]:
        suffix = f"；错误：{source['error']}" if source["error"] else ""
        print(f"[{source['status']}] {source['name']}：读取 {source['fetched']}，新增 {source['imported']}，更新 {source['updated']}{suffix}")
    print(f"合计：读取 {summary['fetched']}，新增 {summary['imported']}，更新 {summary['updated']}，失败来源 {summary['failed_sources']}")


def _score(store: Store, profile_path: str, all_notices: bool) -> int:
    matcher = Matcher.from_file(profile_path)
    notices = store.all_notices() if all_notices else store.unscored_notices()
    for notice_id, notice in notices:
        store.save_score(notice_id, matcher.score(notice))
    return len(notices)


def _quality_snapshot(store: Store, profile: dict) -> dict:
    quality = store.data_quality()
    awards = store.award_history(limit=100000)
    quality["product_line_related_awards"] = len(analyze_awards(awards, profile, relevant_only=True))
    priority_hits = {}
    for account in profile.get("sales_profile", {}).get("priority_accounts", []):
        name = str(account.get("name") or "")
        aliases = list(dict.fromkeys([name, *[str(item) for item in account.get("aliases", [])]]))
        priority_hits[name] = len(store.award_history(limit=100000, buyer_queries=aliases))
    quality["priority_account_awards"] = sum(priority_hits.values())
    quality["priority_accounts"] = priority_hits
    quality["source_quality"] = store.source_quality()
    return quality


def _write_quality_report(path: Path, quality: dict, collection: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = {"notices": "\u516c\u544a\u603b\u6570", "with_details": "\u6709\u8be6\u60c5\u6b63\u6587", "with_budget": "\u6709\u9884\u7b97", "with_buyer": "\u6709\u91c7\u8d2d\u5355\u4f4d", "award_notices": "\u6709\u4e2d\u6807\u4f9b\u5e94\u5546", "awards_with_amount": "\u6709\u4e2d\u6807\u91d1\u989d", "product_line_related_awards": "\u4ea7\u54c1\u7ebf\u76f8\u5173\u4e2d\u6807", "priority_account_awards": "\u91cd\u70b9\u5ba2\u6237\u4e2d\u6807", "runs": "\u7d2f\u8ba1\u91c7\u96c6\u8fd0\u884c", "successful_runs": "\u6210\u529f\u8fd0\u884c", "failed_runs": "\u5931\u8d25\u8fd0\u884c"}
    lines = ["# \u6570\u636e\u8d28\u91cf\u62a5\u544a", "", f"- \u751f\u6210\u65f6\u95f4\uff1a{datetime.now().astimezone().isoformat(timespec='minutes')}", "", "## \u6570\u636e\u5b8c\u6574\u5ea6", "", "| \u6307\u6807 | \u6570\u91cf |", "|---|---:|"]
    for key, label in labels.items(): lines.append(f"| {label} | {quality.get(key, 0)} |")
    lines.extend(["", "## \u91cd\u70b9\u5ba2\u6237\u4e2d\u6807\u8986\u76d6", "", "| \u5ba2\u6237 | \u516c\u544a\u6570 |", "|---|---:|"])
    for name, count in quality.get("priority_accounts", {}).items(): lines.append(f"| {name} | {count} |")
    lines.extend(["", "## \u5404\u6765\u6e90\u5386\u53f2\u6210\u529f\u7387", "", "| \u6765\u6e90 | \u8fd0\u884c | \u6210\u529f | \u5931\u8d25 | \u6210\u529f\u7387 | \u7d2f\u8ba1\u8bfb\u53d6 |", "|---|---:|---:|---:|---:|---:|"])
    for row in quality.get("source_quality", []):
        lines.append(f"| {row['source_name']} | {row['runs']} | {row['successful_runs']} | {row['failed_runs']} | {row['success_rate']:.1f}% | {row['fetched_count']} |")
    lines.extend(["", "## \u672c\u6b21\u91c7\u96c6\u6765\u6e90", "", "| \u6765\u6e90 | \u72b6\u6001 | \u8bfb\u53d6 | \u65b0\u589e | \u66f4\u65b0 |", "|---|---|---:|---:|---:|"])
    for row in collection.get("sources", []): lines.append(f"| {row['name']} | {row['status']} | {row['fetched']} | {row['imported']} | {row['updated']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run_intelligence(store: Store, args) -> int:
    collection = _collect(store, args.sources, not args.no_details, args.max_details, args.max_pages, args.history_days)
    scored = _score(store, args.profile, all_notices=True)
    profile = load_profile(args.profile)
    output_dir = Path(args.output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d")
    digest_rows = store.ranked(limit=args.limit, min_score=args.min_score)
    digest_path = write_digest(output_dir / f"digest_{stamp}.md", digest_rows)
    awards = analyze_awards(store.award_history(limit=args.history_limit), profile, relevant_only=True)
    overall_path = write_competitor_report(output_dir / f"competitors_{stamp}.md", summarize_suppliers(awards), awards, relationships=build_relationships(awards), relevant_only=True)
    account_paths = []
    for account in profile.get("sales_profile", {}).get("priority_accounts", []):
        name = str(account.get("name") or "")
        aliases = list(dict.fromkeys([name, *[str(item) for item in account.get("aliases", [])]]))
        account_awards = analyze_awards(store.award_history(limit=args.history_limit, buyer_queries=aliases), profile, relevant_only=True)
        safe_name = "".join(char if char not in '<>:"/\\|?*' else "_" for char in name)
        account_paths.append(write_competitor_report(output_dir / f"account_{safe_name}_{stamp}.md", summarize_suppliers(account_awards), account_awards, name, relationships=build_relationships(account_awards), relevant_only=True))
    quality_path = _write_quality_report(output_dir / f"quality_{stamp}.md", _quality_snapshot(store, profile), collection)
    pushed = False; load_dotenv()
    if not args.no_push and os.getenv("FEISHU_WEBHOOK_URL"):
        send_feishu_text(render_feishu_digest(digest_rows)); pushed = True
    _print_collection(collection)
    push_status = "\u6210\u529f" if pushed else "\u8df3\u8fc7"
    print(f"\u5168\u91cf\u91cd\u8bc4\u5206 {scored} \u6761\uff1b\u65e5\u62a5 {digest_path}\uff1b\u7ade\u4e89\u62a5\u544a {overall_path}\uff1b\u91cd\u70b9\u5ba2\u6237\u62a5\u544a {len(account_paths)} \u4efd\uff1b\u8d28\u91cf\u62a5\u544a {quality_path}\uff1b\u98de\u4e66\u63a8\u9001\uff1a{push_status}")
    return 1 if collection["failed_sources"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
