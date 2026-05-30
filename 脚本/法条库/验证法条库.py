#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = PROJECT_ROOT / "数据库"
CHUNK_DIR = PROJECT_ROOT / "切块" / "法条库"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    mod = load_module("import_chunks_to_pg", DB_DIR / "import_chunks_to_pg.py")
    config = mod.load_db_config(DB_DIR / ".env.pg")
    connect, driver = mod.get_db_driver()

    local_chunk_counts: dict[str, int] = {}
    for jsonl_path in sorted(CHUNK_DIR.glob("法条库｜*.jsonl")):
        count = 0
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                if raw_line.strip():
                    count += 1
        local_chunk_counts[jsonl_path.stem] = count

    with connect(config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.book_name,
                    COUNT(c.db_id) AS total_chunks,
                    SUM(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded_chunks,
                    MIN(c.embedding_model) AS embedding_model
                FROM books b
                LEFT JOIN chunks c ON c.book_id = b.id
                WHERE b.book_name LIKE '法条库｜%'
                GROUP BY b.book_name
                ORDER BY b.book_name
                """
            )
            rows = cur.fetchall()

    print(f"driver={driver}")
    print(
        json.dumps(
            {
                "books_in_db": len(rows),
                "books_in_chunk_dir": len(local_chunk_counts),
            },
            ensure_ascii=False,
        )
    )
    for row in rows:
        book_name = str(row[0])
        db_total = 0 if row[1] is None else int(row[1])
        embedded = 0 if row[2] is None else int(row[2])
        model = "" if row[3] is None else str(row[3])
        local_total = local_chunk_counts.get(book_name, 0)
        print(
            "|".join(
                [
                    book_name,
                    str(local_total),
                    str(db_total),
                    str(embedded),
                    model,
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
