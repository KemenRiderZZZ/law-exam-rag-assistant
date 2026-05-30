#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

from 官方法条工具 import build_project_text, find_record, get_project_text_path, get_raw_source_path, load_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将官方原件提取为项目可入库文本")
    parser.add_argument("--book-name")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--input")
    parser.add_argument("--pdf")
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not any([args.book_name, args.all, args.input, args.pdf]):
        raise SystemExit("请使用 --book-name、--all 或 --input/--pdf 指定来源")

    if args.input or args.pdf:
        input_path = Path(args.input or args.pdf)
        if not input_path.is_absolute():
            input_path = (PROJECT_ROOT / input_path).resolve()
        if not input_path.exists():
            raise SystemExit(f"原件不存在: {input_path}")
        output_path = Path(args.output) if args.output else input_path.with_suffix(".txt")
        if not output_path.is_absolute():
            output_path = (PROJECT_ROOT / output_path).resolve()
        from 官方法条工具 import extract_raw_file, normalize_text_content

        law_name = input_path.stem
        output_path.write_text(
            normalize_text_content(extract_raw_file(input_path), law_name),
            encoding="utf-8",
        )
        print(f"原件: {input_path}")
        print(f"TXT: {output_path}")
        return 0

    manifest = load_manifest()
    targets = manifest if args.all else [find_record(manifest, args.book_name)]

    for record in targets:
        output_path = Path(args.output) if args.output and not args.all else None
        if output_path and not output_path.is_absolute():
            output_path = (PROJECT_ROOT / output_path).resolve()
        if output_path is None:
            output_path = get_project_text_path(record["file_name"])
        current_record, raw_path, text_path = build_project_text(record, output_path=output_path)
        print(f"书目: {current_record['book_name']}")
        print(f"原件: {raw_path}")
        print(f"TXT: {text_path}")
        print("---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
