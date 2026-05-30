#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""李佳行政法真金题二次整理脚本。"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECLARED_QUESTION_COUNT = 434
STAGE1_QUESTION_COUNT = 401

BOOK_TITLE = "李佳行政法真金题（二次清洗版）"
SOURCE_LABEL = "整理后文本/李佳行政法真金题_整理版.md"

QUESTION_HINTS = (
    "下列",
    "关于",
    "哪些",
    "哪一",
    "哪个",
    "何者",
    "何项",
    "说法",
    "表述",
    "正确",
    "错误",
    "属于",
    "体现",
)

NON_QUESTION_PREFIXES = (
    "在程序法上",
    "公民可以",
    "法院可以",
    "情况紧急",
    "法定标准",
    "实际损失标准",
    "实际投入标准",
    "补偿程序",
    "带来损失",
    "简易程序",
    "可以口头",
)

SPECIAL_QUESTION_PREFIXES = (
    "2023年3月",
    "国家税务总局为国务院直属机构",
    "甲省乙市政府拟",
    "国务院某部拟",
    "国家邮政局是交通运输部管理的国家局",
    "国家数据局",
)

CANONICAL_LABELS = {
    "命题规律": "【命题规律】",
    "解析": "【解析】",
    "技术流": "【技术流】",
    "设题陷阱与常见错误分析": "【设题陷阱与常见错误分析】",
    "归纳总结": "【归纳总结】",
    "脚注": "【脚注】",
    "待复核": "【待复核】",
    "表格整理": "【表格整理】",
}

QUESTION_HEAD_RE = re.compile(r"^####\s*(\d{1,3})\.\s*(.+?)\s*$")
NORMAL_QUESTION_RE = re.compile(r"^\s*(\d{1,3})[.．、]\s*(.+?)\s*$")
MISSING_DOT_QUESTION_RE = re.compile(r"^\s*(\d{1,3})(?=[\u4e00-\u9fff《（(【])(.+?)\s*$")
OPTION_SPLIT_RE = re.compile(r"(?<!\n)(?<![A-Z])(?<![A-D][.．、，,])\s*([A-D])[.．、，,](?=\S)")
LABEL_VARIANT_RE = re.compile(
    r"[\[［【「]\s*(命题规律|解析|技术流|设题陷阱与常见错误分析|归纳总结|脚注|待复核|表格整理)\s*[\]］】」]"
)
PAGE_FRAGMENT_RE = re.compile(r"^\s*[①②③④⑤⑥⑦⑧⑨⑩]?\s*$")
FAKE_HEAD_RE = re.compile(r"^####\s*(\d{1,3})\.\s*([单双任][）)]?)\s*$")
PREV_YEAR_TAIL_RE = re.compile(r"[（(](?:19|20)\d{2}[^）)]*-\s*$")
EXAM_REF_RE = re.compile(r"[（(](?:19|20)\d{2}[^）)]{0,30}[）)]")
INLINE_HEAD_RE = re.compile(
    r"(^|[。！？；;：:）】]\s+)(0\s*)?(\d{1,3})([.．、]?\s*)(?=(?:[\u4e00-\u9fff《（(【]|(?:19|20)\d{2}))"
)
SECONDARY_INLINE_HEAD_RE = re.compile(
    r"\s+(0\s*)?(\d{1,3})([.．、]?\s*)(?=(?:[\u4e00-\u9fff《（(【]|(?:19|20)\d{2}))"
)


@dataclass
class Stats:
    before_lines: int = 0
    after_lines: int = 0
    topics_after: int = 0
    questions_before: int = 0
    questions_after: int = 0
    recovered_questions: int = 0
    missing_after_count: int = 0
    mechanical_review_removed: int = 0
    real_review_kept: int = 0
    table_blocks_normalized: int = 0
    continuation_markers_removed: int = 0
    fake_heads_merged: int = 0
    embedded_questions_split: int = 0
    inline_option_splits: int = 0
    inline_labels_normalized: int = 0
    ocr_heads_found: int = 0
    remaining_missing: list[int] = field(default_factory=list)
    repair_summary: Counter = field(default_factory=Counter)


@dataclass
class Question:
    number: int
    title: str
    body: list[str] = field(default_factory=list)


@dataclass
class Topic:
    board: str
    title: str
    intro: list[str] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)


def find_one(pattern: str) -> Path:
    matches = sorted(PROJECT_ROOT.rglob(pattern))
    if not matches:
        raise FileNotFoundError(f"未找到文件：{pattern}")
    return matches[0]


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = text.replace("「设题陷阱与常见错误分析]", "【设题陷阱与常见错误分析】")
    text = text.replace("[表格整理]", "【表格整理】")
    text = text.replace("［表格整理］", "【表格整理】")
    text = text.replace("[解析]", "【解析】")
    text = text.replace("［解析］", "【解析】")
    text = text.replace("[技术流]", "【技术流】")
    text = text.replace("［技术流］", "【技术流】")
    text = text.replace("[归纳总结]", "【归纳总结】")
    text = text.replace("［归纳总结］", "【归纳总结】")
    text = text.replace("[脚注]", "【脚注】")
    text = text.replace("［脚注］", "【脚注】")
    text = text.replace("[待复核]", "【待复核】")
    text = text.replace("［待复核］", "【待复核】")
    text = text.replace("[命题规律]", "【命题规律】")
    text = text.replace("［命题规律］", "【命题规律】")
    text = text.replace("【归纳总结】2]", "【归纳总结】")
    text = text.replace("A，", "A.")
    text = text.replace("B，", "B.")
    text = text.replace("C，", "C.")
    text = text.replace("D，", "D.")
    return text


def question_like(text: str) -> bool:
    head = text.strip()
    if not head or len(head) < 4:
        return False
    preview = head[:120]
    if preview.startswith(NON_QUESTION_PREFIXES):
        return False
    if preview.startswith(SPECIAL_QUESTION_PREFIXES):
        return True
    if re.search(r"[（(](?:19|20)\d{2}", preview):
        return True
    return any(hint in preview for hint in QUESTION_HINTS)


def is_high_conf_question(text: str, require_exam_ref: bool = False) -> bool:
    preview = text.strip()[:180]
    if not preview:
        return False
    has_ref = bool(EXAM_REF_RE.search(preview))
    if require_exam_ref and not has_ref:
        return False
    if has_ref:
        return True
    return question_like(preview)


def is_inline_question_candidate(text: str) -> bool:
    preview = text.strip()[:100]
    if not preview:
        return False
    if preview.startswith(NON_QUESTION_PREFIXES):
        return False
    if question_like(preview):
        return True
    return bool(EXAM_REF_RE.search(preview))


def has_front_exam_ref(text: str) -> bool:
    preview = text.strip()[:120]
    return bool(EXAM_REF_RE.search(preview))


def has_special_question_prefix(text: str) -> bool:
    return text.strip().startswith(SPECIAL_QUESTION_PREFIXES)


def normalize_label_match(match: re.Match[str], stats: Stats) -> str:
    label = CANONICAL_LABELS[match.group(1)]
    stats.inline_labels_normalized += 1
    return f"\n{label}\n"


def split_inline_labels_and_options(line: str, stats: Stats) -> str:
    original = line
    line = LABEL_VARIANT_RE.sub(lambda m: normalize_label_match(m, stats), line)
    line = re.sub(r"(【(?:命题规律|解析|技术流|设题陷阱与常见错误分析|归纳总结|脚注|待复核|表格整理)】)", r"\n\1\n", line)

    def repl_option(match: re.Match[str]) -> str:
        stats.inline_option_splits += 1
        return f"\n{match.group(1)}. "

    line = OPTION_SPLIT_RE.sub(repl_option, line)
    if line != original:
        stats.repair_summary["inline_structure"] += 1
    return line


def is_option_line(text: str) -> bool:
    return bool(re.match(r"^[A-D][.．、，,]", text.strip()))


def starts_question_head(text: str) -> bool:
    stripped = text.strip()
    return bool(NORMAL_QUESTION_RE.match(stripped) or MISSING_DOT_QUESTION_RE.match(stripped))


def merge_broken_question_header(lines: list[str], idx: int) -> tuple[str, int]:
    current = lines[idx].strip()
    if not starts_question_head(current):
        return current, 0
    if is_high_conf_question(NORMAL_QUESTION_RE.sub(r"\2", current) if NORMAL_QUESTION_RE.match(current) else MISSING_DOT_QUESTION_RE.match(current).group(2)):  # type: ignore[union-attr]
        return current, 0

    merged = current
    consumed = 0
    for lookahead in range(1, 4):
        if idx + lookahead >= len(lines):
            break
        nxt = lines[idx + lookahead].strip()
        if not nxt:
            continue
        if nxt.startswith("#### ") or nxt.startswith("### ") or nxt.startswith("## "):
            break
        merged = f"{merged} {nxt}".strip()
        consumed = lookahead
        head = NORMAL_QUESTION_RE.match(merged) or MISSING_DOT_QUESTION_RE.match(merged)
        if head and is_high_conf_question(head.group(2)):
            return merged, consumed
        if is_option_line(nxt) or "【解析】" in nxt:
            break
    return current, 0


def find_question_splits(line: str) -> list[tuple[int, int]]:
    matches: list[tuple[int, int]] = []
    stripped = line.strip()
    head_match = MISSING_DOT_QUESTION_RE.match(stripped)
    if head_match and is_high_conf_question(head_match.group(2)):
        prefix_len = len(line) - len(line.lstrip())
        matches.append((prefix_len, int(head_match.group(1))))
        return matches

    for match in INLINE_HEAD_RE.finditer(line):
        number = int(match.group(3))
        if not (1 <= number <= DECLARED_QUESTION_COUNT):
            continue
        candidate = line[match.start(3) :].strip()
        prefix = line[: match.start(3)]
        if "|" in prefix and not (has_front_exam_ref(candidate) or has_special_question_prefix(candidate)):
            continue
        if is_inline_question_candidate(candidate):
            matches.append((match.start(3), number))

    for match in SECONDARY_INLINE_HEAD_RE.finditer(line):
        number = int(match.group(2))
        if not (1 <= number <= DECLARED_QUESTION_COUNT):
            continue
        start = match.start(2)
        if any(existing_start == start for existing_start, _ in matches):
            continue
        candidate = line[start:].strip()
        prefix = line[:start]
        if "|" not in prefix:
            continue
        if not (has_front_exam_ref(candidate) or has_special_question_prefix(candidate)):
            continue
        if is_inline_question_candidate(candidate):
            matches.append((start, number))

    matches.sort(key=lambda item: item[0])
    return matches


def split_embedded_question_line(line: str, stats: Stats) -> list[str]:
    if line.startswith("#### "):
        return [line]

    splits = find_question_splits(line)
    if not splits:
        return [line]

    parts: list[str] = []
    positions = [pos for pos, _ in splits]
    for idx, (start, number) in enumerate(splits):
        prev_start = positions[idx - 1] if idx > 0 else None
        if idx == 0 and start > 0:
            before = line[:start].rstrip()
            before = re.sub(r"\s+0$", "", before)
            if before.strip():
                parts.append(before)
        elif idx > 0 and prev_start is not None:
            between = line[prev_start:start].rstrip()
            if between.strip():
                parts.append(between)

        end = positions[idx + 1] if idx + 1 < len(positions) else len(line)
        piece = line[start:end].strip()
        head = NORMAL_QUESTION_RE.match(piece)
        missing_dot = MISSING_DOT_QUESTION_RE.match(piece)
        if head:
            piece = f"#### {number}. {head.group(2).strip()}"
        elif missing_dot:
            piece = f"#### {number}. {missing_dot.group(2).strip()}"
        else:
            piece = re.sub(rf"^{number}(?!\d)", f"#### {number}.", piece, count=1)
            piece = re.sub(rf"^#### {number}\.(?=[^\s])", f"#### {number}. ", piece, count=1)
        parts.append(piece)

    stats.embedded_questions_split += max(0, len(splits) - (1 if positions and positions[0] == 0 else 0))
    if len(splits) > 1 or positions[0] > 0:
        stats.repair_summary["embedded_question"] += 1

    normalized: list[str] = []
    for item in parts:
        if item.startswith("#### "):
            normalized.append(item)
            continue
        if not normalized or normalized[-1].startswith("#### "):
            normalized.append(item)
        else:
            normalized[-1] = f"{normalized[-1]} {item}".strip()
    return normalized


def is_mechanical_review_block(lines: list[str], start: int) -> tuple[bool, int]:
    current = lines[start].strip()
    if current == "【待复核】 解析内容未稳定识别。":
        return True, 1
    if current != "【待复核】":
        return False, 0

    idx = start + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    consumed = idx - start
    if idx < len(lines) and re.fullmatch(r"选项识别数为\s*\d+\s*，建议人工抽查。", lines[idx].strip()):
        idx += 1
        consumed = idx - start
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
            consumed = idx - start

    if idx < len(lines) and lines[idx].strip() == "解析块未稳定识别。":
        consumed = idx - start + 1
        return True, consumed
    return False, 0


def preprocess_text(text: str, stats: Stats) -> list[str]:
    text = normalize_text(text)
    raw_lines = text.split("\n")
    stats.before_lines = len(raw_lines)
    stats.questions_before = sum(1 for line in raw_lines if line.startswith("#### "))

    lines: list[str] = []
    last_question_head_index: int | None = None

    idx = 0
    while idx < len(raw_lines):
        line = raw_lines[idx].rstrip()
        stripped = line.strip()

        mechanical, consumed = is_mechanical_review_block(raw_lines, idx)
        if mechanical:
            stats.mechanical_review_removed += 1
            stats.repair_summary["mechanical_review"] += 1
            idx += consumed
            continue

        if not stripped:
            lines.append("")
            idx += 1
            continue

        if stripped == "续表":
            stats.continuation_markers_removed += 1
            stats.table_blocks_normalized += 1
            stats.repair_summary["续表"] += 1
            idx += 1
            continue

        if PAGE_FRAGMENT_RE.fullmatch(stripped):
            idx += 1
            continue

        merged_header, consumed = merge_broken_question_header(raw_lines, idx)
        if consumed:
            line = merged_header
            stripped = line.strip()

        line = split_inline_labels_and_options(line, stats)
        for subline in line.splitlines():
            item = subline.strip()
            if not item:
                lines.append("")
                continue

            fake_match = FAKE_HEAD_RE.match(item)
            if fake_match and last_question_head_index is not None:
                prev_line = lines[last_question_head_index]
                if PREV_YEAR_TAIL_RE.search(prev_line):
                    lines[last_question_head_index] = prev_line + f"{fake_match.group(1)}，{fake_match.group(2)}"
                    stats.fake_heads_merged += 1
                    stats.repair_summary["fake_head_merge"] += 1
                    continue

            split_parts = split_embedded_question_line(item, stats)
            for part in split_parts:
                part = part.strip()
                if not part:
                    continue

                head = NORMAL_QUESTION_RE.match(part)
                missing_dot = MISSING_DOT_QUESTION_RE.match(part)
                if head and is_high_conf_question(head.group(2)) and not part.startswith("#### "):
                    part = f"#### {head.group(1)}. {head.group(2).strip()}"
                    stats.repair_summary["question_head_promote"] += 1
                elif missing_dot and is_high_conf_question(missing_dot.group(2)):
                    part = f"#### {missing_dot.group(1)}. {missing_dot.group(2).strip()}"
                    stats.repair_summary["question_head_promote"] += 1

                if part.startswith("#### "):
                    last_question_head_index = len(lines)
                if part == "【表格整理】":
                    stats.table_blocks_normalized += 1
                lines.append(part)
        idx += consumed + 1

    return collapse_blank_lines(lines)


def collapse_blank_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    blank = False
    for line in lines:
        if line.strip():
            cleaned.append(line.rstrip())
            blank = False
        elif not blank:
            cleaned.append("")
            blank = True
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return cleaned


def cleanup_question_body(body: list[str], stats: Stats) -> list[str]:
    body = collapse_blank_lines(body)
    cleaned: list[str] = []
    labels = set(CANONICAL_LABELS.values())
    idx = 0
    while idx < len(body):
        line = body[idx].strip()
        if line == "【待复核】 解析内容未稳定识别。":
            stats.mechanical_review_removed += 1
            idx += 1
            continue
        if line == "【待复核】":
            next_idx = idx + 1
            while next_idx < len(body) and not body[next_idx].strip():
                next_idx += 1
            if next_idx < len(body) and body[next_idx].strip() == "解析块未稳定识别。":
                stats.mechanical_review_removed += 1
                idx = next_idx + 1
                continue
        if line in {"【表格整理】", "【解析】", "【技术流】", "【归纳总结】", "【脚注】", "【待复核】", "【设题陷阱与常见错误分析】"}:
            next_idx = idx + 1
            while next_idx < len(body) and not body[next_idx].strip():
                next_idx += 1
            if next_idx >= len(body) or body[next_idx].strip() in labels or body[next_idx].startswith("#### "):
                idx += 1
                continue
        cleaned.append(body[idx].rstrip())
        idx += 1
    return collapse_blank_lines(cleaned)


def parse_topics(lines: list[str], stats: Stats) -> list[Topic]:
    topics: list[Topic] = []
    board = ""
    topic: Topic | None = None
    question: Question | None = None

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("## "):
            board = line[3:].strip()
            if question and topic:
                question.body = cleanup_question_body(question.body, stats)
                topic.questions.append(question)
                question = None
            if topic:
                topics.append(topic)
            topic = None
            continue

        if line.startswith("### "):
            if question and topic:
                question.body = cleanup_question_body(question.body, stats)
                topic.questions.append(question)
                question = None
            if topic:
                topics.append(topic)
            topic = Topic(board=board, title=line[4:].strip())
            continue

        head_match = QUESTION_HEAD_RE.match(line)
        if head_match:
            if topic is None:
                topic = Topic(board=board, title="待归类专题")
            previous_number = question.number if question else (topic.questions[-1].number if topic.questions else None)
            if (
                previous_number is not None
                and int(head_match.group(1)) < previous_number - 5
                and not EXAM_REF_RE.search(line)
                and not question_like(head_match.group(2))
            ):
                downgraded = head_match.group(2).strip()
                if question is None:
                    topic.intro.append(downgraded)
                else:
                    question.body.append(downgraded)
                continue
            if question:
                question.body = cleanup_question_body(question.body, stats)
                topic.questions.append(question)
            question = Question(number=int(head_match.group(1)), title=head_match.group(2).strip())
            continue

        if topic is None:
            continue

        if question is None:
            topic.intro.append(line)
        else:
            question.body.append(line)

    if question and topic:
        question.body = cleanup_question_body(question.body, stats)
        topic.questions.append(question)
    if topic:
        topics.append(topic)

    stats.topics_after = len(topics)
    return topics


def repair_topics(topics: list[Topic], stats: Stats) -> list[Topic]:
    for topic in topics:
        if topic.title != "专题二 行政主体":
            continue

        filtered_questions: list[Question] = []
        removed_false_head = False
        for question in topic.questions:
            if question.number == 1 and question.title.strip() == "正2副或1正1副":
                removed_false_head = True
                continue
            filtered_questions.append(question)
        if removed_false_head:
            topic.questions = filtered_questions
            stats.repair_summary["manual_false_head_cleanup"] += 1

        numbers = [q.number for q in topic.questions]
        if 24 not in numbers:
            question_24 = Question(
                number=24,
                title="甲省乙市政府拟将本市的环境资源管理局与国土资源局合并，应当报哪个机关予以批准？（2019金题-1-3-3，单）",
                body=[
                    "A. 【待复核】OCR 原稿该选项缺失，待后续人工核对补全。",
                    "B. 甲省政府",
                    "C. 乙市人大常委会",
                    "D. 甲省人大常委会",
                    "",
                    "【解析】",
                    "",
                    "《地方各级人民政府机构设置和编制管理条例》第9条规定：“地方各级人民政府行政机构的设立、撤销、合并或者变更规格、名称，由本级人民政府提出方案，经上一级人民政府机构编制管理机关审核后，报上一级人民政府批准；其中，县级以上地方各级人民政府行政机构的设立、撤销或者合并，还应当依法报本级人民代表大会常务委员会备案。”乙市政府的上一级政府为甲省政府，所以B选项正确。",
                    "本题从理解的角度也较为容易解释，机构改革所涉及的设立、撤销或合并等内容是较为专业的行政事务，自然要由专业的上一级行政机关事先批准；本级人大常委会在这里承担的是事后备案监督，而非事先批准职能。",
                    "综上，本题答案为B。",
                    "",
                    "【待复核】",
                    "",
                    "本题 OCR 原稿中 A 选项缺失，现依据题干、B-D 选项和解析恢复题块。",
                ],
            )
            insert_at = next((idx for idx, q in enumerate(topic.questions) if q.number > 24), len(topic.questions))
            topic.questions.insert(insert_at, question_24)
            stats.repair_summary["manual_question_restore"] += 1

        break

    return topics


def load_ocr_head_numbers() -> tuple[set[int], Path]:
    ocr_path = find_one("*2026客观真金题行政李佳.md")
    text = ocr_path.read_text(encoding="utf-8")
    heads = {
        int(m.group(1))
        for m in re.finditer(r"(?m)^\s*(\d{1,3})[.．、]\s*", text)
        if 1 <= int(m.group(1)) <= DECLARED_QUESTION_COUNT
    }
    return heads, ocr_path


def render_markdown(topics: list[Topic]) -> str:
    lines: list[str] = [
        f"# {BOOK_TITLE}",
        "",
        f"> 二次清洗说明：本文件基于 `{SOURCE_LABEL}` 强修复整理，并参考 OCR 原稿校题号与断题；本轮不切块、不嵌入、不入库。",
        "",
    ]

    current_board = None
    for topic in topics:
        if topic.board != current_board:
            current_board = topic.board
            lines.extend([f"## {current_board}", ""])
        lines.extend([f"### {topic.title}", ""])
        for line in collapse_blank_lines(topic.intro):
            lines.append(line)
        if topic.intro:
            lines.append("")
        for question in topic.questions:
            lines.extend([f"#### {question.number}. {question.title}", ""])
            for body_line in collapse_blank_lines(question.body):
                lines.append(body_line)
            lines.append("")
    return "\n".join(collapse_blank_lines(lines)) + "\n"


def render_report(stats: Stats, ocr_path: Path) -> str:
    summary_lines = [
        "# 李佳行政法真金题二次清洗说明",
        "",
        "## 概况",
        "",
        f"- 主输入：`{SOURCE_LABEL}`",
        f"- 辅助核对：`{ocr_path.as_posix().split(PROJECT_ROOT.as_posix() + '/')[-1]}`",
        f"- 一整理题量：{STAGE1_QUESTION_COUNT}",
        f"- 二清后题量：{stats.questions_after}",
        f"- 新增恢复题目数：{stats.recovered_questions}",
        f"- 距原稿声明 434 题的剩余缺口：{stats.missing_after_count}",
        "",
        "## 统计",
        "",
        f"- 处理前总行数：{stats.before_lines}",
        f"- 处理后总行数：{stats.after_lines}",
        f"- 二清后识别专题数：{stats.topics_after}",
        f"- 删除的机械 `【待复核】` 数：{stats.mechanical_review_removed}",
        f"- 保留的真实 `【待复核】` 数：{stats.real_review_kept}",
        f"- 改写/统一的表格与续表块数：{stats.table_blocks_normalized + stats.continuation_markers_removed}",
        f"- 合并的伪题头数：{stats.fake_heads_merged}",
        f"- 内嵌题头拆出次数：{stats.embedded_questions_split}",
        f"- 内联选项拆出次数：{stats.inline_option_splits}",
        f"- OCR 中可识别题头数：{stats.ocr_heads_found}",
        "",
        "## 典型修复",
        "",
        "- 将 `1关于...`、`14.国务院某部...`、`76.对具体行政行为...`、`156.在行政强制执行过程中...` 这类内嵌题头恢复为规范 `####` 题头。",
        "- 将 `#### 43. 单）` 这类年份括注断裂伪题头并回上一题，避免假题头挤占真实题号。",
        "- 清除了机械生成的 `【待复核】 解析内容未稳定识别。`、`解析块未稳定识别。` 及其配套空壳块。",
        "- 统一了 `【解析】`、`【技术流】`、`【设题陷阱与常见错误分析】`、`【归纳总结】`、`【脚注】`、`【表格整理】` 等标签格式。",
        "- 删除了裸 `续表`，保留其后条目化内容，不再让续表标记单独残留。",
        "",
        "## 剩余缺口",
        "",
    ]

    if stats.remaining_missing:
        summary_lines.append(f"- 仍缺失题号：{', '.join(map(str, stats.remaining_missing))}")
        summary_lines.append("- 说明：这些题号在一整理稿中未能稳定重建，本轮未做低置信硬猜。")
    else:
        summary_lines.append("- 已恢复到连续 434 题，未发现剩余题号缺口。")

    return "\n".join(summary_lines) + "\n"


def main() -> None:
    stage1_path = find_one("*李佳行政法真金题_整理版.md")
    output_dir = stage1_path.parent
    dst = output_dir / "李佳行政法真金题_二次清洗版.md"
    report = output_dir / "李佳行政法真金题_二次清洗说明.md"

    stats = Stats()
    text = stage1_path.read_text(encoding="utf-8")
    lines = preprocess_text(text, stats)
    topics = parse_topics(lines, stats)
    topics = repair_topics(topics, stats)

    ocr_heads, ocr_path = load_ocr_head_numbers()
    stats.ocr_heads_found = len(ocr_heads)

    question_numbers = [q.number for topic in topics for q in topic.questions]
    stats.questions_after = len(question_numbers)
    stats.recovered_questions = stats.questions_after - STAGE1_QUESTION_COUNT
    stats.remaining_missing = [n for n in range(1, DECLARED_QUESTION_COUNT + 1) if n not in question_numbers]
    stats.missing_after_count = len(stats.remaining_missing)
    stats.real_review_kept = sum(
        1 for topic in topics for q in topic.questions for line in q.body if "【待复核】" in line
    )

    markdown = render_markdown(topics)
    stats.after_lines = len(markdown.splitlines())
    report_text = render_report(stats, ocr_path)

    dst.write_text(markdown, encoding="utf-8")
    report.write_text(report_text, encoding="utf-8")

    print(f"已生成：{dst}")
    print(f"已生成：{report}")
    print(f"二清题量：{stats.questions_after}")
    print(f"剩余缺口：{stats.remaining_missing}")


if __name__ == "__main__":
    main()
