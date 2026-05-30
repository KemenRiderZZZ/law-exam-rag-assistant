#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

from 官方法条工具 import download_official_source, find_record, load_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="下载法条库官方原始文件并归档到 Obsidian")
    parser.add_argument("--book-name")
    parser.add_argument("--all", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.all and not args.book_name:
        raise SystemExit("请使用 --book-name 或 --all 指定范围")

    manifest = load_manifest()
    targets = manifest if args.all else [find_record(manifest, args.book_name)]

    for record in targets:
        enriched, output_path = download_official_source(record)
        print(f"书目: {enriched['book_name']}")
        print(f"原件: {output_path}")
        print(f"来源: {enriched['source_url']}")
        print("---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
