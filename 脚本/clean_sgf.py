#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""杨帆《三国法》OCR 一次整理脚本。

目标：
1. 生成适合后续切块的整理版正文；
2. 保留“编-专题-节-目”知识层级；
3. 清理目录、页码、概览图、pandoc 残留和高置信 OCR 噪音；
4. 第一遍不做切块，不重写内容。
"""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "OCR原稿" / "杨帆《三国法》.md"
DST = PROJECT_ROOT / "整理后文本" / "杨帆三国法_整理版.md"
REPORT = PROJECT_ROOT / "整理后文本" / "杨帆三国法_整理说明.md"

BOOK_TITLE = "杨帆三国法专题讲座精讲卷（2026版）"

TOPIC_ANCHORS = {
    "第一编 国际法": [
        ("#### 第一节 国际法概述", "专题一 导论"),
        ("#### 第一节 国际法主体", "专题二 国际法主体和国际法律责任"),
        ("#### 第一节 领土制度", "专题三 国际法上的空间划分"),
        ("#### 第一节 《中华人民共和国国籍法》", "专题四 国际法上的个人"),
        ("#### 第一节 外交关系和领事关系", "专题五 外交关系法和领事关系法"),
        ("#### 第一节 条约法概述", "专题六 条约法"),
        ("#### 第一节 国际争端的强制性解决方式", "专题七 国际争端的解决方式"),
        ("#### 第一节 战争的开始", "专题八 战争和武装冲突法"),
    ],
    "第二编 国际私法": [
        ("##### 一、国际私法的调整对象", "专题一 国际私法概述"),
        ("#### 第一节 冲突规范和准据法", "专题二 冲突规范"),
        ("#### 第一节 民商事法律适用的原则", "专题三 国际民商事法律适用"),
        ("#### 第一节 国际商事仲裁", "专题四 国际民商事争议的解决"),
        ("#### 第一节 国际司法协助", "专题五 司法协助"),
    ],
    "第三编 国际经济法": [
        ("##### 一、国际经济法的调整对象", "专题一 导论"),
        ("#### 第一节 《国际贸易术语解释通则》", "专题二 国际货物买卖法"),
        ("#### 第一节 国际海上货物运输法", "专题三 国际货物运输与保险法"),
        ("#### 第一节 银行托收", "专题四 国际贸易支付"),
        ("#### 第一节 《出口管制法》", "专题五 对外贸易管理制度"),
        ("#### 第一节 概述", "专题六 世界贸易组织（WTO）"),
        ("#### 第一节 知识产权的国际保护", "专题七 国际经济领域的其他法律制度"),
    ],
}

END_PUNCT = "。！？；：,，、）)]\"'》」】"
NO_MERGE_START = re.compile(
    r"^\s*("
    r"#{1,6}\s+|"
    r"第[一二三四五六七八九十百零\d]+编|"
    r"专题[一二三四五六七八九十百零\d]+|"
    r"第[一二三四五六七八九十百零\d]+节|"
    r"[一二三四五六七八九十]+、|"
    r"[（(][一二三四五六七八九十\d]+[)）]|"
    r"\d+\.\s|"
    r"[①②③④⑤⑥⑦⑧⑨⑩]|"
    r"【|"
    r">|"
    r"\||"
    r"\+-[-:=+]+|"
    r"```"
    r")"
)

MARKER_NAMES = [
    "技术流",
    "易混辨析",
    "热点追踪",
    "考查角度",
    "关联法条",
    "例",
    "例1",
    "例2",
    "例3",
    "例4",
    "口诀",
    "总结",
    "注意",
    "经典真题",
]

JUNK_LINE_PATTERNS = [
    r"^\s*n\s*$",
    r"^\s*z\s*$",
    r"^\s*[■◆▲△□]+[A-Za-z0-9ⅠⅡⅢIVXivx]*\s*$",
    r"^\s*[\[\]\\]+\s*$",
    r"^\s*[\^`~_\\/$%]+[\^`~_\\/$%\sA-Za-z0-9.-]*$",
    r"^\s*[厂LFI][\-—一^]*.*$",
    r"^\s*O\^j.*$",
    r"^\s*三国法、专题讲座精讲卷\s*$",
    r"^\s*/\d+\s*$",
    r"^\s*[A-Za-z][A-Za-z .:/-]{2,}\s*$",
    r"^\s*<!--\s*-->\s*$",
    r"^\s*本专题知识点概览\s*$",
]

INLINE_REPLACEMENTS = {
    "\\|": "|",
    "\\\"": "\"",
    "\\'": "'",
    "（-）": "（一）",
    "(-)": "（一）",
    "(一)": "（一）",
    "（二） ": "（二）",
    "（三） ": "（三）",
    "（四） ": "（四）",
    "1.  .": "1. ",
    "2.  .": "2. ",
    "3.  .": "3. ",
    "4.  .": "4. ",
    "5.  .": "5. ",
    "6.  .": "6. ",
    "7.  .": "7. ",
    "8.  .": "8. ",
    "9.  .": "9. ",
    "10.  .": "10. ",
    "一一": " - ",
}


def remove_pandoc_artifacts(text: str) -> str:
    text = re.sub(r"\[([^\[\]]*?)\]\{\.underline\}", r"\1", text)
    text = re.sub(r"\[([^\[\]]*?)\]\{\.smallcaps\}", r"\1", text)
    text = re.sub(r"\[\]\{#bookmark\d+\s*\.anchor\}", "", text)
    text = re.sub(r"\{\.[a-zA-Z][\w-]*\}", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


def remove_meaningless_bold(text: str) -> str:
    pattern = re.compile(
        r"\*\*([\d\w\.\,\-\+\(\)\[\]（）【】、，：；/:\s]{1,18}?)\*\*"
    )

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        if re.search(r"[一-龥]", inner):
            return match.group(0)
        return inner

    text = pattern.sub(repl, text)
    text = re.sub(r"\*\*([（(][\d一二三四五六七八九十]+[)）])\*\*", r"\1", text)
    text = re.sub(r"\*\*([①②③④⑤⑥⑦⑧⑨⑩])\*\*", r"\1", text)
    text = re.sub(r"\*\*(\d+)\*\*", r"\1", text)
    text = re.sub(r"\*\*([A-Za-z])\*\*", r"\1", text)
    return text


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for old, new in INLINE_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n", "\n", text)
    return text


def find_body_start(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if line.strip() != "第一编":
            continue
        window = "\n".join(lines[i:i + 20])
        if "第一节国际法概述" in window:
            return i
    raise RuntimeError("未找到正文起点：第一编/第一节国际法概述")


def is_junk_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return any(re.match(pat, s) for pat in JUNK_LINE_PATTERNS)


def clean_inline(line: str) -> str:
    s = line.strip()
    if not s:
        return ""

    s = re.sub(r"^:+|:+$", "", s).strip()
    s = re.sub(r"^[·•▪]+", "", s).strip()
    s = re.sub(r"[“”]", "\"", s)
    s = re.sub(r"[‘’]", "'", s)
    s = s.replace("◎", " ")
    s = re.sub(r"［\s*([^\[\]［］]{1,16})\s*］", r"【\1】", s)
    s = re.sub(r"\[\s*([^\[\]]{1,16})\s*\]", r"【\1】", s)
    s = re.sub(r"【\s+", "【", s)
    s = re.sub(r"\s+】", "】", s)

    for name in MARKER_NAMES:
        if name in s and len(s) <= 24:
            s = f"【{name}】"
            break

    s = re.sub(r"^专题([一二三四五六七八九十百零\d]+)([^ \n])", r"专题\1 \2", s)
    s = re.sub(r"^第([一二三四五六七八九十百零\d]+)节([^ \n])", r"第\1节 \2", s)
    s = re.sub(r"^第([一二三四五六七八九十百零\d]+)编\s+", r"第\1编 ", s)
    s = re.sub(r"^([一二三四五六七八九十]+、.*?)\s+[一-龥A-Za-z]$", r"\1", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def remove_duplicate_second_part(lines: list[str]) -> tuple[list[str], int]:
    second_part_indexes = [i for i, line in enumerate(lines) if line.strip() == "第二编"]
    third_part_index = next(
        (i for i, line in enumerate(lines) if line.strip().startswith("第三编")),
        None,
    )
    if len(second_part_indexes) < 2 or third_part_index is None:
        return lines, 0
    dup_start = second_part_indexes[1]
    if dup_start >= third_part_index:
        return lines, 0
    removed = third_part_index - dup_start
    return lines[:dup_start] + lines[third_part_index:], removed


def skip_topic_overview(lines: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    skip_overview = False
    removed = 0

    for raw in lines:
        line = clean_inline(raw)
        if not line:
            out.append("")
            continue

        if line == "本专题知识点概览":
            skip_overview = True
            removed += 1
            continue

        if skip_overview:
            if (
                re.match(r"^第[一二三四五六七八九十百零\d]+节", line)
                or re.match(r"^[一二三四五六七八九十]+、", line)
                or (len(line) >= 20 and re.search(r"[。！？]$", line) and not is_junk_line(line))
            ):
                skip_overview = False
            else:
                removed += 1
                continue

        out.append(line)

    return out, removed


def normalize_headings(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

        if not line:
            out.append("")
            i += 1
            continue

        if re.match(r"^第[一二三四五六七八九十百零\d]+编(?:\s+.+)?$", line):
            merged = line
            if re.fullmatch(r"第[一二三四五六七八九十百零\d]+编", line):
                title = next_line if next_line and not re.match(r"^(专题|第.+节|[一二三四五六七八九十]+、)", next_line) else ""
                if title:
                    merged = f"{line} {title}"
                    i += 1
            merged = f"## {merged}"
            out.extend([merged, ""])
            i += 1
            continue

        if re.match(r"^专题[一二三四五六七八九十百零\d]+", line):
            if re.fullmatch(r"专题[一二三四五六七八九十百零\d]+", line) and next_line:
                line = f"{line} {next_line}"
                i += 1
            line = re.sub(r"^专题([一二三四五六七八九十百零\d]+)\s*", r"### 专题\1 ", line)
            out.extend([line.strip(), ""])
            i += 1
            continue

        if re.match(r"^第[一二三四五六七八九十百零\d]+节", line):
            if re.fullmatch(r"第[一二三四五六七八九十百零\d]+节", line) and next_line:
                line = f"{line} {next_line}"
                i += 1
            line = re.sub(r"^第([一二三四五六七八九十百零\d]+)节\s*", r"#### 第\1节 ", line)
            out.extend([line.strip(), ""])
            i += 1
            continue

        if re.match(r"^[一二三四五六七八九十]+、", line):
            out.extend([f"##### {line}", ""])
            i += 1
            continue

        out.append(line)
        i += 1

    return out


def inject_topic_headings(lines: list[str]) -> list[str]:
    out: list[str] = []
    current_part = ""
    current_topic = ""

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            current_part = stripped[3:]
            current_topic = ""
            out.append(line)
            continue

        if stripped.startswith("### "):
            current_topic = stripped[4:]
            out.append(line)
            continue

        anchors = TOPIC_ANCHORS.get(current_part, [])
        for anchor, topic in anchors:
            full_topic = f"### {topic}"
            if stripped == anchor and current_topic != topic:
                if out and out[-1] != "":
                    out.append("")
                out.extend([full_topic, ""])
                current_topic = topic
                break

        out.append(line)

    return out


def parse_pandoc_table(block: list[str]) -> str | None:
    rows: list[list[str]] = []
    for line in block:
        if re.match(r"^\s*\+[-:=+]+", line):
            continue
        if not line.strip():
            continue
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if any(cells):
            rows.append(cells)
    if not rows:
        return None

    cols = max(len(row) for row in rows)
    normalized: list[list[str]] = []
    for row in rows:
        row = row + [""] * (cols - len(row))
        row = [re.sub(r"\s+", " ", cell).strip() for cell in row]
        normalized.append(row)

    if cols < 2:
        return None

    out = ["| " + " | ".join(normalized[0]) + " |", "| " + " | ".join(["---"] * cols) + " |"]
    for row in normalized[1:]:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def normalize_tables(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if re.match(r"^\s*\+[-:=+]+", line):
            block: list[str] = []
            j = i
            while j < len(lines) and (re.match(r"^\s*[\+\|]", lines[j]) or not lines[j].strip()):
                block.append(lines[j])
                j += 1
            parsed = parse_pandoc_table(block)
            if parsed:
                out.extend(["", parsed, ""])
            i = j
            continue

        if line.strip().startswith("|") and line.count("|") >= 2:
            block: list[str] = []
            j = i
            while j < len(lines) and lines[j].strip().startswith("|") and lines[j].count("|") >= 2:
                block.append(lines[j])
                j += 1
            rows = []
            for row in block:
                cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
                rows.append(cells)
            cols = max(len(row) for row in rows)
            out.append("| " + " | ".join(rows[0] + [""] * (cols - len(rows[0]))) + " |")
            out.append("| " + " | ".join(["---"] * cols) + " |")
            for row in rows[1:]:
                out.append("| " + " | ".join(row + [""] * (cols - len(row))) + " |")
            i = j
            continue

        out.append(line)
        i += 1

    return "\n".join(out)


def remove_noise_lines(lines: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    removed = 0
    for raw in lines:
        line = clean_inline(raw)
        if not line:
            out.append("")
            continue
        if is_junk_line(line):
            removed += 1
            continue
        out.append(line)
    return out, removed


def merge_paragraphs(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0

    while i < len(lines):
        cur = lines[i]
        if (
            cur.strip()
            and i + 1 < len(lines)
            and lines[i + 1].strip()
            and not NO_MERGE_START.match(cur)
            and not NO_MERGE_START.match(lines[i + 1])
            and not cur.strip().startswith("|")
            and not lines[i + 1].strip().startswith("|")
        ):
            last = cur.rstrip()
            if last and last[-1] not in END_PUNCT:
                out.append(last + lines[i + 1].lstrip())
                i += 2
                continue
        out.append(cur)
        i += 1

    return "\n".join(out)


def normalize_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def build_report(stats: dict[str, int]) -> str:
    return f"""# 杨帆三国法整理说明

## 本轮范围

- 输入文件：`OCR原稿/杨帆《三国法》.md`
- 输出文件：`整理后文本/杨帆三国法_整理版.md`
- 处理原则：只做高置信结构整理和 OCR 降噪，保留知识层级，不切块、不改写论述逻辑。

## 本轮规则

- 以正文中的 `第一编` 为起点，跳过前置出版信息、前言、目录和目录页页码。
- 保留并统一 `编 -> 专题 -> 节 -> 目` 四级结构。
- 删除各专题的“本专题知识点概览”及其后续导图噪音，直到进入第一节正文。
- 清理 pandoc 残留、无意义加粗、孤立页码、页眉页脚和高置信乱码行。
- 保留正文表格，尽量转成 Markdown 表格，便于后续切块和向量化。
- 合并被 OCR 硬换行打断的自然段，但不跨标题、表格、编号项强行拼接。

## 统计

- 正文起点行：`{stats["body_start_line"]}`
- 原稿总行数：`{stats["raw_lines"]}`
- 正文截取后行数：`{stats["body_lines"]}`
- 删除噪音行：`{stats["noise_removed"]}`
- 删除概览导图行：`{stats["overview_removed"]}`
- 输出总行数：`{stats["output_lines"]}`

## 后续建议

- 第二步切块前，建议优先人工抽查 `【经典真题】`、表格较密集段落和国际私法部分的外国法查明表格。
- 若后续要做题库化，可再单独把“经典真题”相关问答块从整理版里结构化拆出。
"""


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    raw = remove_pandoc_artifacts(raw)
    raw = remove_meaningless_bold(raw)
    raw = normalize_text(raw)

    all_lines = raw.split("\n")
    body_start = find_body_start(all_lines)
    body_lines = all_lines[body_start:]
    body_lines, duplicate_removed = remove_duplicate_second_part(body_lines)

    body_lines, overview_removed = skip_topic_overview(body_lines)
    body_lines, noise_removed = remove_noise_lines(body_lines)
    body_lines = normalize_headings(body_lines)
    body_lines = inject_topic_headings(body_lines)

    body = "\n".join(body_lines)
    body = normalize_tables(body)
    body = merge_paragraphs(body)
    body = normalize_blank_lines(body)

    final_text = f"# {BOOK_TITLE}\n\n> 整理说明：本文件依据 OCR 原稿进行第一遍整理，统一编-专题-节-目层级，清理目录、概览导图、页码与高置信噪音，为后续切块和向量数据库入库做准备。本轮不切块。\n\n---\n\n{body}"
    DST.write_text(final_text, encoding="utf-8")

    stats = {
        "body_start_line": body_start + 1,
        "raw_lines": len(all_lines),
        "body_lines": len(body_lines),
        "noise_removed": noise_removed,
        "overview_removed": overview_removed,
        "duplicate_removed": duplicate_removed,
        "output_lines": len(final_text.splitlines()),
    }
    REPORT.write_text(build_report(stats), encoding="utf-8")

    print(f"已生成：{DST}")
    print(f"已生成：{REPORT}")
    for key, value in stats.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
