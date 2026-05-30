#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import sys
import urllib.error
import urllib.request
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


def load_embedding_config(env_path: Path) -> dict[str, str]:
    env = load_env_file(env_path)
    return {
        "api_key": env.get("SILICONFLOW_API_KEY", ""),
        "base_url": env.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1").rstrip("/"),
        "model": env.get("EMBEDDING_MODEL", "BAAI/bge-m3"),
        "batch_size": env.get("EMBEDDING_BATCH_SIZE", "32"),
        "max_input_tokens": env.get("EMBEDDING_MAX_INPUT_TOKENS", "8192"),
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


def create_embeddings(config: dict[str, str], texts: list[str]) -> tuple[list[list[float]], dict]:
    payload = {
        "model": config["model"],
        "input": texts,
        "encoding_format": "float",
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{config['base_url']}/embeddings",
        data=body,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SiliconFlow embeddings 请求失败: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SiliconFlow embeddings 请求失败: {exc}") from exc

    items = data.get("data") or []
    items = sorted(items, key=lambda item: item["index"])
    vectors = [item["embedding"] for item in items]
    if len(vectors) != len(texts):
        raise RuntimeError(
            f"返回向量数量与输入不一致: 输入 {len(texts)} 条, 返回 {len(vectors)} 条"
        )
    return vectors, data.get("usage") or {}


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".12g") for value in values) + "]"


def fetch_batch(cur, batch_size: int, book_name: str | None):
    if book_name:
        cur.execute(
            """
            SELECT c.db_id, c.chunk_id, c.text_content
            FROM chunks c
            JOIN books b ON b.id = c.book_id
            WHERE c.embedding IS NULL
              AND b.book_name = %s
            ORDER BY c.db_id
            LIMIT %s
            """,
            (book_name, batch_size),
        )
    else:
        cur.execute(
            """
            SELECT c.db_id, c.chunk_id, c.text_content
            FROM chunks c
            WHERE c.embedding IS NULL
            ORDER BY c.db_id
            LIMIT %s
            """,
            (batch_size,),
        )
    return cur.fetchall()


def update_embeddings(cur, batch_rows, vectors: list[list[float]], model_name: str) -> None:
    for row, vector in zip(batch_rows, vectors):
        db_id = row[0]
        cur.execute(
            """
            UPDATE chunks
            SET embedding = %s::vector,
                embedding_model = %s
            WHERE db_id = %s
            """,
            (vector_literal(vector), model_name, db_id),
        )


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="调用硅基流动 embedding 并回填 chunks.embedding")
    parser.add_argument("--book-name", help="只处理指定书名")
    parser.add_argument("--all", action="store_true", help="处理所有未写入 embedding 的记录")
    parser.add_argument("--limit", type=int, help="本次最多处理多少条")
    parser.add_argument("--batch-size", type=int, help="覆盖 .env.embedding 中的批大小")
    parser.add_argument(
        "--db-env",
        default=str(script_dir / ".env.pg"),
        help="数据库环境变量文件路径，默认使用 数据库/.env.pg",
    )
    parser.add_argument(
        "--embedding-env",
        default=str(script_dir / ".env.embedding"),
        help="embedding 环境变量文件路径，默认使用 数据库/.env.embedding",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.all and not args.book_name:
        raise SystemExit("请使用 --all 或 --book-name 指定处理范围")

    cwd = Path.cwd()
    db_env_path = resolve_path(args.db_env, cwd)
    embedding_env_path = resolve_path(args.embedding_env, cwd)

    db_config = load_db_config(db_env_path)
    embedding_config = load_embedding_config(embedding_env_path)
    if not embedding_config["api_key"]:
        raise SystemExit(f"请先在 {embedding_env_path} 中填写 SILICONFLOW_API_KEY")

    batch_size = args.batch_size or int(embedding_config["batch_size"])
    remaining = args.limit
    processed = 0

    connect, driver_name = get_db_driver()

    with connect(db_config) as conn:
        while True:
            current_batch = batch_size if remaining is None else min(batch_size, remaining)
            if current_batch <= 0:
                break

            with conn.cursor() as cur:
                rows = fetch_batch(cur, current_batch, args.book_name)
            if not rows:
                break

            texts = [row[2] for row in rows]
            vectors, usage = create_embeddings(embedding_config, texts)

            with conn.cursor() as cur:
                update_embeddings(cur, rows, vectors, embedding_config["model"])
            conn.commit()

            processed += len(rows)
            if remaining is not None:
                remaining -= len(rows)

            dims = len(vectors[0]) if vectors else 0
            usage_text = json.dumps(usage, ensure_ascii=False) if usage else "{}"
            print(
                f"已写入 {processed} 条 embedding，"
                f"本批 {len(rows)} 条，维度 {dims}，usage={usage_text}"
            )

            if remaining == 0:
                break

    print(f"数据库驱动: {driver_name}")
    print(f"embedding 模型: {embedding_config['model']}")
    print(f"共处理: {processed} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
