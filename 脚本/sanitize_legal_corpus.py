#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成保密版书稿与切块，去除书名、版次、出版和资料来源痕迹。"""

from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXT_SRC_DIR = PROJECT_ROOT / "整理后文本"
CHUNK_SRC_DIR = PROJECT_ROOT / "切块"
TEXT_DST_DIR = PROJECT_ROOT / "保密版文本"
CHUNK_DST_DIR = PROJECT_ROOT / "保密版切块"

SOURCE_MARKERS = (
    "出版社",
    "ISBN",
    "CIP",
    "整理说明",
    "OCR原稿",
    "本案来源于",
    "资料来源",
    "来源：",
    "来源:",
    "参见",
    "编著",
    "版权",
    "出版发行",
    "印刷",
    "邮编",
    "E-mail",
    "http",
    "新华书店",
)
TEACHER_NAMES = (
    "孟献贵",
    "左宁",
    "戴鹏",
    "李佳",
    "杨帆",
    "柏浪涛",
    "郄鹏恩",
)
EDITION_PATTERN = re.compile(r"[\(\uff08]?\s*20\d{2}\s*版\s*[\)\uff09]?")
BOOK_TITLE_PATTERN = re.compile(r"^#\s*.+$")
DOUBLE_BLANKS_PATTERN = re.compile(r"\n{3,}")


def contains_source_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in SOURCE_MARKERS)


def scrub_line(line: str) -> str:
    line = line.replace("\ufeff", "").strip()
    if not line:
      return ""
    if contains_source_marker(line):
        return ""
    line = EDITION_PATTERN.sub("", line).strip()
    for teacher_name in TEACHER_NAMES:
        line = line.replace(teacher_name, "")
    line = re.sub(r"[《》]", "", line).strip()
    line = re.sub(r"\s{2,}", " ", line)
    return line


def sanitize_markdown_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for index, raw_line in enumerate(text.replace("\r", "").split("\n")):
        line = scrub_line(raw_line)
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if index == 0 and BOOK_TITLE_PATTERN.match(raw_line):
            line = "# 法考知识汇编"
        cleaned_lines.append(line)

    return DOUBLE_BLANKS_PATTERN.sub("\n\n", "\n".join(cleaned_lines)).strip() + "\n"


def sanitize_chunk_record(record: dict, index: int) -> dict:
    text = sanitize_markdown_text(record.get("text", "")).strip()
    metadata = record.get("metadata") or {}
    return {
        "id": f"knowledge::{index:04d}",
        "text": text,
        "metadata": {
            "book": "法考知识汇编",
            "doc_type": metadata.get("doc_type") or "教材",
            "char_count": len(text),
        },
        "chunk_index": index,
    }


def write_text_outputs() -> list[Path]:
    TEXT_DST_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in sorted(TEXT_SRC_DIR.glob("*.md")):
        if "说明" in path.stem:
            continue
        sanitized = sanitize_markdown_text(path.read_text(encoding="utf-8", errors="ignore"))
        target = TEXT_DST_DIR / path.name
        target.write_text(sanitized, encoding="utf-8")
        written.append(target)
    return written


def write_chunk_outputs() -> list[Path]:
    CHUNK_DST_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in sorted(CHUNK_SRC_DIR.glob("*.jsonl")):
        target = CHUNK_DST_DIR / path.name
        rows: list[str] = []
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for index, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                record = json.loads(line)
                rows.append(json.dumps(sanitize_chunk_record(record, index), ensure_ascii=False))
        target.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
        written.append(target)
    return written


def main() -> int:
    text_outputs = write_text_outputs()
    chunk_outputs = write_chunk_outputs()
    print(f"保密版文本: {len(text_outputs)}")
    print(f"保密版切块: {len(chunk_outputs)}")
    print(f"输出目录: {TEXT_DST_DIR}")
    print(f"输出目录: {CHUNK_DST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
