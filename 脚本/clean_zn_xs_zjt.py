#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""左宁刑诉真金题第一遍整理脚本。"""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = (
    PROJECT_ROOT
    / "OCR原稿"
    / "刑诉真金题"
    / "26刑诉法左宁真金题"
    / "ocr"
    / "26刑诉法左宁真金题.md"
)
OUT = PROJECT_ROOT / "整理后文本" / "左宁刑诉真金题_整理版.md"
REPORT = PROJECT_ROOT / "整理后文本" / "左宁刑诉真金题_整理说明.md"

BOOK_TITLE = "左宁刑诉真金题（第一遍整理版）"
SOURCE_NAME = "OCR原稿/刑诉真金题/26刑诉法左宁真金题/ocr/26刑诉法左宁真金题.md"
BODY_START_TEXT = "## PART第一编基础原理"
ANSWER_INDEX_TEXT = "## 本书答案速查"

IMAGE_RE = re.compile(r"!\[\]\(images/([^)]+)\)")
PAGE_TAIL_RE = re.compile(r"\s*/\d{1,4}\s*$")
PART_RE = re.compile(r"^##\s*(?:PART\s*)?(第[一二三四五六七八九十]+编)\s*(.+)?$")
APPENDIX_RE = re.compile(r"^#\s*(附录[一二三四五六七八九十])[:：]?\s*(.+)$")
TOPIC_HEADING_RE = re.compile(r"^#\s*(?:专题|/专题).*$")
TOPIC_TOC_RE = re.compile(r"^(专题[一二三四五六七八九十百0-9]+)\s*(.+?)\s*/\d+\s*$")
TOPIC_TITLE_RE = re.compile(r"^(专题[一二三四五六七八九十百0-9]+)\s*(.+)$")
POINT_RE = re.compile(r"^##\s*(考点\s*[0-9一二三四五六七八九十百]+[:：]?\s*.+)$")
QUESTION_OPTION_RE = re.compile(r"^(?P<stem>\d+[\.．].*?)(?=(?:[A-D][\.．]))")
OPTION_SPLIT_RE = re.compile(r"(?<!^)(?=(?:[A-D][\.．]))")
LABEL_SPLIT_RE = re.compile(
    r"(?=【(?:解析|注意|归纳|背下来|命题规律|设题陷阱|常见错误分析|脚注|图片整理|待复核)】)"
)
CJK_SPACE_RE = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
MULTI_SPACE_RE = re.compile(r"\s+")

# 广告和导流残片常见形态
AD_FRAGMENT_RE = re.compile(
    r"(?:戴)?(?:内部课程|最权威内部课程|最权威内)?/?解(?:密|岔|宓)?\s*(?:VX|VY)?[:：·]?\s*[0-9A-Za-z'’./-]*",
    re.IGNORECASE,
)
VX_FRAGMENT_RE = re.compile(
    r"\S{0,12}(?:VX|VY)[:：·]?\s*[0-9A-Za-z'’./-]{4,}",
    re.IGNORECASE,
)
JIE_PREFIX_RE = re.compile(
    r"\S{0,12}/\S{0,6}(?:VX|VY)[:：·]?\s*[0-9A-Za-z'’./-]{3,}",
    re.IGNORECASE,
)
TRAILING_TOP_AUTH_RE = re.compile(r"(?:最权威|鏈€鏉冨▉)\s*$")

LABEL_MAP = {
    "（解析）": "【解析】",
    "[解析]": "【解析】",
    "［解析］": "【解析】",
    "（注意）": "【注意】",
    "[注意]": "【注意】",
    "［注意］": "【注意】",
    "（归纳）": "【归纳】",
    "[归纳]": "【归纳】",
    "［归纳］": "【归纳】",
    "（背下来）": "【背下来】",
    "[背下来]": "【背下来】",
    "［背下来］": "【背下来】",
    "（命题规律）": "【命题规律】",
    "[命题规律]": "【命题规律】",
    "（设题陷阱）": "【设题陷阱】",
    "[设题陷阱]": "【设题陷阱】",
    "（常见错误分析）": "【常见错误分析】",
    "[常见错误分析]": "【常见错误分析】",
    "（脚注）": "【脚注】",
    "[脚注]": "【脚注】",
}

NOISE_LINES = {
    "点评",
    "点 评",
    "解密",
    "最权威",
    "内部课程",
}


def collapse_cjk_spaces(text: str) -> str:
    previous = None
    current = text
    while previous != current:
        previous = current
        current = CJK_SPACE_RE.sub("", current)
    return current


def normalize_label_tokens(text: str) -> str:
    for src, dst in LABEL_MAP.items():
        text = text.replace(src, dst)
    return text


def normalize_topic_spacing(text: str) -> str:
    match = TOPIC_TITLE_RE.match(text)
    if not match:
        return text
    return f"{match.group(1)} {match.group(2).strip()}"


def normalize_line(line: str) -> str:
    line = line.replace("\u3000", " ").replace("\xa0", " ").strip()
    line = line.replace("【解析：", "【解析】")
    line = normalize_label_tokens(line)
    line = PAGE_TAIL_RE.sub("", line)

    line = line.replace("最权威内部课程/解专题", "专题")
    line = line.replace("内部课程/解专题", "专题")
    line = line.replace("专题灵权期向送送", "专题八 期间、送达")
    line = line.replace("最权威内专题二 管", "专题二 管辖")
    line = line.replace("专题一 立 案", "专题一 立案")
    line = line.replace("专题二 侦 查", "专题二 侦查")
    line = line.replace("专题三 起 诉", "专题三 起诉")

    line = AD_FRAGMENT_RE.sub("", line)
    line = VX_FRAGMENT_RE.sub("", line)
    line = JIE_PREFIX_RE.sub("", line)
    line = re.sub(r"最权威内部课程/?", "", line)
    line = re.sub(r"内部课程/?", "", line)
    line = re.sub(r"最权威内", "", line)
    line = re.sub(r"^/+", "", line)
    line = TRAILING_TOP_AUTH_RE.sub("", line).strip()

    line = MULTI_SPACE_RE.sub(" ", line).strip()
    line = collapse_cjk_spaces(line)

    if line == "## 第三编办案流程":
        return "## 第三编 办案流程"
    if line == "## 特别程序":
        return "## 第四编 特别程序"
    if line.startswith("# /专题"):
        line = "# 专题" + line.split("/专题", 1)[1]

    if line.startswith("# 专题"):
        line = "# " + normalize_topic_spacing(line[2:].strip())
    elif line.startswith("专题"):
        line = normalize_topic_spacing(line)

    return line.strip()


def extract_topic_order(lines: list[str]) -> list[str]:
    topics: list[str] = []
    for raw in lines:
        line = normalize_line(raw)
        if line == BODY_START_TEXT:
            break
        match = TOPIC_TOC_RE.match(line)
        if not match:
            continue
        topic = normalize_topic_spacing(f"{match.group(1)} {match.group(2).strip()}")
        topic = MULTI_SPACE_RE.sub(" ", topic).strip()
        topics.append(topic)
    return topics


def normalize_part_heading(line: str) -> str | None:
    appendix_match = APPENDIX_RE.match(line)
    if appendix_match:
        return f"{appendix_match.group(1)} {appendix_match.group(2).strip()}"

    match = PART_RE.match(line)
    if not match:
        return None
    title = (match.group(2) or "").strip()
    return f"{match.group(1)} {title}".strip()


def normalize_point_heading(line: str) -> str | None:
    match = POINT_RE.match(line)
    if not match:
        return None
    return collapse_cjk_spaces(match.group(1).strip())


def split_compound_line(line: str) -> list[str]:
    if not line:
        return []

    parts: list[str] = []
    queue = [line]

    while queue:
        current = queue.pop(0).strip()
        if not current:
            continue

        question_match = QUESTION_OPTION_RE.match(current)
        if question_match and re.search(r"[A-D][\.．]", current):
            stem = question_match.group("stem").strip()
            remainder = current[len(stem) :].strip()
            parts.append(stem)
            if remainder:
                queue[:0] = [item.strip() for item in OPTION_SPLIT_RE.split(remainder) if item.strip()]
            continue

        if re.match(r"^[A-D][\.．]", current):
            split_options = [item.strip() for item in OPTION_SPLIT_RE.split(current) if item.strip()]
            if len(split_options) > 1:
                queue[:0] = split_options
                continue

        if "【" in current and not current.startswith("【"):
            split_labels = [item.strip() for item in LABEL_SPLIT_RE.split(current) if item.strip()]
            if len(split_labels) > 1:
                queue[:0] = split_labels
                continue

        parts.append(current)

    return parts


def is_pure_ad_line(line: str) -> bool:
    if not line:
        return True
    if line in NOISE_LINES:
        return True
    if line.startswith(("VX", "VY")):
        return True
    if "解密" in line and len(line) <= 12:
        return True
    return False


def should_mark_review(line: str) -> bool:
    if "?" in line and not line.startswith("http"):
        return True
    if "�" in line:
        return True
    if re.search(r"[A-Za-z0-9]+/$", line):
        return True
    return False


def build_output(lines: list[str]) -> tuple[str, int, int, int]:
    topic_order = extract_topic_order(lines)
    image_total = sum(1 for raw in lines if IMAGE_RE.search(raw))
    image_kept = 0

    out: list[str] = [
        f"# {BOOK_TITLE}",
        "",
        f"> 整理说明：本文件由 `{SOURCE_NAME}` 第一遍整理而来，采用“编 -> 专题 -> 考点 -> 题目”结构，保留题干、选项、解析及轻标签内容；本轮删除封面、前言、目录、APP 导流、答案速查与原始图片链接，不切块、不入库。",
        "",
    ]

    body_started = False
    current_part = ""
    topic_index = 0
    review_count = 0

    for raw in lines:
        if not body_started:
            if normalize_line(raw) == BODY_START_TEXT:
                body_started = True
                current_part = "第一编 基础原理"
                out.extend([f"## {current_part}", ""])
            continue

        if IMAGE_RE.search(raw):
            continue

        line = normalize_line(raw)
        if not line:
            continue

        if line.startswith(ANSWER_INDEX_TEXT):
            break

        if is_pure_ad_line(line):
            continue

        appendix_heading = normalize_part_heading(line) if line.startswith("# 附录") else None
        if appendix_heading:
            if appendix_heading != current_part:
                current_part = appendix_heading
                out.extend([f"## {current_part}", ""])
            continue

        part_heading = normalize_part_heading(line)
        if line.startswith("##") and part_heading and (part_heading.startswith("第") or part_heading.startswith("附录")):
            if part_heading != current_part:
                current_part = part_heading
                out.extend([f"## {current_part}", ""])
            continue

        if line.startswith("## ") and not normalize_point_heading(line):
            line = line[3:].strip()
            if not line or is_pure_ad_line(line):
                continue

        if TOPIC_HEADING_RE.match(line):
            if topic_index < len(topic_order):
                topic = topic_order[topic_index]
            else:
                topic = normalize_topic_spacing(re.sub(r"^#\s*", "", line))
            topic_index += 1
            out.extend([f"### {topic}", ""])
            continue

        point = normalize_point_heading(line)
        if point:
            out.extend([f"#### {point}", ""])
            continue

        for part in split_compound_line(line):
            part = part.strip()
            if not part or is_pure_ad_line(part):
                continue
            if should_mark_review(part):
                out.append("【待复核】原文存在 OCR 断裂或乱码残留，本轮先保留结构。")
                out.append("")
                review_count += 1
            out.append(part)
            out.append("")

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text, image_total, image_kept, review_count


def build_report(image_total: int, image_kept: int, review_count: int) -> str:
    removed_images = image_total - image_kept
    return "\n".join(
        [
            "# 左宁刑诉真金题_整理说明",
            "",
            "## 本轮输入输出",
            "",
            f"- 输入文件：`{SOURCE_NAME}`",
            "- 辅助参考：`OCR原稿/刑诉真金题/26刑诉法左宁真金题/ocr/26刑诉法左宁真金题_middle.json`、`OCR原稿/刑诉真金题/26刑诉法左宁真金题/ocr/26刑诉法左宁真金题_content_list.json`、`OCR原稿/刑诉真金题/26刑诉法左宁真金题/ocr/26刑诉法左宁真金题_content_list_v2.json`、`OCR原稿/刑诉真金题/26刑诉法左宁真金题/ocr/images/`",
            "- 输出文件：`整理后文本/左宁刑诉真金题_整理版.md`",
            "- 说明文件：`整理后文本/左宁刑诉真金题_整理说明.md`",
            "",
            "## 本轮清洗规则",
            "",
            "- 正文从 `## PART第一编基础原理` 起算，删除封面、CIP、前言、课程使用说明、目录、APP 导流页及明显广告噪音。",
            "- 输出结构统一为 `编 -> 专题 -> 考点 -> 题目`，专题顺序优先参考目录回填，以修复正文中少量标题串位或 OCR 变形。",
            "- 统一轻标签样式为 `【解析】`、`【注意】`、`【归纳】`、`【背下来】`、`【图片整理】`、`【待复核】`；若正文出现 `【命题规律】`、`【设题陷阱】`、`【常见错误分析】`、`【脚注】`，保留原标签。",
            "- `综上所述，本题答案为...` 一类结论句保留在题目块内部，不另拆字段。",
            "- 保留 `附录一：监察法与刑诉法结合考查知识点`，删除 `附录二：本书答案速查` 及其索引表残片。",
            "",
            "## 图片处理策略",
            "",
            f"- 原稿共识别到 `{image_total}` 处图片引用，本轮全部移除原始 `![](images/...)` 链接。",
            f"- 转写为 `【图片整理】` 的图片：`{image_kept}` 处。",
            f"- 直接删除的图片：`{removed_images}` 处，主要为封面、APP 截图或本轮暂不稳定转写的图片。",
            "",
            "## 仍需二次清洗的遗留类型",
            "",
            f"- 本轮共插入 `【待复核】` 提示 `{review_count}` 处，主要用于 OCR 断裂、乱码残留或选项断行异常的低置信片段。",
            "- 个别题目仍可能存在行内断裂、表格边界噪音或解释性段落压行，适合下一轮二次清洗继续压缩。",
            "- 本轮目标是把结构先拉稳，便于后续精修和切块准备，不建议直接将本版作为最终入库文本。",
            "",
        ]
    )


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    text, image_total, image_kept, review_count = build_output(lines)
    OUT.write_text(text, encoding="utf-8")
    REPORT.write_text(build_report(image_total, image_kept, review_count), encoding="utf-8")
    print(f"输出整理版：{OUT}")
    print(f"输出说明：{REPORT}")
    print(f"图片引用：{image_total}")
    print(f"图片转写：{image_kept}")
    print(f"待复核：{review_count}")


if __name__ == "__main__":
    main()
