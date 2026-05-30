#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXT_DIR = PROJECT_ROOT / "整理后文本" / "法条库" / "正文"
OUTPUT_DIR = PROJECT_ROOT / "切块" / "法条库"

ARTICLE_RE = re.compile(r"^第([一二三四五六七八九十百千万零〇两0-9]+)条[　 ]?(.*)$")
BOOK_RE = re.compile(r"^#\s+(.+?)\s*$")
CHAPTER_RE = re.compile(r"^(第[一二三四五六七八九十百千万零〇两0-9]+编)\s*(.*)$")
SECTION_RE = re.compile(r"^(第[一二三四五六七八九十百千万零〇两0-9]+章)\s*(.*)$")
SUBSECTION_RE = re.compile(r"^(第[一二三四五六七八九十百千万零〇两0-9]+节)\s*(.*)$")


def load_manifest(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_line(line: str) -> str:
    return line.replace("\ufeff", "").strip()


def split_articles(text: str) -> list[dict]:
    lines = text.splitlines()
    current_book = None
    current_chapter = None
    current_section = None
    current_subsection = None
    articles: list[dict] = []
    current_article: dict | None = None

    def flush_current():
        nonlocal current_article
        if not current_article:
            return
        current_article["text"] = "\n".join(current_article["lines"]).strip()
        del current_article["lines"]
        articles.append(current_article)
        current_article = None

    for idx, raw in enumerate(lines, start=1):
        line = normalize_line(raw)
        if not line:
            if current_article:
                current_article["lines"].append("")
            continue

        m_book = BOOK_RE.match(line)
        if m_book:
            current_book = m_book.group(1).strip()
            continue

        m_chapter = CHAPTER_RE.match(line)
        if m_chapter:
            current_chapter = line
            current_section = None
            current_subsection = None
            if current_article:
                current_article["lines"].append(line)
            continue

        m_section = SECTION_RE.match(line)
        if m_section:
            current_section = line
            current_subsection = None
            if current_article:
                current_article["lines"].append(line)
            continue

        m_subsection = SUBSECTION_RE.match(line)
        if m_subsection:
            current_subsection = line
            if current_article:
                current_article["lines"].append(line)
            continue

        m_article = ARTICLE_RE.match(line)
        if m_article:
            flush_current()
            current_article = {
                "article_no": f"第{m_article.group(1)}条",
                "book_heading": current_book,
                "chapter": current_chapter,
                "section": current_section,
                "subsection": current_subsection,
                "line_start": idx,
                "line_end": idx,
                "lines": [line],
            }
            continue

        if current_article:
            current_article["lines"].append(line)
            current_article["line_end"] = idx

    flush_current()
    return articles


def make_chunk_id(meta: dict, index: int) -> str:
    category = "法解" if meta["doc_type"] == "司法解释" else "法条"
    law_name = meta["book"].replace("法条库｜", "")
    chapter = meta.get("chapter") or "正文"
    article_no = meta.get("article_no") or f"片段{index:04d}"
    return f"{category}::{law_name}::{chapter}::{article_no}::{index:04d}"


def build_chunks(record: dict, source_text: str) -> list[dict]:
    articles = split_articles(source_text)
    chunks: list[dict] = []
    for index, article in enumerate(articles, start=1):
        text = article["text"].strip()
        if not text:
            continue
        metadata = {
            "book": record["book_name"],
            "doc_type": record["doc_type"],
            "law_category": record["law_category"],
            "chapter": article.get("chapter"),
            "section": article.get("section"),
            "subsection": article.get("subsection"),
            "article_no": article.get("article_no"),
            "source_url": record.get("source_url") or record.get("pdf_url"),
            "effective_status": record.get("effective_status"),
            "issued_authority": record.get("issued_authority"),
            "issued_date": record.get("issued_date"),
            "effective_date": record.get("effective_date"),
            "source_line_start": article.get("line_start"),
            "source_line_end": article.get("line_end"),
            "char_count": len(text),
        }
        chunks.append(
            {
                "id": make_chunk_id(metadata, index),
                "text": text,
                "metadata": metadata,
                "chunk_index": index,
            }
        )
    return chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将法条文本切为法条库 JSONL")
    parser.add_argument("--manifest", default=str(Path(__file__).with_name("法条库清单.json")))
    parser.add_argument("--book-name", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(Path(args.manifest))
    record = next((item for item in manifest if item["book_name"] == args.book_name), None)
    if not record:
        raise SystemExit(f"未在清单中找到书目: {args.book_name}")

    src_path = TEXT_DIR / record["file_name"]
    if not src_path.exists():
        raise SystemExit(f"原文不存在: {src_path}")

    source_text = src_path.read_text(encoding="utf-8")
    chunks = build_chunks(record, source_text)
    if not chunks:
        raise SystemExit(f"未切出任何法条: {src_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{record['book_name']}.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"书目: {record['book_name']}")
    print(f"输入: {src_path}")
    print(f"输出: {output_path}")
    print(f"chunks: {len(chunks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
