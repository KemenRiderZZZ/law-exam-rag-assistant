#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""左宁刑诉真金题二次清洗脚本。

目标：
1. 以第一遍整理版为输入；
2. 保持“专题 -> 考点 -> 题目”主结构不变；
3. 处理中等强度的标题补正、导流噪音清理和表格条目化；
4. 输出独立的二次清洗版与说明文件，不切块、不入库。
"""

from __future__ import annotations

from collections import Counter
from html import unescape
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "左宁刑诉真金题_整理版.md"
DST = PROJECT_ROOT / "整理后文本" / "左宁刑诉真金题_二次清洗版.md"
RULES_DOC = PROJECT_ROOT / "整理后文本" / "左宁刑诉真金题_二次清洗说明.md"

TITLE_NEW = "# 左宁刑诉真金题（二次清洗版）"

TOPIC_RE = re.compile(r"^### 专题")
POINT_RE = re.compile(r"^#### 考点")
TABLE_RE = re.compile(r"^\s*<table>.*</table>\s*$", re.IGNORECASE)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
TD_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]*>", re.IGNORECASE)
LONG_DIGITS_RE = re.compile(r"(?<!\d)\d{6,}(?!\d)")
INLINE_CONTACT_RE = re.compile(
    r"(?:VX|VY|QQ)\s*[:：]?\s*\d{5,}|(?:解密|解宓|内部课程|最权威课程)",
    re.IGNORECASE,
)
PURE_NOISE_RE = re.compile(r"^[\s|/\\<>\-_=~^*·•,.;:：；、]+$")
WEAK_NOISE_RE = re.compile(r"(?:VX|VY|QQ)\s*[:：]?\s*\d{5,}|07555686|207555686", re.IGNORECASE)

TOPIC_FIXES = {
    "### 专题二 当事人和的公诉案件诉讼程序": "### 专题二 当事人和解的公诉案件诉讼程序",
}

EXACT_REPAIRS = {
    "法院应组织妊娠检查最权威": "法院应组织妊娠检查",
    "最权应当同时告知公安机关": "应当同时告知公安机关",
    "审程序07555686纠正": "启动再审纠正",
}

DROP_LINES = {
    "评",
}


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ").replace("\xa0", " ")

    first_line, sep, rest = text.partition("\n")
    if first_line.startswith("# 左宁刑诉真金题"):
        text = TITLE_NEW + (sep + rest if sep else "")
    else:
        text = TITLE_NEW + "\n\n" + text

    for old, new in EXACT_REPAIRS.items():
        text = text.replace(old, new)
    return text


def normalize_spaces(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([，。；：）】》])", r"\1", text)
    text = re.sub(r"([（【《])\s+", r"\1", text)
    return text.strip()


def clean_heading(line: str, stats: Counter) -> str:
    raw = line
    line = normalize_spaces(line)
    line = TOPIC_FIXES.get(line, line)
    if raw != line:
        stats["heading_fixed"] += 1
    return line


def clean_inline_text(line: str, stats: Counter) -> str:
    raw = line.strip()
    if not raw:
        return ""

    if raw in DROP_LINES or PURE_NOISE_RE.fullmatch(raw):
        stats["noise_lines_removed"] += 1
        return ""

    cleaned = raw
    cleaned = INLINE_CONTACT_RE.sub("", cleaned)
    cleaned = LONG_DIGITS_RE.sub("", cleaned)
    cleaned = cleaned.replace("最权应当同时告知公安机关", "应当同时告知公安机关")
    cleaned = cleaned.replace("法院应组织妊娠检查最权威", "法院应组织妊娠检查")
    cleaned = normalize_spaces(cleaned)

    if cleaned != raw:
        stats["inline_noise_cleaned"] += 1

    if not cleaned or cleaned in DROP_LINES or PURE_NOISE_RE.fullmatch(cleaned):
        stats["noise_lines_removed"] += 1
        return ""

    return cleaned


def clean_cell(cell: str, stats: Counter) -> str:
    raw = cell
    if IMG_RE.search(cell):
        stats["table_images_removed"] += len(IMG_RE.findall(cell))
        cell = IMG_RE.sub("", cell)

    cell = re.sub(r"<br\s*/?>", " / ", cell, flags=re.IGNORECASE)
    cell = TAG_RE.sub("", cell)
    cell = unescape(cell)
    cell = cell.replace("\u3000", " ")
    cell = INLINE_CONTACT_RE.sub("", cell)
    cell = LONG_DIGITS_RE.sub("", cell)
    cell = cell.replace("最权应当同时告知公安机关", "应当同时告知公安机关")
    cell = cell.replace("法院应组织妊娠检查最权威", "法院应组织妊娠检查")
    cell = cell.replace("最权威", "最权威" if "鉴定意见" in cell else "")
    cell = normalize_spaces(cell)
    cell = cell.strip(" |：;；,，")

    if raw != cell:
        stats["table_cells_cleaned"] += 1
    return cell


def looks_like_header(row: list[str]) -> bool:
    if len(row) <= 1:
        return False
    if any(len(cell) > 16 for cell in row):
        return False
    if any(any(p in cell for p in "。；;？?") for cell in row):
        return False
    return True


def format_row(row: list[str]) -> str:
    if len(row) == 1:
        return f"- {row[0]}"
    return "- " + "；".join(row)


def convert_table(line: str, stats: Counter) -> list[str]:
    rows: list[list[str]] = []
    had_noise = bool(WEAK_NOISE_RE.search(line) or INLINE_CONTACT_RE.search(line))

    for tr in TR_RE.findall(line):
        cells = [clean_cell(cell, stats) for cell in TD_RE.findall(tr)]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)

    if not rows:
        stats["tables_dropped"] += 1
        return []

    emitted: list[str] = []
    header: list[str] | None = None
    if len(rows) >= 2 and looks_like_header(rows[0]):
        header = rows[0]

    if header:
        emitted.append("【表格整理】")
        emitted.append(format_row(header))
        for row in rows[1:]:
            if len(row) == len(header):
                pairs = [f"{head}：{value}" if head != value else value for head, value in zip(header, row)]
                emitted.append("- " + "；".join(pairs))
            else:
                emitted.append(format_row(row))
    else:
        emitted.append("【表格整理】")
        for row in rows:
            emitted.append(format_row(row))

    if had_noise:
        emitted.append("【待复核】表格原文含导流数字或 OCR 噪音，已按可辨内容转写。")
        stats["table_review_added"] += 1

    stats["tables_converted"] += 1
    stats["table_rows_emitted"] += len(rows)
    return emitted


def process_lines(lines: list[str]) -> tuple[list[str], Counter]:
    stats: Counter = Counter()
    output: list[str] = []
    table_buffer: list[str] = []

    for raw in lines:
        line = raw.rstrip("\n")

        if table_buffer:
            table_buffer.append(line)
            if "</table>" in line.lower():
                table_lines = convert_table("".join(table_buffer), stats)
                if table_lines:
                    if output and output[-1] != "":
                        output.append("")
                    output.extend(table_lines)
                    output.append("")
                table_buffer = []
            continue

        if TABLE_RE.match(line.strip()):
            table_lines = convert_table(line, stats)
            if table_lines:
                if output and output[-1] != "":
                    output.append("")
                output.extend(table_lines)
                output.append("")
            continue

        if "<table>" in line.lower():
            table_buffer = [line]
            if "</table>" in line.lower():
                table_lines = convert_table("".join(table_buffer), stats)
                if table_lines:
                    if output and output[-1] != "":
                        output.append("")
                    output.extend(table_lines)
                    output.append("")
                table_buffer = []
            continue

        if line.startswith("### ") or line.startswith("#### "):
            line = clean_heading(line, stats)
            if output and output[-1] == "":
                while len(output) >= 2 and output[-2] == "":
                    output.pop()
            output.append(line)
            continue

        cleaned = clean_inline_text(line, stats)
        if not cleaned:
            if output and output[-1] == "":
                continue
            output.append("")
            continue

        output.append(cleaned)

    final_lines: list[str] = []
    for line in output:
        if line == "" and final_lines and final_lines[-1] == "":
            continue
        final_lines.append(line)

    while final_lines and final_lines[-1] == "":
        final_lines.pop()
    return final_lines, stats


def collect_output_stats(lines: list[str]) -> Counter:
    stats: Counter = Counter()
    for line in lines:
        if TOPIC_RE.match(line):
            stats["topics"] += 1
        if POINT_RE.match(line):
            stats["points"] += 1
        if line.startswith("【待复核】"):
            stats["review_markers"] += 1
        if line == "【表格整理】":
            stats["table_blocks"] += 1
    return stats


def build_rules_doc(process_stats: Counter, output_stats: Counter) -> str:
    return "\n".join(
        [
            "# 左宁刑诉真金题_二次清洗说明",
            "",
            "## 输入与输出",
            "",
            f"- 输入文件：`{SRC.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- 输出文件：`{DST.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- 说明文件：`{RULES_DOC.relative_to(PROJECT_ROOT).as_posix()}`",
            "",
            "## 本轮清洗规则",
            "",
            "- 以第一遍整理版为底稿，不切块、不入库，只做二次清洗。",
            "- 保留既有 `专题 -> 考点 -> 题目` 主结构，不改成教材式章节。",
            "- 修正常见标题残缺，重点补正“当事人和解的公诉案件诉讼程序”等明显缺字标题。",
            "- 删除嵌入正文或表格中的高置信导流噪音，如 `VX/VY/QQ` 联系方式、`内部课程`、`解密/解宓` 等。",
            "- 保留 `【解析】`、`【注意】`、`【归纳】`、`【背下来】`、`【命题规律】`、`【设题陷阱】`、`【常见错误分析】`、`【脚注】`、`【待复核】` 等标签。",
            "- 保留“综上所述，本题答案为...”这类结论句，不额外拆字段。",
            "- 原始 HTML 表格统一转为 `【表格整理】 + 条目化文本`，不再保留 `<table>` 标签。",
            "- 无法高置信修复的片段继续显式标记为 `【待复核】`，不强猜。",
            "",
            "## 表格处理策略",
            "",
            "- 单元格先做去标签、去图片、去导流串、去长数字噪音。",
            "- 默认每一行转成一条文本；能识别表头的，按“表头：内容”组织。",
            "- 原表格若包含导流数字或明显 OCR 尾巴，会额外补 `【待复核】` 提示。",
            "",
            "## 本轮结果统计",
            "",
            f"- 专题数：`{output_stats['topics']}`",
            f"- 考点数：`{output_stats['points']}`",
            f"- 表格块转写数：`{process_stats['tables_converted']}`",
            f"- 表格条目行数：`{process_stats['table_rows_emitted']}`",
            f"- 标题修正数：`{process_stats['heading_fixed']}`",
            f"- 行内噪音清理数：`{process_stats['inline_noise_cleaned']}`",
            f"- 删除噪音行数：`{process_stats['noise_lines_removed']}`",
            f"- 新增表格待复核标记：`{process_stats['table_review_added']}`",
            f"- 输出中的待复核标记总数：`{output_stats['review_markers']}`",
            "",
            "## 仍需后续复核的遗留类型",
            "",
            "- 少量题干或选项仍可能保留 OCR 断裂，但本轮只修高置信问题。",
            "- 个别表格原文存在结构断裂或噪音尾巴，已转写并保留 `【待复核】`。",
            "- 若后续仍发现少量特别难修的碎片，建议单开“局部再审核”，不在本轮继续强修。",
            "",
        ]
    )


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"未找到输入文件：{SRC}")

    raw_text = SRC.read_text(encoding="utf-8")
    text = normalize_text(raw_text)
    lines = text.split("\n")
    cleaned_lines, process_stats = process_lines(lines)
    output_stats = collect_output_stats(cleaned_lines)

    DST.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")
    RULES_DOC.write_text(build_rules_doc(process_stats, output_stats), encoding="utf-8")

    print(f"已生成：{DST.name}")
    print(f"已生成：{RULES_DOC.name}")
    print(f"专题数：{output_stats['topics']}")
    print(f"考点数：{output_stats['points']}")
    print(f"表格转写数：{process_stats['tables_converted']}")
    print(f"待复核标记：{output_stats['review_markers']}")


if __name__ == "__main__":
    main()
