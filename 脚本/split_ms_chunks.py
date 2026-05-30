#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""戴鹏民诉整理稿切块脚本。"""

import json
import re
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "戴鹏民诉_整理版.md"
DST = PROJECT_ROOT / "切块" / "戴鹏民诉_chunks.jsonl"

BOOK = "戴鹏《民诉》整理版"
DOC_TYPE = "教材"
CHUNK_SIZE = 800
OVERLAP = 100
MIN_CHUNK_SIZE = 80
MAX_CHUNK_SIZE = 1000
TOPIC_START_RE = re.compile(r"^###\s+专题一\b")
TOPIC_23_TITLE = "专题二十三 非讼程序之督促程序"
TOPIC_24_TITLE = "专题二十四 非讼程序之公示催告程序"


def preprocess_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("#bookmark", "")
    text = text.replace("{.underline}", "")
    text = re.sub(r"(?m)^[fｆF]\s*注意】", "【注意】", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = text.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if TOPIC_START_RE.match(line.strip()):
            start_idx = i
            break
    lines = lines[start_idx:]
    return "\n".join(lines).strip() + "\n"


def parse_headings(text: str):
    lines = text.split("\n")
    state = {
        "book": BOOK,
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


def repair_misplaced_supervision_blocks(blocks):
    def retag_topic23(block):
        block["path"]["chapter"] = TOPIC_23_TITLE
        if block["path"].get("section") and "遗产管理人" in block["path"]["section"]:
            block["path"]["section"] = None
        if block["path"].get("subsection") and (
            "实现担保物权" in block["path"]["subsection"] or
            (topic24_line and block["end"] >= topic24_line)
        ):
            block["path"]["subsection"] = None
        return block

    topic23_line = None
    topic24_line = None
    for block in blocks:
        title_line = block["lines"][0].strip() if block["lines"] else ""
        if title_line == f"### {TOPIC_23_TITLE}":
            topic23_line = block["start"]
        elif title_line == f"### {TOPIC_24_TITLE}":
            topic24_line = block["start"]

    if not topic23_line:
        return blocks

    repaired = []
    for block in blocks:
        if not (topic23_line - 160 <= block["start"] < topic23_line):
            repaired.append(block)
            continue
        text = "\n".join(block["lines"])
        if not re.search(r"督促程序|支付令", text):
            repaired.append(block)
            continue
        if block["path"].get("chapter") == TOPIC_23_TITLE:
            repaired.append(block)
            continue

        split_at = None
        if "实现担保物权" in text:
            for idx, line in enumerate(block["lines"]):
                if line.strip() == "【知识体系】":
                    suffix = "\n".join(block["lines"][idx:])
                    if re.search(r"督促程序|支付令", suffix):
                        split_at = idx

        if split_at:
            prefix_lines = block["lines"][:split_at]
            suffix_lines = block["lines"][split_at:]

            if prefix_lines:
                prefix_block = deepcopy(block)
                prefix_block["lines"] = prefix_lines
                prefix_block["end"] = prefix_block["start"] + len(prefix_lines) - 1
                repaired.append(prefix_block)

            if suffix_lines:
                suffix_block = deepcopy(block)
                suffix_block["lines"] = suffix_lines
                suffix_block["start"] = block["start"] + split_at
                suffix_block["path"] = dict(block["path"])
                retag_topic23(suffix_block)
                repaired.append(suffix_block)
            continue

        repaired.append(retag_topic23(block))

    return repaired


def is_navigation_block(block) -> bool:
    text = "\n".join(block["lines"]).strip()
    chapter = block["path"].get("chapter")

    if not text:
        return True
    if chapter is None and len(text) < 250:
        return True
    if "图书在版编目" in text or "中国国家版本馆" in text:
        return True
    if chapter and "目录" in chapter:
        return True

    topic_lines = re.findall(r"^\s*[-*]?\s*专题[一二三四五六七八九十百零〇\d]+", text, re.M)
    section_lines = re.findall(r"^\s*[-*]?\s*第[一二三四五六七八九十百零〇\d]+节", text, re.M)
    if len(topic_lines) >= 3 or len(section_lines) >= 5:
        return True
    return False


def normalize_compare_text(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^#{1,5}\s*", "", line)
    line = re.sub(r"^\s*>+\s*", "", line)
    line = re.sub(r"^\s*[-*]+\s*", "", line)
    line = re.sub(r"^\s*\d+[.、]\s*", "", line)
    line = re.sub(r"\s+", "", line)
    return line


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in {"专题+ ©证据", "续表", "> 续表"}:
        return True
    if re.fullmatch(r"[\|\+\-=\s]{3,}", stripped):
        return True
    if re.fullmatch(r"[.。·•\-—_=~^*#@]{6,}", stripped):
        return True
    if stripped.endswith(".........................................................................."):
        return True
    return False


def clean_chunk_text(text: str) -> str:
    text = text.replace("#bookmark", "")
    text = text.replace("{.underline}", "")
    text = re.sub(r"(?m)^[fｆF]\s*注意】", "【注意】", text)

    lines = text.splitlines()
    cleaned = []
    prev_norm = ""
    for line in lines:
        if is_noise_line(line):
            continue

        current = line.rstrip()
        norm = normalize_compare_text(current)
        if norm:
            if norm == prev_norm:
                continue
            if len(norm) >= 12 and prev_norm and norm in prev_norm:
                continue

        cleaned.append(current)
        if norm:
            prev_norm = norm

    compact = "\n".join(cleaned)
    compact = re.sub(r"\n{3,}", "\n\n", compact).strip()
    return compact


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

    parts = []
    current = []
    for para in re.split(r"\n\n+", body_text):
        para = para.strip()
        if not para:
            continue
        if re.match(r"^(?:\d+[.、]|[-*]|[（(]?[一二三四五六七八九十\d]+[)）]|【.+?】|\|)", para):
            if current:
                parts.append("\n\n".join(current))
                current = []
            parts.append(para)
        else:
            current.append(para)
    if current:
        parts.append("\n\n".join(current))

    chunks = []
    cur = head + "\n\n" if head else ""
    for part in parts:
        if len(cur) + len(part) + 2 <= max_size:
            cur += part + "\n\n"
            continue

        if len(cur.strip()) >= MIN_CHUNK_SIZE:
            chunks.append(cur.strip())

        if len(part) > max_size:
            sentences = [s for s in re.split(r"(?<=[。！？；])", part) if s]
            cur2 = head + "\n\n" if head else ""
            for sent in sentences:
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
            cur = (head + "\n\n" if head else "") + tail + part + "\n\n"

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
            sentences = [s.strip() for s in para.split("\n") if s.strip()]

        for sent in sentences:
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

    return [chunk for chunk in chunks if len(chunk) >= MIN_CHUNK_SIZE]


def is_lone_title(text: str) -> bool:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) <= 2 and all(line.startswith("#") for line in lines):
        return True
    return len(text.strip()) < MIN_CHUNK_SIZE and text.lstrip().startswith("#")


def trim_duplicate_heading_prefix(prev_text: str, next_text: str) -> str:
    prev_lines = prev_text.splitlines()
    next_lines = next_text.splitlines()
    if prev_lines and next_lines and prev_lines[0].strip() == next_lines[0].strip():
        next_lines = next_lines[1:]
        while next_lines and not next_lines[0].strip():
            next_lines.pop(0)
    return "\n".join(next_lines).strip()


def same_path(a, b) -> bool:
    keys = ("chapter", "section", "subsection")
    return all(a["metadata"].get(key) == b["metadata"].get(key) for key in keys)


def can_merge_title_with_next(current, nxt) -> bool:
    curr_meta = current["metadata"]
    next_meta = nxt["metadata"]

    if curr_meta.get("chapter") != next_meta.get("chapter"):
        return False

    if curr_meta.get("section") is None and curr_meta.get("subsection") is None:
        return True
    if curr_meta.get("section") is not None and curr_meta.get("subsection") is None:
        return curr_meta.get("section") == next_meta.get("section")
    return same_path(current, nxt)


def merge_lone_titles(chunks):
    merged = []
    i = 0
    while i < len(chunks):
        current = chunks[i]
        if is_lone_title(current["text"]) and i + 1 < len(chunks) and can_merge_title_with_next(current, chunks[i + 1]):
            nxt = chunks[i + 1]
            nxt["text"] = current["text"].strip() + "\n\n" + nxt["text"]
            nxt["metadata"]["source_line_start"] = current["metadata"]["source_line_start"]
            nxt["metadata"]["char_count"] = len(nxt["text"])
            merged.append(nxt)
            i += 2
        else:
            merged.append(current)
            i += 1
    return merged


def merge_small_neighbors(chunks, threshold=120, max_size=980):
    merged = []
    i = 0
    while i < len(chunks):
        current = deepcopy(chunks[i])
        while i + 1 < len(chunks):
            nxt = chunks[i + 1]
            if not same_path(current, nxt):
                break

            current_len = len(current["text"].strip())
            nxt_len = len(nxt["text"].strip())
            if current_len >= threshold and nxt_len >= threshold and not is_lone_title(current["text"]):
                break

            nxt_text = trim_duplicate_heading_prefix(current["text"], nxt["text"])
            candidate = (current["text"].strip() + "\n\n" + nxt_text).strip()
            if len(candidate) > max_size:
                break

            current["text"] = candidate
            current["metadata"]["source_line_end"] = max(
                current["metadata"]["source_line_end"],
                nxt["metadata"]["source_line_end"],
            )
            current["metadata"]["char_count"] = len(current["text"])
            i += 1
        merged.append(current)
        i += 1
    return merged


def drop_pure_title_chunks(chunks):
    return [chunk for chunk in chunks if not is_lone_title(chunk["text"])]


def safe_part(s: str | None, limit=12) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[\\/:*?\"<>|]", "", s)
    return s[:limit]


def make_chunk_id(meta, idx):
    parts = ["民诉"]
    for key, limit in (("chapter", 14), ("section", 14), ("subsection", 12)):
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
            text = clean_chunk_text(sub_text)
            if not text:
                continue
            path = blk["path"]
            meta = {
                "book": path.get("book") or BOOK,
                "doc_type": DOC_TYPE,
                "chapter": path.get("chapter"),
                "section": path.get("section"),
                "subsection": path.get("subsection"),
                "source_line_start": blk["start"],
                "source_line_end": blk["end"],
                "char_count": len(text),
            }
            chunks.append({
                "id": "",
                "text": text,
                "metadata": meta,
            })

    chunks = merge_lone_titles(chunks)

    final = []
    for chunk in chunks:
        if chunk["metadata"]["char_count"] <= MAX_CHUNK_SIZE:
            final.append(chunk)
            continue
        pieces = force_split_text(chunk["text"])
        if len(pieces) <= 1:
            final.append(chunk)
            continue
        for piece in pieces:
            piece = clean_chunk_text(piece)
            if not piece:
                continue
            new_chunk = deepcopy(chunk)
            new_chunk["text"] = piece
            new_chunk["metadata"]["char_count"] = len(piece)
            final.append(new_chunk)

    final = merge_lone_titles(final)
    final = merge_small_neighbors(final)
    final = drop_pure_title_chunks(final)
    final = [chunk for chunk in final if chunk["text"].strip()]

    for chunk in final:
        chunk["text"] = clean_chunk_text(chunk["text"])
        chunk["metadata"]["char_count"] = len(chunk["text"])

    final = [chunk for chunk in final if chunk["text"].strip()]
    for i, chunk in enumerate(final, start=1):
        chunk["chunk_index"] = i
        chunk["id"] = make_chunk_id(chunk["metadata"], i)
    return final


def print_stats(chunks):
    sizes = [len(chunk["text"]) for chunk in chunks]
    print(f"输出: {DST}")
    print(f"块数: {len(chunks)}")
    print(f"平均字符: {sum(sizes) / len(sizes):.0f}")
    print(f"最大块: {max(sizes)}")
    print(f"最小块: {min(sizes)}")
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
        elif size <= 1000:
            buckets["800-1000"] += 1
        else:
            buckets[">1000"] += 1
    print("分布:")
    for key, value in buckets.items():
        print(f"  {key}: {value}")

    chapter_count = len({c["metadata"].get("chapter") for c in chunks if c["metadata"].get("chapter")})
    print(f"覆盖专题数: {chapter_count}")


def main():
    text = preprocess_text(SRC.read_text(encoding="utf-8"))
    parsed = parse_headings(text)
    blocks = split_into_blocks(parsed)
    blocks = repair_misplaced_supervision_blocks(blocks)
    chunks = build_chunks(blocks)

    with DST.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print_stats(chunks)


if __name__ == "__main__":
    main()
