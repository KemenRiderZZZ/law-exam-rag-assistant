#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""左宁刑诉真金题（二次清洗版）切块脚本。"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "左宁刑诉真金题_二次清洗版.md"
DST = PROJECT_ROOT / "切块" / "左宁刑诉真金题_chunks.jsonl"

BOOK = "左宁刑诉真金题（二次清洗版）"
DOC_TYPE = "真题解析"
TARGET_SIZE = 800
SOFT_LIMIT = 950
MAX_CHUNK_SIZE = 1100
MIN_CHUNK_SIZE = 80
OVERLAP = 90

SUPPLEMENTARY_LABELS = (
    "【注意】",
    "【归纳】",
    "【背下来】",
    "【命题规律】",
    "【设题陷阱】",
    "【常见错误分析】",
    "【脚注】",
    "【待复核】",
    "【表格整理】",
    "【图片整理】",
)

FORCE_SUPPLEMENTARY_NUMBER_LABELS = {
    "【注意】",
    "【归纳】",
    "【表格整理】",
    "【图片整理】",
    "【脚注】",
    "【待复核】",
}

ANSWER_PATTERNS = (
    re.compile(r"综上所述，本题答案为\s*([A-D]+)", re.I),
    re.compile(r"本题答案为\s*([A-D]+)", re.I),
    re.compile(r"答案为\s*([A-D]+)", re.I),
)

EXAM_ID_PATTERN = re.compile(r"20\d{2}(?:金题|延金题|金题一)?-\d-\d+(?:-\d+)?|20\d{2}-\d-\d+(?:-\d+)?")
OPTION_MARKER_PATTERN = re.compile(r"(?:^|[^A-Z])([A-D])[.．、]")

QUESTION_TYPE_MAP = {
    "单": "单选",
    "多": "多选",
    "任": "不定项",
    "不定项": "不定项",
    "案例": "案例题",
    "主观": "主观题",
}


def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(
        r"(?<=[。！？；）\)])\s*(\d{1,3}\.)",
        r"\n\1",
        text,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def slugify_title(title: str, max_len: int = 18) -> str:
    compact = re.sub(r"\s+", "", title)
    compact = re.sub(r"[：:，,（）()\[\]【】]", "", compact)
    return compact[:max_len] or "未命名"


def make_global_id(
    chapter: str,
    section: str,
    question_index: int,
    block_type: str,
    chunk_index: int,
    piece_index: int | None = None,
) -> str:
    chapter_slug = slugify_title(chapter)
    section_slug = slugify_title(section)
    type_slug = block_type if piece_index is None else f"{block_type}-{piece_index:02d}"
    return f"左宁刑诉真金题:{chapter_slug}:{section_slug}:Q{question_index:03d}:{type_slug}:{chunk_index:04d}"


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

        while len(current) > max_size:
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


def parse_exam_meta(question_line: str) -> tuple[str | None, int | None, str | None]:
    compact = question_line.replace(" ", "")

    exam_id = None
    exam_year = None
    question_type = None

    exam_match = re.search(r"(20\d{2}(?:金题|延金题)?-\d-\d(?:-\d+)?)", compact)
    if exam_match:
        exam_id = exam_match.group(1)
        year_match = re.match(r"(20\d{2})", exam_id)
        if year_match:
            exam_year = int(year_match.group(1))
    else:
        year_match = re.search(r"(20\d{2})", compact)
        if year_match:
            exam_year = int(year_match.group(1))

    type_match = re.search(r"（[^）]*?(单|多|任|不定项|案例|主观)[）)]", compact)
    if not type_match:
        type_match = re.search(r"\(([^)]*?)(单|多|任|不定项|案例|主观)\)", compact)
    if type_match:
        question_type = QUESTION_TYPE_MAP.get(type_match.group(1) if len(type_match.groups()) == 1 else type_match.group(len(type_match.groups())))

    return exam_id, exam_year, question_type


def extract_answer(text: str) -> str | None:
    compact = text.replace(" ", "")
    for pattern in ANSWER_PATTERNS:
        match = pattern.search(compact)
        if match:
            answer = re.sub(r"[^A-D]", "", match.group(1).upper())
            return answer or None
    return None


def parse_question_start(stripped: str) -> tuple[int, str] | None:
    match = re.match(r"^(\d+)\.(.+)$", stripped)
    if not match:
        return None
    return int(match.group(1)), stripped


def is_option_line(stripped: str) -> bool:
    return bool(re.match(r"^[A-D][.．、]\s*", stripped))


def is_label_line(stripped: str) -> bool:
    return stripped.startswith("【") and "】" in stripped


def candidate_head_text(lines: list[str], start_index: int, window: int = 12) -> str:
    collected: list[str] = []
    seen_nonempty = 0
    for offset, raw_line in enumerate(lines[start_index:]):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if offset > 0 and parse_question_start(stripped):
            break
        if offset > 0 and (stripped.startswith("### ") or stripped.startswith("#### ") or is_label_line(stripped)):
            break
        collected.append(stripped)
        seen_nonempty += 1
        if seen_nonempty >= window:
            break
    return "\n".join(collected)


def is_probable_question_start(lines: list[str], start_index: int) -> bool:
    head = candidate_head_text(lines, start_index)
    if not head:
        return False
    if EXAM_ID_PATTERN.search(head):
        return True
    option_hits = OPTION_MARKER_PATTERN.findall(head)
    unique_options = set(option_hits)
    if len(unique_options) >= 2 and "下列" in head:
        return True
    if len(unique_options) >= 3:
        return True
    return False


def parse_questions(text: str) -> tuple[list[dict], dict[str, int]]:
    lines = text.splitlines()
    current_topic = None
    current_section = None
    current_question: dict | None = None
    current_label: str | None = None
    stats = {"topics": 0, "sections": 0, "questions": 0}
    questions: list[dict] = []

    def flush_question() -> None:
        nonlocal current_question, current_label
        current_label = None
        if current_question is None:
            return
        current_question["end_line"] = current_question.get("last_content_line", current_question["start_line"])
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
            stats["sections"] += 1
            continue

        question_start = parse_question_start(stripped)
        if question_start:
            if not is_probable_question_start(lines, idx - 1):
                if current_label is not None and current_question["supplementary"]:
                    bucket = current_question["supplementary"][-1]
                    bucket["lines"].append(line)
                    bucket["end_line"] = idx
                elif current_question["analysis_lines"]:
                    current_question["analysis_lines"].append(line)
                elif current_question["option_lines"]:
                    current_question["option_lines"].append(line)
                else:
                    current_question["stem_lines"].append(line)
                current_question["last_content_line"] = idx
                continue

            flush_question()
            question_index, header = question_start
            current_question = {
                "chapter": current_topic,
                "section": current_section,
                "header": header,
                "question_index": question_index,
                "start_line": idx,
                "end_line": idx,
                "stem_lines": [line],
                "option_lines": [],
                "analysis_lines": [],
                "supplementary": [],
                "last_content_line": idx,
            }
            current_label = None
            stats["questions"] += 1
            continue

        if current_question is None:
            continue

        if not stripped:
            if current_label is not None:
                current_question["supplementary"][-1]["lines"].append("")
            elif current_question["analysis_lines"]:
                current_question["analysis_lines"].append("")
            elif current_question["option_lines"]:
                current_question["option_lines"].append("")
            else:
                current_question["stem_lines"].append("")
            current_question["last_content_line"] = idx
            continue

        if is_label_line(stripped):
            label_match = re.match(r"^(【[^】]+】)(.*)$", stripped)
            if label_match:
                label = label_match.group(1)
                remainder = label_match.group(2).strip()
                if label in SUPPLEMENTARY_LABELS:
                    current_question["supplementary"].append(
                        {
                            "label": label,
                            "start_line": idx,
                            "end_line": idx,
                            "lines": [remainder] if remainder else [],
                        }
                    )
                    current_label = label
                else:
                    content = f"{label}{remainder}" if remainder else label
                    current_question["analysis_lines"].append(content)
                    current_label = None
                current_question["last_content_line"] = idx
                continue

        if current_label is not None and current_question["supplementary"]:
            bucket = current_question["supplementary"][-1]
            bucket["lines"].append(line)
            bucket["end_line"] = idx
            current_question["last_content_line"] = idx
            continue

        if current_question["analysis_lines"]:
            current_question["analysis_lines"].append(line)
            current_question["last_content_line"] = idx
            continue

        if current_question["option_lines"] or is_option_line(stripped):
            current_question["option_lines"].append(line)
            current_question["last_content_line"] = idx
            continue

        current_question["stem_lines"].append(line)
        current_question["last_content_line"] = idx

    flush_question()
    return questions, stats


def compose_title(question: dict) -> str:
    parts = [
        f"### {question['chapter']}" if question["chapter"] else None,
        f"#### {question['section']}" if question["section"] else None,
        f"##### 第{question['question_index']:03d}题",
    ]
    return "\n\n".join(part for part in parts if part)


def build_main_body(question: dict) -> str:
    parts: list[str] = []
    stem = "\n".join(line for line in question["stem_lines"]).strip()
    if stem:
        parts.append(stem)
    options = "\n".join(line for line in question["option_lines"]).strip()
    if options:
        parts.append(options)
    analysis = "\n".join(line for line in question["analysis_lines"]).strip()
    if analysis:
        parts.append(analysis)
    answer = extract_answer(analysis)
    if answer:
        parts.append(f"【答案】{answer}")
    return "\n\n".join(part for part in parts if part.strip()).strip()


def build_main_chunks(question: dict) -> list[dict]:
    title = compose_title(question)
    body = build_main_body(question)
    if not body:
        return []

    parts = enforce_size(body)
    total = len(parts)
    line_start = question["start_line"]
    line_end = question["end_line"]

    chunks: list[dict] = []
    for idx, part in enumerate(parts, start=1):
        text_parts = [title]
        if total > 1:
            text_parts.append(f"【分片】主块 {idx}/{total}")
        text_parts.append(part.strip())
        chunks.append(
            {
                "text": "\n\n".join(text_parts).strip(),
                "line_start": line_start,
                "line_end": line_end,
                "piece_index": idx if total > 1 else None,
            }
        )
    return chunks


def build_supplementary_chunks(question: dict) -> list[dict]:
    title = compose_title(question)
    chunks: list[dict] = []

    for block in question["supplementary"]:
        label = block["label"]
        content = "\n".join(block["lines"]).strip()
        if not content:
            text_body = label
        else:
            text_body = f"{label}\n{content}"
        parts = enforce_size(text_body)
        total = len(parts)
        for idx, part in enumerate(parts, start=1):
            text_parts = [title]
            if total > 1:
                text_parts.append(f"【分片】{label} {idx}/{total}")
            text_parts.append(part.strip())
            chunks.append(
                {
                    "label": label,
                    "text": "\n\n".join(text_parts).strip(),
                    "line_start": block["start_line"],
                    "line_end": block["end_line"],
                    "piece_index": idx if total > 1 else None,
                }
            )
    return chunks


def make_metadata_base(question: dict) -> dict:
    stem = "\n".join(question["stem_lines"]).strip()
    exam_id, exam_year, question_type = parse_exam_meta(stem)
    analysis = "\n".join(question["analysis_lines"]).strip()
    answer = extract_answer(analysis)
    has_review_flag = any(block["label"] == "【待复核】" for block in question["supplementary"])

    return {
        "book": BOOK,
        "doc_type": DOC_TYPE,
        "chapter": question["chapter"],
        "section": question["section"],
        "subsection": f"第{question['question_index']:03d}题",
        "question_index": question["question_index"],
        "exam_id": exam_id,
        "exam_year": exam_year,
        "question_type": question_type,
        "answer": answer,
        "has_review_flag": has_review_flag,
    }


def build_chunks(questions: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    chunk_index = 0

    for question in questions:
        meta_base = make_metadata_base(question)

        for item in build_main_chunks(question):
            chunk_index += 1
            metadata = deepcopy(meta_base)
            metadata.update(
                {
                    "subsub": "主块",
                    "source_line_start": item["line_start"],
                    "source_line_end": item["line_end"],
                    "char_count": len(item["text"]),
                }
            )
            chunks.append(
                {
                    "id": make_global_id(
                        chapter=question["chapter"] or "未知专题",
                        section=question["section"] or "未知考点",
                        question_index=question["question_index"],
                        block_type="主块",
                        chunk_index=chunk_index,
                        piece_index=item.get("piece_index"),
                    ),
                    "text": item["text"],
                    "metadata": metadata,
                    "chunk_index": chunk_index,
                }
            )

        for item in build_supplementary_chunks(question):
            chunk_index += 1
            metadata = deepcopy(meta_base)
            metadata.update(
                {
                    "subsub": item["label"].strip("【】"),
                    "source_line_start": item["line_start"],
                    "source_line_end": item["line_end"],
                    "char_count": len(item["text"]),
                }
            )
            chunks.append(
                {
                    "id": make_global_id(
                        chapter=question["chapter"] or "未知专题",
                        section=question["section"] or "未知考点",
                        question_index=question["question_index"],
                        block_type=item["label"].strip("【】"),
                        chunk_index=chunk_index,
                        piece_index=item.get("piece_index"),
                    ),
                    "text": item["text"],
                    "metadata": metadata,
                    "chunk_index": chunk_index,
                }
            )

    return chunks


def print_stats(questions: list[dict], chunks: list[dict], parse_stats: dict[str, int]) -> None:
    main_count = sum(1 for c in chunks if c["metadata"].get("subsub") == "主块")
    supp_count = len(chunks) - main_count
    sizes = [len(c["text"]) for c in chunks]
    print(f"专题数: {parse_stats['topics']}")
    print(f"考点数: {parse_stats['sections']}")
    print(f"题目数: {parse_stats['questions']}")
    print(f"总块数: {len(chunks)}")
    print(f"主块数: {main_count}")
    print(f"附属块数: {supp_count}")
    print(f"最大块长: {max(sizes) if sizes else 0}")
    print(f">950 字块数: {sum(1 for s in sizes if s > SOFT_LIMIT)}")
    print(f">1100 字块数: {sum(1 for s in sizes if s > MAX_CHUNK_SIZE)}")
    print(f"带待复核题数: {sum(1 for q in questions if any(b['label'] == '【待复核】' for b in q['supplementary']))}")


def main() -> None:
    text = clean_text(SRC.read_text(encoding="utf-8"))
    questions, parse_stats = parse_questions(text)
    chunks = build_chunks(questions)

    DST.parent.mkdir(parents=True, exist_ok=True)
    with DST.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print_stats(questions, chunks, parse_stats)
    print(f"输出文件: {DST}")


if __name__ == "__main__":
    main()
