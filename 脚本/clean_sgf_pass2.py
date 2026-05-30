#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""杨帆三国法二次清洗脚本。

目标：
1. 以第一版整理稿为唯一输入；
2. 面向后续切块与向量入库做入库优化；
3. 处理重复总结块、伪表格、断裂句、专题标题缺口和高频噪音；
4. 生成新的二次清洗版与说明文件，不覆盖第一版。
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "杨帆三国法_整理版.md"
DST = PROJECT_ROOT / "整理后文本" / "杨帆三国法_二次清洗版.md"
REPORT = PROJECT_ROOT / "整理后文本" / "杨帆三国法_二次清洗说明.md"

BOOK_TITLE = "杨帆三国法专题讲座精讲卷（2026版）"

TOPIC_ANCHORS = {
    "## 第一编 国际法": [
        ("#### 第一节 国际法概述", "### 专题一 导论"),
        ("#### 第一节 国际法主体", "### 专题二 国际法主体和国际法律责任"),
        ("#### 第一节 领土制度", "### 专题三 国际法上的空间划分"),
        ("#### 第一节 《中华人民共和国国籍法》", "### 专题四 国际法上的个人"),
        ("#### 第一节 外交关系和领事关系", "### 专题五 外交关系法和领事关系法"),
        ("#### 第一节 条约法概述", "### 专题六 条约法"),
        ("#### 第一节 国际争端的强制性解决方式", "### 专题七 国际争端的解决方式"),
        ("#### 第一节 战争的开始", "### 专题八 战争和武装冲突法"),
    ],
    "## 第二编 国际私法": [
        ("##### 一、国际私法的调整对象", "### 专题一 国际私法概述"),
        ("#### 第一节 冲突规范和准据法", "### 专题二 冲突规范"),
        ("#### 第一节 民商事法律适用的原则", "### 专题三 国际民商事法律适用"),
        ("#### 第一节 国际商事仲裁", "### 专题四 国际民商事争议的解决"),
        ("#### 第一节 国际司法协助", "### 专题五 司法协助"),
    ],
    "## 第三编 国际经济法": [
        ("##### 一、国际经济法的调整对象", "### 专题一 导论"),
        ("#### 第一节 《国际贸易术语解释通则》", "### 专题二 国际货物买卖法"),
        ("#### 第一节 国际海上货物运输法", "### 专题三 国际货物运输与保险法"),
        ("#### 第一节 银行托收", "### 专题四 国际贸易支付"),
        ("#### 第一节 《出口管制法》", "### 专题五 对外贸易管理制度"),
        ("#### 第一节 概述", "### 专题六 世界贸易组织（WTO）"),
        ("#### 第一节 知识产权的国际保护", "### 专题七 国际经济领域的其他法律制度"),
    ],
}

REVIEW_LABEL = "【专题重点回顾】"
MARKER_LABELS = {"【技术流】", "【易混辨析】", "【关联法条】", "【经典真题】", REVIEW_LABEL}
NOISE_PREFIXES = ("O^j", "a/^7", "{1^", "密^")
HEADING_RE = re.compile(r"^(#{2,5})\s+")
BROKEN_TABLE_RE = re.compile(r"^\|\s*\+[-+|=:\s]+\|")
PURE_BORDER_RE = re.compile(r"^\s*\+[-+=:]+\+?\s*$")
TABLE_ROW_RE = re.compile(r"^\|.*\|$")
TOPIC_RE = re.compile(r"^###\s+专题")
BARE_TOPIC_RE = re.compile(r"^(###\s+专题[一二三四五六七八九十]+)$")
PART_TITLE_RE = re.compile(r"^##\s+第[一二三四五六七八九十]+编$")
PAGE_NOISE_RE = re.compile(r"^[^\u4e00-\u9fffA-Za-z0-9]{0,2}\s*\d*\s*\^\d+\^$")
SHORT_PAGE_NOISE_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z»]{0,2}\s*\^\d+\^$")


def load_text() -> str:
    return SRC.read_text(encoding="utf-8")


def normalize_text(text: str, stats: Counter) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    replacements = {
        "（-）": "（一）",
        "(-)": "（一）",
        "(一)": "（一）",
        "）~0~": "）",
        "~0~": "",
        "①【答案】**BD~O~**": "①【答案】BD。",
        "①【答案】**C~o~**": "①【答案】C。",
        "\\": "",
        "■\\[": "",
        "■[": "",
        "■I": "",
        "■II": "",
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
            stats["replace_hits"] += 1

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def normalize_line_noise(line: str, stats: Counter) -> str:
    raw = line
    line = line.rstrip()

    if any(prefix in line for prefix in NOISE_PREFIXES):
        for prefix in NOISE_PREFIXES:
            if prefix in line:
                line = line.replace(prefix, "")
                stats["noise_token_fixed"] += 1

    if ";；" in line:
        line = line.replace(";；", "；")
        stats["semicolon_fix"] += 1
    if "；;" in line:
        line = line.replace("；;", "；")
        stats["semicolon_fix"] += 1
    if "; ;" in line:
        line = line.replace("; ;", "")
        stats["semicolon_fix"] += 1
    if "j;" in line:
        line = line.replace("j;", "")
        stats["semicolon_fix"] += 1
    if "I;" in line:
        line = line.replace("I;", "")
        stats["semicolon_fix"] += 1
    if ";i" in line:
        line = line.replace(";i", "")
        stats["semicolon_fix"] += 1
    if ";j" in line:
        line = line.replace(";j", "")
        stats["semicolon_fix"] += 1
    if line.startswith(";"):
        line = line.lstrip("; ")
        stats["semicolon_fix"] += 1
    if line.startswith("；"):
        line = line.lstrip("； ")
        stats["semicolon_fix"] += 1

    line = re.sub(r"(?<=[\u4e00-\u9fff]);(?=[\u4e00-\u9fff])", "", line)
    line = re.sub(r"(?<=[\u4e00-\u9fff]);(?=[①②③④⑤⑥⑦⑧⑨⑩（(])", "，", line)
    line = re.sub(r"(?<=[。！？；])\s*;", "", line)
    line = re.sub(r"(?<=[。！？])；(?=[\u4e00-\u9fff])", "", line)
    line = re.sub(r"(?<=[\u4e00-\u9fff])[］\]】\[]?[ijJIl1!]{1,3}(?=[\u4e00-\u9fff])", "", line)
    line = re.sub(r"(?<=[\u4e00-\u9fff])[］\]】\[]+；(?=[\u4e00-\u9fff])", "", line)
    line = re.sub(r"(?<=[\u4e00-\u9fff])；(?=[\u4e00-\u9fff]{1,2}[并立民家法国海洋经物约产税诉保责权局院会员货庭])", "", line)
    line = re.sub(r"。；\s*$", "。", line)
    line = re.sub(r"；\s*[Jj]\s*$", "", line)
    line = re.sub(r"；\s*$", "", line)

    line = line.replace("过I;程", "过程")
    line = line.replace("成；立", "成立")
    line = line.replace("开；", "开展")
    line = line.replace("开展展活动", "开展活动")
    line = line.replace("国；际", "国际")
    line = line.replace("获i1得", "获得")
    line = line.replace("主永而厂", "主张")
    line = line.replace("擔", "担")
    line = re.sub(r"\s+", " ", line).strip()

    if raw != line:
        stats["line_changed"] += 1
    return line


def split_lines(text: str) -> list[str]:
    lines = text.split("\n")
    first_body = next((i for i, line in enumerate(lines) if line.startswith("## ")), 0)
    return lines[first_body:]


def merge_part_titles(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        if PART_TITLE_RE.match(cur) and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and not nxt.startswith("#") and not nxt.startswith("【") and len(nxt) <= 12:
                out.append(f"{cur} {nxt}")
                stats["part_title_merged"] += 1
                i += 2
                continue
        out.append(lines[i].strip() if lines[i].strip() else "")
        i += 1
    return out


def merge_bare_topic_titles(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    current_part = ""
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        if cur.startswith("## "):
            current_part = cur
        bare = BARE_TOPIC_RE.match(cur)
        if bare and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and not nxt.startswith("#") and not nxt.startswith("【") and len(nxt) <= 20:
                prefix = bare.group(1)
                merged = f"{prefix} {nxt}"
                for _, topic in TOPIC_ANCHORS.get(current_part, []):
                    if topic.startswith(prefix):
                        merged = topic
                        break
                out.append(merged)
                stats["topic_completed"] += 1
                i += 2
                continue
        out.append(lines[i])
        i += 1
    return out


def ensure_topic_headings(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    current_part = ""
    seen_topics: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_part = stripped
            seen_topics = set()
            out.append(line)
            continue

        if stripped.startswith("### "):
            bare = BARE_TOPIC_RE.match(stripped)
            if bare:
                prefix = bare.group(1)
                matched = False
                for _, topic in TOPIC_ANCHORS.get(current_part, []):
                    if topic.startswith(prefix):
                        stripped = topic
                        stats["topic_completed"] += 1
                        matched = True
                        break
                if not matched:
                    stats["bare_topic_removed"] += 1
                    continue
            seen_topics.add(stripped)
            out.append(stripped)
            continue

        anchors = TOPIC_ANCHORS.get(current_part, [])
        for anchor, topic in anchors:
            if stripped == anchor and topic not in seen_topics:
                if out and out[-1] != "":
                    out.append("")
                out.extend([topic, ""])
                seen_topics.add(topic)
                stats["topic_inserted"] += 1
                break
        out.append(line)

    return dedupe_adjacent_duplicate_lines(out)


def dedupe_adjacent_duplicate_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if out and out[-1] == line and line.strip():
            continue
        out.append(line)
    return out


def dedupe_repeated_topics(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    current_part = ""
    seen_topics: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_part = stripped
            seen_topics = set()
            out.append(line)
            continue
        if stripped.startswith("### 专题"):
            if stripped in seen_topics:
                stats["duplicate_topic_removed"] += 1
                continue
            seen_topics.add(stripped)
        out.append(line)
    return out


def collapse_topic_echoes(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        if cur.startswith("### 专题"):
            topic_title = re.sub(r"^###\s+专题[一二三四五六七八九十]+\s*", "", cur).strip()
            out.append(lines[i])
            i += 1
            while i < len(lines):
                nxt = lines[i].strip()
                if nxt == cur:
                    stats["duplicate_topic_removed"] += 1
                    i += 1
                    continue
                if nxt == topic_title or nxt in {"**I**", "I"}:
                    stats["topic_echo_removed"] += 1
                    i += 1
                    continue
                break
            continue
        out.append(lines[i])
        i += 1
    return out


def transform_review_blocks(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line != "本专题重点回顾":
            out.append(lines[i])
            i += 1
            continue

        stats["review_blocks"] += 1
        out.append(REVIEW_LABEL)
        i += 1
        while i < len(lines):
            cur = lines[i].strip()
            if not cur:
                out.append("")
                i += 1
                continue
            if cur.startswith("## ") or cur.startswith("### ") or cur.startswith("#### "):
                break
            cur = normalize_line_noise(cur, stats)
            if "晶物买卖法" in cur or cur in {"(M晶物买卖法", "M晶物买卖法"}:
                stats["review_noise_removed"] += 1
                i += 1
                continue
            previous = out[-1] if out else ""
            if (
                previous.startswith("- ")
                and cur
                and not re.match(r"^\d+\.\s*", cur)
                and not re.match(r"^[（(]\d+[)）]", cur)
                and cur not in MARKER_LABELS
                and previous[-1] not in "。！？；："
            ):
                out[-1] = previous + cur
                stats["review_line_merged"] += 1
                i += 1
                continue
            cur = re.sub(r"^\d+\.\s*", "- ", cur)
            if re.match(r"^[（(]\d+[)）]", cur):
                cur = "- " + cur
            if not cur.startswith("- ") and cur not in MARKER_LABELS and not cur.startswith("|"):
                cur = "- " + cur
            out.append(cur)
            i += 1
        if out and out[-1] != "":
            out.append("")
    return out


def is_markdown_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r"\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?", stripped))


def extract_table_cells(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    if not stripped:
        return []
    cells = [cell.strip() for cell in stripped.split("|")]
    return [cell for cell in cells if cell]


def is_broken_table_line(line: str) -> bool:
    stripped = line.strip()
    if stripped in {"续表", "> 续表"}:
        return True
    if stripped.startswith("| +") or stripped.endswith("+") and "| +" in stripped:
        return True
    if PURE_BORDER_RE.match(stripped) or BROKEN_TABLE_RE.match(stripped):
        return True
    if re.search(r"\+\-[-+=:| ]{3,}", stripped):
        return True
    if "| +" in stripped or stripped.startswith("+---") or stripped.startswith("--------------------") or stripped.startswith("-----------"):
        return True
    return False


def is_loose_broken_table_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if is_broken_table_line(stripped):
        return True
    if re.fullmatch(r"[-= ]{10,}", stripped):
        return True
    if stripped.startswith("| +") or stripped.startswith("| -") or stripped.startswith("| ="):
        return True
    return False


def should_rewrite_table(block: list[str]) -> bool:
    data_rows = [line for line in block if TABLE_ROW_RE.match(line.strip()) and not is_markdown_separator(line)]
    if any(is_broken_table_line(line) for line in block):
        return True
    for row in data_rows:
        cells = extract_table_cells(row)
        if len(cells) > 2:
            return True
        if len(cells) == 0:
            return True
        if any(cell in {"I", "II", "III"} or "＞" in cell or "->" in cell or "-＞" in cell for cell in cells):
            return True
    return False


def block_to_bullets(block: list[str], stats: Counter) -> list[str]:
    bullets: list[str] = []
    seen: set[str] = set()
    for line in block:
        stripped = line.strip()
        if not stripped or stripped in {"续表", "> 续表"}:
            continue
        if PURE_BORDER_RE.match(stripped) or is_markdown_separator(stripped):
            continue
        if TABLE_ROW_RE.match(stripped):
            cells = extract_table_cells(stripped)
            cleaned_cells = []
            for cell in cells:
                cell = re.sub(r"\+\-[-+=:| ]*", " ", cell)
                cell = cell.replace("-＞", "到").replace("->", "到")
                cell = normalize_line_noise(cell, stats)
                if cell:
                    cleaned_cells.append(cell)
            if not cleaned_cells:
                continue
            if len(cleaned_cells) == 1:
                bullet = cleaned_cells[0]
            elif len(cleaned_cells) == 2:
                bullet = f"{cleaned_cells[0]}：{cleaned_cells[1]}"
            else:
                bullet = "；".join(cleaned_cells)
        else:
            bullet = normalize_line_noise(re.sub(r"\+\-[-+=:| ]*", " ", stripped), stats)
        bullet = re.sub(r"\s+", " ", bullet).strip("；， ")
        if not bullet or bullet == "|" or bullet in seen:
            continue
        seen.add(bullet)
        bullets.append(f"- {bullet}")
    if bullets:
        stats["complex_table_rewritten"] += 1
    return bullets


def rewrite_tables(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped in {"续表", "> 续表"}:
            stats["continuation_removed"] += 1
            i += 1
            continue

        if TABLE_ROW_RE.match(stripped) or PURE_BORDER_RE.match(stripped) or is_loose_broken_table_line(stripped):
            block: list[str] = []
            j = i
            while j < len(lines):
                s = lines[j].strip()
                if not s:
                    block.append(lines[j])
                    j += 1
                    continue
                if TABLE_ROW_RE.match(s) or PURE_BORDER_RE.match(s) or s in {"续表", "> 续表"} or is_loose_broken_table_line(s):
                    block.append(lines[j])
                    j += 1
                    continue
                break
            if should_rewrite_table(block):
                bullets = block_to_bullets(block, stats)
                if bullets:
                    if out and out[-1] != "":
                        out.append("")
                    out.extend(bullets)
                    out.append("")
                stats["broken_table_removed"] += 1
            else:
                out.extend(block)
            i = j
            continue

        out.append(lines[i])
        i += 1
    return out


def remove_empty_examples(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "【例】":
            next_nonempty = ""
            for j in range(idx + 1, min(idx + 4, len(lines))):
                if lines[j].strip():
                    next_nonempty = lines[j].strip()
                    break
            if next_nonempty.startswith("【例】") or next_nonempty in MARKER_LABELS or next_nonempty.startswith("##### ") or next_nonempty.startswith("#### "):
                stats["empty_example_removed"] += 1
                continue
        out.append(line)
    return out


def fix_marker_blocks(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "【技术流】" and out and out[-1].strip() == "【技术流】":
            continue
        if stripped == "【易混辨析】" and out and out[-1].strip() == "【易混辨析】":
            continue
        if stripped == "【关联法条】" and out and out[-1].strip() == "【关联法条】":
            continue
        if stripped == "【经典真题】" and out and out[-1].strip() == "【经典真题】":
            continue
        out.append(line)
    return out


def tighten_intro_blocks(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        if cur == "【易混辨析】" and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and not nxt.startswith("【") and not nxt.startswith("#"):
                out.append(cur)
                out.append(f"- {normalize_line_noise(nxt, stats)}")
                i += 2
                continue
        out.append(lines[i])
        i += 1
    return out


def merge_semicolon_continuations(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt.startswith(("；", "都", "立", "际")) and cur.strip() and not cur.startswith("#") and not cur.startswith("【"):
                out.append(cur.rstrip("；; ") + nxt.lstrip("；; "))
                stats["semicolon_joined_lines"] += 1
                i += 2
                continue
            if (
                cur.rstrip().endswith(("；", "；i", "；j", "；J"))
                and nxt
                and not nxt.startswith("#")
                and not nxt.startswith("【")
                and not nxt.startswith("|")
            ):
                cleaned_cur = re.sub(r"[；;][ijJIl1!]*\s*$", "", cur.rstrip())
                cleaned_nxt = re.sub(r"^[；;]+", "", nxt)
                out.append(cleaned_cur + cleaned_nxt)
                stats["semicolon_joined_lines"] += 1
                i += 2
                continue
        out.append(cur)
        i += 1
    return out


def clean_lines(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue

        stripped = normalize_line_noise(stripped, stats)
        if not stripped:
            stats["line_removed"] += 1
            continue

        if stripped in {"■[", "■\\[", "z", "n", "j"}:
            stats["line_removed"] += 1
            continue
        if stripped in {"J", "**■II**", "■II", "■I", "**I**", "I"} or PAGE_NOISE_RE.match(stripped) or SHORT_PAGE_NOISE_RE.match(stripped):
            stats["line_removed"] += 1
            continue
        if "晶物买卖法" in stripped and len(stripped) <= 20:
            stats["line_removed"] += 1
            continue

        if stripped.startswith("# 杨帆三国法专题讲座精讲卷（2026版）"):
            stats["line_removed"] += 1
            continue
        if stripped.startswith("> 整理说明：本文件依据 OCR 原稿进行第一遍整理"):
            stats["line_removed"] += 1
            continue
        if stripped == "---":
            stats["line_removed"] += 1
            continue

        out.append(stripped)
    return out


def merge_paragraphs(lines: list[str], stats: Counter) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if (
            i + 1 < len(lines)
            and cur.strip()
            and lines[i + 1].strip()
            and not HEADING_RE.match(cur)
            and not HEADING_RE.match(lines[i + 1])
            and not cur.startswith("|")
            and not lines[i + 1].startswith("|")
            and cur not in MARKER_LABELS
            and lines[i + 1] not in MARKER_LABELS
            and not cur.startswith("- ")
            and not lines[i + 1].startswith("- ")
            and cur[-1] not in "。！？；："
        ):
            merged = cur + lines[i + 1].lstrip()
            out.append(merged)
            stats["paragraph_merged"] += 1
            i += 2
            continue
        out.append(cur)
        i += 1
    return out


def normalize_blank_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    last_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and last_blank:
            continue
        out.append(line)
        last_blank = blank
    return out


def collect_review_items(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        if "【待复核】" in line:
            items.append(line.strip())
    return items


def build_report(stats: Counter, input_lines: int, output_lines: int, review_items: list[str]) -> str:
    review_excerpt = "\n".join(f"- {item}" for item in review_items[:20]) if review_items else "- 本轮未新增显式 `【待复核】`。"
    return f"""# 杨帆三国法二次清洗说明

## 本轮范围

- 输入文件：`整理后文本/杨帆三国法_整理版.md`
- 输出文件：`整理后文本/杨帆三国法_二次清洗版.md`
- 处理原则：以第一版整理稿为唯一输入，偏向入库优化；主动压噪音、修断裂、改坏表格、保留并标签化重复总结块。

## 本轮规则

- 保留 `编 -> 专题 -> 节 -> 目` 主层级，并补齐缺失专题标题。
- 将 `本专题重点回顾` 统一改为 `【专题重点回顾】` 块，便于后续切块过滤。
- 复杂坏表格默认改写为条目文本，简单表格保留。
- 自动修复高频断裂噪音，如 `j;`、`I;`、`~0~`、`密^`、导图残符等。
- 只对少量无法稳妥恢复的片段保留 `【待复核】`。

## 统计

- 输入总行数：`{input_lines}`
- 输出总行数：`{output_lines}`
- 删除/改写的伪表格块数：`{stats["broken_table_removed"]}`
- 转条目文本的复杂表格数：`{stats["complex_table_rewritten"]}`
- `【专题重点回顾】` 块数：`{stats["review_blocks"]}`
- `【待复核】` 片段数：`{len(review_items)}`
- 自动修复断裂噪音次数：`{stats["semicolon_fix"] + stats["noise_token_fixed"]}`
- 插入缺失专题标题数：`{stats["topic_inserted"]}`

## 自动修复摘要

- 去除或替换的典型噪音：`j; / I; / ~0~ / O^j / a/^7 / 密^ / 续表 / 伪表格骨架`
- 本轮优先修正了海洋法、国际私法总论、外国法查明、国际经济法导论等问题密集区域。

## `【待复核】` 位置摘录

{review_excerpt}
"""


def main() -> None:
    stats: Counter = Counter()
    raw = load_text()
    input_lines = len(raw.splitlines())

    text = normalize_text(raw, stats)
    lines = split_lines(text)
    lines = clean_lines(lines, stats)
    lines = merge_part_titles(lines, stats)
    lines = merge_bare_topic_titles(lines, stats)
    lines = ensure_topic_headings(lines, stats)
    lines = transform_review_blocks(lines, stats)
    lines = rewrite_tables(lines, stats)
    lines = remove_empty_examples(lines, stats)
    lines = fix_marker_blocks(lines, stats)
    lines = tighten_intro_blocks(lines, stats)
    lines = merge_semicolon_continuations(lines, stats)
    lines = dedupe_repeated_topics(lines, stats)
    lines = collapse_topic_echoes(lines, stats)
    lines = merge_paragraphs(lines, stats)
    lines = normalize_blank_lines(lines)

    body = "\n".join(lines).strip() + "\n"
    final_text = (
        f"# {BOOK_TITLE}（二次清洗版）\n\n"
        "> 二次清洗说明：本文件以第一版整理稿为基础，面向后续切块和向量入库做二次整理；本轮重点处理重复总结块、伪表格、断裂句和高频 OCR 噪音，不切块、不导库。\n\n"
        "---\n\n"
        f"{body}"
    )
    DST.write_text(final_text, encoding="utf-8")

    review_items = collect_review_items(lines)
    REPORT.write_text(build_report(stats, input_lines, len(final_text.splitlines()), review_items), encoding="utf-8")

    print(f"二次清洗完成：{DST}")
    print(f"说明文件：{REPORT}")
    print(f"input_lines={input_lines}")
    print(f"output_lines={len(final_text.splitlines())}")
    print(f"broken_table_removed={stats['broken_table_removed']}")
    print(f"complex_table_rewritten={stats['complex_table_rewritten']}")
    print(f"review_blocks={stats['review_blocks']}")
    print(f"review_count={len(review_items)}")


if __name__ == "__main__":
    main()
