#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""杨帆三国真金题第一遍整理脚本。

目标：
1. 直接读取 docx 内部 XML，不引入额外依赖。
2. 输出“板块 + 专题 + 题目固定结构”的整理版 Markdown。
3. 保留命题规律、设题陷阱、常见错误分析、脚注等附属内容并显式标注。
4. 本轮不切块、不做二次清洗、不入库。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OCR_DIR = PROJECT_ROOT / "OCR原稿"
OUTPUT_PATH = PROJECT_ROOT / "整理后文本" / "杨帆三国真金题_整理版.md"
REPORT_PATH = PROJECT_ROOT / "整理后文本" / "杨帆三国真金题_整理说明.md"

BOOK_TITLE = "杨帆三国真金题（第一遍整理版）"
SOURCE_BOOK_NAME = "2026客观真金题三国杨帆_页.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

PARTS = [
    ("国际法", 8),
    ("国际私法", 5),
    ("国际经济法", 7),
]

PROJECT_RE = re.compile(r"^PROJECT\s+(\d+)$")
SECTION_RE = re.compile(r"^[一二三四五六七八九十]+、.+$")
OPTION_RE = re.compile(r"^([A-D])[\.．、]\s*(.+)$")
ANSWER_RE = re.compile(r"(?:综上[^。；]*?|本题[^。；]*?)答案为\s*([A-D]{1,4})([A-Za-z0-9^~\\/-]*)")
EXAM_REF_RE = re.compile(r"[（(][^（）()]*?(?:单|多|不定项|任|案例)[^（）()]*?[）)]")
FOOTNOTE_RE = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩].+")
TOPIC_HINT_RE = re.compile(r"^专题([一二三四五六七八九十]+)(.+)$")
QUESTION_NO_RE = re.compile(r"^[,.;:!！\"'“”‘’·•■\-—\s]*([0-9]{1,3})\.")
QUESTION_START_RE = re.compile(r"^[,.;:!！\"'“”‘’·•■\-—\s\dA-Za-z]*?(下列|哪些|哪一|哪项|何者|说法|表述|如何处理|属于).*(\?|？)")

TOPIC_LABELS = {
    "［本专题命题规律］": "【命题规律】",
    "[本专题命题规律]": "【命题规律】",
    "【本专题命题规律】": "【命题规律】",
}

SUPPLEMENTARY_LABELS = [
    ("设题陷阱与常见错误分析", "【常见错误分析】"),
    ("常见错误分析", "【常见错误分析】"),
    ("设题陷阱", "【设题陷阱】"),
    ("命题思路", "【命题思路】"),
    ("深度拓展", "【深度拓展】"),
    ("举一反三", "【举一反三】"),
    ("背下来", "【背下来】"),
    ("考点", "【考点】"),
]

LINE_REPLACEMENTS = {
    "\u00a0": " ",
    "\u2002": " ",
    "\u2003": " ",
    "\u2009": " ",
    "\u3000": " ",
    "\ufeff": "",
    "［": "【",
    "］": "】",
    "[解析]": "【解析】",
    "【解析】": "【解析】",
    "[本专题命题规律]": "【本专题命题规律】",
    "【本专题命题规律】": "【本专题命题规律】",
    "【考查】": "【考点】",
    "【考查角度】": "【考点】",
    "「": "",
    "」": "",
    "『": "",
    "』": "",
    "．": ".",
    "、 ": "、",
    " :: ": " ",
    "♦": "",
    "◆": "",
}

EXACT_REPAIRS = {
    "专题一导论": "专题一 导论",
    "专题二国际法主体和国际法律责任": "专题二 国际法主体和国际法律责任",
    "专题三国际法上的空间划分": "专题三 国际法上的空间划分",
    "专题四国际法上的个人": "专题四 国际法上的个人",
    "专题五外交关系法和领事关系法": "专题五 外交关系法和领事关系法",
    "专题六条约法": "专题六 条约法",
    "专题七国际争端的解决方式": "专题七 国际争端的解决方式",
    "专题八战争与武装冲突法": "专题八 战争与武装冲突法",
    "专题一国际私法概述": "专题一 国际私法概述",
    "专题二冲突规范": "专题二 冲突规范",
    "专题三国际民商事法律适用": "专题三 国际民商事法律适用",
    "专题四国际民商事争议的解决": "专题四 国际民商事争议的解决",
    "专题五司法伎助": "专题五 司法协助",
    "专题五司法协助": "专题五 司法协助",
    "专题二国际货物买卖法": "专题二 国际货物买卖法",
    "专题三国际货物运输与保险法": "专题三 国际货物运输与保险法",
    "专题四国际贸易支付": "专题四 国际贸易支付",
    "专题五对外贸易管理制度": "专题五 对外贸易管理制度",
    "专题六世界贸易组织（WTO）": "专题六 世界贸易组织（WTO）",
    "专题七国际经济领域的其他法律制度": "专题七 国际经济领域的其他法律制度",
    "WT0": "WTO",
    "ＷT0": "WTO",
    "W T O": "WTO",
    "于连入境": "出入境",
    "司法伎助": "司法协助",
    "裕免": "豁免",
    "金甩": "金题",
    "金胞": "金题",
    "金题-「": "金题-1-",
    "金题-一": "金题-1-",
    "考题-「": "考题-1-",
}


@dataclass
class Question:
    title_index: int
    section_title: str | None
    stem: str
    options: list[str]
    answer: str | None
    analysis: list[str]
    supplementary: list[tuple[str, list[str]]]
    footnotes: list[str]
    review_notes: list[str]


@dataclass
class TopicBlock:
    part: str
    title: str
    intro_blocks: list[tuple[str, list[str]]] = field(default_factory=list)
    preface_notes: list[str] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)


def find_source_docx() -> Path:
    for path in OCR_DIR.glob("*.docx"):
        if "三国" in path.name and "真金题" in path.name:
            return path
    raise FileNotFoundError("未找到杨帆三国真金题 docx 原稿")


def iter_docx_paragraphs(path: Path) -> list[str]:
    with ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))

    lines: list[str] = []
    for para in root.findall(".//w:body/w:p", NS):
        parts: list[str] = []
        for node in para.iter():
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "t" and node.text:
                parts.append(node.text)
            elif tag == "tab":
                parts.append(" ")
        text = "".join(parts).strip()
        if text:
            lines.append(text)
    return lines


def normalize_line(text: str) -> str:
    for old, new in LINE_REPLACEMENTS.items():
        text = text.replace(old, new)
    for old, new in EXACT_REPAIRS.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([，。；：？！）])", r"\1", text)
    text = re.sub(r"([（])\s*", r"\1", text)
    text = re.sub(r"\s+([A-D]\.)", r" \1", text)
    text = text.strip(" \t\r\n")
    return text


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped in {"目录", "Contents", "国际法", "国际私法", "国际经济法"}:
        return False
    if re.fullmatch(r"/?\d+", stripped):
        return True
    if re.fullmatch(r"[.·•\-—_=~^]{1,6}", stripped):
        return True
    if stripped.startswith("专题") and re.search(r"/\s*\d+$", stripped):
        return True
    return False


def preprocess_lines(raw_lines: Iterable[str]) -> list[str]:
    lines: list[str] = []
    body_started = False

    for raw in raw_lines:
        line = normalize_line(raw)
        if not line:
            continue

        if not body_started:
            if line == "PROJECT 01":
                body_started = True
            else:
                continue

        if is_noise_line(line):
            continue
        lines.append(line)

    return lines


def split_projects(lines: list[str]) -> list[list[str]]:
    projects: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if PROJECT_RE.match(line):
            if current:
                projects.append(current)
            current = [line]
            continue
        if current:
            current.append(line)

    if current:
        projects.append(current)

    return projects


def normalize_topic_title(title: str) -> str:
    title = title.strip()
    if title in EXACT_REPAIRS:
        return EXACT_REPAIRS[title]
    matched = TOPIC_HINT_RE.match(title)
    if matched:
        return f"专题{matched.group(1)} {matched.group(2).strip()}"
    return title


def annotate_project_parts(projects: list[list[str]]) -> list[TopicBlock]:
    blocks: list[TopicBlock] = []
    project_index = 0

    for part_name, count in PARTS:
        for _ in range(count):
            block_lines = projects[project_index]
            topic_title = normalize_topic_title(block_lines[1]) if len(block_lines) > 1 else f"专题{project_index + 1}"
            blocks.append(TopicBlock(part=part_name, title=topic_title))
            project_index += 1

    return blocks


def contains_exam_ref(line: str) -> bool:
    return bool(EXAM_REF_RE.search(line))


def split_inline_options(line: str) -> list[str]:
    if line.startswith(("A.", "B.", "C.", "D.")):
        return [line]
    if sum(1 for marker in ("A.", "B.", "C.", "D.") if marker in line) >= 2:
        parts = re.split(r"(?=\b[A-D]\.)", line)
        return [part.strip() for part in parts if part.strip()]
    return [line]


def looks_like_question_start(line: str, next_lines: list[str]) -> bool:
    if not line or line.startswith("【"):
        return False
    first_four = next_lines[:4]
    has_ordered_abcd = (
        len(first_four) >= 4
        and first_four[0].startswith("A.")
        and first_four[1].startswith("B.")
        and first_four[2].startswith("C.")
        and first_four[3].startswith("D.")
    )
    nearby = "\n".join(next_lines[:6])
    has_abcd = (
        bool(re.search(r"^A\.", nearby, flags=re.M))
        and bool(re.search(r"^B\.", nearby, flags=re.M))
        and bool(re.search(r"^C\.", nearby, flags=re.M))
        and bool(re.search(r"^D\.", nearby, flags=re.M))
    )
    if has_ordered_abcd:
        return True
    if has_abcd and ("下列" in line or "哪些" in line or "哪一" in line or "哪项" in line or "说法" in line):
        return True
    if contains_exam_ref(line) and any(re.match(r"^[A-D]\.", item) for item in next_lines[:5]):
        return True
    return False


def is_section_heading(line: str) -> bool:
    return bool(SECTION_RE.match(line))


def detect_topic_label(line: str) -> str | None:
    return TOPIC_LABELS.get(line)


def detect_supplementary_label(line: str) -> tuple[str, str] | None:
    compact = line.strip("【】[]:： ")
    for key, label in SUPPLEMENTARY_LABELS:
        if key in compact:
            remainder = compact.replace(key, "", 1).lstrip("是：:，, ")
            return label, remainder
    return None


def normalize_exam_ref(text: str) -> str:
    match = EXAM_REF_RE.search(text)
    if not match:
        return text

    raw = match.group(0)
    compact = raw.strip("（）()").replace(" ", "").replace("，", ",")
    compact = compact.replace("金甩", "金题").replace("金胞", "金题")
    compact = compact.replace("任）", "任）")
    compact = compact.replace("金题-「", "金题-1-")
    compact = compact.replace("金题-一", "金题-1-")

    normalized = compact
    if "," in normalized:
        normalized = normalized.replace(",", "，")
    normalized = f"（{normalized}）"
    return text.replace(raw, normalized)


def cleanup_question_stem(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[,.;:!！\"'“”‘’·•■\-—\s]+", "", line)
    line = re.sub(r"^[A-Za-z]-\s*", "", line)
    return normalize_exam_ref(line)


def looks_like_unlabeled_option(line: str) -> bool:
    if not line:
        return False
    if contains_exam_ref(line) or line.startswith("【") or line.startswith("综上"):
        return False
    if FOOTNOTE_RE.match(line) or SECTION_RE.match(line):
        return False
    if len(line) > 35:
        return False
    if line.endswith(("。", "；", "：")):
        return False
    return True


def patch_unlabeled_options(lines: list[str]) -> list[str]:
    if len(lines) < 5:
        return lines

    head = [lines[0]]
    rest = lines[1:]
    patched: list[str] = []
    i = 0
    while i < len(rest):
        window = rest[i:i + 4]
        if (
            len(window) == 4
            and all(looks_like_unlabeled_option(item) for item in window)
            and not any(OPTION_RE.match(item) for item in window)
        ):
            patched.extend(
                [
                    f"A. {window[0]}",
                    f"B. {window[1]}",
                    f"C. {window[2]}",
                    f"D. {window[3]}",
                ]
            )
            i += 4
            continue
        patched.append(rest[i])
        i += 1
    return head + patched


def extract_answer(line: str) -> tuple[str | None, str | None]:
    matched = ANSWER_RE.search(line)
    if not matched:
        return None, None
    answer = matched.group(1)
    noise = matched.group(2).strip()
    note = None
    if noise:
        note = f"答案原文含噪音：{answer}{noise}"
    return answer, note


def split_option_and_analysis(line: str) -> tuple[str, str | None]:
    matched = OPTION_RE.match(line)
    if not matched:
        return line, None
    body = matched.group(2).strip()
    split_match = re.search(r"\s+(《[^》]{1,18}》|[A-Za-z（）()0-9一-龥]{2,18})$", body)
    if not split_match:
        return f"{matched.group(1)}. {body}", None
    tail = split_match.group(1)
    if re.search(r"[。？！?；：]", tail):
        return f"{matched.group(1)}. {body}", None
    option_body = body[:split_match.start()].strip()
    if len(tail) > 18 or len(option_body) < 8:
        return f"{matched.group(1)}. {body}", None
    return f"{matched.group(1)}. {option_body}", tail


def parse_question(lines: list[str], index: int, section_title: str | None) -> Question:
    lines = patch_unlabeled_options(lines)

    stem_lines: list[str] = []
    options: list[str] = []
    analysis: list[str] = []
    supplementary: list[tuple[str, list[str]]] = []
    footnotes: list[str] = []
    review_notes: list[str] = []
    answer: str | None = None
    current_label: str | None = None
    current_payload: list[str] = []
    stage = "stem"

    def flush_supplementary() -> None:
        nonlocal current_label, current_payload
        if current_label and current_payload:
            supplementary.append((current_label, current_payload[:]))
        current_label = None
        current_payload = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if FOOTNOTE_RE.match(line):
            if current_label:
                current_payload.append(line)
            else:
                footnotes.append(line)
            continue

        label_hit = detect_supplementary_label(line)
        if label_hit:
            flush_supplementary()
            current_label = label_hit[0]
            current_payload = [label_hit[1]] if label_hit[1] else []
            stage = "supplementary"
            continue

        extracted_answer, answer_note = extract_answer(line)
        if extracted_answer:
            flush_supplementary()
            answer = extracted_answer
            if answer_note:
                review_notes.append(answer_note)
            prefix = line[: line.find("答案为")].strip("：: ，。；")
            if prefix and prefix not in {"综上", "本题"}:
                analysis.append(prefix)
            stage = "analysis"
            continue

        if OPTION_RE.match(line):
            flush_supplementary()
            option_text, trailing_analysis = split_option_and_analysis(line)
            options.append(option_text)
            if trailing_analysis:
                analysis.append(trailing_analysis)
            stage = "options"
            continue

        if current_label:
            current_payload.append(line)
            continue

        if stage == "stem":
            stem_lines.append(cleanup_question_stem(line))
            continue

        if stage == "options":
            if options and not any(marker in line for marker in ("A.", "B.", "C.", "D.")):
                if len(options) < 4 and not line.startswith("【") and not contains_exam_ref(line):
                    options[-1] = f"{options[-1]} {line}".strip()
                else:
                    analysis.append(line)
                    stage = "analysis"
            else:
                options[-1] = f"{options[-1]} {line}".strip()
            continue

        analysis.append(line)

    flush_supplementary()

    stem = " ".join(stem_lines).strip()
    stem = re.sub(r"\s+", " ", stem)
    if not answer:
        review_notes.append("未识别出明确答案，建议二轮抽查。")

    return Question(
        title_index=index,
        section_title=section_title,
        stem=stem,
        options=options,
        answer=answer,
        analysis=analysis,
        supplementary=supplementary,
        footnotes=footnotes,
        review_notes=review_notes,
    )


def parse_topic_block(topic: TopicBlock, block_lines: list[str]) -> None:
    body = block_lines[2:]
    current_section: str | None = None
    current_question: list[str] | None = None
    command_mode = False
    command_lines: list[str] = []

    def flush_question() -> None:
        nonlocal current_question
        if not current_question:
            current_question = None
            return
        parsed = parse_question(current_question, len(topic.questions) + 1, current_section)
        topic.questions.append(parsed)
        current_question = None

    def flush_command() -> None:
        nonlocal command_mode, command_lines
        if command_lines:
            topic.intro_blocks.append(("【命题规律】", command_lines[:]))
        command_mode = False
        command_lines = []

    for idx, raw in enumerate(body):
        line = raw.strip()
        if not line:
            continue

        topic_label = detect_topic_label(line)
        if topic_label == "【命题规律】":
            flush_question()
            flush_command()
            command_mode = True
            continue

        next_lines = body[idx + 1: idx + 8]
        if looks_like_question_start(line, next_lines):
            flush_command()
            flush_question()
            current_question = [line]
            continue

        if is_section_heading(line):
            flush_command()
            flush_question()
            current_section = line
            continue

        if command_mode:
            command_lines.append(line)
            continue

        if current_question is not None:
            if looks_like_question_start(line, next_lines):
                flush_question()
                current_question = [line]
                continue
            for part in split_inline_options(line):
                current_question.append(part)
            continue

        topic.preface_notes.append(line)

    flush_command()
    flush_question()


def render_question(question: Question) -> list[str]:
    out: list[str] = [f"#### 第{question.title_index:03d}题", ""]

    if question.section_title:
        out.append(f"【小节】{question.section_title}")
        out.append("")

    out.append(f"【题干】{question.stem}")
    out.append("")

    out.append("【选项】")
    out.extend(question.options or ["【待复核】未稳定识别选项，请人工抽查。"])
    out.append("")

    if question.answer:
        out.append(f"【答案】{question.answer}")
        out.append("")

    if question.analysis:
        out.append("【解析】")
        out.extend(question.analysis)
        out.append("")

    for label, lines in question.supplementary:
        out.append(label)
        out.extend(lines)
        out.append("")

    if question.footnotes:
        out.append("【脚注】")
        out.extend(question.footnotes)
        out.append("")

    if question.review_notes:
        out.append("【待复核】")
        out.extend(question.review_notes)
        out.append("")

    return out


def render_markdown(topics: list[TopicBlock], source_name: str) -> str:
    out: list[str] = [
        f"# {BOOK_TITLE}",
        "",
        f"> 整理说明：本文件由 `{source_name}` 第一遍整理而来，采用“专题 + 题目”结构，保留题干、选项、答案、解析，以及命题规律、设题陷阱、常见错误分析、脚注等附属内容；本轮不切块、不入库。",
        "",
    ]

    current_part = None
    for topic in topics:
        if topic.part != current_part:
            out.append(f"## {topic.part}")
            out.append("")
            current_part = topic.part

        out.append(f"### {topic.title}")
        out.append("")

        for label, lines in topic.intro_blocks:
            out.append(label)
            out.extend(lines)
            out.append("")

        if topic.preface_notes:
            out.append("【专题前导】")
            out.extend(topic.preface_notes)
            out.append("")

        for question in topic.questions:
            out.extend(render_question(question))

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def build_report(source_name: str, topics: list[TopicBlock], raw_count: int, body_count: int) -> str:
    question_count = sum(len(topic.questions) for topic in topics)
    review_count = sum(
        len(question.review_notes)
        for topic in topics
        for question in topic.questions
    )
    intro_count = sum(len(topic.intro_blocks) for topic in topics)

    return (
        "# 杨帆三国真金题整理说明\n\n"
        "## 本轮范围\n\n"
        f"- 输入文件：`OCR原稿/{source_name}`\n"
        "- 输出文件：`整理后文本/杨帆三国真金题_整理版.md`\n"
        "- 处理原则：只做第一遍结构化整理，稳定专题边界、题目边界和附属内容归属；本轮不切块、不做二次清洗。\n\n"
        "## 本轮规则\n\n"
        "- 从正文第一个 `PROJECT 01` 起进入题库主体，跳过目录、Contents 和前置导航信息。\n"
        "- 固定整理为 `## 板块 -> ### 专题 -> #### 题目` 结构。\n"
        "- 每道题统一整理为 `【题干】/【选项】/【答案】/【解析】` 主体，并保留 `【命题规律】`、`【设题陷阱】`、`【常见错误分析】`、`【脚注】` 等附属标签。\n"
        "- 对高置信 OCR 问题做轻量修正，如专题标题空格、明显错字、题号前噪音和答案句规范化。\n"
        "- 对无法高置信修复的内容保留原文并加 `【待复核】`。\n\n"
        "## 统计\n\n"
        f"- 原始非空段落数：`{raw_count}`\n"
        f"- 进入正文后的段落数：`{body_count}`\n"
        f"- 三大板块数：`{len(PARTS)}`\n"
        f"- 专题数：`{len(topics)}`\n"
        f"- 题目数：`{question_count}`\n"
        f"- 命题规律块数：`{intro_count}`\n"
        f"- `【待复核】` 条目数：`{review_count}`\n\n"
        "## 后续建议\n\n"
        "- 第二轮可直接基于本整理版做二次清洗，重点处理少量选项丢字、题目尾巴粘连和 `【待复核】` 条目。\n"
        "- 切块时建议保留 `板块 / 专题 / 题号 / 小节` 作为 metadata，上层标签已足够稳定。\n"
    )


def main() -> None:
    source = find_source_docx()
    raw_lines = iter_docx_paragraphs(source)
    lines = preprocess_lines(raw_lines)
    project_blocks = split_projects(lines)

    expected_projects = sum(count for _, count in PARTS)
    if len(project_blocks) != expected_projects:
        raise RuntimeError(f"识别到的 PROJECT 数为 {len(project_blocks)}，预期为 {expected_projects}")

    topics = annotate_project_parts(project_blocks)
    for topic, block in zip(topics, project_blocks):
        parse_topic_block(topic, block)

    markdown = render_markdown(topics, source.name)
    report = build_report(source.name, topics, len(raw_lines), len(lines))

    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")

    question_count = sum(len(topic.questions) for topic in topics)
    print(f"输出文件：{OUTPUT_PATH}")
    print(f"说明文件：{REPORT_PATH}")
    print(f"专题数：{len(topics)}")
    print(f"题目数：{question_count}")


if __name__ == "__main__":
    main()
