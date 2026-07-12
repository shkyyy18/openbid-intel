from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .models import Notice, ScoreResult
from .normalize import notice_fingerprint


SCHEMA = """
CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TEXT NOT NULL,
    deadline_at TEXT,
    stage TEXT NOT NULL,
    buyer TEXT NOT NULL,
    region TEXT NOT NULL,
    budget_cny REAL,
    award_supplier TEXT NOT NULL DEFAULT '',
    award_amount_cny REAL,
    content TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scores (
    notice_id INTEGER PRIMARY KEY,
    score INTEGER NOT NULL,
    level TEXT NOT NULL,
    result_json TEXT NOT NULL,
    scored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(notice_id) REFERENCES notices(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notice_id INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(notice_id) REFERENCES notices(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_notices_published ON notices(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC);
CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    status TEXT NOT NULL,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    imported_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_collection_runs_started ON collection_runs(started_at DESC);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            _ensure_notice_columns(connection)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def upsert_notice(self, notice: Notice) -> tuple[int, bool]:
        fingerprint = notice_fingerprint(notice.title, notice.buyer, notice.project_id, notice.url)
        with self.connect() as connection:
            existing = connection.execute("SELECT id FROM notices WHERE fingerprint=?", (fingerprint,)).fetchone()
            payload = (
                notice.title, notice.url, notice.source, notice.published_at, notice.deadline_at,
                notice.stage, notice.buyer, notice.region, notice.budget_cny, notice.award_supplier,
                notice.award_amount_cny, notice.content, json.dumps(notice.raw, ensure_ascii=False), fingerprint,
            )
            if existing:
                connection.execute(
                    """UPDATE notices SET title=?, url=?, source=?, published_at=?, deadline_at=?, stage=?,
                    buyer=?, region=?, budget_cny=?, award_supplier=?, award_amount_cny=?, content=?, raw_json=? WHERE fingerprint=?""",
                    payload,
                )
                connection.execute("DELETE FROM scores WHERE notice_id=?", (int(existing["id"]),))
                return int(existing["id"]), False
            cursor = connection.execute(
                """INSERT INTO notices(title,url,source,published_at,deadline_at,stage,buyer,region,budget_cny,
                award_supplier,award_amount_cny,content,raw_json,fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                payload,
            )
            return int(cursor.lastrowid), True

    def save_score(self, notice_id: int, result: ScoreResult) -> None:
        data = {
            "score": result.score, "level": result.level, "business_lines": result.business_lines,
            "strong_hits": result.strong_hits, "related_hits": result.related_hits,
            "buyer_hits": result.buyer_hits, "negative_hits": result.negative_hits,
            "priority_account_hits": result.priority_account_hits,
            "region_match": result.region_match, "budget_status": result.budget_status,
            "reasons": result.reasons, "risks": result.risks,
            "recommended_actions": result.recommended_actions,
        }
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO scores(notice_id,score,level,result_json) VALUES(?,?,?,?)
                ON CONFLICT(notice_id) DO UPDATE SET score=excluded.score, level=excluded.level,
                result_json=excluded.result_json, scored_at=CURRENT_TIMESTAMP""",
                (notice_id, result.score, result.level, json.dumps(data, ensure_ascii=False)),
            )

    def unscored_notices(self) -> list[tuple[int, Notice]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT n.* FROM notices n LEFT JOIN scores s ON s.notice_id=n.id
                WHERE s.notice_id IS NULL ORDER BY n.published_at DESC"""
            ).fetchall()
        return [(int(row["id"]), _row_to_notice(row)) for row in rows]

    def all_notices(self) -> list[tuple[int, Notice]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM notices ORDER BY published_at DESC").fetchall()
        return [(int(row["id"]), _row_to_notice(row)) for row in rows]

    def ranked(self, limit: int = 20, min_score: int = 0) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT n.*, s.score, s.level, s.result_json,
                (SELECT verdict FROM feedback f WHERE f.notice_id=n.id ORDER BY f.id DESC LIMIT 1) latest_verdict
                FROM notices n JOIN scores s ON s.notice_id=n.id
                WHERE s.score >= ? ORDER BY s.score DESC, n.published_at DESC LIMIT ?""",
                (min_score, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["result"] = json.loads(item.pop("result_json"))
            result.append(item)
        return result

    def competitor_summary(self, limit: int = 30, buyer_query: str = "") -> list[dict]:
        where = "award_supplier <> ''"
        params: list[object] = []
        if buyer_query:
            where += " AND buyer LIKE ?"
            params.append(f"%{buyer_query}%")
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT award_supplier supplier, COUNT(*) award_count,
                SUM(COALESCE(award_amount_cny, 0)) total_award_cny,
                AVG(award_amount_cny) average_award_cny,
                GROUP_CONCAT(DISTINCT buyer) buyers
                FROM notices WHERE {where}
                GROUP BY award_supplier
                ORDER BY award_count DESC, total_award_cny DESC LIMIT ?""",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def award_history(
        self, buyer_query: str = "", limit: int = 100, buyer_queries: list[str] | None = None,
    ) -> list[dict]:
        where = "award_supplier <> ''"
        params: list[object] = []
        queries = [item.strip() for item in (buyer_queries or []) if item.strip()]
        if not queries and buyer_query.strip():
            queries = [buyer_query.strip()]
        if queries:
            where += " AND (" + " OR ".join("buyer LIKE ?" for _ in queries) + ")"
            params.extend(f"%{item}%" for item in queries)
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT id,title,buyer,region,published_at,stage,award_supplier,award_amount_cny,url,content
                FROM notices WHERE {where}
                ORDER BY published_at DESC LIMIT ?""", params
            ).fetchall()
        return [dict(row) for row in rows]

    def data_quality(self) -> dict[str, int]:
        with self.connect() as connection:
            row = connection.execute("""SELECT
                COUNT(*) notices,
                SUM(CASE WHEN raw_json LIKE '%\"detail_fetched_at\"%' THEN 1 ELSE 0 END) with_details,
                SUM(CASE WHEN budget_cny IS NOT NULL THEN 1 ELSE 0 END) with_budget,
                SUM(CASE WHEN buyer <> '' THEN 1 ELSE 0 END) with_buyer,
                SUM(CASE WHEN award_supplier <> '' THEN 1 ELSE 0 END) award_notices,
                SUM(CASE WHEN award_supplier <> '' AND award_amount_cny IS NOT NULL THEN 1 ELSE 0 END) awards_with_amount
                FROM notices""").fetchone()
            runs = connection.execute("""SELECT
                COUNT(*) runs,
                SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) successful_runs,
                SUM(CASE WHEN status<>'ok' THEN 1 ELSE 0 END) failed_runs
                FROM collection_runs""").fetchone()
        result = {key: int(row[key] or 0) for key in row.keys()}
        result.update({key: int(runs[key] or 0) for key in runs.keys()})
        return result

    def add_feedback(self, notice_id: int, verdict: str, note: str = "") -> None:
        with self.connect() as connection:
            exists = connection.execute("SELECT 1 FROM notices WHERE id=?", (notice_id,)).fetchone()
            if not exists:
                raise ValueError(f"公告不存在: {notice_id}")
            connection.execute("INSERT INTO feedback(notice_id, verdict, note) VALUES(?,?,?)", (notice_id, verdict, note))

    def add_collection_run(
        self, source_id: str, source_name: str, status: str, fetched_count: int,
        imported_count: int, updated_count: int, error: str, started_at: str, finished_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO collection_runs(source_id,source_name,status,fetched_count,imported_count,
                updated_count,error,started_at,finished_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (source_id, source_name, status, fetched_count, imported_count, updated_count, error, started_at, finished_at),
            )

    def recent_collection_runs(self, limit: int = 20) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM collection_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def source_quality(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute("""SELECT source_id, MAX(source_name) source_name,
                COUNT(*) runs,
                SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) successful_runs,
                SUM(CASE WHEN status<>'ok' THEN 1 ELSE 0 END) failed_runs,
                SUM(fetched_count) fetched_count,
                SUM(imported_count) imported_count,
                SUM(updated_count) updated_count
                FROM collection_runs GROUP BY source_id ORDER BY source_id""").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["success_rate"] = round(item["successful_runs"] * 100 / item["runs"], 1) if item["runs"] else 0.0
            result.append(item)
        return result

    def stats(self) -> dict[str, int]:
        with self.connect() as connection:
            notice_count = connection.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
            score_count = connection.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
            feedback_count = connection.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            supplier_count = connection.execute("SELECT COUNT(*) FROM notices WHERE award_supplier <> ''").fetchone()[0]
        return {"notices": notice_count, "scores": score_count, "feedback": feedback_count, "awards_with_supplier": supplier_count}


def _row_to_notice(row: sqlite3.Row) -> Notice:
    return Notice(
        title=row["title"], url=row["url"], source=row["source"], published_at=row["published_at"],
        deadline_at=row["deadline_at"], stage=row["stage"], buyer=row["buyer"], region=row["region"],
        budget_cny=row["budget_cny"], award_supplier=row["award_supplier"],
        award_amount_cny=row["award_amount_cny"], content=row["content"], raw=json.loads(row["raw_json"]),
    )


def _ensure_notice_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(notices)")}
    if "award_supplier" not in columns:
        connection.execute("ALTER TABLE notices ADD COLUMN award_supplier TEXT NOT NULL DEFAULT ''")
    if "award_amount_cny" not in columns:
        connection.execute("ALTER TABLE notices ADD COLUMN award_amount_cny REAL")
