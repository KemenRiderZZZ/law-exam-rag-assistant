#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""郄鹏恩商经知真金题二次清洗脚本。

目标：
1. 以第一遍整理稿为主输入；
2. 保持讲义型 Markdown 结构稳定；
3. 做中强度、高置信的标签修复、标题归位、噪音清理和表格转条目化；
4. 输出独立的二次清洗版与说明文件，不覆盖第一遍整理稿。
"""

from __future__ import annotations

from collections import Counter
from html import unescape
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知真金题_整理版.md"
DST = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知真金题_二次清洗版.md"
RULES_DOC = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知真金题_二次清洗说明.md"

TITLE = "# 郄鹏恩商经知真金题（二次清洗版）"

LIGHT_LABELS = {
    "题干信息解读",
    "题支逐项解析",
    "总结与归纳",
    "背下来",
    "角度拓展",
    "命题规律",
    "命题陷阱",
    "常见错误分析",
    "脚注",
    "图片整理",
    "特别提示",
}

PART_INSERT_BEFORE = {
    "### PROJECT01 专题一 公司法": "## 商法",
    "### PROJECT01 专题一 竞争法": "## 经济法",
}

PART_HEADINGS = {
    "## 前言与使用说明",
    "## 商法",
    "## 经济法",
    "## 环境与自然资源法",
    "## 劳动与社会保障法",
    "## 知识产权法",
}

TOPIC_RE = re.compile(r"^###\s+PROJECT\s*0?\d+\s+专题[一二三四五六七八九十]+\s+.+$")
SECTION_RE = re.compile(r"^####\s+第[一二三四五六七八九十\d]+节\s+.+$")
POINT_RE = re.compile(r"^#####\s+考点\d+\s+.+$")
TABLE_RE = re.compile(r"^\s*<table>.*</table>\s*$", re.IGNORECASE)
TD_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]*>", re.IGNORECASE)
LABEL_WITH_TAIL_RE = re.compile(r"^(【([^】]+)】)\]?\s*(.+)$")
CONTACT_RE = re.compile(
    r"(?:法考资料.*(?:VX|QQ))|(?:解密\s*VX)|(?:密\s*VX\s*[:：]?\s*\d{5,})|(?:VX\s*[:：]?\s*\d{5,})|(?:QQ\s*[:：]?\s*\d{5,})",
    re.IGNORECASE,
)
PURE_NOISE_RE = re.compile(r"^[\s_\-=\^~`<>|/\\\[\]{}■□◆△▲•.。·:：;；,，*\"'“”‘’()（）]+$")
WEAK_REVIEW_RE = re.compile(r"[\^~]{3,}|[■□◆]{2,}|[A-Za-z]{3,}\d{2,}")


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    replacements = {
        "# 郄鹏恩商经知真金题（第一遍整理版）": TITLE,
        "### PROJECT03 课程专题三 商标法": "### PROJECT03 专题三 商标法",
        "【题支逐项解析】]": "【题支逐项解析】",
        "【命题陷阱】]": "【命题陷阱】",
        "【总结与归纳】]": "【总结与归纳】",
        "【背下来】]": "【背下来】",
        "【角度拓展】]": "【角度拓展】",
        "【命题规律】]": "【命题规律】",
        "【常见错误分析】]": "【常见错误分析】",
        "【脚注】]": "【脚注】",
        "【特别提示】]": "【特别提示】",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def clean_cell(cell: str, stats: Counter) -> str:
    raw = cell
    if IMG_RE.search(cell):
        stats["table_inline_image_removed"] += len(IMG_RE.findall(cell))
        cell = IMG_RE.sub("", cell)
    cell = re.sub(r"<br\s*/?>", " / ", cell, flags=re.IGNORECASE)
    cell = TAG_RE.sub("", cell)
    cell = unescape(cell)
    cell = re.sub(r"\[特别提示\]", "特别提示：", cell)
    cell = re.sub(r"(?:内部课|最权威|解密\s*VX.*|密\s*VX\s*[:：]?\s*\d{5,})", "", cell, flags=re.IGNORECASE)
    cell = re.sub(r"QQ\s*[:：]?\s*\d{5,}", "", cell, flags=re.IGNORECASE)
    cell = re.sub(r"\s+", " ", cell).strip(" 　\t|")
    if raw != cell:
        stats["table_cell_changed"] += 1
    return cell


def convert_table(line: str, stats: Counter) -> list[str]:
    rows: list[list[str]] = []
    for tr in TR_RE.findall(line):
        cells = [clean_cell(cell, stats) for cell in TD_RE.findall(tr)]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    if not rows:
        stats["table_dropped"] += 1
        return []

    bullet_lines: list[str] = []
    for row in rows:
        if len(row) == 1:
            bullet_lines.append(f"- {row[0]}")
        else:
            bullet_lines.append(f"- {'；'.join(row)}")
    stats["tables_converted"] += 1
    stats["table_rows_emitted"] += len(bullet_lines)
    return bullet_lines


def clean_heading(line: str, stats: Counter) -> str:
    raw = line
    line = re.sub(r"\s+", " ", line.strip())
    line = re.sub(r"^####\s*第([一二三四五六七八九十\d]+)节(?!\s)", r"#### 第\1节 ", line)
    line = re.sub(r"^#####\s*考点(\d+)(?!\s)", r"##### 考点\1 ", line)
    line = re.sub(r"^###\s*PROJECT0?(\d+)\s*专题", lambda m: f"### PROJECT{int(m.group(1)):02d} 专题", line)
    if raw != line:
        stats["heading_normalized"] += 1
    return line


def flatten_h6(line: str, prev_line: str, stats: Counter) -> list[str]:
    content = line.removeprefix("###### ").strip()
    if not content:
        stats["h6_removed"] += 1
        return []
    if content == "为共同被告":
        stats["h6_merged"] += 1
        return ["__MERGE_PREV__", content]
    stats["h6_flattened"] += 1
    return [f"**{content}**"]


def is_noise(line: str) -> bool:
    if not line.strip():
        return False
    if PURE_NOISE_RE.fullmatch(line):
        return True
    if len(line.strip()) <= 4 and re.fullmatch(r"[A-Za-z]+", line.strip()):
        return True
    return False


def split_label_tail(line: str, stats: Counter) -> list[str]:
    m = LABEL_WITH_TAIL_RE.match(line.strip())
    if not m:
        return [line]
    label, label_name, tail = m.groups()
    if label_name not in LIGHT_LABELS:
        return [line]
    if not tail:
        return [label]
    stats["label_tail_split"] += 1
    return [label, "", tail.strip()]


def strip_inline_contact(line: str, stats: Counter) -> str:
    raw = line
    line = CONTACT_RE.sub("", line)
    line = re.sub(r"(?:APP下载|众合在线APP|竹马APP)", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\s+", " ", line).strip()
    if raw != line:
        stats["contact_inline_removed"] += 1
    return line


def process_lines(lines: list[str]) -> tuple[list[str], Counter]:
    stats: Counter = Counter()
    output: list[str] = []
    current_part = ""

    for raw_line in lines:
        line = raw_line.rstrip()

        if line in PART_INSERT_BEFORE and current_part != PART_INSERT_BEFORE[line]:
            if output and output[-1] != "":
                output.append("")
            output.append(PART_INSERT_BEFORE[line])
            output.append("")
            current_part = PART_INSERT_BEFORE[line]
            stats["part_heading_inserted"] += 1

        if line.startswith("## "):
            line = clean_heading(line, stats)
            if line in PART_HEADINGS:
                current_part = line
            output.append(line)
            continue

        if line.startswith("### ") or line.startswith("#### ") or line.startswith("##### "):
            line = clean_heading(line, stats)
            output.append(line)
            continue

        if line.startswith("###### "):
            flattened = flatten_h6(line, output[-1] if output else "", stats)
            if not flattened:
                continue
            if flattened[0] == "__MERGE_PREV__" and output:
                idx = len(output) - 1
                while idx >= 0 and not output[idx].strip():
                    idx -= 1
                if idx >= 0:
                    output[idx] = output[idx].rstrip() + flattened[1]
                else:
                    output.append(flattened[1])
                continue
            output.extend(flattened)
            continue

        if TABLE_RE.match(line):
            table_lines = convert_table(line, stats)
            if table_lines:
                output.extend(table_lines)
            continue

        line = strip_inline_contact(line, stats)
        if not line:
            if output and output[-1] == "":
                continue
            output.append("")
            continue

        if is_noise(line):
            stats["noise_removed"] += 1
            continue

        split_lines = split_label_tail(line, stats)
        for item in split_lines:
            if not item:
                if output and output[-1] == "":
                    continue
                output.append("")
                continue
            if is_noise(item):
                stats["noise_removed"] += 1
                continue
            output.append(item)

    cleaned: list[str] = []
    for line in output:
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)

    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return cleaned, stats


def collect_counts(lines: list[str]) -> Counter:
    counter: Counter = Counter()
    for line in lines:
        if line.startswith("## "):
            counter["parts"] += 1
        if line.startswith("### PROJECT"):
            counter["topics"] += 1
        if line.startswith("#### "):
            counter["sections"] += 1
        if line.startswith("##### "):
            counter["points"] += 1
        if line.startswith("【图片整理】"):
            counter["image_blocks"] += 1
        if line.startswith("【待复核】"):
            counter["review"] += 1
    return counter


def collect_residual_review(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        if line.startswith("【待复核】"):
            items.append(line)
            continue
        if (
            line.startswith("# ")
            or line.startswith("## ")
            or line.startswith("### ")
            or line.startswith("#### ")
            or line.startswith("##### ")
            or line.startswith("**")
        ):
            continue
        if "<table" in line or "<img" in line:
            items.append(f"【待复核】仍残留 HTML 片段：{line[:120]}")
        elif WEAK_REVIEW_RE.search(line) and len(line) < 160:
            items.append(f"【待复核】疑似 OCR 残片：{line[:120]}")
    return items[:20]


def build_report(before: Counter, after: Counter, stats: Counter, residual: list[str]) -> str:
    report_lines = [
        "# 郄鹏恩商经知真金题二次清洗说明",
        "",
        "## 本轮范围",
        "",
        f"- 输入文件：`{SRC.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- 输出文件：`{DST.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- 脚本文件：`{Path(__file__).relative_to(PROJECT_ROOT).as_posix()}`",
        "- 处理原则：保持讲义型标题树稳定，优先做高置信标签修复、法别补齐、表格转条目化和广告噪音清理。",
        "- 本轮仍不切块、不生成 JSONL、不入库、不做 embedding。",
        "",
        "## 本轮规则",
        "",
        "- 补齐缺失的 `## 商法`、`## 经济法` 顶层法别标题，保留既有 `PROJECT -> 节 -> 考点` 结构。",
        "- 将 `【题支逐项解析】]`、`【命题陷阱】]`、`【总结与归纳】]`、`【背下来】]`、`【角度拓展】]` 等标签统一修正，并把“标签与正文粘连”拆为独立标签块。",
        "- 将残留 `######` 伪标题压平处理：能并入上一行的并入，其他统一改为正文强调小标题，不新增更深标题层级。",
        "- 将残留 HTML `<table>` 统一改写为条目化正文，保留表格语义，不保留标签、框线和内嵌图片标签。",
        "- 删除或剔除课程导流、`VX/QQ` 联系方式、`内部课` 等非正文污染；对合法正文中的普通 `QQ音乐` 之类词语不误删。",
        "- 图片转写继续采用“关键图保留”：保留独立 `【图片整理】` 块，不恢复原图链接。",
        "",
        "## 统计结果",
        "",
        f"- 处理前总行数：`{before['lines']}`",
        f"- 处理后总行数：`{after['lines']}`",
        f"- 顶层法别标题：`{after['parts']}`（处理前 `4`，处理后 `6`）",
        f"- 专题标题：`{after['topics']}`",
        f"- 节标题：`{after['sections']}`",
        f"- 考点标题：`{after['points']}`",
        f"- `【图片整理】`：`{after['image_blocks']}`",
        f"- `【待复核】`：`{after['review']}`",
        f"- 补齐法别标题：`{stats['part_heading_inserted']}`",
        f"- 标题规范化：`{stats['heading_normalized']}`",
        f"- 标签拆分修正：`{stats['label_tail_split']}`",
        f"- 压平 `######` 伪标题：`{stats['h6_flattened']}`，并入上一行：`{stats['h6_merged']}`",
        f"- 条目化改写表格：`{stats['tables_converted']}` 个，输出条目：`{stats['table_rows_emitted']}` 行",
        f"- 删除或剔除广告/联系方式污染：`{stats['contact_inline_removed']}` 处",
        f"- 删除纯噪音行：`{stats['noise_removed']}` 行",
        "",
        "## 残留待复核",
        "",
    ]
    if residual:
        report_lines.extend(f"- {item}" for item in residual)
    else:
        report_lines.append("- 本轮未保留新的 `【待复核】` 残片；后续切块可直接以本稿为主输入。")
    report_lines.extend(
        [
            "",
            "## 后续建议",
            "",
            "- 下一轮切块可直接按 `法别 -> PROJECT/专题 -> 节 -> 考点 -> 轻标签块` 解析。",
            "- 若后续还要继续精修，优先人工抽查条目化表格较密集的公司法、破产法、专利法、商标法位置。",
        ]
    )
    return "\n".join(report_lines) + "\n"


def main() -> None:
    text = normalize_text(SRC.read_text(encoding="utf-8"))
    before_lines = text.splitlines()
    cleaned_lines, stats = process_lines(before_lines)

    after_counts = collect_counts(cleaned_lines)
    before_counts = Counter({"lines": len(before_lines)})
    before_counts["parts"] = sum(1 for line in before_lines if line.startswith("## "))
    after_counts["lines"] = len(cleaned_lines)

    residual = collect_residual_review(cleaned_lines)
    report = build_report(before_counts, after_counts, stats, residual)

    DST.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")
    RULES_DOC.write_text(report, encoding="utf-8")

    print(f"Wrote: {DST}")
    print(f"Wrote: {RULES_DOC}")


if __name__ == "__main__":
    main()
