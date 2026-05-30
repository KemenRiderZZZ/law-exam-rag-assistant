#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""郄鹏恩《商经知》第一遍整理脚本。

目标：
1. 从 OCR 原稿重建结构化 Markdown；
2. 保留前言，删除封面/CIP/目录/纯导航残片；
3. 以目录为准恢复“篇-专题-节-考点”层级；
4. 做中度清洗，不切块、不导库。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "OCR原稿" / "郄鹏恩《商经知》.md"
DST = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知_整理版.md"
REPORT = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知_整理说明.md"

BOOK_TITLE = "商经知专题讲座精讲卷（2026版）"

PART_RE = re.compile(r"^第([一二三四五六七八九十\d]+)部分\s*(.+篇)$")
TOPIC_RE = re.compile(r"^专题([一二三四五六七八九十\d]+)\s*(.+)$")
SECTION_RE = re.compile(r"^第([一二三四五六七八九十\d]+)节\s*(.+)$")
POINT_RE = re.compile(r"^考点\s*([一二三四五六七八九十\d]+)\s*(.+)$")
PAGE_TAIL_RE = re.compile(r"(?:\*+)?\s*/\s*[0-9A-Za-zIlO]{1,4}(?:\*+)?\s*$")
DOT_LEADER_RE = re.compile(r"[.．。·•・⋯…'\s]{3,}")
HEADING_LINE_RE = re.compile(r"^(#{1,6})\s+")
TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
LIST_LINE_RE = re.compile(
    r"^\s*(?:"
    r"[-*•]|"
    r"\d+\.\s+|"
    r"[（(]?[一二三四五六七八九十\d]+[)）]\s*|"
    r"[一二三四五六七八九十]+、|"
    r"[①②③④⑤⑥⑦⑧⑨⑩]"
    r")"
)
NOISE_ONLY_RE = re.compile(r"^[\s_\-=\^~`<>|/\\\[\]{}■□◆△▲•.。·:：;；,，]+$")
TRAILING_GARBAGE_RE = re.compile(r"[\s_\-=\^~`<>|/\\]{4,}.*$")

INLINE_REPLACEMENTS = {
    "\u3000": " ",
    "\xa0": " ",
    "（-）": "（一）",
    "(-)": "（一）",
    "（二） ": "（二）",
    "（三） ": "（三）",
    "（四） ": "（四）",
    "（五） ": "（五）",
    "（六） ": "（六）",
    "——": "—",
    "--": "—",
    "T运行T": "、运行、",
    "\\|": "|",
    "\\\"": "\"",
    "\\'": "'",
}

SKIP_EXACT = {
    "目录",
    "Contents",
    "Preface",
    "体系结构图",
    "框架体系",
    "续表",
    "第二部分",
    "第三部分",
    "第四部分",
    "第五部分",
    "第一部分",
}

SKIP_CONTAINS = [
    "图书在版编目",
    "中国国家版本馆",
    "中国石化出版社",
    "全国各地新华书店经销",
    "印张",
    "开本",
    "定价",
    "http://",
    "http：//",
    "E-mail",
    "纸质书购买",
    "解密VX",
]

HELPER_LABELS = {"体系解说", "复习旨要", "特别提示"}
PART_NAMES = {
    "商法篇",
    "经济法篇",
    "环境与自然资源法篇",
    "劳动与社会保障法篇",
    "知识产权法篇",
}


@dataclass
class TocRecord:
    kind: str
    title: str
    part: str | None
    topic: str | None
    section: str | None
    norm: str


def strip_emphasis(text: str) -> str:
    return text.replace("**", "").replace("__", "")


def normalize_spaces(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for old, new in INLINE_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n", "\n", text)
    return text


def clean_page_tail(text: str) -> str:
    text = strip_emphasis(text).strip()
    text = PAGE_TAIL_RE.sub("", text).strip()
    return text


def normalize_title(text: str) -> str:
    text = strip_emphasis(text)
    text = PAGE_TAIL_RE.sub("", text)
    text = text.replace("——", "—").replace("--", "—")
    text = text.replace("◎", "")
    text = text.replace(" ", "")
    text = text.replace("\t", "")
    text = re.sub(r"[|｜]", "", text)
    text = re.sub(r"[.．。·•・⋯…'\"“”‘’]", "", text)
    return text.strip()


def cleanup_toc_line(line: str) -> str:
    line = strip_emphasis(line).strip()
    if not line:
        return ""
    line = line.replace("◎", " ")
    line = line.replace("•", " ")
    line = line.replace("'", " ")
    line = line.replace("I03", "103").replace("H3", "113")
    if TABLE_LINE_RE.match(line):
        cells = [cell.strip() for cell in line.strip("|").split("|") if cell.strip()]
        if not cells:
            return ""
        if cells[0].startswith("考点"):
            line = "".join(cells)
        else:
            line = " ".join(cells)
    line = DOT_LEADER_RE.sub(" ", line)
    line = clean_page_tail(line)
    line = re.sub(r"\s+\d{1,4}$", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def parse_toc(lines: list[str]) -> list[TocRecord]:
    records: list[TocRecord] = []
    current_part: str | None = None
    current_topic: str | None = None
    current_section: str | None = None

    for raw in lines:
        line = cleanup_toc_line(raw)
        if not line:
            continue
        part_match = PART_RE.match(line)
        if part_match:
            current_part = part_match.group(2).strip()
            current_topic = None
            current_section = None
            continue

        topic_match = TOPIC_RE.match(line)
        if topic_match:
            current_topic = f"专题{topic_match.group(1)} {topic_match.group(2).strip()}"
            current_section = None
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            current_section = f"第{section_match.group(1)}节 {section_match.group(2).strip()}"
            records.append(
                TocRecord(
                    kind="section",
                    title=current_section,
                    part=current_part,
                    topic=current_topic,
                    section=current_section,
                    norm=normalize_title(current_section),
                )
            )
            continue

        point_match = POINT_RE.match(line)
        if point_match:
            point_title = f"考点{point_match.group(1)} {point_match.group(2).strip()}"
            records.append(
                TocRecord(
                    kind="point",
                    title=point_title,
                    part=current_part,
                    topic=current_topic,
                    section=current_section,
                    norm=normalize_title(point_title),
                )
            )

    return records


def find_body_start(lines: list[str]) -> int:
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped not in {"第一部分", "第一部分商法篇"}:
            continue
        window = "\n".join(lines[idx:idx + 25])
        if "商法体系结构图" in window or "公司法框架体系" in window:
            return idx
    raise RuntimeError("未找到正文起点")


def find_toc_start(lines: list[str]) -> int:
    for idx, line in enumerate(lines):
        if line.strip() == "目录":
            return idx
    raise RuntimeError("未找到目录起点")


def extract_preface(lines: list[str], toc_start: int) -> list[str]:
    preface_start = None
    for idx, line in enumerate(lines[:toc_start]):
        if line.strip() == "以信念为灯，以韧性为盾":
            preface_start = idx
            break
    if preface_start is None:
        return []
    return lines[preface_start:toc_start]


def clean_body_line(line: str) -> str:
    line = strip_emphasis(line)
    line = line.strip()
    if not line:
        return ""
    line = TRAILING_GARBAGE_RE.sub("", line).strip()
    line = line.replace("［", "【").replace("］", "】")
    line = line.replace("〈", "《").replace("〉", "》")
    line = line.replace("｛", "（").replace("｝", "）")
    line = line.replace("•", "·")
    line = line.replace("……", "…")
    line = line.replace(" .", ".")
    line = line.replace(" ,", ",")
    line = re.sub(r"\s+/+\s*", "/", line)
    line = re.sub(r"\s+", " ", line)
    line = clean_page_tail(line)
    line = re.sub(r"^考点(\d+)(\S)", r"考点\1 \2", line)
    line = re.sub(r"^考点[iI](\S)", r"考点1 \1", line)
    line = re.sub(r"^第([一二三四五六七八九十\d]+)节(\S)", r"第\1节 \2", line)
    line = re.sub(r"^专题([一二三四五六七八九十\d]+)(\S)", r"专题\1 \2", line)
    line = line.replace("第一节概 述", "第一节概述")
    line = line.replace("第一节总 ", "第一节总")
    line = line.replace("第四节汇 票", "第四节汇票")
    line = line.replace("第五节支 票", "第五节支票")
    line = line.replace("专题四◎", "专题四 ")
    topic_noise = re.search(r"专题([一二三四五六七八九十\d]+).*?([一-龥]{2,}(?:法|保护))", line)
    if topic_noise and not TOPIC_RE.match(line):
        line = f"专题{topic_noise.group(1)} {topic_noise.group(2)}"
    line = re.sub(r"^(专题[一二三四五六七八九十\d]+\s+.+?)\s+\d{1,4}$", r"\1", line)
    line = re.sub(r"^(第[一二三四五六七八九十\d]+节\s+.+?)\s+\d{1,4}$", r"\1", line)
    line = re.sub(r"^(考点\s*[一二三四五六七八九十\d]+\s+.+?)\s+\d{1,4}$", r"\1", line)
    return line.strip()


def should_skip_line(line: str) -> bool:
    if not line:
        return False
    if line in SKIP_EXACT:
        return True
    if any(token in line for token in SKIP_CONTAINS):
        return True
    if "本专题小结" in line:
        return True
    if NOISE_ONLY_RE.match(line):
        return True
    if len(line) <= 3 and re.fullmatch(r"[A-Za-z]+", line):
        return True
    if line in {"Qie", "Peng", "En", "ill", "雪", "■ 1 ■", "I I I F"}:
        return True
    if line in {"商法", "经济法", "知识产权法", "则"}:
        return True
    if "专题" in line and not TOPIC_RE.match(line) and len(line) <= 40:
        return True
    return False


def is_diagram_line(line: str) -> bool:
    if not line:
        return False
    if "体系结构图" in line or "框架体系" in line:
        return True
    if line.startswith(("商法", "经济法", "公司法", "竞争法")) and len(line) <= 8:
        return True
    if NOISE_ONLY_RE.match(line):
        return True
    if re.search(r"[*_<>^]{3,}", line):
        return True
    if re.fullmatch(r"[A-Za-z0-9\s\-—·]+", line) and len(line) <= 16:
        return True
    return False


def mark_low_confidence(line: str) -> str:
    if not line or line.startswith("【待复核】"):
        return line
    suspicious = [
        r"[A-Za-z]\?[A-Za-z一-龥]",
        r"[一-龥][A-Za-z][一-龥]",
        r"[A-Za-z]\d+[A-Za-z]",
        r"[_^]{3,}",
    ]
    if any(re.search(pattern, line) for pattern in suspicious):
        return f"【待复核】{line}"
    return line


def split_compound_line(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []

    for marker in ["以信念为灯，以韧性为盾", "本书写作特点"]:
        if line.startswith(marker) and line != marker:
            tail = line[len(marker):].strip()
            if tail:
                return [marker, tail]
            return [marker]

    helper_match = re.match(r"^(体系解说|复习旨要|特别提示)(.*)$", line)
    if helper_match:
        head = helper_match.group(1)
        tail = helper_match.group(2).strip("：:：·. I")
        if tail:
            return [head, tail]
        return [head]

    sec_pos = line.find("考点")
    if sec_pos > 0 and SECTION_RE.match(line[:sec_pos].strip()):
        section = line[:sec_pos].strip()
        point = line[sec_pos:].strip()
        point = re.sub(r"^考点[iI](\S)", r"考点1 \1", point)
        return [section, point]

    return [line]


def merge_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if not line:
            if merged and merged[-1] != "":
                merged.append("")
            continue

        is_structural = (
            HEADING_LINE_RE.match(line)
            or TABLE_LINE_RE.match(line)
            or LIST_LINE_RE.match(line)
            or line.startswith("> ")
            or line.startswith("**")
        )
        if not merged or merged[-1] == "" or is_structural:
            merged.append(line)
            continue

        prev = merged[-1]
        if (
            HEADING_LINE_RE.match(prev)
            or TABLE_LINE_RE.match(prev)
            or LIST_LINE_RE.match(prev)
            or prev.startswith("> ")
            or prev.startswith("**")
        ):
            merged.append(line)
            continue

        if prev[-1] in "。！？；：”）】》":
            merged.append(line)
        else:
            merged[-1] = f"{prev}{line}"

    while merged and merged[-1] == "":
        merged.pop()
    return merged


def build_markdown(raw_lines: list[str], records: list[TocRecord]) -> tuple[list[str], dict[str, int]]:
    out: list[str] = [f"# {BOOK_TITLE}", "", "## 前言", ""]
    stats = {
        "helper_labels": 0,
        "low_confidence": 0,
        "sections": 0,
        "points": 0,
    }

    body_start = find_body_start(raw_lines)
    toc_start = find_toc_start(raw_lines)
    preface_lines = extract_preface(raw_lines, toc_start)

    for raw in preface_lines:
        for piece in split_compound_line(clean_body_line(raw)):
            line = piece
            if not line or should_skip_line(line):
                continue
            if line == "以信念为灯，以韧性为盾":
                out.extend([f"**{line}**", ""])
                continue
            if line == "本书写作特点":
                out.extend(["**本书写作特点**", ""])
                stats["helper_labels"] += 1
                continue
            out.append(mark_low_confidence(line))

    out.append("")

    ptr = 0
    current_part: str | None = None
    current_topic: str | None = None
    current_section: str | None = None
    skip_diagram = False

    def emit_context(record: TocRecord) -> None:
        nonlocal current_part, current_topic, current_section
        if record.part and record.part != current_part:
            if out and out[-1] != "":
                out.append("")
            out.append(f"## {record.part}")
            out.append("")
            current_part = record.part
            current_topic = None
            current_section = None
        if record.topic and record.topic != current_topic:
            if out and out[-1] != "":
                out.append("")
            out.append(f"### {record.topic}")
            out.append("")
            current_topic = record.topic
            current_section = None

    body_lines = raw_lines[body_start:]
    for raw in body_lines:
        pieces = split_compound_line(clean_body_line(raw))
        if not pieces:
            continue

        for line in pieces:
            if not line or should_skip_line(line):
                continue

            if line in {"商法", "经济法篇", "知识产权法篇"} or line in PART_NAMES:
                continue

            if line.endswith("体系结构图") or line.endswith("框架体系"):
                next_topic = records[ptr].topic if ptr < len(records) else None
                topic_root = ""
                if next_topic:
                    topic_root = re.sub(r"^专题[一二三四五六七八九十\d]+\s*", "", next_topic)
                if next_topic and topic_root and topic_root in line:
                    emit_context(records[ptr])
                skip_diagram = True
                continue

            if skip_diagram:
                if line in HELPER_LABELS or SECTION_RE.match(line) or POINT_RE.match(line):
                    skip_diagram = False
                elif "体系解说" in line or "复习旨要" in line:
                    skip_diagram = False
                else:
                    continue

            next_topic = records[ptr].topic if ptr < len(records) else None
            if next_topic:
                topic_root = re.sub(r"^专题[一二三四五六七八九十\d]+\s*", "", next_topic)
                if topic_root and topic_root in line and current_topic != next_topic:
                    emit_context(records[ptr])
                    loose_norm = normalize_title(line)
                    if "专题" in line or loose_norm.endswith(normalize_title(topic_root)):
                        continue

            if line in HELPER_LABELS:
                out.append(f"**{line}**")
                out.append("")
                stats["helper_labels"] += 1
                continue

            norm = normalize_title(line)
            matched_idx = None
            for probe in range(ptr, min(ptr + 10, len(records))):
                if norm == records[probe].norm:
                    matched_idx = probe
                    break
            if matched_idx is not None:
                record = records[matched_idx]
                ptr = matched_idx + 1
                emit_context(record)
                if record.kind == "section":
                    if out and out[-1] != "":
                        out.append("")
                    out.append(f"#### {record.title}")
                    out.append("")
                    current_section = record.section
                    stats["sections"] += 1
                else:
                    if record.section and record.section != current_section:
                        if out and out[-1] != "":
                            out.append("")
                        out.append(f"#### {record.section}")
                        out.append("")
                        current_section = record.section
                        stats["sections"] += 1
                    level = "####" if record.section is None else "#####"
                    if out and out[-1] != "":
                        out.append("")
                    out.append(f"{level} {record.title}")
                    out.append("")
                    stats["points"] += 1
                continue

            section_match = SECTION_RE.match(line)
            if section_match:
                section_title = f"第{section_match.group(1)}节 {section_match.group(2).strip()}"
                if len(section_match.group(2).strip()) < 2:
                    continue
                if out and out[-1] != "":
                    out.append("")
                out.append(f"#### {section_title}")
                out.append("")
                current_section = section_title
                stats["sections"] += 1
                continue

            point_match = POINT_RE.match(line)
            if point_match:
                point_title = f"考点{point_match.group(1)} {point_match.group(2).strip()}"
                if out and out[-1] != "":
                    out.append("")
                out.append(f"{'####' if current_section is None else '#####'} {point_title}")
                out.append("")
                stats["points"] += 1
                continue

            line = mark_low_confidence(line)
            if line.startswith("【待复核】"):
                stats["low_confidence"] += 1
            out.append(line)

    merged = merge_lines(out)
    return merged, stats


def build_report(stats: dict[str, int]) -> str:
    lines = [
        "# 郄鹏恩商经知_整理说明",
        "",
        "## 本轮目标",
        "",
        "- 将 `OCR原稿/郄鹏恩《商经知》.md` 整理为适合后续切块的结构化 Markdown。",
        "- 保留前言，删除封面、CIP、目录及明显导航残片。",
        "- 本轮不切块、不生成 JSONL、不导入向量库。",
        "",
        "## 结构约定",
        "",
        "- `#` 书名。",
        "- `##` 篇级标题，按原书内容保留商法篇、经济法篇、环境与自然资源法篇、劳动与社会保障法篇、知识产权法篇。",
        "- `###` 专题标题。",
        "- `####` 节标题；若某专题原书无“节”层，则考点直接挂在专题下。",
        "- `#####` 考点标题。",
        "",
        "## 清洗规则",
        "",
        "- 删除封面、版权页、CIP、目录页、页码尾巴和纯图示/导航残片。",
        "- 目录仅用于恢复层级，不写回主整理稿。",
        "- 保留“体系解说”“复习旨要”“特别提示”等辅助文字块。",
        "- 表格尽量原样保留；明显错位的框架图与 ASCII 噪音不保留。",
        "- 低置信内容统一加 `【待复核】` 标记，供下一轮复核。",
        "",
        "## 本轮结果",
        "",
        f"- 识别节标题：{stats['sections']} 条。",
        f"- 识别考点标题：{stats['points']} 条。",
        f"- 保留辅助标签：{stats['helper_labels']} 处。",
        f"- 标记 `【待复核】`：{stats['low_confidence']} 处。",
        "",
        "## 下一轮建议",
        "",
        "- 先针对 `【待复核】` 做人工抽查，再决定是否补第二遍精修。",
        "- 切块时优先按“篇 -> 专题 -> 节 -> 考点”分层；无节专题按“专题 -> 考点”处理。",
        "- 若需要保留来源定位，可在切块阶段补充篇/专题/考点路径元数据，而不是把页码写回正文。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    text = normalize_spaces(SRC.read_text(encoding="utf-8"))
    raw_lines = text.split("\n")
    toc_start = find_toc_start(raw_lines)
    body_start = find_body_start(raw_lines)
    toc_records = parse_toc(raw_lines[toc_start:body_start])
    markdown_lines, stats = build_markdown(raw_lines, toc_records)
    DST.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    REPORT.write_text(build_report(stats), encoding="utf-8")
    print(f"写入整理稿：{DST}")
    print(f"写入说明：{REPORT}")
    print(f"节标题：{stats['sections']}；考点标题：{stats['points']}；待复核：{stats['low_confidence']}")


if __name__ == "__main__":
    main()
