#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""民诉真金题二次清洗版切块脚本。"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "民诉真金题_二次清洗版.md"
DST = PROJECT_ROOT / "切块" / "民诉真金题_chunks.jsonl"

BOOK = "民诉真金题（二次清洗版）"
DOC_TYPE = "真题解析"
TARGET_SIZE = 800
SOFT_LIMIT = 950
MAX_CHUNK_SIZE = 1100
MIN_CHUNK_SIZE = 80
OVERLAP = 90

MAIN_LABELS = ("【题干】", "【选项】", "【解析】", "【答案】")
SUPPLEMENTARY_LABELS = (
    "【背下来】",
    "【命题思路】",
    "【深度拓展】",
    "【举一反三】",
    "【脚注】",
    "【总结】",
    "【原理与逻辑】",
    "【注意】",
    "【待复核】",
)
ALL_LABELS = MAIN_LABELS + SUPPLEMENTARY_LABELS
QUESTION_TYPE_MAP = {
    "单": "单选",
    "多": "多选",
    "不定项": "不定项",
    "任": "案例题",
    "主": "主观题",
}


def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def slugify_title(title: str, max_len: int = 18) -> str:
    compact = re.sub(r"\s+", "", title)
    compact = compact.replace("：", "").replace(":", "")
    compact = compact.replace("（", "").replace("）", "")
    return compact[:max_len] or "未命名"


def make_global_id(chapter: str, question_header: str, block_type: str, chunk_index: int, piece_index: int | None = None) -> str:
    chapter_slug = slugify_title(chapter)
    if piece_index is None:
        type_slug = block_type
    else:
        type_slug = f"{block_type}-{piece_index:02d}"
    return f"民诉真金题::{chapter_slug}::{question_header}::{type_slug}::{chunk_index:04d}"


def split_paragraph_text(text: str, max_size: int = TARGET_SIZE, overlap: int = OVERLAP) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            tail = current[-overlap:] if len(current) > overlap else current
            current = f"{tail}{para}".strip()
            if len(current) <= max_size:
                continue
            current = para

        if len(para) <= max_size:
            current = para
            continue

        sentence_chunks = split_sentence_text(para, max_size=max_size, overlap=overlap)
        if not sentence_chunks:
            continue
        chunks.extend(sentence_chunks[:-1])
        current = sentence_chunks[-1]

    if current.strip():
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk.strip()]


def split_sentence_text(text: str, max_size: int = TARGET_SIZE, overlap: int = OVERLAP) -> list[str]:
    sentences = [s for s in re.split(r"(?<=[。！？；])", text) if s]
    if not sentences:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    current = ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        candidate = current + sent
        if len(candidate) <= max_size:
            current = candidate
            continue
        if current:
            chunks.append(current.strip())
            tail = current[-overlap:] if len(current) > overlap else current
            current = (tail + sent).strip()
            if len(current) <= max_size:
                continue
            current = sent
        else:
            current = sent

        if len(current) > max_size:
            chunks.append(current[:max_size].strip())
            current = current[max(0, max_size - overlap):].strip()

    if current.strip():
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk.strip()]


def enforce_size(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= SOFT_LIMIT:
        return [text]

    pieces = split_paragraph_text(text)
    if not pieces:
        return [text]

    final: list[str] = []
    for piece in pieces:
        if len(piece) <= MAX_CHUNK_SIZE:
            final.append(piece)
        else:
            final.extend(split_sentence_text(piece))

    merged: list[str] = []
    for piece in final:
        if not merged:
            merged.append(piece)
            continue
        if len(piece) < MIN_CHUNK_SIZE and len(merged[-1]) + 2 + len(piece) <= MAX_CHUNK_SIZE:
            merged[-1] = f"{merged[-1]}\n\n{piece}".strip()
        else:
            merged.append(piece)
    return merged


def parse_exam_meta(stem_text: str) -> tuple[str | None, int | None, str | None]:
    compact = stem_text.replace(" ", "")
    compact = compact.replace("，", ",").replace("．", ".")
    compact = compact.replace("（", "(").replace("）", ")")

    exam_id = None
    exam_year = None
    question_type = None

    gold = re.search(r"(20\d{2}金题-\d-\d-\d{1,3}).{0,8}?(单|多|不定项)", compact)
    if gold:
        exam_id = gold.group(1)
        exam_year = int(gold.group(1)[:4])
        question_type = QUESTION_TYPE_MAP.get(gold.group(2))
        return exam_id, exam_year, question_type

    real = re.search(r"(20\d{2}-\d-\d{1,3}).{0,8}?(单|多|不定项)", compact)
    if real:
        exam_id = real.group(1)
        exam_year = int(real.group(1)[:4])
        question_type = QUESTION_TYPE_MAP.get(real.group(2))
        return exam_id, exam_year, question_type

    loose_year = re.search(r"(20\d{2})", compact)
    if loose_year:
        exam_year = int(loose_year.group(1))

    loose_type = re.search(r"(不定项|单|多)", compact)
    if loose_type:
        question_type = QUESTION_TYPE_MAP.get(loose_type.group(1))

    return exam_id, exam_year, question_type


def parse_answer(answer_text: str) -> str | None:
    answer = re.sub(r"[^A-D]", "", answer_text.upper())
    return answer or None


def parse_questions(text: str) -> tuple[list[dict], dict[str, int]]:
    lines = text.splitlines()
    current_topic = None
    current_section = None
    current_question: dict | None = None
    current_label: str | None = None
    current_content: list[str] = []
    stats = {"topics": 0, "questions": 0}
    questions: list[dict] = []

    def flush_label() -> None:
        nonlocal current_label, current_content, current_question
        if current_question is None or current_label is None:
            current_label = None
            current_content = []
            return
        current_question["labels"][current_label] = "\n".join(current_content).strip()
        current_question["label_line_end"][current_label] = current_question["current_line"]
        current_label = None
        current_content = []

    def flush_question() -> None:
        nonlocal current_question
        flush_label()
        if current_question is not None:
            questions.append(current_question)
        current_question = None

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("### 专题"):
            flush_question()
            current_topic = stripped[4:].strip()
            current_section = None
            stats["topics"] += 1
            continue

        if stripped.startswith("#### "):
            flush_question()
            current_section = stripped[5:].strip()
            continue

        if stripped.startswith("##### 第"):
            flush_question()
            stats["questions"] += 1
            current_question = {
                "header": stripped[6:].strip(),
                "chapter": current_topic,
                "section": current_section,
                "start_line": idx,
                "end_line": idx,
                "labels": {},
                "label_line_start": {},
                "label_line_end": {},
                "current_line": idx,
            }
            continue

        if current_question is None:
            continue

        current_question["end_line"] = idx
        current_question["current_line"] = idx

        label_match = None
        for label in ALL_LABELS:
            if stripped.startswith(label):
                label_match = label
                break

        if label_match:
            flush_label()
            current_label = label_match
            current_question["label_line_start"][label_match] = idx
            remainder = stripped[len(label_match):].strip()
            current_content = [remainder] if remainder else []
            continue

        if current_label is not None:
            current_content.append(line)

    flush_question()
    return questions, stats


def build_main_segments(question: dict) -> list[tuple[str, int, int]]:
    segments: list[tuple[str, int, int]] = []
    for label in MAIN_LABELS:
        content = question["labels"].get(label)
        if not content:
            continue
        start = question["label_line_start"].get(label, question["start_line"])
        end = question["label_line_end"].get(label, question["end_line"])
        segments.append((f"{label}\n{content}".strip(), start, end))
    return segments


def compose_main_text(question: dict, segment_slice: list[tuple[str, int, int]], piece_index: int | None = None, total_pieces: int | None = None) -> str:
    title_lines = [
        f"### {question['chapter']}",
        f"#### {question['section']}" if question["section"] else None,
        f"##### {question['header']}",
    ]
    title = "\n\n".join(line for line in title_lines if line)
    body = "\n\n".join(text for text, _, _ in segment_slice if text.strip())
    if piece_index is not None and total_pieces and total_pieces > 1:
        body = f"【分片】主块 {piece_index}/{total_pieces}\n\n{body}"
    return f"{title}\n\n{body}".strip()


def split_main_question(question: dict) -> list[dict]:
    segments = build_main_segments(question)
    if not segments:
        return []

    assembled = compose_main_text(question, segments)
    if len(assembled) <= SOFT_LIMIT:
        return [{
            "text": assembled,
            "line_start": min(seg[1] for seg in segments),
            "line_end": max(seg[2] for seg in segments),
            "piece_index": None,
        }]

    groups: list[list[tuple[str, int, int]]] = []
    current: list[tuple[str, int, int]] = []
    for seg in segments:
        trial = current + [seg]
        if not current or len(compose_main_text(question, trial)) <= SOFT_LIMIT:
            current = trial
        else:
            groups.append(current)
            current = [seg]
    if current:
        groups.append(current)

    output: list[dict] = []
    for group in groups:
        full_text = compose_main_text(question, group)
        if len(full_text) <= MAX_CHUNK_SIZE:
            output.append({
                "text": full_text,
                "line_start": min(seg[1] for seg in group),
                "line_end": max(seg[2] for seg in group),
            })
            continue

        body_parts = enforce_size("\n\n".join(text for text, _, _ in group))
        start_line = min(seg[1] for seg in group)
        end_line = max(seg[2] for seg in group)
        total = len(body_parts)
        for idx, part in enumerate(body_parts, start=1):
            title_lines = [
                f"### {question['chapter']}",
                f"#### {question['section']}" if question["section"] else None,
                f"##### {question['header']}",
                f"【分片】主块 {idx}/{total}",
                part.strip(),
            ]
            output.append({
                "text": "\n\n".join(line for line in title_lines if line).strip(),
                "line_start": start_line,
                "line_end": end_line,
            })

    if len(output) <= 1:
        return [{**item, "piece_index": None} for item in output]

    for idx, item in enumerate(output, start=1):
        item["piece_index"] = idx
    return output


def build_supplementary_chunks(question: dict) -> list[dict]:
    chunks: list[dict] = []
    for label in SUPPLEMENTARY_LABELS:
        content = question["labels"].get(label)
        if not content:
            continue
        text_body = f"{label}\n{content}".strip()
        parts = enforce_size(text_body)
        start_line = question["label_line_start"].get(label, question["start_line"])
        end_line = question["label_line_end"].get(label, question["end_line"])
        for idx, part in enumerate(parts, start=1):
            title_lines = [
                f"### {question['chapter']}",
                f"#### {question['section']}" if question["section"] else None,
                f"##### {question['header']}",
            ]
            if len(parts) > 1:
                title_lines.append(f"【分片】{label} {idx}/{len(parts)}")
            title_lines.append(part.strip())
            chunks.append({
                "label": label,
                "text": "\n\n".join(line for line in title_lines if line).strip(),
                "line_start": start_line,
                "line_end": end_line,
                "piece_index": idx if len(parts) > 1 else None,
            })
    return chunks


def make_metadata_base(question: dict) -> dict:
    stem = question["labels"].get("【题干】", "")
    answer = parse_answer(question["labels"].get("【答案】", ""))
    exam_id, exam_year, question_type = parse_exam_meta(stem)
    question_number = int(re.sub(r"\D", "", question["header"]) or "0")
    return {
        "book": BOOK,
        "doc_type": DOC_TYPE,
        "chapter": question["chapter"],
        "section": question["section"],
        "subsection": question["header"],
        "question_index": question_number,
        "exam_id": exam_id,
        "exam_year": exam_year,
        "question_type": question_type,
        "answer": answer,
        "has_review_flag": "【待复核】" in question["labels"],
    }


def build_chunks(questions: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    chunk_index = 0

    for question in questions:
        meta_base = make_metadata_base(question)

        main_chunks = split_main_question(question)
        for item in main_chunks:
            chunk_index += 1
            metadata = deepcopy(meta_base)
            metadata.update({
                "subsub": "主块",
                "source_line_start": item["line_start"],
                "source_line_end": item["line_end"],
                "char_count": len(item["text"]),
            })
            chunks.append({
                "id": make_global_id(
                    chapter=question["chapter"] or "未知专题",
                    question_header=question["header"],
                    block_type="主块",
                    chunk_index=chunk_index,
                    piece_index=item.get("piece_index"),
                ),
                "text": item["text"],
                "metadata": metadata,
                "chunk_index": chunk_index,
            })

        supplementary_chunks = build_supplementary_chunks(question)
        for item in supplementary_chunks:
            chunk_index += 1
            metadata = deepcopy(meta_base)
            metadata.update({
                "subsub": item["label"].strip("【】"),
                "source_line_start": item["line_start"],
                "source_line_end": item["line_end"],
                "char_count": len(item["text"]),
            })
            chunks.append({
                "id": make_global_id(
                    chapter=question["chapter"] or "未知专题",
                    question_header=question["header"],
                    block_type=item["label"].strip("【】"),
                    chunk_index=chunk_index,
                    piece_index=item.get("piece_index"),
                ),
                "text": item["text"],
                "metadata": metadata,
                "chunk_index": chunk_index,
            })

    return chunks


def print_stats(questions: list[dict], chunks: list[dict], parse_stats: dict[str, int]) -> None:
    main_count = sum(1 for c in chunks if c["metadata"].get("subsub") == "主块")
    supp_count = len(chunks) - main_count
    sizes = [len(c["text"]) for c in chunks]
    print(f"专题数: {parse_stats['topics']}")
    print(f"题目数: {parse_stats['questions']}")
    print(f"总块数: {len(chunks)}")
    print(f"主块数: {main_count}")
    print(f"附属块数: {supp_count}")
    print(f"最大块长: {max(sizes) if sizes else 0}")
    print(f">950 字块数: {sum(1 for s in sizes if s > SOFT_LIMIT)}")
    print(f">1100 字块数: {sum(1 for s in sizes if s > MAX_CHUNK_SIZE)}")
    print(f"带待复核题数: {sum(1 for q in questions if '【待复核】' in q['labels'])}")


def main() -> None:
    text = clean_text(SRC.read_text(encoding="utf-8"))
    questions, parse_stats = parse_questions(text)
    chunks = build_chunks(questions)

    with DST.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print_stats(questions, chunks, parse_stats)
    print(f"输出文件: {DST}")


if __name__ == "__main__":
    main()
