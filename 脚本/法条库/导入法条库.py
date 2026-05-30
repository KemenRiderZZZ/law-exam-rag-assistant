#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_IMPORT = PROJECT_ROOT / "数据库" / "import_chunks_to_pg.py"
DB_EMBED = PROJECT_ROOT / "数据库" / "embed_and_update.py"
MANIFEST_PATH = Path(__file__).with_name("法条库清单.json")
CHUNK_DIR = PROJECT_ROOT / "切块" / "法条库"


def load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def resolve_python() -> str:
    return (
        os.environ.get("CODEX_BUNDLED_PYTHON")
        or sys.executable
    )


def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入法条库 JSONL 并可选嵌入")
    parser.add_argument("--book-name", required=True)
    parser.add_argument("--embed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    python_bin = resolve_python()
    manifest = load_manifest()
    record = next((item for item in manifest if item["book_name"] == args.book_name), None)
    if not record:
        raise SystemExit(f"未在清单中找到书目: {args.book_name}")

    jsonl_path = CHUNK_DIR / f"{record['book_name']}.jsonl"
    if not jsonl_path.exists():
        raise SystemExit(f"切块文件不存在: {jsonl_path}")
    source_file = PROJECT_ROOT / "整理后文本" / "法条库" / record["file_name"]

    run(
        [
            python_bin,
            str(DB_IMPORT),
            "--jsonl",
            str(jsonl_path),
            "--book-name",
            record["book_name"],
            "--source-file",
            str(source_file),
            "--note",
            "法条库导入",
            "--sync-book",
        ]
    )

    if args.embed:
        run(
            [
                python_bin,
                str(DB_EMBED),
                "--book-name",
                record["book_name"],
            ]
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
