#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行政法第二阶段二次清洗脚本。

本轮目标：
1. 以 OCR 原稿为主，按正文顺序重建专题边界；
2. 仅把一阶段整理稿作为概览与局部规则参考；
3. 产出全文可读、条目化讲义风格的 Markdown；
4. 暂不切块、暂不导库、暂不生成 JSONL。
"""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SRC_OCR = PROJECT_ROOT / "OCR原稿" / "李佳《行政法》2表格版.md"
SRC_STAGE1 = PROJECT_ROOT / "整理后文本" / "李佳行政法_整理版.md"
DST = PROJECT_ROOT / "整理后文本" / "李佳行政法_二次清洗版.md"
RULES_DOC = PROJECT_ROOT / "整理后文本" / "李佳行政法_二次清洗说明.md"

BOOK_TITLE = "李佳行政法专题讲座精讲卷（2026版）"
OVERVIEW_TITLE = "行政法学体系概览"

TOPIC_SPECS = [
    {
        "title": "专题一 行政法概述",
        "phase": "main",
        "hint_line": 353,
        "markers": ["第一节行政法的基本概念及体系", "第二节行政法的基本原则"],
    },
    {
        "title": "专题二 行政主体",
        "phase": "main",
        "hint_line": 719,
        "markers": ["一、行政主体的概念", "二、行政机关", "五、行政主体的机构设置和编制管理"],
    },
    {
        "title": "专题三 公务员法",
        "phase": "main",
        "hint_line": 1071,
        "markers": ["公务员的内涵", "公务员的进、转、出制度", "公务员的管理制度"],
    },
    {
        "title": "专题四 抽象行政行为",
        "phase": "main",
        "hint_line": 1531,
        "markers": ["第一节抽象行政行为概述", "第二节行政法规制定程序", "第三节行政规章的制定程序"],
    },
    {
        "title": "专题五 具体行政行为概述",
        "phase": "main",
        "hint_line": 2097,
        "markers": ["第一节具体行政行为的概念", "第二节具体行政行为的成立和效力"],
    },
    {
        "title": "专题六 行政许可",
        "phase": "main",
        "hint_line": 2717,
        "markers": ["第一节行政许可的概述", "第二节行政许可的设定与具体规定", "第三节行政许可的实施", "第四节行政许可的监督检查"],
    },
    {
        "title": "专题七 行政处罚",
        "phase": "main",
        "hint_line": 3413,
        "markers": ["第一节行政处罚概述", "第二节行政处罚的设定与具体规定", "第三节行政处罚的实施", "第四节治安管理处罚的实施", "第五节行政处罚的执行"],
    },
    {
        "title": "专题八 行政强制",
        "phase": "main",
        "hint_line": 4697,
        "title_markers": ["专题八", "行政强制"],
        "markers": ["第一节行政强制概述", "第二节行政强制的种类和设定", "第三节行政强制措施的实施", "第四节行政强制执行的实施"],
    },
    {
        "title": "专题九 其他具体行政行为",
        "phase": "main",
        "hint_line": 5654,
        "markers": ["行政确认", "行政裁决", "行政给付", "行政奖励", "行政征收与行政征用"],
    },
    {
        "title": "专题十 政府信息公开",
        "phase": "main",
        "hint_line": 5800,
        "markers": ["政府信息的公开主体", "政府信息公开的范围", "政府信息公开的程序", "信息更正程序"],
    },
    {
        "title": "专题十一 行政争议法总论",
        "phase": "main",
        "hint_line": 6111,
        "markers": ["行政复议与行政诉讼的联系", "复议、诉讼自由选择", "复议终局"],
    },
    {
        "title": "专题十二 行政诉讼参加人",
        "phase": "main",
        "hint_line": 6426,
        "markers": ["第一节行政诉讼被告", "第二节行政诉讼原告", "第三节共同诉讼", "第四节行政诉讼第三人", "第五节诉讼代表人与诉讼代理人"],
    },
    {
        "title": "专题十三 行政诉讼的管辖",
        "phase": "main",
        "hint_line": 7238,
        "markers": ["第一节管辖的一般原理", "第二节管辖的具体知识"],
    },
    {
        "title": "专题十四 行政诉讼的受案范围",
        "phase": "main",
        "hint_line": 7494,
        "markers": ["第一节受案范围概述", "第二节具体行政行为可受案", "第三节行政合同可受案", "第四节部分抽象行政行为可附带性受案"],
    },
    {
        "title": "专题十五 行政诉讼程序",
        "phase": "main",
        "hint_line": 7870,
        "markers": ["第一节起诉和受理", "第二节行政诉讼审理程序", "第三节行政诉讼审理中的特殊制度"],
    },
    {
        "title": "专题十六 行政诉讼证据",
        "phase": "main",
        "hint_line": 8916,
        "markers": ["行政诉讼证据", "举证责任"],
    },
    {
        "title": "专题十七 行政诉讼的法律适用",
        "phase": "main",
        "hint_line": 9434,
        "markers": ["行政诉讼的法律适用"],
    },
    {
        "title": "专题十八 行政诉讼的裁判与执行",
        "phase": "main",
        "hint_line": 9527,
        "markers": ["第一节一审判决", "第二节二审判决"],
    },
    {
        "title": "专题十九 行政公益诉讼",
        "phase": "main",
        "hint_line": 9988,
        "markers": ["行政公益诉讼"],
    },
    {
        "title": "专题二十 行政协议及其诉讼制度",
        "phase": "main",
        "hint_line": 10024,
        "markers": ["行政协议"],
    },
    {
        "title": "专题二十一 行政复议制度",
        "phase": "main",
        "hint_line": 10414,
        "title_markers": ["行政复议制度"],
        "markers": ["第一节行政复议受案范围", "第二节行政复议参加人和行政复议机关"],
    },
    {
        "title": "专题二十二 国家赔偿",
        "phase": "main",
        "hint_line": 11575,
        "title_markers": ["专题二十二", "国家赔偿"],
        "markers": ["国家赔偿", "第一节国家赔偿总论", "第二节行政赔偿", "第四节国家赔偿方式、标准和费用"],
    },
    {
        "title": "专题一 行政行为定性（进阶篇）",
        "phase": "advanced",
        "hint_line": 12620,
        "title_markers": ["行为定性"],
        "markers": ["行政行为定性", "行为定性"],
    },
    {
        "title": "专题二 行政处罚、行政许可、行政强制知识对比（进阶篇）",
        "phase": "advanced",
        "hint_line": 12748,
        "title_markers": ["行政处罚、行政许可、行政强制知识对比"],
        "markers": ["行政处罚、行政许可、行政强制知识对比"],
    },
    {
        "title": "专题三 经过复议再起诉的几个难点知识（进阶篇）",
        "phase": "advanced",
        "hint_line": 12803,
        "title_markers": ["经过复议再起诉的几个难点知识", "复议再起诉的几个难点知识"],
        "markers": ["经过复议再起诉的几个难点知识", "复议再起诉的几个难点知识"],
    },
    {
        "title": "专题四 政府信息公开行政案件知识点总结（进阶篇）",
        "phase": "advanced",
        "hint_line": 12871,
        "title_markers": ["政府信息公开行政案件知识点总结"],
        "markers": ["政府信息公开行政案件知识点总结"],
    },
    {
        "title": "专题五 行政诉讼与其他诉讼交叉案件（进阶篇）",
        "phase": "advanced",
        "hint_line": 12950,
        "title_markers": ["行政诉讼与其他诉讼交叉案件"],
        "markers": ["行政诉讼与其他诉讼交叉案件"],
    },
    {
        "title": "专题六 行政法必背细节归纳（进阶篇）",
        "phase": "advanced",
        "hint_line": 13101,
        "title_markers": ["行政法必背细节归纳", "必背细节归纳"],
        "markers": ["行政法必背细节归纳", "必背细节归纳"],
    },
]

TOPIC_TITLES = [item["title"] for item in TOPIC_SPECS]
TOPIC_TITLE_SET = set(TOPIC_TITLES)

SECTION_RE = re.compile(r"^第[一二三四五六七八九十百千零两\d]+节")
POINT_RE = re.compile(r"^知识点[一二三四五六七八九十百千零两\d]+")
MAIN_RE = re.compile(r"^[一二三四五六七八九十百千零两\d]+、")
SUB_RE = re.compile(r"^[（(][一二三四五六七八九十百千零两\d]+[)）]")
LIST_RE = re.compile(r"^(?:[（(]?\d+[）)]?[、.]?|[A-D][.．]|[①②③④⑤⑥⑦⑧⑨⑩])\s*")
TABLE_LINE_RE = re.compile(r"^\s*\|")
TABLE_BORDER_RE = re.compile(r"^[\|\-:\s]+$")
PURE_SYMBOL_RE = re.compile(r"^[\-\|_=~^·•\.\s]{3,}$")
ONLY_PAGE_RE = re.compile(r"^\d{1,4}$")
LOW_CONF_ASCII_RE = re.compile(r"[A-Za-z]{5,}")
RAW_ADVANCED_START = 12613


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\[([^\]]+)\]\(#bookmark\d+\s*\"[^\"]*\"\)", r"\1", text)
    text = re.sub(r"\[\]\{#bookmark\d+\s*\.anchor\}", "", text)
    text = re.sub(r"#bookmark\d+", "", text)
    text = re.sub(r"\{\.[^}]+\}", "", text)
    text = text.replace("<br><br>", "\n").replace("<br>", "\n")
    text = text.replace("\\(", "(").replace("\\)", ")")
    text = text.replace("\\[", "[").replace("\\]", "]")
    text = text.replace('\\"', '"').replace("\\'", "'")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def normalize_compare(text: str) -> str:
    text = re.sub(r"[*_`#>\s]", "", text)
    text = re.sub(r"[，。；：！？、（）()《》【】“”‘’\"'./\\\-—…·|]", "", text)
    return text.strip()


def clean_inline(line: str) -> str:
    line = line.replace("\xa0", " ").replace("\t", " ").strip()
    line = re.sub(r"\*{1,}", "", line)
    line = re.sub(r"_{2,}", "", line)
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"\s+([，。；：？！、）》】])", r"\1", line)
    line = re.sub(r"([（《【])\s+", r"\1", line)
    line = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", line)
    line = re.sub(r"^\s*[■◆●◦]\s*", "", line)
    return line.strip()


def short_key(title: str) -> str:
    return title.split(" ", 1)[0]


def subject_fragment(title: str) -> str:
    return title.split(" ", 1)[1] if " " in title else title


def find_line_from(lines: list[str], marker: str, start: int) -> int | None:
    target = normalize_compare(marker)
    if not target:
        return None
    for idx in range(start, len(lines)):
        if target in normalize_compare(lines[idx]):
            return idx
    if 4 <= len(target) <= 8:
        for idx in range(start, len(lines)):
            compared = normalize_compare(lines[idx])
            if not compared:
                continue
            if target[:4] in compared or target[-4:] in compared or compared in target:
                return idx
    return None


def detect_advanced_start(lines: list[str]) -> int:
    pos = find_line_from(lines, "进阶篇", 10000)
    return pos if pos is not None else RAW_ADVANCED_START


def adjusted_hint_index(lines: list[str], spec: dict[str, object]) -> int:
    hint = int(spec.get("hint_line", 1)) - 1
    if str(spec.get("phase", "main")) != "advanced":
        return hint
    advanced_start = detect_advanced_start(lines)
    delta = advanced_start - RAW_ADVANCED_START
    return max(advanced_start, hint + delta)


def phase_range(lines: list[str], phase: str, total_lines: int) -> tuple[int, int]:
    advanced_start = detect_advanced_start(lines)
    if phase == "advanced":
        return advanced_start, total_lines
    return 0, advanced_start


def find_line_in_window(lines: list[str], marker: str, start: int, end: int) -> int | None:
    target = normalize_compare(marker)
    if not target:
        return None
    start = max(0, start)
    end = min(len(lines), end)
    for idx in range(start, end):
        compared = normalize_compare(lines[idx])
        if target and target in compared:
            return idx
    if 4 <= len(target) <= 8:
        for idx in range(start, end):
            compared = normalize_compare(lines[idx])
            if not compared:
                continue
            if target[:4] in compared or target[-4:] in compared or compared in target:
                return idx
    return None


def find_explicit_title_anchor(lines: list[str], spec: dict[str, object], lower_bound: int) -> int | None:
    hint_line = adjusted_hint_index(lines, spec)
    phase_start, phase_end = phase_range(lines, str(spec.get("phase", "main")), len(lines))
    start = max(lower_bound, phase_start, hint_line - 120)
    end = min(phase_end, hint_line + 60)
    title_markers = list(spec.get("title_markers", []))
    title_markers.extend([spec["title"], subject_fragment(str(spec["title"])), short_key(str(spec["title"]))])
    candidates: list[int] = []
    for marker in title_markers:
        pos = find_line_in_window(lines, str(marker), start, end)
        if pos is not None:
            candidates.append(pos)
    if not candidates:
        return None
    return min(candidates)


def find_core_anchors(lines: list[str]) -> list[dict[str, object]]:
    anchors: list[dict[str, object]] = []
    cursor = 0
    for spec in TOPIC_SPECS:
        phase_start, phase_end = phase_range(lines, str(spec.get("phase", "main")), len(lines))
        hint_line = adjusted_hint_index(lines, spec)
        start = max(cursor, phase_start, hint_line - 140)
        end = min(phase_end, hint_line + 220)
        search_markers = list(spec["markers"]) + list(spec.get("title_markers", [])) + [spec["title"], subject_fragment(spec["title"]), short_key(spec["title"])]
        found = None
        used = None
        for marker in search_markers:
            pos = find_line_in_window(lines, marker, start, end)
            if pos is None:
                pos = find_line_from(lines, marker, max(cursor, phase_start))
            if pos is not None:
                found = pos
                used = marker
                break
        if found is None:
            raise RuntimeError(f"未找到专题锚点：{spec['title']}")
        anchors.append({"title": spec["title"], "core": found, "marker": used})
        cursor = found + 1
    return anchors


def refine_topic_start(lines: list[str], spec: dict[str, object], core: int, lower_bound: int) -> int:
    title = str(spec["title"])
    explicit = find_explicit_title_anchor(lines, spec, lower_bound)
    if explicit is not None:
        return explicit

    hint_line = adjusted_hint_index(lines, spec)
    phase_start, _ = phase_range(lines, str(spec.get("phase", "main")), len(lines))
    window_start = max(lower_bound, phase_start, min(core, hint_line) - 220)
    strong: list[int] = []
    weak: list[int] = []
    title_cmp = normalize_compare(title)
    short_cmp = normalize_compare(short_key(title))
    subject_cmp = normalize_compare(subject_fragment(title))
    for idx in range(window_start, core + 1):
        current = clean_inline(lines[idx])
        current_cmp = normalize_compare(current)
        if not current_cmp:
            continue
        if current_cmp == short_cmp or title_cmp in current_cmp or subject_cmp in current_cmp:
            strong.append(idx)
            continue
        if current in {"知识索引", "本专题命题规律", "笔记要点", "进阶篇"} or "知识索引" in current or "命题规律" in current:
            weak.append(idx)
    if strong:
        return min(strong)
    if weak:
        return max(weak)
    return core


def build_topic_segments(lines: list[str]) -> tuple[list[dict[str, object]], list[str]]:
    anchors = find_core_anchors(lines)
    starts: list[int] = []
    anchor_notes: list[str] = []
    lower_bound = 0
    for item, spec in zip(anchors, TOPIC_SPECS):
        start = refine_topic_start(lines, spec, int(item["core"]), lower_bound)
        starts.append(start)
        lower_bound = int(item["core"]) + 1
        marker = str(item["marker"])
        title = str(item["title"])
        explicit = find_explicit_title_anchor(lines, spec, 0)
        if explicit is not None:
            anchor_notes.append(f"{title}：起点优先命中 OCR 显式标题附近区域（约第 {explicit + 1} 行）。")
        elif normalize_compare(marker) != normalize_compare(title):
            anchor_notes.append(f"{title}：起点依赖正文锚点“{marker}”重建。")

    segments: list[dict[str, object]] = []
    for idx, item in enumerate(anchors):
        start = starts[idx]
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        segments.append(
            {
                "title": item["title"],
                "marker": item["marker"],
                "start": start,
                "end": end,
                "lines": lines[start:end],
            }
        )
    return segments, anchor_notes


def extract_stage1_overview(stage1_text: str) -> list[str]:
    lines = [line.rstrip() for line in stage1_text.splitlines()]
    capture = False
    out: list[str] = []
    for line in lines:
        current = clean_inline(line)
        if current == f"## {OVERVIEW_TITLE}":
            capture = True
            continue
        if capture and current.startswith("## "):
            break
        if capture:
            out.append(current)
    return squeeze(out)


def build_fallback_overview(ocr_lines: list[str]) -> list[str]:
    out: list[str] = []
    capture = False
    table_block: list[str] = []
    for raw in ocr_lines:
        line = clean_inline(raw)
        if line == "行政法学体系图":
            capture = True
            continue
        if capture and line == "目录":
            break
        if not capture:
            continue
        if is_table_line(raw):
            table_block.append(raw.strip())
            continue
        if table_block:
            out.extend(convert_table(table_block))
            out.append("")
            table_block = []
        if line:
            out.append(line)
    if table_block:
        out.extend(convert_table(table_block))
    return squeeze(out)


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if TABLE_LINE_RE.match(stripped):
        return True
    return stripped.endswith("|")


def is_topic_title_line(line: str) -> bool:
    cleaned = clean_inline(line)
    compared = normalize_compare(cleaned)
    if not compared:
        return False
    if cleaned in TOPIC_TITLE_SET:
        return True
    if any(normalize_compare(title) == compared for title in TOPIC_TITLES):
        return True
    if cleaned.startswith("专题") and len(cleaned) <= 16:
        return True
    if "专题" in cleaned and "..." in cleaned:
        return True
    return False


def is_noise_line(line: str) -> bool:
    cleaned = clean_inline(line)
    if not cleaned:
        return False
    if cleaned in {"目录", "Contents", "进阶篇", "画", "B", "续表"}:
        return True
    if cleaned.startswith("bookmark"):
        return True
    if ONLY_PAGE_RE.fullmatch(cleaned):
        return True
    if PURE_SYMBOL_RE.fullmatch(cleaned):
        return True
    if re.fullmatch(r"[A-Za-z]{1,3}", cleaned):
        return True
    if "专题" in cleaned and "..." in cleaned:
        return True
    if len(cleaned) <= 10 and sum(ch.isdigit() for ch in cleaned) >= 2 and "题" in cleaned:
        return True
    return False


def structural_line(line: str) -> str | None:
    cleaned = clean_inline(line)
    if not cleaned:
        return None
    if cleaned in {"知识索引", "本专题命题规律", "笔记要点"} or POINT_RE.match(cleaned):
        return f"### {cleaned}"
    if SECTION_RE.match(cleaned):
        return f"### {cleaned}"
    if MAIN_RE.match(cleaned):
        return f"#### {cleaned}"
    if SUB_RE.match(cleaned):
        return f"##### {cleaned}"
    if cleaned.startswith(("表", "图")):
        return f"#### {cleaned}"
    if cleaned.startswith(("-", "—", "－")):
        return f"- {cleaned.lstrip('-—－').strip()}"
    if LIST_RE.match(cleaned):
        body = LIST_RE.sub("", cleaned).strip()
        return f"- {body}" if body else None
    if cleaned in {"概念", "法条"}:
        return f"#### {cleaned}"
    return None


def convert_table(block: list[str]) -> list[str]:
    rows: list[list[str]] = []
    for raw in block:
        line = raw.strip()
        if TABLE_BORDER_RE.fullmatch(line.strip("|")):
            continue
        cells = [clean_inline(cell) for cell in line.strip("|").split("|")]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    if not rows:
        return []

    header = rows[0]
    data_rows = rows[1:] if len(rows) > 1 else []
    out: list[str] = []

    if data_rows:
        for row in data_rows:
            if len(header) == len(row) and len(row) > 1:
                pairs = [f"{head}：{cell}" for head, cell in zip(header, row) if cell]
                out.append(f"- {'；'.join(pairs)}")
            elif len(row) == 1:
                if len(header) == 1:
                    out.append(f"- {header[0]}：{row[0]}")
                else:
                    out.append(f"- {row[0]}")
            else:
                out.append(f"- {'；'.join(row)}")
    else:
        out.append(f"- {'；'.join(header)}")

    return squeeze(out)


def smart_join(parts: list[str]) -> str:
    if not parts:
        return ""
    text = parts[0]
    for part in parts[1:]:
        if not part:
            continue
        if text.endswith(("。", "；", "！", "？", "：", "）", "】", "》")):
            text += part
        else:
            text += part
    return clean_inline(text)


def low_confidence_reason(text: str) -> str | None:
    if "^" in text or "_0_" in text or "^^" in text:
        return "OCR 噪音符号残留"
    if LOW_CONF_ASCII_RE.search(text):
        return "长串拉丁字符残留"
    if re.search(r"[A-Za-z]\^[A-Za-z]", text):
        return "混合乱码残留"
    return None


def mark_review(text: str, title: str, review_items: list[str]) -> str:
    reason = low_confidence_reason(text)
    if not reason:
        return text
    marked = text if "【待复核】" in text else f"{text} 【待复核】"
    excerpt = marked[:120]
    review_items.append(f"{title}：{reason}；{excerpt}")
    return marked


def squeeze(lines: list[str]) -> list[str]:
    out: list[str] = []
    prev_blank = True
    for line in lines:
        current = line.rstrip()
        if not current:
            if not prev_blank:
                out.append("")
            prev_blank = True
            continue
        out.append(current)
        prev_blank = False
    while out and not out[-1]:
        out.pop()
    return out


def process_topic_lines(title: str, raw_lines: list[str]) -> tuple[list[str], int, list[str]]:
    out: list[str] = [f"## {title}", ""]
    paragraph: list[str] = []
    review_items: list[str] = []
    table_count = 0
    idx = 0
    last_was_bullet = False

    def flush_paragraph() -> None:
        nonlocal paragraph, last_was_bullet
        if not paragraph:
            return
        text = smart_join(paragraph)
        if text:
            out.append(mark_review(text, title, review_items))
        paragraph = []
        last_was_bullet = False

    while idx < len(raw_lines):
        original = raw_lines[idx]
        cleaned = clean_inline(original)

        if is_table_line(original):
            flush_paragraph()
            block: list[str] = []
            while idx < len(raw_lines) and is_table_line(raw_lines[idx]):
                block.append(raw_lines[idx])
                idx += 1
            converted = convert_table(block)
            if converted:
                table_count += 1
                for item in converted:
                    out.append(mark_review(item, title, review_items))
                out.append("")
            last_was_bullet = False
            continue

        idx += 1

        if not cleaned:
            flush_paragraph()
            continue
        if is_topic_title_line(cleaned) or is_noise_line(cleaned):
            flush_paragraph()
            continue

        structured = structural_line(cleaned)
        if structured:
            flush_paragraph()
            if structured.startswith("- "):
                out.append(mark_review(structured, title, review_items))
                last_was_bullet = True
            else:
                out.append(structured)
                out.append("")
                last_was_bullet = False
            continue

        if last_was_bullet and out and out[-1].startswith("- "):
            out[-1] = mark_review(smart_join([out[-1], cleaned]), title, review_items)
            continue

        paragraph.append(cleaned)

    flush_paragraph()
    return squeeze(out), table_count, list(dict.fromkeys(review_items))


def build_output(ocr_text: str, stage1_text: str) -> tuple[str, dict[str, int], list[str], list[str]]:
    ocr_lines = [line.rstrip() for line in normalize_text(ocr_text).splitlines()]
    stage1_lines = extract_stage1_overview(normalize_text(stage1_text))
    overview_lines = stage1_lines if stage1_lines else build_fallback_overview(ocr_lines)

    segments, anchor_notes = build_topic_segments(ocr_lines)

    output_lines: list[str] = [
        f"# {BOOK_TITLE}",
        "",
        "> 二次清洗说明：本稿按 OCR 原稿顺序重建专题结构，统一为条目化讲义风格；仅对高置信错误做结构修复，低置信残留以 `【待复核】` 标记。",
        "",
        f"## {OVERVIEW_TITLE}",
        "",
        *overview_lines,
        "",
    ]

    table_count = 0
    review_items: list[str] = []
    for segment in segments:
        cleaned, current_tables, current_reviews = process_topic_lines(str(segment["title"]), list(segment["lines"]))
        output_lines.extend(cleaned)
        output_lines.append("")
        table_count += current_tables
        review_items.extend(current_reviews)

    final_lines = squeeze(output_lines)
    output = "\n".join(final_lines) + "\n"
    stats = {
        "topic_count": len(TOPIC_SPECS),
        "table_rewrites": table_count,
        "review_count": len(dict.fromkeys(review_items)),
        "line_count": output.count("\n"),
    }
    return output, stats, list(dict.fromkeys(review_items)), anchor_notes


def build_rules_doc(stats: dict[str, int], review_items: list[str], anchor_notes: list[str]) -> str:
    review_block = "\n".join(f"- {item}" for item in review_items[:20]) if review_items else "- 本轮未新增显式 `【待复核】` 标记。"
    anchor_block = "\n".join(f"- {item}" for item in anchor_notes[:20]) if anchor_notes else "- 本轮主要专题均能从 OCR 正文中找到直接标题或高置信正文锚点。"
    return f"""# 李佳行政法二次清洗说明

- 输入原稿：`OCR原稿/李佳《行政法》2表格版.md`
- 参考底稿：`整理后文本/李佳行政法_整理版.md`
- 输出正文：`整理后文本/李佳行政法_二次清洗版.md`
- 本轮定位：全文可读版 + 条目化讲义风格；不切块、不导库、不生成 JSONL。

## 本轮已自动完成

- 按 OCR 正文顺序重建 28 个顶层专题单元，不再沿用一阶段稿内错误 `##` 边界。
- 清除重复、错位或误插入正文的专题标题、裸 `专题X` 孤行、目录页码残留、bookmark 残留、纯符号行和大块页码噪音。
- 统一 Markdown 层级为：
  - `# 书名`
  - `## 专题 / 国家赔偿 / 进阶篇单元`
  - `### 第一节 / 第二节 / 知识点类小节 / 本专题命题规律`
  - `#### 一、二、三 / 表图说明`
  - `##### （一）（二）`
- 将 OCR 原稿中的 pipe 表格统一改写为条目化讲义表达，不保留 Markdown 表格框线。
- 对明显 OCR 残留但暂不宜强改的句子追加 `【待复核】` 标记，保留原意供下一轮人工复核。

## 专题起点重建说明

{anchor_block}

## 抽取统计

- 顶层专题数：{stats["topic_count"]}
- 表格改写块数：{stats["table_rewrites"]}
- `【待复核】` 片段数：{stats["review_count"]}
- 输出总行数：{stats["line_count"]}

## `【待复核】` 位置摘录

{review_block}

## 后续切块前建议处理区

- 进阶篇中的对比型内容已经改写为条目化讲义，但仍建议在切块前再做一次人工压缩和语义去重。
- 国家赔偿部分篇幅较长，且包含多处表格改写内容，后续如需做高质量问答卡片，建议再拆细为“归责原则 / 范围 / 程序 / 费用标准”等子单元。
- 个别 OCR 残留较重的片段已打 `【待复核】`，适合后续按专题逐段精修，而不建议在本轮继续自动强改。
"""


def main() -> int:
    ocr_text = SRC_OCR.read_text(encoding="utf-8")
    stage1_text = SRC_STAGE1.read_text(encoding="utf-8")
    output, stats, review_items, anchor_notes = build_output(ocr_text, stage1_text)
    DST.write_text(output, encoding="utf-8")
    RULES_DOC.write_text(build_rules_doc(stats, review_items, anchor_notes), encoding="utf-8")
    print(f"二次清洗完成：{DST}")
    print(f"说明文件：{RULES_DOC}")
    print(f"专题数：{stats['topic_count']}；表格改写：{stats['table_rewrites']}；待复核：{stats['review_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
