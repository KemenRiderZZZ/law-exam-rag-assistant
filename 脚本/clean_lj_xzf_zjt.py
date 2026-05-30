#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行政法真金题第一遍整理脚本。"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = (
    PROJECT_ROOT
    / "OCR原稿"
    / "行政法真金题"
    / "2026客观真金题行政李佳"
    / "ocr"
    / "2026客观真金题行政李佳.md"
)
DST = PROJECT_ROOT / "整理后文本" / "李佳行政法真金题_整理版.md"
REPORT = PROJECT_ROOT / "整理后文本" / "李佳行政法真金题_整理说明.md"

BOOK_TITLE = "李佳行政法真金题（整理版）"
SOURCE_NAME = "OCR原稿/行政法真金题/2026客观真金题行政李佳/ocr/2026客观真金题行政李佳.md"
EXPECTED_BASIC_TOPICS = 22
EXPECTED_ADVANCED_TOPICS = 6
EXPECTED_TOPICS = EXPECTED_BASIC_TOPICS + EXPECTED_ADVANCED_TOPICS
DECLARED_QUESTION_COUNT = 434

BOARD_BASIC = "基础专题"
BOARD_ADVANCED = "进阶专题"
INTRO_LABEL = "【命题规律】"
ANALYSIS_LABEL = "【解析】"
TABLE_LABEL = "【表格整理】"
REVIEW_LABEL = "【待复核】"
LABEL_MAP = {
    "解析": ANALYSIS_LABEL,
    "技术流": "【技术流】",
    "设题陷阱与常见错误分析": "【设题陷阱与常见错误分析】",
    "归纳总结": "【归纳总结】",
    "脚注": "【脚注】",
    "待复核": REVIEW_LABEL,
}

PROJECT_RE = re.compile(r"^#\s*PROJECT\s*0?(\d{1,2})\s*$", re.I)
PROJECT_TOPIC_RE = re.compile(r"^#\s*PROJECT\s*0?(\d{1,2})\s*(专题.+)$", re.I)
TOPIC_RE = re.compile(r"^#\s*专题\s*([一二三四五六七八九十百零两〇]+)\s*(.*)$")
TOC_TOPIC_RE = re.compile(r"^专题\s*([一二三四五六七八九十百零两〇]+)\s*(.+?)\s*/\d+\s*$")
QUESTION_HEAD_RE = re.compile(
    r"^\s*(?:##\s*)?(?:[OoQq品]\s*|8\s+(?=\d{2,3}[.．、，])|[一二三四五六七八九十]\s+(?=\d{2,3}[.．、，]))?(\d{1,3})[.．、，]?\s*(.*)$"
)
OPTION_RE = re.compile(r"^([A-D])[.．]\s*(.*)$")
IMAGE_RE = re.compile(r"!\[\]\(images/[^)]+\)")
PAGE_RE = re.compile(r"\s*/\s*\d{1,4}\s*$")
LABEL_RE = re.compile(
    r"^[\[\【［]?\s*(解析|技术流|设题陷阱与常见错误分析|归纳总结|脚注|待复核)\s*[\]】］]?\s*[：: ]?\s*(.*)$"
)
TABLE_RE = re.compile(r"<table.*?</table>", re.I | re.S)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
TD_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
NOISE_ONLY_RE = re.compile(r"^[\s\-_=~`|<>\\/.:;·•]+$")
EXAM_REF_RE = re.compile(r"[（(](?:19|20)\d{2}[^（）()]{0,40}?(?:单|多|任|不定项)[^（）()]*[）)]")
EMBEDDED_SPLIT_RE = re.compile(
    r"([。！？；;】\]）)])\s*[:：]?\s*(?=(?:##\s*)?(?:[OoQq品]\s*|8\s+\d{2,3}[.．、，]|[一二三四五六七八九十]\s+\d{2,3}[.．、，]|\d{1,3}[.．、，]))"
)
QUESTION_START_CANDIDATE_RE = re.compile(
    r"(?:^|\n)\s*(?:##\s*)?(?:[OoQq品]\s*|8\s+(?=\d{2,3}[.．、，])|[一二三四五六七八九十]\s+(?=\d{2,3}[.．、，]))?(\d{1,3})[.．、，]\s*",
    re.M,
)

QUESTION_HINTS = ("下列", "哪一", "哪些", "何者", "说法", "表述", "属于", "正确", "错误", "体现", "要求", "金题")


@dataclass
class Stats:
    before_lines: int = 0
    after_lines: int = 0
    front_blocks_removed: int = 0
    appendix_blocks_removed: int = 0
    topics_kept: int = 0
    questions_kept: int = 0
    tables_rewritten: int = 0
    review_count: int = 0
    dropped_images: int = 0
    junk_lines_removed: int = 0
    split_project_topic_lines: int = 0
    normalized_topic_titles: int = 0
    normalized_labels: int = 0
    embedded_question_splits: int = 0
    label_counts: Counter = field(default_factory=Counter)
    noise_summary: Counter = field(default_factory=Counter)


@dataclass
class Question:
    number: int
    stem: str
    options: list[str]
    analysis: list[str]
    supplementary: list[tuple[str, list[str]]]
    review_notes: list[str]


@dataclass
class Topic:
    board: str
    title: str
    raw_lines: list[str] = field(default_factory=list)
    intro: list[str] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    stray_notes: list[str] = field(default_factory=list)


def count_non_empty_blocks(lines: list[str]) -> int:
    count = 0
    in_block = False
    for line in lines:
        if line.strip():
            if not in_block:
                count += 1
            in_block = True
        else:
            in_block = False
    return count


def normalize_text(text: str) -> str:
    text = (
        text.replace("\ufeff", "")
        .replace("\u3000", " ")
        .replace("\xa0", " ")
        .replace("．", ".")
        .replace("：", ":")
        .replace("［", "[")
        .replace("］", "]")
        .replace("【", "[")
        .replace("】", "]")
    )
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def contains_exam_ref(text: str) -> bool:
    return bool(EXAM_REF_RE.search(text))


def clean_cell_text(text: str) -> str:
    text = TAG_RE.sub("", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
    )
    return re.sub(r"\s+", " ", text).strip()


def table_to_text_block(table_html: str) -> str:
    rows: list[str] = []
    for row_html in TR_RE.findall(table_html):
        cells = [clean_cell_text(cell) for cell in TD_RE.findall(row_html)]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append("- " + " | ".join(cells))
    if not rows:
        rows = [f"- {REVIEW_LABEL} 表格内容未稳定识别，请人工抽查。"]
    return TABLE_LABEL + "\n" + "\n".join(rows)


def rewrite_tables(text: str, stats: Stats) -> str:
    def repl(match: re.Match[str]) -> str:
        stats.tables_rewritten += 1
        stats.noise_summary["table_rewritten"] += 1
        return table_to_text_block(match.group(0))

    return TABLE_RE.sub(repl, text)


def split_project_topic_lines(lines: list[str], stats: Stats) -> list[str]:
    out: list[str] = []
    for raw in lines:
        line = normalize_text(raw)
        match = PROJECT_TOPIC_RE.match(line)
        if match:
            stats.split_project_topic_lines += 1
            stats.noise_summary["project_topic_split"] += 1
            out.append(f"# PROJECT{int(match.group(1)):02d}")
            out.append("# " + match.group(2).strip())
            continue
        out.append(line)
    return out


def parse_toc_titles(lines: list[str]) -> list[str]:
    titles: list[str] = []
    for line in lines:
        match = TOC_TOPIC_RE.match(line.strip())
        if match:
            titles.append(f"专题{match.group(1)} {match.group(2).strip()}")
    return titles


def normalize_topic_title(raw: str, idx: int, toc_titles: list[str], stats: Stats) -> str:
    title = re.sub(r"\s+", " ", raw.strip())
    title = re.sub(r"^专题([一二三四五六七八九十百零两〇]+)\s*", r"专题\1 ", title)
    if idx <= len(toc_titles):
        toc_title = re.sub(r"\s+", " ", toc_titles[idx - 1].strip())
        if re.sub(r"\s+", "", toc_title).startswith(re.sub(r"\s+", "", title)):
            title = toc_title
    if title != raw.strip():
        stats.normalized_topic_titles += 1
        stats.noise_summary["topic_title"] += 1
    return title


def canonicalize_label_line(line: str, stats: Stats) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("客观题命题规律"):
        stats.normalized_labels += 1
        stats.label_counts[INTRO_LABEL] += 1
        return [INTRO_LABEL]
    match = LABEL_RE.match(stripped)
    if not match:
        return [stripped]
    canonical = LABEL_MAP.get(match.group(1), ANALYSIS_LABEL)
    stats.normalized_labels += 1
    stats.label_counts[canonical] += 1
    rest = match.group(2).strip()
    return [canonical, rest] if rest else [canonical]


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped in {"#", "##", "###", "目录", "Contents"}:
        return True
    if re.fullmatch(r"/\d{1,4}", stripped):
        return True
    if NOISE_ONLY_RE.fullmatch(stripped):
        return True
    return False


def preprocess_lines(raw_text: str, stats: Stats) -> tuple[list[str], list[str]]:
    text = rewrite_tables(raw_text, stats)
    lines = split_project_topic_lines(text.splitlines(), stats)
    stats.before_lines = len(lines)
    toc_titles = parse_toc_titles(lines)

    body_start = None
    appendix_start = None
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if body_start is None and line.startswith("# PROJECT01"):
            body_start = idx
        if body_start is not None and line in {"## 附录", "# 本书答案速查"}:
            appendix_start = idx
            break
    if body_start is None:
        raise RuntimeError("未找到正文起点 # PROJECT01")

    prefix = lines[:body_start]
    suffix = lines[appendix_start:] if appendix_start is not None else []
    stats.front_blocks_removed = count_non_empty_blocks(prefix)
    stats.appendix_blocks_removed = count_non_empty_blocks(suffix) if suffix else 0

    body_lines = lines[body_start:appendix_start] if appendix_start is not None else lines[body_start:]
    cleaned: list[str] = []
    for raw in body_lines:
        hits = IMAGE_RE.findall(raw)
        if hits:
            stats.dropped_images += len(hits)
            stats.noise_summary["image_removed"] += len(hits)
            raw = IMAGE_RE.sub("", raw)
        line = normalize_text(PAGE_RE.sub("", raw))
        if line.startswith("## "):
            line = line[3:].strip()
        if line.startswith("# ") and not line.startswith("# PROJECT") and not line.startswith("# 专题"):
            line = line[2:].strip()
        if not line or is_noise_line(line):
            if raw.strip():
                stats.junk_lines_removed += 1
                stats.noise_summary["junk_line"] += 1
            continue
        for part in canonicalize_label_line(line, stats):
            if part and not is_noise_line(part):
                cleaned.append(part)
    stats.after_lines = len(cleaned)
    return cleaned, toc_titles


def parse_topics(lines: list[str], toc_titles: list[str], stats: Stats) -> list[Topic]:
    topics: list[Topic] = []
    current: Topic | None = None
    topic_idx = 0
    for line in lines:
        if PROJECT_RE.match(line):
            continue
        match = TOPIC_RE.match(line)
        if match:
            topic_idx += 1
            board = BOARD_BASIC if topic_idx <= EXPECTED_BASIC_TOPICS else BOARD_ADVANCED
            title = normalize_topic_title(
                f"专题{match.group(1)} {match.group(2).strip()}".strip(),
                topic_idx,
                toc_titles,
                stats,
            )
            current = Topic(board=board, title=title)
            topics.append(current)
            continue
        if current is not None:
            current.raw_lines.append(line)
    stats.topics_kept = len(topics)
    return topics


def normalize_possible_question_start(line: str) -> str:
    line = line.strip()
    if not line:
        return line
    line = re.sub(r"^\s*##\s*(?=\d{1,3}[.．、，])", "", line)
    line = re.sub(r"^\s*[:：]\s*(?=\d{1,3}[.．、，])", "", line)
    line = re.sub(r"^\s*[OoQq品]\s*(?=\d{1,3}[.．、，])", "", line)
    line = re.sub(r"^\s*8\s+(?=\d{2,3}[.．、，])", "", line)
    line = re.sub(r"^\s*[一二三四五六七八九十]\s+(?=\d{2,3}[.．、，])", "", line)
    line = re.sub(r"^(\d{1,3})[，,](?=(?:关于|下列|某|甲|乙|丙|丁|行政|国家|国务院|对|有|如))", r"\1. ", line)
    return line.strip()


def prepare_topic_text(lines: list[str], stats: Stats) -> str:
    text = "\n".join(lines)
    text = EMBEDDED_SPLIT_RE.sub(r"\1\n", text)
    split_count = text.count("\n") - ("\n".join(lines)).count("\n")
    if split_count > 0:
        stats.embedded_question_splits += split_count
        stats.noise_summary["embedded_question_split"] += split_count

    normalized_lines: list[str] = []
    for raw in text.splitlines():
        line = normalize_possible_question_start(raw)
        if line:
            normalized_lines.append(line)
    return "\n".join(normalized_lines)


def is_plausible_question_window(window: str) -> bool:
    option_count = sum(token in window for token in ("A.", "B.", "C.", "D."))
    if option_count >= 3:
        return True
    if contains_exam_ref(window[:240]) and any(hint in window[:260] for hint in QUESTION_HINTS):
        return True
    if option_count >= 2 and any(hint in window[:220] for hint in QUESTION_HINTS):
        return True
    if option_count >= 2 and re.search(r"[（(]20\d{2}", window[:260]):
        return True
    return False


def find_question_start(text: str, expected_number: int, start_pos: int) -> int | None:
    patterns = [
        re.compile(
            rf"(?:^|\n)\s*(?:##\s*)?(?:[OoQq品]\s*|8\s+(?=\d{{2,3}}[.．、，])|[一二三四五六七八九十]\s+(?=\d{{2,3}}[.．、，]))?{expected_number}[.．、，]?\s*",
            re.M,
        ),
        re.compile(
            rf"(?:[。！？；;】\]）)]|综上，本题答案为[A-D]+。?)\s*[:：]?\s*(?:##\s*)?(?:[OoQq品]\s*|8\s+(?=\d{{2,3}}[.．、，])|[一二三四五六七八九十]\s+(?=\d{{2,3}}[.．、，]))?{expected_number}[.．、，]?\s*"
        ),
    ]

    for pattern in patterns:
        for match in pattern.finditer(text, start_pos):
            pos = match.start()
            digit_pos = text.find(str(expected_number), pos, match.end())
            if digit_pos == -1:
                digit_pos = pos
            tail = text[digit_pos : digit_pos + 1600]
            if is_plausible_question_window(tail):
                return digit_pos
    return None


def collect_question_positions(text: str, expected_number: int) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    seen_positions: set[int] = set()

    for match in QUESTION_START_CANDIDATE_RE.finditer(text):
        number = int(match.group(1))
        digit_pos = text.find(match.group(1), match.start(), match.end())
        if digit_pos == -1 or digit_pos in seen_positions:
            continue
        tail = text[digit_pos : digit_pos + 1600]
        if not is_plausible_question_window(tail):
            continue
        candidates.append((number, digit_pos))
        seen_positions.add(digit_pos)

    positions: list[tuple[int, int]] = []
    last_number = expected_number - 1
    first_kept = False
    for number, pos in sorted(candidates, key=lambda item: item[1]):
        if not first_kept:
            if number < expected_number:
                continue
            positions.append((number, pos))
            last_number = number
            first_kept = True
            continue
        if number <= last_number:
            continue
        positions.append((number, pos))
        last_number = number

    if positions:
        return positions

    return []


def split_topic_text(topic: Topic, expected_number: int, stats: Stats) -> tuple[list[str], list[str], int]:
    text = prepare_topic_text(topic.raw_lines, stats)
    positions = collect_question_positions(text, expected_number)

    if not positions:
        return topic.raw_lines[:], [], expected_number

    intro_text = text[: positions[0][1]].strip()
    intro_lines = [line.strip() for line in intro_text.splitlines() if line.strip()]

    chunks: list[str] = []
    for idx, (_, pos) in enumerate(positions):
        end = positions[idx + 1][1] if idx + 1 < len(positions) else len(text)
        chunk = text[pos:end].strip()
        if chunk:
            chunks.append(chunk)
    return intro_lines, chunks, positions[-1][0] + 1


def normalize_question_chunk(chunk: str) -> str:
    chunk = chunk.replace("[解析]", f"\n{ANALYSIS_LABEL}\n")
    chunk = chunk.replace("［解析］", f"\n{ANALYSIS_LABEL}\n")
    chunk = chunk.replace("【解析】", f"\n{ANALYSIS_LABEL}\n")
    for raw, label in LABEL_MAP.items():
        chunk = chunk.replace(f"[{raw}]", f"\n{label}\n")
        chunk = chunk.replace(f"［{raw}］", f"\n{label}\n")
        chunk = chunk.replace(f"【{raw}】", f"\n{label}\n")
    chunk = re.sub(r"(?<![A-Za-z0-9])([A-D])[.．](?=\S)", r"\n\1. ", chunk)
    return chunk


def parse_question_block(chunk: str) -> Question | None:
    chunk = normalize_question_chunk(chunk)
    lines = [normalize_text(line) for line in chunk.splitlines() if normalize_text(line)]
    if not lines:
        return None
    head_match = QUESTION_HEAD_RE.match(lines[0])
    if not head_match:
        return None

    number = int(head_match.group(1))
    head_remainder = head_match.group(2).strip()
    stem_parts = [head_remainder] if head_remainder else []
    options: list[str] = []
    analysis: list[str] = []
    supplementary: list[tuple[str, list[str]]] = []
    review_notes: list[str] = []
    current_label: str | None = None
    current_payload: list[str] = []
    stage = "stem"

    def flush_label() -> None:
        nonlocal current_label, current_payload
        if current_label is not None:
            supplementary.append((current_label, current_payload[:]))
        current_label = None
        current_payload = []

    for line in lines[1:]:
        if line == ANALYSIS_LABEL:
            flush_label()
            stage = "analysis"
            continue
        if line in LABEL_MAP.values():
            flush_label()
            current_label = line
            current_payload = []
            stage = "supplementary"
            continue

        option_match = OPTION_RE.match(line)
        if option_match and current_label is None:
            options.append(f"{option_match.group(1)}. {option_match.group(2).strip()}".strip())
            stage = "options"
            continue

        if current_label is not None:
            current_payload.append(line)
            continue

        if stage == "options" and options:
            options[-1] = f"{options[-1]} {line}".strip()
            continue

        if stage == "analysis":
            analysis.append(line)
        else:
            stem_parts.append(line)

    flush_label()

    stem = re.sub(r"\s+", " ", " ".join(part for part in stem_parts if part)).strip()
    if not stem:
        stem = f"{REVIEW_LABEL} 题干未稳定识别"
        review_notes.append("题干未稳定识别。")
    if len(options) != 4:
        review_notes.append(f"选项识别数为 {len(options)}，建议人工抽查。")
    if not analysis:
        review_notes.append("解析块未稳定识别。")

    return Question(
        number=number,
        stem=stem,
        options=options,
        analysis=analysis,
        supplementary=supplementary,
        review_notes=review_notes,
    )


def parse_topic_content(topic: Topic, expected_number: int, stats: Stats) -> int:
    intro_lines, chunks, next_expected = split_topic_text(topic, expected_number, stats)
    if intro_lines:
        if intro_lines and intro_lines[0] == INTRO_LABEL:
            topic.intro.extend(intro_lines[1:])
        else:
            topic.intro.extend([line for line in intro_lines if line != INTRO_LABEL])
    for chunk in chunks:
        question = parse_question_block(chunk)
        if question is None:
            topic.stray_notes.append(chunk)
            continue
        topic.questions.append(question)
    return next_expected


def render_question(question: Question) -> list[str]:
    out = [f"#### {question.number}. {question.stem}", ""]
    out.extend(question.options)
    if question.options:
        out.append("")
    out.append(ANALYSIS_LABEL)
    out.extend(question.analysis or [f"{REVIEW_LABEL} 解析内容未稳定识别。"])
    out.append("")
    for label, payload in question.supplementary:
        out.append(label)
        out.extend(payload or [f"{REVIEW_LABEL} 该标签下内容为空，请人工抽查。"])
        out.append("")
    if question.review_notes:
        out.append(REVIEW_LABEL)
        out.extend(question.review_notes)
        out.append("")
    return out


def render_markdown(topics: list[Topic]) -> str:
    out = [
        f"# {BOOK_TITLE}",
        "",
        f"> 整理说明：本文件由 `{SOURCE_NAME}` 第一遍整理而来，采用“专题 + 题目”结构，保留 `{INTRO_LABEL}`、`{ANALYSIS_LABEL}`、`【技术流】`、`【设题陷阱与常见错误分析】`、`【归纳总结】`、`【脚注】` 等附属内容；本轮不做二次清洗、不切块、不入库。",
        "",
    ]
    current_board = None
    for topic in topics:
        if topic.board != current_board:
            out.append(f"## {topic.board}")
            out.append("")
            current_board = topic.board
        out.append(f"### {topic.title}")
        out.append("")
        if topic.intro:
            out.append(INTRO_LABEL)
            out.extend(topic.intro)
            out.append("")
        if topic.stray_notes:
            out.append(REVIEW_LABEL)
            out.extend(topic.stray_notes)
            out.append("")
        for question in topic.questions:
            out.extend(render_question(question))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def build_report(stats: Stats, topics: list[Topic]) -> str:
    question_count = sum(len(topic.questions) for topic in topics)
    stats.questions_kept = question_count
    stats.review_count = sum(
        len(question.review_notes)
        for topic in topics
        for question in topic.questions
    ) + sum(1 for topic in topics if topic.stray_notes)

    delta = question_count - DECLARED_QUESTION_COUNT
    delta_line = (
        f"- 题目数与原稿声明一致：`{question_count}`。"
        if delta == 0
        else f"- 题目数与原稿声明 `{DECLARED_QUESTION_COUNT}` 存在偏差：当前识别为 `{question_count}`，偏差为 `{delta:+d}`，建议后续抽查专题交界处。"
    )

    label_lines = []
    for label in (
        INTRO_LABEL,
        ANALYSIS_LABEL,
        "【技术流】",
        "【设题陷阱与常见错误分析】",
        "【归纳总结】",
        "【脚注】",
        REVIEW_LABEL,
        TABLE_LABEL,
    ):
        label_lines.append(f"- {label}：`{stats.label_counts.get(label, 0)}`")

    noise_lines = [f"- {key}：`{value}`" for key, value in sorted(stats.noise_summary.items())]
    return "\n".join(
        [
            f"# {BOOK_TITLE}整理说明",
            "",
            "## 本轮范围",
            "",
            f"- 输入文件：`{SOURCE_NAME}`",
            f"- 输出文件：`整理后文本/{DST.name}`",
            "- 处理目标：第一遍整理，重建“基础专题 / 进阶专题 -> 专题 -> 题目”结构，保留附属标签，改写坏掉的 HTML 表格，不做二次清洗、切块或入库。",
            "",
            "## 结构结果",
            "",
            "- 板块数：`2`",
            f"- 基础专题数：`{sum(1 for topic in topics if topic.board == BOARD_BASIC)}`",
            f"- 进阶专题数：`{sum(1 for topic in topics if topic.board == BOARD_ADVANCED)}`",
            f"- 识别专题总数：`{stats.topics_kept}`",
            f"- 识别题目总数：`{question_count}`",
            delta_line,
            "",
            "## 统计",
            "",
            f"- 处理前总行数：`{stats.before_lines}`",
            f"- 进入正文后保留行数：`{stats.after_lines}`",
            f"- 排除的前置非正文块数：`{stats.front_blocks_removed}`",
            f"- 排除的附录块数：`{stats.appendix_blocks_removed}`",
            f"- 改写的复杂表格块数：`{stats.tables_rewritten}`",
            f"- 删除的图片链接数：`{stats.dropped_images}`",
            f"- 清理的噪音行数：`{stats.junk_lines_removed}`",
            f"- 修复的 `PROJECT+专题` 粘连行数：`{stats.split_project_topic_lines}`",
            f"- 统一规范的专题标题数：`{stats.normalized_topic_titles}`",
            f"- 统一规范的标签数：`{stats.normalized_labels}`",
            f"- `【待复核】` 片段数：`{stats.review_count}`",
            "",
            "## 标签统计",
            "",
            *label_lines,
            "",
            "## 典型噪音清理摘要",
            "",
            *(noise_lines or ["- 无。"]),
            "",
        ]
    )


def main() -> None:
    raw_text = SRC.read_text(encoding="utf-8")
    stats = Stats()
    cleaned_lines, toc_titles = preprocess_lines(raw_text, stats)
    topics = parse_topics(cleaned_lines, toc_titles, stats)

    expected_number = 1
    for topic in topics:
        expected_number = parse_topic_content(topic, expected_number, stats)

    markdown = render_markdown(topics)
    report = build_report(stats, topics)

    DST.write_text(markdown, encoding="utf-8")
    REPORT.write_text(report, encoding="utf-8")

    print(f"输出文件：{DST}")
    print(f"说明文件：{REPORT}")
    print(f"专题数：{stats.topics_kept}")
    print(f"题目数：{stats.questions_kept}")
    print(f"表格改写数：{stats.tables_rewritten}")
    print(f"待复核数：{stats.review_count}")


if __name__ == "__main__":
    main()
