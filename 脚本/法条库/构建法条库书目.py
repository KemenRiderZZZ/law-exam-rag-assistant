#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
TEXT_DIR = PROJECT_ROOT / "整理后文本" / "法条库" / "正文"
MANIFEST_PATH = SCRIPT_DIR / "法条库清单.json"


def resolve_python() -> str:
    return os.environ.get("CODEX_BUNDLED_PYTHON") or sys.executable


def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="一键构建单本法条库书目")
    parser.add_argument("--book-name")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--embed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.all and not args.book_name:
        raise SystemExit("请使用 --book-name 或 --all 指定范围")

    python_bin = resolve_python()
    manifest = load_manifest()
    targets = manifest if args.all else [
        next((item for item in manifest if item["book_name"] == args.book_name), None)
    ]
    if not targets or targets[0] is None:
        raise SystemExit(f"未在清单中找到书目: {args.book_name}")

    for record in targets:
        txt_path = TEXT_DIR / record["file_name"]
        run([python_bin, str(SCRIPT_DIR / "抓取法条PDF.py"), "--book-name", record["book_name"]])
        run(
            [
                python_bin,
                str(SCRIPT_DIR / "PDF转文本.py"),
                "--book-name",
                record["book_name"],
                "--output",
                str(txt_path),
            ]
        )
        run([python_bin, str(SCRIPT_DIR / "法条切块.py"), "--book-name", record["book_name"]])

        import_cmd = [python_bin, str(SCRIPT_DIR / "导入法条库.py"), "--book-name", record["book_name"]]
        if args.embed:
            import_cmd.append("--embed")
        run(import_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
