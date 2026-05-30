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
        "base_url": env.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/"),
        "model": env.get("EMBEDDING_MODEL", "BAAI/bge-m3"),
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


def create_query_embedding(config: dict[str, str], query: str) -> tuple[list[float], dict]:
    payload = {
        "model": config["model"],
        "input": query,
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
        raise RuntimeError(f"SiliconFlow query embedding 请求失败: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SiliconFlow query embedding 请求失败: {exc}") from exc

    items = data.get("data") or []
    if not items:
        raise RuntimeError("SiliconFlow 未返回 embedding 数据")
    vector = items[0]["embedding"]
    return vector, data.get("usage") or {}


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".12g") for value in values) + "]"


def fetch_matches(
    conn,
    query_vector: list[float],
    top_k: int,
    book_name: str | None,
    chapter: str | None,
    embedding_model: str | None,
):
    sql = """
        SELECT *
        FROM match_chunks(
            %s::vector,
            %s,
            %s,
            %s,
            %s
        )
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                vector_literal(query_vector),
                top_k,
                book_name,
                chapter,
                embedding_model,
            ),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def print_human_results(results: list[dict], usage: dict, driver_name: str) -> None:
    print(f"数据库驱动: {driver_name}")
    if usage:
        print(f"embedding usage: {json.dumps(usage, ensure_ascii=False)}")
    print(f"命中数量: {len(results)}")
    print("")

    for idx, row in enumerate(results, start=1):
        print(f"[{idx}] score={row['score']:.6f} 书名={row['book_name']}")
        print(f"    chunk_id={row['chunk_id']}")
        print(f"    chapter={row['chapter'] or ''}")
        print(f"    section={row['section'] or ''}")
        print(f"    subsection={row['subsection'] or ''}")
        print(f"    lines={row['source_line_start']} - {row['source_line_end']}")
        print(f"    embedding_model={row['embedding_model']}")
        print("    text:")
        for line in (row["text_content"] or "").splitlines():
            print(f"      {line}")
        print("")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="输入问题并检索最相似的 chunks")
    parser.add_argument("--query", required=True, help="待检索问题")
    parser.add_argument("--top-k", type=int, default=5, help="返回前几条，默认 5")
    parser.add_argument("--book-name", help="只检索指定书名")
    parser.add_argument("--chapter", help="只检索指定章名")
    parser.add_argument("--no-model-filter", action="store_true", help="不限制 embedding_model")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
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
    cwd = Path.cwd()

    db_env_path = resolve_path(args.db_env, cwd)
    embedding_env_path = resolve_path(args.embedding_env, cwd)

    db_config = load_db_config(db_env_path)
    embedding_config = load_embedding_config(embedding_env_path)
    if not embedding_config["api_key"]:
        raise SystemExit(f"请先在 {embedding_env_path} 中填写 SILICONFLOW_API_KEY")

    query_vector, usage = create_query_embedding(embedding_config, args.query)
    embedding_model = None if args.no_model_filter else embedding_config["model"]

    connect, driver_name = get_db_driver()
    with connect(db_config) as conn:
        results = fetch_matches(
            conn=conn,
            query_vector=query_vector,
            top_k=args.top_k,
            book_name=args.book_name,
            chapter=args.chapter,
            embedding_model=embedding_model,
        )

    if args.json:
        print(
            json.dumps(
                {
                    "query": args.query,
                    "top_k": args.top_k,
                    "usage": usage,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_human_results(results, usage, driver_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
