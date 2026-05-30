#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import sys
from pathlib import Path


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def load_db_config(env_path: Path) -> dict[str, str]:
    env = load_env_file(env_path)
    return {
        "host": env.get("POSTGRES_HOST", "127.0.0.1"),
        "port": env.get("POSTGRES_PORT", "5432"),
        "dbname": env.get("POSTGRES_DB", "lawqa"),
        "user": env.get("POSTGRES_USER", "law"),
        "password": env.get("POSTGRES_PASSWORD", "please-change-this-password"),
    }


def get_db_driver():
    try:
        import psycopg

        def connect(config: dict[str, str]):
            return psycopg.connect(**config)

        return connect, "psycopg"
    except ImportError:
        pass

    try:
        import psycopg2

        def connect(config: dict[str, str]):
            return psycopg2.connect(**config)

        return connect, "psycopg2"
    except ImportError:
        pass

    raise SystemExit(
        "未找到 psycopg / psycopg2。请先安装其一，例如：\n"
        "  pip install psycopg[binary]\n"
        "或\n"
        "  pip install psycopg2-binary"
    )


def resolve_path(path_str: str, cwd: Path) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (cwd / path).resolve()


def load_rows(jsonl_path: Path) -> list[dict]:
    rows: list[dict] = []
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{jsonl_path} 第 {line_no} 行 JSON 解析失败: {exc}") from exc
    if not rows:
        raise SystemExit(f"{jsonl_path} 没有可导入的数据")
    return rows


def infer_book_name(rows: list[dict], fallback: str) -> str:
    meta = rows[0].get("metadata") or {}
    return meta.get("book") or fallback


def upsert_book(cur, book_name: str, source_file: str | None, note: str | None) -> int:
    cur.execute(
        """
        INSERT INTO books (book_name, source_file, note)
        VALUES (%s, %s, %s)
        ON CONFLICT (book_name)
        DO UPDATE SET
            source_file = COALESCE(EXCLUDED.source_file, books.source_file),
            note = COALESCE(EXCLUDED.note, books.note)
        RETURNING id
        """,
        (book_name, source_file, note),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("books 表 upsert 后未返回 id")
    return int(row[0])


def upsert_chunks(cur, rows: list[dict], book_id: int) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for fallback_index, row in enumerate(rows, start=1):
        metadata = row.get("metadata") or {}
        chunk_id = row["id"]
        chunk_index = row.get("chunk_index") or fallback_index
        text_content = row["text"]

        cur.execute("SELECT 1 FROM chunks WHERE chunk_id = %s", (chunk_id,))
        existed = cur.fetchone() is not None

        cur.execute(
            """
            INSERT INTO chunks (
                chunk_id,
                book_id,
                chunk_index,
                text_content,
                chapter,
                section,
                subsection,
                subsub,
                source_line_start,
                source_line_end,
                char_count,
                metadata
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            ON CONFLICT (chunk_id)
            DO UPDATE SET
                book_id = EXCLUDED.book_id,
                chunk_index = EXCLUDED.chunk_index,
                text_content = EXCLUDED.text_content,
                chapter = EXCLUDED.chapter,
                section = EXCLUDED.section,
                subsection = EXCLUDED.subsection,
                subsub = EXCLUDED.subsub,
                source_line_start = EXCLUDED.source_line_start,
                source_line_end = EXCLUDED.source_line_end,
                char_count = EXCLUDED.char_count,
                metadata = EXCLUDED.metadata
            """,
            (
                chunk_id,
                book_id,
                chunk_index,
                text_content,
                metadata.get("chapter"),
                metadata.get("section"),
                metadata.get("subsection"),
                metadata.get("subsub"),
                metadata.get("source_line_start"),
                metadata.get("source_line_end"),
                metadata.get("char_count"),
                json.dumps(metadata, ensure_ascii=False),
            ),
        )

        if existed:
            updated += 1
        else:
            inserted += 1

    return inserted, updated


def delete_missing_chunks_for_book(cur, book_id: int, keep_chunk_ids: list[str]) -> int:
    if not keep_chunk_ids:
        cur.execute("DELETE FROM chunks WHERE book_id = %s", (book_id,))
        return cur.rowcount or 0

    cur.execute(
        """
        DELETE FROM chunks
        WHERE book_id = %s
          AND NOT (chunk_id = ANY(%s))
        """,
        (book_id, keep_chunk_ids),
    )
    return cur.rowcount or 0


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="将切块 JSONL 导入 PostgreSQL")
    parser.add_argument("--jsonl", required=True, help="JSONL 文件路径")
    parser.add_argument("--book-name", help="覆盖 JSONL metadata.book")
    parser.add_argument("--source-file", help="原始 Markdown 文件路径")
    parser.add_argument("--note", help="写入 books.note")
    parser.add_argument(
        "--sync-book",
        action="store_true",
        help="删除该书目下本次 JSONL 未包含的旧 chunks，保持数据库与当前切块一致",
    )
    parser.add_argument(
        "--db-env",
        default=str(script_dir / ".env.pg"),
        help="数据库环境变量文件路径，默认使用 数据库/.env.pg",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()

    jsonl_path = resolve_path(args.jsonl, cwd)
    db_env_path = resolve_path(args.db_env, cwd)
    source_file = resolve_path(args.source_file, cwd) if args.source_file else None

    rows = load_rows(jsonl_path)
    book_name = args.book_name or infer_book_name(rows, jsonl_path.stem)
    db_config = load_db_config(db_env_path)
    connect, driver_name = get_db_driver()

    with connect(db_config) as conn:
        with conn.cursor() as cur:
            book_id = upsert_book(
                cur,
                book_name=book_name,
                source_file=str(source_file) if source_file else None,
                note=args.note,
            )
            inserted, updated = upsert_chunks(cur, rows, book_id)
            deleted = 0
            if args.sync_book:
                keep_chunk_ids = [str(row["id"]) for row in rows]
                deleted = delete_missing_chunks_for_book(cur, book_id, keep_chunk_ids)
        conn.commit()

    print(f"数据库驱动: {driver_name}")
    print(f"JSONL: {jsonl_path}")
    print(f"书名: {book_name}")
    print(f"books.id: {book_id}")
    print(f"总记录: {len(rows)}")
    print(f"新增 chunks: {inserted}")
    print(f"更新 chunks: {updated}")
    print(f"删除旧 chunks: {deleted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
