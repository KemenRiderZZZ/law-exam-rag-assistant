#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""孟献贵民法整理稿切块脚本。"""

import json
import re
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "孟献贵民法_整理版.md"
DST = PROJECT_ROOT / "切块" / "孟献贵民法_chunks.jsonl"

BOOK = "孟献贵民法专题讲座精讲卷（2026版）"
DOC_TYPE = "教材"
CHUNK_SIZE = 800
OVERLAP = 100
MIN_CHUNK_SIZE = 80

TOPIC_PARTS = [
    (1, 5, "第一部分 总则编"),
    (6, 10, "第二部分 物权编"),
    (11, 11, "第三部分 债法总则"),
    (12, 39, "第四部分 合同编"),
    (40, 40, "第五部分 人格权编"),
    (41, 42, "第六部分 婚姻家庭编"),
    (43, 43, "第七部分 继承编"),
    (44, 47, "第八部分 侵权责任编"),
    (48, 49, "第一部分 总则编"),
]


def cn_to_int(s: str) -> int | None:
    vals = {c: i + 1 for i, c in enumerate("一二三四五六七八九")}
    if s == "十":
        return 10
    if "十" in s:
        left, right = s.split("十", 1)
        tens = 1 if not left else vals.get(left)
        ones = 0 if not right else vals.get(right)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    return vals.get(s)


def infer_part_from_chapter(chapter: str | None, fallback: str | None) -> str | None:
    if not chapter:
        return fallback
    m = re.match(r"专题([一二三四五六七八九十]+)", chapter)
    if not m:
        return fallback
    num = cn_to_int(m.group(1))
    if not num:
        return fallback
    for start, end, part in TOPIC_PARTS:
        if start <= num <= end:
            return part
    return fallback


def parse_headings(text: str):
    lines = text.split("\n")
    state = {
        "book": BOOK,
        "part": None,
        "chapter": None,
        "section": None,
        "subsection": None,
    }
    parsed = []
    for i, line in enumerate(lines, start=1):
        m = re.match(r"^(#{1,5})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 1:
                state["book"] = title or BOOK
                state["part"] = None
                state["chapter"] = None
                state["section"] = None
                state["subsection"] = None
            elif level == 2:
                state["part"] = title
                state["chapter"] = None
                state["section"] = None
                state["subsection"] = None
            elif level == 3:
                state["chapter"] = title
                state["section"] = None
                state["subsection"] = None
            elif level == 4:
                state["section"] = title
                state["subsection"] = None
            elif level == 5:
                state["subsection"] = title
        parsed.append((i, line, dict(state)))
    return parsed


def split_into_blocks(parsed):
    blocks = []
    current = None
    for ln, line, state in parsed:
        if re.match(r"^#{1,5}\s+", line):
            if current is not None:
                blocks.append(current)
            current = {
                "start": ln,
                "end": ln,
                "path": state,
                "lines": [line],
            }
        else:
            if current is None:
                current = {
                    "start": ln,
                    "end": ln,
                    "path": state,
                    "lines": [line],
                }
            else:
                current["lines"].append(line)
                current["end"] = ln
    if current is not None:
        blocks.append(current)
    return blocks


def is_navigation_block(block) -> bool:
    text = "\n".join(block["lines"]).strip()
    if not text:
        return True
    if block["path"].get("chapter") is None and len(text) < 200:
        return True
    toc_lines = re.findall(r"^\s*[-*]?\s*专题[一二三四五六七八九十百零〇\d]+", text, re.M)
    if len(toc_lines) >= 5:
        return True
    return False


def split_long_block(block, max_size=CHUNK_SIZE, overlap=OVERLAP):
    body = "\n".join(block["lines"]).strip()
    if len(body) <= max_size:
        return [body]

    head = ""
    body_lines = block["lines"]
    if body_lines and re.match(r"^#{1,5}\s+", body_lines[0]):
        head = body_lines[0].strip()
        body_lines = body_lines[1:]
    body_text = "\n".join(body_lines).strip()

    paragraphs = re.split(r"\n\n+", body_text)
    chunks = []
    cur = head + "\n\n" if head else ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(cur) + len(para) + 2 <= max_size:
            cur += para + "\n\n"
            continue

        if len(cur.strip()) >= MIN_CHUNK_SIZE:
            chunks.append(cur.strip())

        if len(para) > max_size:
            sentences = re.split(r"(?<=[。！？；])", para)
            cur2 = head + "\n\n" if head else ""
            for sent in sentences:
                if not sent:
                    continue
                if len(cur2) + len(sent) <= max_size:
                    cur2 += sent
                else:
                    if len(cur2.strip()) >= MIN_CHUNK_SIZE:
                        chunks.append(cur2.strip())
                    tail = cur2[-overlap:] if len(cur2) > overlap else ""
                    cur2 = (head + "\n\n" if head else "") + tail + sent
            cur = cur2 + "\n\n" if cur2.strip() else (head + "\n\n" if head else "")
        else:
            tail = cur[-overlap:] if len(cur) > overlap else ""
            cur = (head + "\n\n" if head else "") + tail + para + "\n\n"

    if len(cur.strip()) >= MIN_CHUNK_SIZE:
        chunks.append(cur.strip())
    return chunks


def force_split_text(text: str, max_size=CHUNK_SIZE, overlap=OVERLAP):
    if len(text) <= max_size:
        return [text]

    lines = text.split("\n")
    head = ""
    if lines and re.match(r"^#{1,5}\s+", lines[0].strip()):
        head = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        body = text.strip()

    prefix = head + "\n\n" if head else ""
    limit = max_size - len(prefix)
    if limit < 300:
        prefix = ""
        limit = max_size

    units = []
    for para in re.split(r"\n\n+", body):
        para = para.strip()
        if not para:
            continue
        if len(para) <= limit:
            units.append(para)
            continue

        sentences = [s.strip() for s in re.split(r"(?<=[。！？；])", para) if s.strip()]
        if len(sentences) <= 1:
            sentences = [s for s in para.split("\n") if s.strip()]

        for sent in sentences:
            sent = sent.strip()
            if len(sent) <= limit:
                units.append(sent)
                continue
            step = max(1, limit - overlap)
            for start in range(0, len(sent), step):
                piece = sent[start:start + limit].strip()
                if piece:
                    units.append(piece)

    chunks = []
    cur = prefix
    for unit in units:
        sep = "\n\n" if cur.strip() else ""
        if len(cur) + len(sep) + len(unit) <= max_size:
            cur = cur + sep + unit
            continue
        if cur.strip():
            chunks.append(cur.strip())
        cur = prefix + unit
        if len(cur) > max_size:
            chunks.append(cur[:max_size].strip())
            cur = prefix + cur[max_size - overlap:].strip()
    if cur.strip():
        chunks.append(cur.strip())

    return [c for c in chunks if len(c) >= MIN_CHUNK_SIZE]


def is_lone_title(text: str) -> bool:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) <= 2 and all(line.startswith("#") for line in lines):
        return True
    return len(text.strip()) < MIN_CHUNK_SIZE and text.lstrip().startswith("#")


def merge_lone_titles(chunks):
    merged = []
    i = 0
    while i < len(chunks):
        c = chunks[i]
        if is_lone_title(c["text"]) and i + 1 < len(chunks):
            nxt = chunks[i + 1]
            nxt["text"] = c["text"].strip() + "\n\n" + nxt["text"]
            nxt["metadata"]["source_line_start"] = c["metadata"]["source_line_start"]
            nxt["metadata"]["char_count"] = len(nxt["text"])
            merged.append(nxt)
            i += 2
        else:
            merged.append(c)
            i += 1
    return merged


def safe_part(s: str | None, limit=12) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[\\/:*?\"<>|]", "", s)
    return s[:limit]


def make_chunk_id(meta, idx):
    parts = ["民法"]
    for key, limit in [("chapter", 14), ("section", 12), ("subsection", 12)]:
        value = safe_part(meta.get(key), limit)
        if value:
            parts.append(value)
    parts.append(f"{idx:04d}")
    return "::".join(parts)


def build_chunks(blocks):
    chunks = []
    for blk in blocks:
        if is_navigation_block(blk):
            continue
        for sub_text in split_long_block(blk):
            path = blk["path"]
            meta = {
                "book": BOOK,
                "doc_type": DOC_TYPE,
                "part": infer_part_from_chapter(path.get("chapter"), path.get("part")),
                "chapter": path.get("chapter"),
                "section": path.get("section"),
                "subsection": path.get("subsection"),
                "source_line_start": blk["start"],
                "source_line_end": blk["end"],
                "char_count": len(sub_text),
            }
            chunks.append({
                "id": "",
                "text": sub_text,
                "metadata": meta,
            })

    chunks = merge_lone_titles(chunks)

    final = []
    for c in chunks:
        if c["metadata"]["char_count"] <= 1000:
            final.append(c)
            continue
        pieces = force_split_text(c["text"])
        if len(pieces) <= 1:
            final.append(c)
            continue
        for piece in pieces:
            new_c = deepcopy(c)
            new_c["text"] = piece
            new_c["metadata"]["char_count"] = len(piece)
            final.append(new_c)

    for i, c in enumerate(final, start=1):
        c["chunk_index"] = i
        c["id"] = make_chunk_id(c["metadata"], i)
    return final


def print_stats(chunks):
    sizes = [len(c["text"]) for c in chunks]
    print(f"输出：{DST}")
    print(f"块数：{len(chunks)}")
    print(f"平均字符：{sum(sizes) / len(sizes):.0f}")
    print(f"最大：{max(sizes)}")
    print(f"最小：{min(sizes)}")
    buckets = {"<200": 0, "200-400": 0, "400-600": 0, "600-800": 0, "800-1000": 0, ">1000": 0}
    for size in sizes:
        if size < 200:
            buckets["<200"] += 1
        elif size < 400:
            buckets["200-400"] += 1
        elif size < 600:
            buckets["400-600"] += 1
        elif size < 800:
            buckets["600-800"] += 1
        elif size < 1000:
            buckets["800-1000"] += 1
        else:
            buckets[">1000"] += 1
    print("分布：")
    for key, value in buckets.items():
        print(f"  {key}: {value}")

    chapter_count = len({c["metadata"].get("chapter") for c in chunks if c["metadata"].get("chapter")})
    print(f"覆盖专题数：{chapter_count}")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    parsed = parse_headings(text)
    blocks = split_into_blocks(parsed)
    chunks = build_chunks(blocks)

    with DST.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print_stats(chunks)


if __name__ == "__main__":
    main()
