#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""郄鹏恩商经知真金题二次清洗版切块脚本。"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知真金题_二次清洗版.md"
DST = PROJECT_ROOT / "切块" / "郄鹏恩商经知真金题_chunks.jsonl"

BOOK = "郄鹏恩商经知真金题卷（2026版）"
DOC_TYPE = "真题解析"
SOURCE_STAGE = "二次清洗版"
TARGET_SIZE = 800
SOFT_LIMIT = 950
MAX_CHUNK_SIZE = 1100
MIN_CHUNK_SIZE = 80
OVERLAP = 90

MAIN_LABELS = (
    "【题干信息解读】",
    "【题支逐项解析】",
)
SUPPLEMENTARY_LABELS = (
    "【命题陷阱】",
    "【总结与归纳】",
    "【背下来】",
    "【图片整理】",
    "【角度拓展】",
    "【命题规律】",
    "【常见错误分析】",
    "【脚注】",
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
OPTION_RE = re.compile(r"^[A-D][.．、]\s*")
QUESTION_RE = re.compile(r"^(\d+)[.．、]\s*(.+)$")


def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def slugify_title(title: str, max_len: int = 24) -> str:
    compact = re.sub(r"\s+", "", title)
    compact = compact.replace("：", "").replace(":", "")
    compact = compact.replace("（", "").replace("）", "")
    compact = compact.replace("【", "").replace("】", "")
    compact = compact.replace("/", "")
    return compact[:max_len] or "未命名"


def make_global_id(part: str, topic: str, point: str, question_header: str, block_type: str, chunk_index: int, piece_index: int | None = None) -> str:
    part_slug = slugify_title(part)
    topic_slug = slugify_title(topic)
    point_slug = slugify_title(point)
    if piece_index is None:
        type_slug = block_type
    else:
        type_slug = f"{block_type}-{piece_index:02d}"
    return f"商经知真金题::{part_slug}::{topic_slug}::{point_slug}::{question_header}::{type_slug}::{chunk_index:04d}"


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
    compact = compact.replace("①", "1")

    exam_id = None
    exam_year = None
    question_type = None

    gold = re.search(r"(20\d{2}金题-\d-\d-\d{1,3}).{0,8}?(单|多|不定项|任|主)", compact)
    if gold:
        exam_id = gold.group(1)
        exam_year = int(gold.group(1)[:4])
        question_type = QUESTION_TYPE_MAP.get(gold.group(2))
        return exam_id, exam_year, question_type

    real = re.search(r"(20\d{2}-\d-\d{1,3}).{0,8}?(单|多|不定项|任|主)", compact)
    if real:
        exam_id = real.group(1)
        exam_year = int(real.group(1)[:4])
        question_type = QUESTION_TYPE_MAP.get(real.group(2))
        return exam_id, exam_year, question_type

    loose_year = re.search(r"(20\d{2})", compact)
    if loose_year:
        exam_year = int(loose_year.group(1))

    loose_type = re.search(r"(不定项|单|多|任|主)", compact)
    if loose_type:
        question_type = QUESTION_TYPE_MAP.get(loose_type.group(1))

    return exam_id, exam_year, question_type


def parse_answer(text: str) -> str | None:
    matches = re.findall(r"答案为\s*([A-D]{1,4})", text)
    if not matches:
        matches = re.findall(r"答案\s*[:：]?\s*([A-D]{1,4})", text)
    if not matches:
        return None
    answer = re.sub(r"[^A-D]", "", matches[-1].upper())
    return answer or None


def is_preface_heading(line: str) -> bool:
    return line.strip() == "## 前言与使用说明"


def parse_questions(text: str) -> tuple[list[dict], dict[str, int]]:
    lines = text.splitlines()
    current_part = None
    current_topic = None
    current_section = None
    current_point = None
    current_question: dict | None = None
    current_label: str | None = None
    current_content: list[str] = []
    stats = {"parts": 0, "topics": 0, "points": 0, "questions": 0}
    questions: list[dict] = []
    in_preface = False

    def flush_label() -> None:
        nonlocal current_label, current_content, current_question
        if current_question is None or current_label is None:
            current_label = None
            current_content = []
            return
        content = "\n".join(current_content).strip()
        if content:
            old = current_question["labels"].get(current_label, "").strip()
            if old:
                current_question["labels"][current_label] = f"{old}\n\n{content}".strip()
            else:
                current_question["labels"][current_label] = content
            current_question["label_line_end"][current_label] = max(
                current_question["label_line_end"].get(current_label, 0),
                current_question["current_line"],
            )
        current_label = None
        current_content = []

    def flush_question() -> None:
        nonlocal current_question
        flush_label()
        if current_question is not None:
            if not current_question["stem"].strip():
                current_question = None
                return
            questions.append(current_question)
        current_question = None

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        stripped = line.strip()

        if is_preface_heading(stripped):
            in_preface = True
            continue

        if stripped.startswith("## "):
            flush_question()
            if stripped == "## 前言与使用说明":
                in_preface = True
                current_part = None
                continue
            in_preface = False
            current_part = stripped[3:].strip()
            current_topic = None
            current_section = None
            current_point = None
            stats["parts"] += 1
            continue

        if in_preface:
            continue

        if stripped.startswith("### PROJECT"):
            flush_question()
            current_topic = stripped[4:].strip()
            current_section = None
            current_point = None
            stats["topics"] += 1
            continue

        if stripped.startswith("#### "):
            flush_question()
            current_section = stripped[5:].strip()
            current_point = None
            continue

        if stripped.startswith("##### "):
            flush_question()
            current_point = stripped[6:].strip()
            stats["points"] += 1
            continue

        question_match = QUESTION_RE.match(stripped)
        if question_match and current_point:
            flush_question()
            stats["questions"] += 1
            q_num = int(question_match.group(1))
            current_question = {
                "number": q_num,
                "header": f"第{q_num:03d}题",
                "part": current_part,
                "chapter": current_topic,
                "section": current_section,
                "point": current_point,
                "start_line": idx,
                "end_line": idx,
                "stem": stripped,
                "options": [],
                "labels": {},
                "answer_line": None,
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
            current_question["label_line_start"].setdefault(label_match, idx)
            tail = stripped[len(label_match):].strip()
            current_content = [tail] if tail else []
            continue

        if current_label is not None:
            current_content.append(line)
            continue

        if OPTION_RE.match(stripped):
            current_question["options"].append(stripped)
            continue

        if stripped.startswith("综上，本题") or stripped.startswith("综上所述"):
            current_question["answer_line"] = stripped
            continue

        if current_question["options"]:
            current_question["stem"] += "\n" + stripped
        else:
            current_question["stem"] += ("\n" if current_question["stem"] else "") + stripped

    flush_question()
    return questions, stats


def make_heading_context(question: dict) -> str:
    parts = [
        f"## {question['part']}",
        f"### {question['chapter']}",
    ]
    if question.get("section"):
        parts.append(f"#### {question['section']}")
    parts.extend([
        f"##### {question['point']}",
        f"###### {question['header']}",
    ])
    return "\n\n".join(parts)


def split_main_question(question: dict) -> list[dict]:
    context = make_heading_context(question)
    parts = [context]
    parts.append("【题干】")
    parts.append(question["stem"].strip())
    if question["options"]:
        parts.append("【选项】")
        parts.append("\n".join(question["options"]).strip())
    for label in MAIN_LABELS:
        content = question["labels"].get(label, "").strip()
        if content:
            parts.append(label)
            parts.append(content)
    answer_line = (question.get("answer_line") or "").strip()
    if answer_line:
        parts.append("【答案】")
        parts.append(answer_line)

    text = "\n\n".join(part for part in parts if part).strip()
    pieces = enforce_size(text)
    if len(pieces) == 1:
        return [{
            "text": pieces[0],
            "line_start": question["start_line"],
            "line_end": question["end_line"],
            "piece_index": None,
        }]

    out = []
    for idx, piece in enumerate(pieces, start=1):
        piece_text = piece
        if idx > 1 and not piece.startswith("## "):
            piece_text = f"{context}\n\n{piece}".strip()
        out.append({
            "text": piece_text,
            "line_start": question["start_line"],
            "line_end": question["end_line"],
            "piece_index": idx,
        })
    return out


def should_split_supplementary(label: str, content: str) -> bool:
    if label in {"【命题陷阱】", "【总结与归纳】", "【图片整理】", "【角度拓展】"}:
        return True
    if len(content) >= 220:
        return True
    return False


def build_supplementary_chunks(question: dict) -> list[dict]:
    chunks: list[dict] = []
    context = make_heading_context(question)
    for label in SUPPLEMENTARY_LABELS:
        content = question["labels"].get(label, "").strip()
        if not content:
            continue
        if not should_split_supplementary(label, content):
            continue
        text = f"{context}\n\n{label}\n\n{content}".strip()
        pieces = enforce_size(text)
        line_start = question["label_line_start"].get(label, question["start_line"])
        line_end = question["label_line_end"].get(label, question["end_line"])
        if len(pieces) == 1:
            chunks.append({
                "label": label,
                "text": pieces[0],
                "line_start": line_start,
                "line_end": line_end,
                "piece_index": None,
            })
            continue
        for idx, piece in enumerate(pieces, start=1):
            piece_text = piece
            if idx > 1 and not piece.startswith("## "):
                piece_text = f"{context}\n\n{label}\n\n{piece}".strip()
            chunks.append({
                "label": label,
                "text": piece_text,
                "line_start": line_start,
                "line_end": line_end,
                "piece_index": idx,
            })
    return chunks


def make_metadata_base(question: dict) -> dict:
    body = "\n".join([
        question["stem"],
        "\n".join(question["options"]),
        *(f"{label}\n{content}" for label, content in question["labels"].items()),
        question.get("answer_line") or "",
    ])
    exam_id, exam_year, question_type = parse_exam_meta(body)
    answer = parse_answer(body)
    return {
        "book": BOOK,
        "doc_type": DOC_TYPE,
        "chapter": question["part"],
        "section": question["chapter"],
        "subsection": question["point"],
        "question_index": question["number"],
        "exam_id": exam_id,
        "exam_year": exam_year,
        "question_type": question_type,
        "answer": answer,
        "has_review_flag": "【待复核】" in question["labels"] or "【待复核】" in body,
        "source_stage": SOURCE_STAGE,
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
                "question_header": question["header"],
                "source_line_start": item["line_start"],
                "source_line_end": item["line_end"],
                "char_count": len(item["text"]),
            })
            chunks.append({
                "id": make_global_id(
                    part=question["part"] or "未知法别",
                    topic=question["chapter"] or "未知专题",
                    point=question["point"] or "未知考点",
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
            block_type = item["label"].strip("【】")
            metadata = deepcopy(meta_base)
            metadata.update({
                "subsub": block_type,
                "question_header": question["header"],
                "source_line_start": item["line_start"],
                "source_line_end": item["line_end"],
                "char_count": len(item["text"]),
            })
            chunks.append({
                "id": make_global_id(
                    part=question["part"] or "未知法别",
                    topic=question["chapter"] or "未知专题",
                    point=question["point"] or "未知考点",
                    question_header=question["header"],
                    block_type=block_type,
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
    print(f"法别数: {parse_stats['parts']}")
    print(f"专题数: {parse_stats['topics']}")
    print(f"考点数: {parse_stats['points']}")
    print(f"题目数: {parse_stats['questions']}")
    print(f"总块数: {len(chunks)}")
    print(f"主块数: {main_count}")
    print(f"附属块数: {supp_count}")
    print(f"最大块长: {max(sizes) if sizes else 0}")
    print(f">950 字块数: {sum(1 for s in sizes if s > SOFT_LIMIT)}")
    print(f">1100 字块数: {sum(1 for s in sizes if s > MAX_CHUNK_SIZE)}")
    print(f"带待复核块数: {sum(1 for c in chunks if c['metadata'].get('has_review_flag'))}")


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
