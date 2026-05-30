#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""民诉真金题第二遍二次清洗脚本。

本轮目标：
1. 仅以第一遍整理稿为输入；
2. 保守修正高置信 OCR 噪音与结构杂质；
3. 输出独立的二次清洗稿与说明文件；
4. 不切块、不生成 JSONL、不改导库脚本。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "整理后文本" / "民诉真金题_整理版.md"
DST = PROJECT_ROOT / "整理后文本" / "民诉真金题_二次清洗版.md"
RULES_DOC = PROJECT_ROOT / "整理后文本" / "民诉真金题_二次清洗说明.md"

TITLE_OLD = "# 民诉真金题（第一遍整理版）"
TITLE_NEW = "# 民诉真金题（二次清洗版）"

CORE_LABELS = ("【题干】", "【选项】", "【解析】", "【答案】")
SUPPLEMENTARY_LABELS = (
    "【背下来】",
    "【命题思路】",
    "【深度拓展】",
    "【举一反三】",
    "【脚注】",
    "【总结】",
    "【原理与逻辑】",
    "【注意】",
    "【待复核】",
)

REVIEW_LABELS = ("【待核】", "【待复核】")
QUESTION_HEADER_RE = re.compile(r"^##### 第\d+题\s*$", re.M)
LABEL_LINE_RE = re.compile(r"^【[^】]+】", re.M)
TOPIC_RE = re.compile(r"^### 专题", re.M)


@dataclass
class ReviewItem:
    question: str
    reason: str


def normalize_newlines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def normalize_title(text: str) -> str:
    if text.startswith(TITLE_OLD):
        return text.replace(TITLE_OLD, TITLE_NEW, 1)
    if text.startswith("# 民诉真金题"):
        first_line, _, rest = text.partition("\n")
        return TITLE_NEW + ("\n" + rest if rest else "")
    return TITLE_NEW + "\n\n" + text


def split_question_blocks(text: str) -> tuple[str, list[str]]:
    matches = list(QUESTION_HEADER_RE.finditer(text))
    if not matches:
        raise ValueError("未识别到题目标题，无法进行第二轮清洗。")
    prefix = text[: matches[0].start()]
    blocks: list[str] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks.append(text[match.start() : end].rstrip("\n"))
    return prefix.rstrip("\n"), blocks


def strip_line_noise(line: str) -> str:
    s = line.strip()
    if not s:
        return ""

    if s in {"：", ":", "；", ";", "|", ".", "．", "］", "［", "】", "【", "’："}:
        return ""

    s = re.sub(r"^[「『“”‘’\"'`]+", "", s)
    s = re.sub(r"[「」『』“”‘’]+", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace(" : :", "：").replace(": :", "：").replace("： :", "：")
    s = s.replace("； :", "；").replace("； :", "；")
    s = s.replace("■", "")
    s = s.replace("一■种", "一种")
    s = s.replace("法皖", "法院")
    s = re.sub(r"^\.\s*", "", s)
    s = re.sub(r"^[iI]\s+(?=[\u4e00-\u9fff])", "", s)
    s = re.sub(r"^[：:；;，,。.、|]+", "", s)
    s = re.sub(r"[|]+$", "", s)
    s = re.sub(r"\s+([，。！？；：）】》])", r"\1", s)
    s = re.sub(r"([（【《])\s+", r"\1", s)
    return s.strip()


def clean_exam_ref(text: str) -> str:
    text = re.sub(r"（\s*2（2，多）", "（2022，多）", text)
    text = re.sub(r"（飞）1\"", "", text)
    text = re.sub(r"（\s*2020 4\s*$", "（2020，待复核）", text)
    return text


def clean_answer_line(line: str) -> str:
    content = line.replace("【答案】", "", 1).strip()
    content = content.replace(" ", "")
    content = content.replace("O", "")
    content = re.sub(r"[^A-D]", "", content)
    return f"【答案】{content}" if content else "【答案】"


def clean_label_line(line: str) -> str:
    line = line.replace("【待核】", "【待复核】")
    for label in CORE_LABELS + SUPPLEMENTARY_LABELS:
        if line.startswith(label):
            body = line[len(label) :].strip()
            body = clean_exam_ref(strip_line_noise(body))
            if label == "【答案】":
                return clean_answer_line(label + body)
            return label if not body else f"{label}{body}"
    return clean_exam_ref(strip_line_noise(line))


def should_drop_after_label(label: str, line: str) -> bool:
    if not line:
        return True
    if label == "【待复核】" and line in {"答案原文含噪音：", "答案原文含噪音"}:
        return True
    return False


def clean_block_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    last_label = ""
    for raw in lines:
        line = clean_label_line(raw.rstrip())
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        if LABEL_LINE_RE.match(line):
            last_label = LABEL_LINE_RE.match(line).group(0)
            cleaned.append(line)
            continue

        if should_drop_after_label(last_label, line):
            continue

        if last_label == "【待复核】" and line == "答案原文含噪音：BD":
            line = "答案原文含噪音：BDO，现仅保留高置信字母 BD。"

        if last_label == "【题干】":
            line = re.sub(r"^[0Oo]+\.\s*", "", line)
            line = re.sub(r"^\?\s*", "", line)

        cleaned.append(line)

    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


def extract_sections(block: str) -> tuple[str, list[tuple[str, list[str]]]]:
    lines = block.split("\n")
    header = lines[0].strip()
    sections: list[tuple[str, list[str]]] = []
    current_label = ""
    current_lines: list[str] = []

    for raw in lines[1:]:
        line = raw.rstrip()
        match = LABEL_LINE_RE.match(line.strip())
        if match:
            if current_label:
                sections.append((current_label, current_lines))
            current_label = match.group(0).replace("【待核】", "【待复核】")
            remainder = line.strip()[len(match.group(0)) :].strip()
            current_lines = [remainder] if remainder else []
        else:
            current_lines.append(line)

    if current_label:
        sections.append((current_label, current_lines))
    return header, sections


def rebuild_question(header: str, sections: list[tuple[str, list[str]]]) -> str:
    order: list[tuple[str, list[str]]] = []
    buffer: dict[str, list[str]] = {}
    seen: list[str] = []

    for label, lines in sections:
        normalized_label = label.replace("【待核】", "【待复核】")
        cleaned_lines = clean_block_lines(lines)
        if normalized_label in buffer:
            if cleaned_lines:
                if buffer[normalized_label] and cleaned_lines[0] != "":
                    buffer[normalized_label].append("")
                buffer[normalized_label].extend(cleaned_lines)
        else:
            buffer[normalized_label] = cleaned_lines
            seen.append(normalized_label)

    preferred = list(CORE_LABELS) + [label for label in seen if label not in CORE_LABELS]
    for label in preferred:
        if label in buffer:
            order.append((label, buffer[label]))

    parts = [header]
    for label, lines in order:
        if lines:
            parts.append(f"{label}{lines[0]}")
            parts.extend(lines[1:])
        else:
            parts.append(label)
        parts.append("")

    while parts and parts[-1] == "":
        parts.pop()
    return "\n".join(parts)


def collect_stats(text: str) -> dict[str, int]:
    lines = text.splitlines()
    blocks = split_question_blocks(text)[1]

    def has_label(block: str, label: str) -> bool:
        return any(line.startswith(label) for line in block.splitlines())

    return {
        "topics": sum(1 for line in lines if line.startswith("### 专题")),
        "questions": sum(1 for line in lines if line.startswith("##### 第")),
        "answers": sum(1 for line in lines if line.startswith("【答案】")),
        "analysis": sum(1 for line in lines if line.startswith("【解析】")),
        "review": sum(
            1
            for line in lines
            if line.startswith("【待复核】") or line.startswith("【待核】")
        ),
        "missing_answers": sum(1 for block in blocks if not has_label(block, "【答案】")),
        "missing_analysis": sum(1 for block in blocks if not has_label(block, "【解析】")),
        "missing_stem": sum(1 for block in blocks if not has_label(block, "【题干】")),
        "missing_options": sum(1 for block in blocks if not has_label(block, "【选项】")),
    }


def collect_review_items(text: str) -> list[ReviewItem]:
    _, blocks = split_question_blocks(text)
    items: list[ReviewItem] = []
    for block in blocks:
        lines = block.splitlines()
        header = lines[0].strip().replace("##### ", "")
        for idx, line in enumerate(lines):
            if line.startswith("【待复核】"):
                payload = line.replace("【待复核】", "", 1).strip()
                if not payload and idx + 1 < len(lines):
                    payload = lines[idx + 1].strip()
                payload = payload or "存在未高置信恢复内容"
                items.append(ReviewItem(question=header, reason=payload))
                break
    return items


def validate(question_blocks: list[str], before: dict[str, int], after: dict[str, int]) -> None:
    numbers = []
    for block in question_blocks:
        header = block.splitlines()[0].strip()
        match = re.search(r"第(\d+)题", header)
        if not match:
            raise ValueError(f"题号格式异常：{header}")
        numbers.append(int(match.group(1)))

    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        raise ValueError("题号不连续，已停止写出。")
    if after["topics"] != 31:
        raise ValueError(f"专题数异常：{after['topics']}，预期为 31。")
    if after["missing_stem"] != 0 or after["missing_options"] != 0:
        raise ValueError("存在缺少【题干】或【选项】的题目。")
    if after["missing_answers"] > before["missing_answers"]:
        raise ValueError("第二轮后缺【答案】题量增加。")
    if after["missing_analysis"] > before["missing_analysis"]:
        raise ValueError("第二轮后缺【解析】题量增加。")


def build_rules_doc(before: dict[str, int], after: dict[str, int], review_items: list[ReviewItem]) -> str:
    if before["review"] > 0:
        review_stat_line = f"- `【待复核】` 数：`{after['review']}`（第一遍待核数为 `{before['review']}`）"
    else:
        review_stat_line = (
            f"- `【待复核】` 数：`{after['review']}`"
            "（第一遍显式待核标记统计口径不稳定，本轮已统一收敛为待复核列表）"
        )

    lines = [
        "# 民诉真金题二次清洗说明",
        "",
        "## 本轮范围",
        "",
        "- 输入文件：`整理后文本/民诉真金题_整理版.md`",
        "- 输出文件：`整理后文本/民诉真金题_二次清洗版.md`",
        "- 处理原则：只做高置信结构修正和 OCR 噪音清理，不重排专题、不重写解析、不补造缺失答案。",
        "- 标签策略：统一使用 `【待复核】`，不再混用 `【待核】`。",
        "",
        "## 本轮规则",
        "",
        "- 题目结构保持为“专题 + 小节 + 题目块 + 附属块”。",
        "- 题目块内部统一按 `【题干】`、`【选项】`、`【解析】`、`【答案】` 优先排序；补充块仍挂在题目后。",
        "- 清除高置信孤立噪音行，如单独的 `:`、`|`、`．`、`’：` 等。",
        "- 清理题干前缀残符，如 `「\"0.`、孤立问号、残留引号等明显 OCR 垃圾。",
        "- 对明显答案噪音做保守修正，如 `BDO` 仅保留高置信答案 `BD`，并在 `【待复核】` 中保留说明。",
        "- 附属块只清结构与噪音，不改写讲义内容。",
        "",
        "## 统计",
        "",
        f"- 专题数：`{after['topics']}`",
        f"- 题目数：`{after['questions']}`",
        f"- `【答案】` 数：`{after['answers']}`（第一遍为 `{before['answers']}`）",
        f"- `【解析】` 数：`{after['analysis']}`（第一遍为 `{before['analysis']}`）",
        review_stat_line,
        f"- 缺 `【答案】` 题量：`{after['missing_answers']}`（第一遍为 `{before['missing_answers']}`）",
        f"- 缺 `【解析】` 题量：`{after['missing_analysis']}`（第一遍为 `{before['missing_analysis']}`）",
        "",
        "## 残留待复核",
        "",
    ]

    if review_items:
        for item in review_items:
            lines.append(f"- {item.question}：{item.reason}")
    else:
        lines.append("- 本轮未检出 `【待复核】` 条目。")

    lines.extend(
        [
            "",
            "## 后续建议",
            "",
            "- 第三步切块前，可优先过滤或单独抽检所有 `【待复核】` 题目。",
            "- 对缺 `【答案】`、缺 `【解析】` 的题目，建议回看原稿或人工校对后再进入向量库流程。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    source_text = normalize_newlines(SRC.read_text(encoding="utf-8"))
    before = collect_stats(source_text)

    text = normalize_title(source_text)
    prefix, blocks = split_question_blocks(text)
    cleaned_blocks = []
    for block in blocks:
        header, sections = extract_sections(block)
        cleaned_blocks.append(rebuild_question(header, sections))

    output_text = prefix.strip() + "\n\n" + "\n\n".join(cleaned_blocks) + "\n"
    output_text = re.sub(r"\n{3,}", "\n\n", output_text)
    output_text = output_text.replace("【待核】", "【待复核】")

    after = collect_stats(output_text)
    validate(cleaned_blocks, before, after)
    review_items = collect_review_items(output_text)
    rules_doc = build_rules_doc(before, after, review_items)

    DST.write_text(output_text, encoding="utf-8")
    RULES_DOC.write_text(rules_doc, encoding="utf-8")

    print("民诉真金题第二轮清洗完成")
    print(f"输出：{DST}")
    print(f"说明：{RULES_DOC}")
    print(after)


if __name__ == "__main__":
    main()
