#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import importlib.util


BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "数据库"


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
    books = ["戴鹏《民诉》整理版", "左宁刑事诉讼法专题讲座精讲卷（2026版）"]

    with connect(config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.id,
                    b.book_name,
                    COUNT(*) AS total_chunks,
                    SUM(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded_chunks,
                    MIN(c.embedding_model) AS embedding_model
                FROM chunks c
                JOIN books b ON b.id = c.book_id
                WHERE b.book_name IN (%s, %s)
                GROUP BY b.id, b.book_name
                ORDER BY b.id
                """,
                books,
            )
            rows = cur.fetchall()

    print(f"driver={driver}")
    for row in rows:
        print("|".join("" if value is None else str(value) for value in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
