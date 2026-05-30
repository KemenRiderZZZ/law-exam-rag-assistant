#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""杨帆三国法二次清洗版切块脚本。"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "杨帆三国法_二次清洗版.md"
DST = PROJECT_ROOT / "切块" / "杨帆三国法_chunks.jsonl"

BOOK = "杨帆三国法专题讲座精讲卷（2026版）"
DOC_TYPE = "教材"
CHUNK_SIZE = 800
OVERLAP = 100
MIN_CHUNK_SIZE = 80
MAX_CHUNK_SIZE = 1000

HEADING_RE = re.compile(r"^(#{1,5})\s+(.+?)\s*$")
TITLE_ONLY_RE = re.compile(r"^#{1,5}\s+")
NOISE_LINE_RE = re.compile(r"^[\|\+\-=\s]{3,}$")
PAGE_NOISE_RE = re.compile(r"^[^\u4e00-\u9fffA-Za-z0-9]{0,2}\s*\d*\s*\^\d+\^$")
SHORT_PAGE_NOISE_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z»]{0,2}\s*\^\d+\^$")

MARKER_LABELS = {
    "【技术流】",
    "【易混辨析】",
    "【关联法条】",
    "【经典真题】",
    "【待复核】",
}
REVIEW_LABEL = "【专题重点回顾】"

PART_ALIAS = {
    "第一编": "第一编 国际法",
    "第二编": "第二编 国际私法",
}

PART_TOPIC_MAP = {
    "第一编 国际法": "专题一 导论",
    "第二编 国际私法": "专题一 国际私法概述",
}

TOPIC_ANCHORS = {
    "第一编 国际法": [
        ("#### 第一节 国际法概述", "专题一 导论"),
        ("#### 第一节 国际法主体", "专题二 国际法主体和国际法律责任"),
        ("#### 第一节 领土制度", "专题三 国际法上的空间划分"),
        ("#### 第一节 《中华人民共和国国籍法》", "专题四 国际法上的个人"),
        ("#### 第一节 外交关系和领事关系", "专题五 外交关系法和领事关系法"),
        ("#### 第一节 条约法概述", "专题六 条约法"),
        ("#### 第一节 国际争端的强制性解决方式", "专题七 国际争端的解决方式"),
        ("#### 第一节 战争的开始", "专题八 战争和武装冲突法"),
    ],
    "第二编 国际私法": [
        ("##### 一、国际私法的调整对象", "专题一 国际私法概述"),
        ("#### 第一节 冲突规范和准据法", "专题二 冲突规范"),
        ("#### 第一节 民商事法律适用的原则", "专题三 国际民商事法律适用"),
        ("#### 第一节 国际商事仲裁", "专题四 国际民商事争议的解决"),
        ("#### 第一节 国际司法协助", "专题五 司法协助"),
    ],
    "第三编 国际经济法": [
        ("##### 一、国际经济法的调整对象", "专题一 导论"),
        ("#### 第一节 《国际贸易术语解释通则》", "专题二 国际货物买卖法"),
        ("#### 第一节 国际海上货物运输法", "专题三 国际货物运输与保险法"),
        ("#### 第一节 银行托收", "专题四 国际贸易支付"),
        ("#### 第一节 《出口管制法》", "专题五 对外贸易管理制度"),
        ("#### 第一节 概述", "专题六 世界贸易组织（WTO）"),
        ("#### 第一节 知识产权的国际保护", "专题七 国际经济领域的其他法律制度"),
    ],
}


def normalize_book_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def inject_missing_topics(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    current_part = ""
    seen_topics: set[str] = set()

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current_part = PART_ALIAS.get(stripped[3:].strip(), stripped[3:].strip()) if stripped in {"## 第一编", "## 第二编"} else stripped[3:].strip()
            if stripped == "## 第三编 国际经济法":
                current_part = "第三编 国际经济法"
            seen_topics = set()
            out.append(raw_line)
            continue

        if stripped.startswith("### "):
            title = stripped[4:].strip()
            seen_topics.add(title)
            out.append(raw_line)
            continue

        anchors = TOPIC_ANCHORS.get(current_part, [])
        inserted = False
        for anchor, topic in anchors:
            if stripped == anchor and topic not in seen_topics:
                if out and out[-1].strip():
                    out.append("")
                out.append(f"### {topic}")
                out.append("")
                seen_topics.add(topic)
                inserted = True
                break
        out.append(raw_line)

    return "\n".join(out)


def normalize_heading_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r"\s+", " ", title)
    return title


def parse_headings(text: str):
    lines = text.split("\n")
    state = {
        "book": BOOK,
        "chapter": None,
        "section": None,
        "subsection": None,
        "subsub": None,
    }
    pending_part: str | None = None
    parsed = []

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        match = HEADING_RE.match(stripped)

        if match:
            level = len(match.group(1))
            title = normalize_heading_title(match.group(2))

            if level == 1:
                state["book"] = title or BOOK
                state["chapter"] = None
                state["section"] = None
                state["subsection"] = None
                state["subsub"] = None
                pending_part = None
            elif level == 2:
                pending_part = PART_ALIAS.get(title, title)
                state["chapter"] = pending_part
                state["section"] = None
                state["subsection"] = None
                state["subsub"] = None
            elif level == 3:
                section_title = title
                if pending_part:
                    state["chapter"] = pending_part
                state["section"] = section_title
                state["subsection"] = None
                state["subsub"] = None
            elif level == 4:
                if pending_part and not state["section"]:
                    state["chapter"] = pending_part
                    state["section"] = PART_TOPIC_MAP.get(pending_part)
                state["subsection"] = title
                state["subsub"] = None
            elif level == 5:
                if pending_part and not state["section"]:
                    state["chapter"] = pending_part
                    state["section"] = PART_TOPIC_MAP.get(pending_part)
                state["subsub"] = title

            parsed.append((i, stripped, dict(state)))
            continue

        if pending_part and stripped and not state["section"]:
            alias = PART_ALIAS.get(stripped)
            if alias and alias == pending_part:
                parsed.append((i, "", dict(state)))
                continue

        if pending_part and stripped and not state["section"]:
            state["chapter"] = pending_part
            state["section"] = PART_TOPIC_MAP.get(pending_part)

        parsed.append((i, stripped, dict(state)))

    return parsed


def split_into_blocks(parsed):
    blocks = []
    current = None
    for ln, line, state in parsed:
        if HEADING_RE.match(line):
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


def normalize_compare_text(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^#{1,5}\s*", "", line)
    line = re.sub(r"^\s*>+\s*", "", line)
    line = re.sub(r"^\s*[-*]+\s*", "", line)
    line = re.sub(r"^\s*\d+[.、]\s*", "", line)
    line = re.sub(r"^\s*[（(]?[一二三四五六七八九十百零〇\d]+[)）]\s*", "", line)
    line = re.sub(r"\s+", "", line)
    return line


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in {"---", "j", "J", "I", "|", "||", "\\|"}:
        return True
    if stripped.startswith("> 二次清洗说明："):
        return True
    if stripped in MARKER_LABELS:
        return False
    if stripped == REVIEW_LABEL:
        return False
    if NOISE_LINE_RE.fullmatch(stripped):
        return True
    if re.fullmatch(r"[.。·•\-—_=~^*#@]{6,}", stripped):
        return True
    if PAGE_NOISE_RE.fullmatch(stripped) or SHORT_PAGE_NOISE_RE.fullmatch(stripped):
        return True
    return False


def is_navigation_block(block) -> bool:
    text = "\n".join(line for line in block["lines"] if line.strip()).strip()
    if not text:
        return True

    first = block["lines"][0].strip() if block["lines"] else ""
    if first.startswith("# ") and BOOK in first:
        return True
    if first.startswith("> 二次清洗说明："):
        return True
    if first == REVIEW_LABEL:
        return True
    if block["path"].get("chapter") is None and len(text) < 180:
        return True

    topic_lines = re.findall(r"^\s*[-*]?\s*专题[一二三四五六七八九十百零〇\d]+", text, re.M)
    section_lines = re.findall(r"^\s*[-*]?\s*第[一二三四五六七八九十百零〇\d]+节", text, re.M)
    if len(topic_lines) >= 4 or len(section_lines) >= 6:
        return True
    return False


def trim_review_block(lines: list[str]) -> list[str]:
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped == REVIEW_LABEL:
            skipping = True
            continue
        if skipping:
            if stripped.startswith("#"):
                skipping = False
                out.append(line)
            continue
        out.append(line)
    return out


def clean_chunk_text(text: str) -> str:
    lines = trim_review_block(text.splitlines())
    cleaned = []
    prev_norm = ""

    for line in lines:
        if is_noise_line(line):
            continue

        current = line.rstrip()
        if not current.strip():
            cleaned.append("")
            continue

        if current.strip().startswith("## "):
            heading = normalize_heading_title(re.sub(r"^##\s+", "", current.strip()))
            current = f"## {PART_ALIAS.get(heading, heading)}"
        elif current.strip().startswith("#"):
            current = re.sub(
                r"^(#{1,5}\s+)(.+)$",
                lambda m: m.group(1) + normalize_heading_title(m.group(2)),
                current.strip(),
            )

        norm = normalize_compare_text(current)
        if norm:
            if norm == prev_norm:
                continue
            if len(norm) >= 12 and prev_norm and norm in prev_norm:
                continue
            if len(norm) >= 12 and prev_norm and prev_norm in norm and cleaned:
                cleaned.pop()

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
    if body_lines and TITLE_ONLY_RE.match(body_lines[0].strip()):
        head = body_lines[0].strip()
        body_lines = body_lines[1:]
    body_text = "\n".join(body_lines).strip()

    parts = []
    current = []
    for para in re.split(r"\n\n+", body_text):
        para = para.strip()
        if not para:
            continue
        if re.match(r"^(?:\d+[.、]|[-*]|[（(]?[一二三四五六七八九十百零〇\d]+[)）]|【.+?】|\|)", para):
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
    if lines and TITLE_ONLY_RE.match(lines[0].strip()):
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
    keys = ("chapter", "section", "subsection", "subsub")
    return all(a["metadata"].get(key) == b["metadata"].get(key) for key in keys)


def same_parent_path(a, b) -> bool:
    keys = ("chapter", "section", "subsection")
    return all(a["metadata"].get(key) == b["metadata"].get(key) for key in keys)


def merge_lone_titles(chunks):
    merged = []
    i = 0
    while i < len(chunks):
        current = chunks[i]
        if is_lone_title(current["text"]) and i + 1 < len(chunks):
            nxt = chunks[i + 1]
            if same_path(current, nxt):
                nxt["text"] = current["text"].strip() + "\n\n" + nxt["text"]
                nxt["metadata"]["source_line_start"] = current["metadata"]["source_line_start"]
                nxt["metadata"]["char_count"] = len(nxt["text"])
                merged.append(nxt)
                i += 2
                continue
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


def merge_tiny_sibling_chunks(chunks, threshold=MIN_CHUNK_SIZE, max_size=980):
    merged = []
    i = 0
    while i < len(chunks):
        current = deepcopy(chunks[i])
        while i + 1 < len(chunks):
            nxt = chunks[i + 1]
            if not same_parent_path(current, nxt):
                break

            current_len = len(current["text"].strip())
            next_len = len(nxt["text"].strip())
            if current_len >= threshold and next_len >= threshold:
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

            if current["metadata"].get("subsub") != nxt["metadata"].get("subsub"):
                current["metadata"]["subsub"] = None
            if current["metadata"].get("subsection") != nxt["metadata"].get("subsection"):
                current["metadata"]["subsection"] = None
                current["metadata"]["subsub"] = None

            i += 1
        merged.append(current)
        i += 1
    return merged


def safe_part(text: str | None, limit=14) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[\\/:*?\"<>|]", "", text)
    return text[:limit]


def make_chunk_id(meta, idx):
    parts = ["三国法"]
    for key, limit in (("chapter", 14), ("section", 14), ("subsection", 12), ("subsub", 12)):
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
            if not text or REVIEW_LABEL in text:
                continue
            path = blk["path"]
            meta = {
                "book": BOOK,
                "doc_type": DOC_TYPE,
                "chapter": path.get("chapter"),
                "section": path.get("section"),
                "subsection": path.get("subsection"),
                "subsub": path.get("subsub"),
                "source_line_start": blk["start"],
                "source_line_end": blk["end"],
                "char_count": len(text),
            }
            chunks.append({
                "id": "",
                "text": text,
                "metadata": meta,
            })

    chunks = [c for c in chunks if c["text"].strip()]
    chunks = merge_lone_titles(chunks)

    final = []
    for chunk in chunks:
        if len(chunk["text"]) <= MAX_CHUNK_SIZE:
            final.append(chunk)
            continue
        pieces = force_split_text(chunk["text"])
        if len(pieces) <= 1:
            final.append(chunk)
            continue
        for piece in pieces:
            new_chunk = deepcopy(chunk)
            new_chunk["text"] = clean_chunk_text(piece)
            new_chunk["metadata"]["char_count"] = len(new_chunk["text"])
            final.append(new_chunk)

    final = merge_lone_titles(final)
    final = merge_small_neighbors(final)
    final = merge_tiny_sibling_chunks(final)
    for chunk in final:
        chunk["text"] = clean_chunk_text(chunk["text"])
        chunk["metadata"]["char_count"] = len(chunk["text"])

    output = []
    for chunk in final:
        text = chunk["text"].strip()
        if not text:
            continue
        if is_lone_title(text):
            continue
        if REVIEW_LABEL in text:
            continue
        output.append(chunk)

    for idx, chunk in enumerate(output, start=1):
        chunk["chunk_index"] = idx
        chunk["id"] = make_chunk_id(chunk["metadata"], idx)
    return output


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
    section_count = len({c["metadata"].get("section") for c in chunks if c["metadata"].get("section")})
    print(f"覆盖编数：{chapter_count}")
    print(f"覆盖专题数：{section_count}")


def main() -> None:
    text = normalize_book_text(SRC.read_text(encoding="utf-8"))
    text = inject_missing_topics(text)
    parsed = parse_headings(text)
    blocks = split_into_blocks(parsed)
    chunks = build_chunks(blocks)

    with DST.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print_stats(chunks)


if __name__ == "__main__":
    main()
