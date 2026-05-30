#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""郄鹏恩《商经知》二次清洗脚本。

目标：
1. 以第一遍整理稿为主输入；
2. 保持既有 Markdown 标题树稳定；
3. 做中强度、高置信的 OCR 噪音清理与结构提纯；
4. 生成独立的二次清洗版与说明文件，不覆盖第一遍整理稿。
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知_整理版.md"
DST = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知_二次清洗版.md"
RULES_DOC = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知_二次清洗说明.md"

HEADING_RE = re.compile(r"^(#{1,6})\s+")
PART_RE = re.compile(r"^##\s+")
TOPIC_RE = re.compile(r"^###\s+专题")
SECTION_RE = re.compile(r"^####\s+第[一二三四五六七八九十\d]+节")
POINT_RE = re.compile(r"^#####\s+考点")
TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
TABLE_BORDER_RE = re.compile(r"^\s*\|?(?:[-:—\s]{2,}\|)+[-:—\s]*\|?\s*$")
PURE_NOISE_RE = re.compile(r"^[\s_\-=\^~`<>|/\\\[\]{}■□◆△▲•.。·:：;；,，*\"'“”‘’()（）]+$")
REVIEW_RE = re.compile(r"^【待复核】\s*")
PHONE_RE = re.compile(r"(?:0\d{2,3}[-— ]?\d{3,4}[-— ]?\d{3,4})|(?:1\d{10})")
HELPER_BOLD_TEXTS = {
    "**以信念为灯，以韧性为盾**",
    "**本书写作特点**",
    "**体系解说**",
    "**复习旨要**",
    "**特别提示**",
}

def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    replacements = {
        "【待核】": "【待复核】",
        "体系解说I": "体系解说",
        "I0T2": "10-12",
        "L年内": "1年内",
        "I元": "1元",
        "“": "\"",
        "”": "\"",
        "‘": "'",
        "’": "'",
        "（-）": "（一）",
        "(-)": "（一）",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def collect_stats(text: str) -> dict[str, int]:
    lines = text.splitlines()
    return {
        "parts": sum(1 for line in lines if line.startswith("## ")),
        "topics": sum(1 for line in lines if line.startswith("### 专题")),
        "sections": sum(1 for line in lines if line.startswith("#### ")),
        "points": sum(1 for line in lines if line.startswith("##### ")),
        "review": sum(1 for line in lines if line.startswith("【待复核】")),
        "vx": text.count("VX"),
        "qq_ad": text.count("法考资料一手更新整理QQ"),
        "topic_summary": text.count("本专题小结"),
    }


def is_contact_heavy(line: str) -> bool:
    hit_count = 0
    for token in ("VX", "vx", "QQ", "www", "http", "邮箱", "电话", "mail", "@"):
        if token in line:
            hit_count += 1
    if PHONE_RE.search(line):
        hit_count += 1
    if "版权页" in line:
        hit_count += 1
    return hit_count >= 2


def is_pure_noise(line: str) -> bool:
    if not line:
        return True
    if PURE_NOISE_RE.match(line):
        return True
    if len(line) <= 4 and re.fullmatch(r"[A-Za-z]+", line):
        return True
    if re.search(r"[*^_<>]{4,}", line):
        return True
    return False


def strip_contact_noise(line: str, stats: Counter) -> str:
    raw = line
    patterns = [
        r"法考资料一手更新整理\s*VX\s*[（(]?\s*QQ\s*[)）]?\s*[:：]?\s*\d+",
        r"法考资料一手更新整理\s*QQ\s*[:：]?\s*\d+",
        r"法考资料一手更新整理[^【\n]{0,80}",
        r"纸质书购买.*",
        r"解密VX.*",
    ]
    for pattern in patterns:
        line, count = re.subn(pattern, "", line, flags=re.IGNORECASE)
        if count:
            stats["ad_inline_removed"] += count
    if raw != line:
        stats["line_changed"] += 1
    return line.strip()


def clean_heading(line: str) -> str:
    line = re.sub(r"\s+", " ", line.strip())
    line = line.replace("◎", "")
    line = re.sub(r"^(#{3})\s*专题([一二三四五六七八九十\d]+)(\S)", r"\1 专题\2 \3", line)
    line = re.sub(r"^(#{4})\s*第([一二三四五六七八九十\d]+)节(\S)", r"\1 第\2节 \3", line)
    line = re.sub(r"^(#{5})\s*考点([一二三四五六七八九十\d]+)(\S)", r"\1 考点\2 \3", line)
    return line


def split_embedded_markers(text: str) -> list[str]:
    markers = ["【例】", "【例1】", "【例2】", "【总结】", "【牛刀小试】", "【特别提示】", "【实务案例】", "【对比】"]
    out = [text]
    for marker in markers:
        next_out: list[str] = []
        for item in out:
            if marker in item and not item.startswith(marker):
                pieces = item.split(marker)
                head = pieces[0].strip()
                if head:
                    next_out.append(head)
                for tail in pieces[1:]:
                    joined = f"{marker}{tail}".strip()
                    if joined:
                        next_out.append(joined)
            else:
                next_out.append(item)
        out = next_out
    return [item.strip() for item in out if item.strip()]


def clean_table_cell(cell: str) -> str:
    cell = cell.replace("<br><br>", "；")
    cell = re.sub(r"<br\s*/?>", "；", cell)
    cell = re.sub(r"\s+", " ", cell)
    cell = cell.strip(" |")
    cell = re.sub(r"；{2,}", "；", cell)
    return cell.strip("； ")


def convert_table_line(line: str, stats: Counter) -> list[str]:
    if TABLE_BORDER_RE.match(line):
        stats["table_border_removed"] += 1
        return []
    cells = [clean_table_cell(cell) for cell in line.strip().strip("|").split("|")]
    cells = [cell for cell in cells if cell and cell not in {"—", "-", "续表"}]
    if not cells:
        stats["table_border_removed"] += 1
        return []
    if len(cells) == 1:
        stats["table_to_text"] += 1
        return split_embedded_markers(cells[0])
    head = cells[0]
    tail = "；".join(cells[1:])
    stats["table_to_text"] += 1
    return split_embedded_markers(f"{head}：{tail}")


def sanitize_line(line: str, stats: Counter) -> list[str]:
    original = line
    had_review = line.startswith("【待复核】")
    line = REVIEW_RE.sub("", line).strip()
    line = line.replace("【待复核】", "")
    line = strip_contact_noise(line, stats)
    if not line:
        if had_review:
            stats["review_removed"] += 1
        return []

    line = line.replace("专题一 公司法", "专题一 公司法")  # keep stable; useful for duplicate detection
    line = line.replace("QQ牛刀小试】", "【牛刀小试】")
    line = line.replace("QQ牛刀小试」", "【牛刀小试】")
    line = line.replace("QQ牛刀小试", "【牛刀小试】")
    line = line.replace("f牛刀小试】", "【牛刀小试】")
    line = line.replace("j 【例】", "【例】")
    line = line.replace(":【例】", "【例】")
    line = line.replace("::【例】", "【例】")
    line = line.replace(":例】", "【例】")
    line = line.replace("【例J", "【例】")
    line = line.replace("【例j", "【例】")
    line = line.replace("［例］", "【例】")
    line = line.replace("［总结］", "【总结】")
    line = line.replace("［对比］", "【对比】")
    line = line.replace("【特别提示j", "【特别提示】")
    line = line.replace("［特别提示j", "【特别提示】")
    line = line.replace("［牛刀小试］", "【牛刀小试】")
    line = line.replace("【JST^i", "【总结】")
    line = line.replace("①【答案】AC0", "①【答案】AC")
    line = re.sub(r"([A-D]+)[0O]\b", r"\1", line)
    line = re.sub(r"(?<=[\u4e00-\u9fff0-9）】])T(?=[\u4e00-\u9fff（(【0-9])", "→", line)
    line = re.sub(r"\(3\+N\)般为", "般为", line)
    line = re.sub(r"(?<=\d)\s*\*\s*(?=\d)", " × ", line)
    line = re.sub(r"\s*<br\s*/?>\s*", "<br>", line)
    line = re.sub(r"\s+", " ", line).strip()

    if "《国家统一法律职业资格考试辅导用书》的版权页" in line:
        stats["copyright_example_trimmed"] += 1
        line = "【例】《国家统一法律职业资格考试辅导用书》的版权页。"

    if line in {"续表", "|续表| |", "专题一 公司法"}:
        return []

    if "本专题小结" in line and (len(line) < 30 or re.search(r"[*^_<>■«»~]", line)):
        stats["topic_summary_removed"] += 1
        return []

    if is_contact_heavy(line):
        stats["contact_line_removed"] += 1
        return []

    if is_pure_noise(line):
        stats["pure_noise_removed"] += 1
        return []

    if original != line:
        stats["line_changed"] += 1

    if "<br>" in line:
        parts = [part.strip() for part in line.split("<br>") if part.strip()]
    else:
        parts = [line]

    fragments: list[str] = []
    for part in parts:
        fragments.extend(split_embedded_markers(part))

    cleaned: list[str] = []
    for fragment in fragments:
        fragment = re.sub(r"\s+", " ", fragment).strip()
        if fragment and not is_pure_noise(fragment):
            cleaned.append(fragment)

    if had_review and not cleaned:
        stats["review_removed"] += 1
    return cleaned


def needs_review(text: str) -> bool:
    if not text:
        return False
    if text in HELPER_BOLD_TEXTS:
        return False
    suspicious_checks = [
        r"[*^_<>■«»~]{2,}",
        r"[�]+",
        r"(?<![A-Za-z])_[A-Za-z]{1,3}\^",
        r"[A-Za-z]{2,}[*^_<>«»~][A-Za-z]{2,}",
    ]
    if any(re.search(pattern, text) for pattern in suspicious_checks):
        return True
    return False


def should_drop_duplicate(line: str, current_topic: str | None, recent_nonempty: list[str]) -> bool:
    if current_topic and line == current_topic.replace("### ", "", 1):
        return True
    if recent_nonempty and line == recent_nonempty[-1]:
        return True
    return False


def build_output(text: str) -> tuple[str, Counter]:
    stats: Counter = Counter()
    lines = text.splitlines()
    out: list[str] = []
    current_topic: str | None = None
    recent_nonempty: list[str] = []

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            if out and out[-1] != "":
                out.append("")
            continue

        if HEADING_RE.match(stripped):
            heading = clean_heading(stripped)
            if heading.startswith("### "):
                current_topic = heading
            if out and out[-1] == "" and len(out) >= 2 and out[-2] == heading:
                continue
            out.append(heading)
            recent_nonempty.append(heading)
            recent_nonempty = recent_nonempty[-8:]
            continue

        if TABLE_LINE_RE.match(stripped):
            cleaned_lines = convert_table_line(stripped, stats)
        else:
            cleaned_lines = sanitize_line(stripped, stats)

        for line in cleaned_lines:
            line = re.sub(r"\s+", " ", line).strip()
            if not line:
                continue
            if should_drop_duplicate(line, current_topic, recent_nonempty):
                stats["duplicate_removed"] += 1
                continue
            if line.startswith("【待复核】"):
                line = REVIEW_RE.sub("", line).strip()

            if needs_review(line):
                line = f"【待复核】{line}"
                stats["review_kept_or_added"] += 1
            else:
                stats["review_removed"] += 1

            out.append(line)
            recent_nonempty.append(line)
            recent_nonempty = recent_nonempty[-8:]

    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"
    return cleaned, stats


def collect_review_items(text: str, limit: int = 20) -> list[str]:
    items: list[str] = []
    current_heading = ""
    for line in text.splitlines():
        if line.startswith("##### "):
            current_heading = line.replace("##### ", "", 1)
        elif line.startswith("#### ") and not current_heading:
            current_heading = line.replace("#### ", "", 1)
        if line.startswith("【待复核】"):
            payload = line.replace("【待复核】", "", 1).strip()
            label = current_heading or "未定位考点"
            items.append(f"- {label}：{payload}")
            if len(items) >= limit:
                break
    return items


def validate(before: dict[str, int], after: dict[str, int], output_text: str) -> None:
    if after["parts"] != before["parts"]:
        raise ValueError(f"篇级标题数量异常：{after['parts']}（原为 {before['parts']}）")
    if after["topics"] != before["topics"]:
        raise ValueError(f"专题标题数量异常：{after['topics']}（原为 {before['topics']}）")
    if after["sections"] != before["sections"]:
        raise ValueError(f"节标题数量异常：{after['sections']}（原为 {before['sections']}）")
    if after["points"] != before["points"]:
        raise ValueError(f"考点标题数量异常：{after['points']}（原为 {before['points']}）")
    if "知识产权诉讼保护" not in output_text:
        raise ValueError("知识产权诉讼保护章节缺失。")
    if after["review"] > before["review"]:
        raise ValueError("二次清洗后 `【待复核】` 数量不应增加。")


def build_rules_doc(before: dict[str, int], after: dict[str, int], stats: Counter, review_items: list[str]) -> str:
    lines = [
        "# 郄鹏恩商经知_二次清洗说明",
        "",
        "## 本轮范围",
        "",
        "- 输入文件：`整理后文本/郄鹏恩商经知_整理版.md`",
        "- 输出文件：`整理后文本/郄鹏恩商经知_二次清洗版.md`",
        "- 处理原则：保持原有标题树不变，优先做高置信 OCR 修正、广告/导图残片删除、伪表格转正文。",
        "- 本轮仍不切块、不生成 JSONL、不做向量化。",
        "",
        "## 本轮规则",
        "",
        "- 删除广告和外部联系方式污染，如 `VX/QQ/电话/网址/邮箱` 等非正文信息。",
        "- 删除纯噪音行、导图边框、ASCII 图框、`本专题小结` 残片和版权页联系方式残片。",
        "- 将明显无法保真的表格框线转为条目化正文，保留主要语义，不保留乱码边框。",
        "- 批量修正常见 OCR 问题，如 `I0T2 -> 10-12`、连接符 `T -> →`、`AC0 -> AC`。",
        "- 仅对仍有明显噪音或低置信内容的行保留 `【待复核】`。",
        "",
        "## 统计",
        "",
        f"- 篇级标题：`{after['parts']}`",
        f"- 专题标题：`{after['topics']}`",
        f"- 节标题：`{after['sections']}`",
        f"- 考点标题：`{after['points']}`",
        f"- `【待复核】`：`{after['review']}`（第一遍为 `{before['review']}`）",
        f"- 伪表格转正文：`{stats['table_to_text']}` 行",
        f"- 删除纯噪音行：`{stats['pure_noise_removed']}` 行",
        f"- 删除广告/联系方式行：`{stats['contact_line_removed']}` 行",
        f"- 删除 `本专题小结` 残片：`{stats['topic_summary_removed']}` 行",
        "",
        "## 残留待复核",
        "",
    ]

    if review_items:
        lines.extend(review_items)
    else:
        lines.append("- 本轮未保留 `【待复核】` 条目。")

    lines.extend(
        [
            "",
            "## 后续建议",
            "",
            "- 下一轮切块可直接按 Markdown 标题层级解析，不必再从广告、框线和目录残片中找边界。",
            "- 若需进一步精修，可优先复核本说明中列出的残留 `【待复核】` 项。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    source_text = normalize_text(SRC.read_text(encoding="utf-8"))
    before = collect_stats(source_text)
    output_text, stats = build_output(source_text)
    after = collect_stats(output_text)
    validate(before, after, output_text)
    review_items = collect_review_items(output_text)
    rules_doc = build_rules_doc(before, after, stats, review_items)

    DST.write_text(output_text, encoding="utf-8")
    RULES_DOC.write_text(rules_doc, encoding="utf-8")

    print("商经知第二轮清洗完成")
    print(f"输出：{DST}")
    print(f"说明：{RULES_DOC}")
    print(after)


if __name__ == "__main__":
    main()
