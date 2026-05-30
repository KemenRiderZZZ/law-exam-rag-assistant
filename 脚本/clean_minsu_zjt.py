#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""民诉真金题第一遍整理脚本。

目标：
1. 直接读取 docx 内部 XML，不引入额外依赖。
2. 输出“专题 + 小节 + 题目固定结构”的整理版 Markdown。
3. 保留背诵/拓展/命题思路等附属内容，并显式标注，方便下一轮切块选择性入库。
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
OUTPUT_PATH = PROJECT_ROOT / "整理后文本" / "民诉真金题_整理版.md"

DOCX_KEYWORDS = ("民诉", "真金题")
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

TOPIC_TITLES = [
    "民事诉讼与民事诉讼法",
    "诉的基本理论",
    "基本原则与基本制度",
    "主管与管辖",
    "当事人",
    "共同诉讼",
    "第三人",
    "诉讼代理人",
    "证明",
    "证据",
    "证明程序",
    "保全与先予执行",
    "对妨碍诉讼的强制措施",
    "期间与送达",
    "调解",
    "一审普通程序",
    "简易程序",
    "公益诉讼程序",
    "第三人撤销之诉",
    "二审程序",
    "审判监督程序",
    "特别程序",
    "非讼程序之一 督促程序",
    "非讼程序之二 公示催告程序",
    "执行程序",
    "涉外民事诉讼程序",
    "仲裁概述",
    "仲裁协议",
    "仲裁程序",
    "司法与仲裁",
    "不定项选择题专项训练",
]

SUPPLEMENTARY_MARKERS = {
    "背下来": "【背下来】",
    "命题思路与常见错误分析": "【命题思路】",
    "命题思路": "【命题思路】",
    "常见错误分析": "【命题思路】",
    "深度拓展": "【深度拓展】",
    "举一反三": "【举一反三】",
    "总结与归纳": "【总结】",
    "总结": "【总结】",
    "原理与逻辑": "【原理与逻辑】",
    "注意": "【注意】",
}

SECTION_ALIASES = {
    "诉讼标的": "诉讼标的",
    "诉的分类": "诉的分类",
    "反诉": "反诉",
    "诉的合并与分离": "诉的合并与分离",
}

NOISE_PATTERNS = [
    r"^PROJECT\s*\d+$",
    r"^资料分享公众号[:：].*$",
    r"^\d{1,4}$",
    r"^[／/|Iil]+$",
    r"^[\W_]{1,6}$",
    r"^（略）$",
]

EXAM_REF_COMPACT_RE = re.compile(r"[（(][^（）()]*?(单|多|不定项|案例)[^（）()]*?[）)]")
OPTION_SPLIT_RE = re.compile(r"(?<!^)\s+(?=[A-D][\.．、])")
OPTION_LINE_RE = re.compile(r"^[A-D][\.．、]\s*")
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+)、(.+)$")
QUESTION_START_NOISE_RE = re.compile(r"^[=;:!！\.,，、/Iil\-\s]*")
QUESTION_LEADING_NUM_RE = re.compile(r"^\d{1,3}(?=[^\d])")
ANSWER_RE = re.compile(r"(?:本题答案为|答案为|【答案】)\s*([A-D]{1,4})([A-Z]*)")
FOOTNOTE_LINE_RE = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩]")
QUESTION_HINT_RE = re.compile(
    r"(？|\?|下列|正确的是|正确的有|哪一选项|哪项|何者|如何处理|说法正确|表述正确)"
)
ANALYSIS_START_RE = re.compile(
    r"^(本题|首先|其次|最后|当然|综上所述|情形一|情形二|一般而言|本案中|我们分析|根据《|A、B选项|B、C选项|C、D选项|D选项|［分析|【分析|\[分析)"
)
ANALYSIS_CONTINUATION_RE = re.compile(
    r"^(首先|其次|最后|当然|综上所述|情形一|情形二|一般而言|本案中|我们分析|据此分析|逐一分析|A、B选项|A、D选项|B、C选项|B选项|C、D选项|C选项|D选项)"
)
SUPPLEMENTARY_PROMPT_RE = re.compile(
    r"^(请同学们判断|请判断|思考|再想一想|举一反三|延伸思考|补充判断)"
)
OPTION_COMMENTARY_RE = re.compile(
    r"^[A-D](?:[\.．、]\s*|[、和及与或]\s*[A-D]){0,3}.*(?:选项|说法).*(?:正确|错误|不当)"
)


@dataclass
class Topic:
    title: str
    intro_sections: dict[str, list[str]] = field(default_factory=dict)
    sections: list["Section"] = field(default_factory=list)


@dataclass
class Section:
    title: str
    questions: list["Question"] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Question:
    index: int
    stem: str
    options: list[str]
    analysis: str
    answer: str | None
    supplementary: list[tuple[str, str]]
    footnotes: list[str]
    review_notes: list[str]


def find_source_docx() -> Path:
    candidates = sorted(
        p for p in OCR_DIR.glob("*.docx")
        if all(keyword in p.name for keyword in DOCX_KEYWORDS)
    )
    if not candidates:
        raise FileNotFoundError("未找到民诉真金题 docx 原稿")
    return candidates[0]


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


def normalize_text(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2009": " ",
        "\u3000": " ",
        "\ufeff": "",
        "（、": "（",
        "（「": "（",
        "（、“": "（",
        "（，": "（",
        "））": "）",
        "，,": "，",
        ",，": "，",
        "——": "——",
        "—": "—",
        "。O": "。0",
        "BDO": "BDO",
        "共同诉娠": "共同诉讼",
        "涉外民事诉松程序": "涉外民事诉讼程序",
        "对妨碍诉讼的强制揩施": "对妨碍诉讼的强制措施",
        "专题+四期间与送达": "专题十四期间与送达",
        "专题二十二审程序": "专题二十 二审程序",
        "专题二十一审判监督程序": "专题二十一审判监督程序",
        "专题二十二特别程序": "专题二十二特别程序",
        "非讼程序之——公示催告程序": "非讼程序之二 公示催告程序",
        "非讼程序之一一督促程序": "非讼程序之一 督促程序",
        "民事诉松": "民事诉讼",
        "诉娠": "诉讼",
        "审理和栽判": "审理和裁判",
        "诉讼标的发生了变更；": "诉讼请求发生了变更；",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([，。；：？！）])", r"\1", text)
    text = re.sub(r"([（])\s*", r"\1", text)
    return text.strip()


def is_noise_line(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    return any(re.match(pattern, line) for pattern in NOISE_PATTERNS)


def split_inline_options(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []
    parts = OPTION_SPLIT_RE.split(line)
    out: list[str] = []
    for part in parts:
        part = part.strip()
        if part:
            out.append(part)
    return out or [line]


def preprocess_lines(raw_lines: Iterable[str]) -> list[str]:
    lines: list[str] = []
    for raw in raw_lines:
        text = normalize_text(raw)
        if is_noise_line(text):
            continue
        if text == "考点必背":
            lines.append("考点必背")
            continue
        for part in split_inline_options(text):
            if not is_noise_line(part):
                lines.append(part)
    return lines


def topic_line(title: str, index: int) -> str:
    return f"专题{index}{title}"


def looks_like_topic(line: str, topic_index: int) -> bool:
    compact = re.sub(r"\s+", "", line)
    if not compact.startswith("专题"):
        return False
    if topic_index >= len(TOPIC_TITLES):
        return False
    expected = re.sub(r"\s+", "", TOPIC_TITLES[topic_index])
    return expected in compact or compact.startswith(f"专题{topic_index + 1}")


def normalize_topic_title(line: str, topic_index: int) -> str:
    _ = line
    return TOPIC_TITLES[topic_index]


def is_section_heading(line: str) -> bool:
    return bool(SECTION_RE.match(line))


def normalize_section_title(line: str) -> str:
    match = SECTION_RE.match(line)
    if not match:
        return line
    title = match.group(2).strip()
    for raw, normalized in SECTION_ALIASES.items():
        if raw in title:
            title = normalized
            break
    return title


def contains_exam_ref(text: str) -> bool:
    return bool(EXAM_REF_COMPACT_RE.search(text))


def looks_like_question_start(line: str, next_lines: list[str]) -> bool:
    compact = line.strip()
    if not compact:
        return False
    if compact in SUPPLEMENTARY_MARKERS:
        return False
    if ANALYSIS_CONTINUATION_RE.search(compact):
        return False
    nearby = "\n".join(next_lines[:6])
    has_options = bool(re.search(r"^A[\.．、]", nearby, flags=re.M)) and bool(
        re.search(r"^B[\.．、]", nearby, flags=re.M)
    )
    if not has_options:
        return False
    if compact.startswith(("【", "［", "[", "（", "(")):
        return False
    if is_section_heading(compact) or compact.startswith("专题"):
        return False
    if contains_exam_ref(compact):
        return True
    return bool(QUESTION_HINT_RE.search(compact))


def cleanup_question_stem(line: str) -> str:
    line = QUESTION_START_NOISE_RE.sub("", line.strip())
    if contains_exam_ref(line) or QUESTION_HINT_RE.search(line):
        line = re.sub(r"^\d{1,3}[\.．、]?\s*", "", line, count=1).strip()
    return line


def normalize_exam_ref_in_stem(text: str) -> str:
    match = EXAM_REF_COMPACT_RE.search(text)
    if not match:
        return text

    raw = match.group(0)
    compact = raw.strip("（）()")
    compact = compact.replace(" ", "")
    compact = compact.replace("，", ",")
    compact = compact.replace("金；", "金题")
    compact = compact.replace("金篇", "金题")
    compact = compact.replace("金題", "金题")
    compact = compact.replace("二", "2") if compact.startswith("2021二") else compact

    normalized = raw
    m_gold = re.search(r"(20\d{2})金题-?(\d)-?(\d)-?(\d+),?(单|多|不定项|案例)", compact)
    m_real = re.search(r"(20\d{2})-?(\d)-?(\d+),?(单|多|不定项|案例)", compact)
    if m_gold:
        normalized = f"（{m_gold.group(1)}金题-{m_gold.group(2)}-{m_gold.group(3)}-{m_gold.group(4)}，{m_gold.group(5)}）"
    elif m_real:
        normalized = f"（{m_real.group(1)}-{m_real.group(2)}-{m_real.group(3)}，{m_real.group(4)}）"
    else:
        cleaned = compact.replace("(", "").replace(")", "")
        cleaned = cleaned.replace("（", "").replace("）", "")
        cleaned = cleaned.replace(",", "，")
        normalized = f"（{cleaned}）"

    return text.replace(raw, normalized)


def detect_supplementary_marker(line: str) -> str | None:
    compact = line.strip().strip("【】[]［］:：!！;； ")
    for key, label in SUPPLEMENTARY_MARKERS.items():
        if key in compact:
            return label
    return None


def normalize_answer(answer: str, trailing_noise: str) -> tuple[str, str | None]:
    if not trailing_noise:
        return answer, None
    note = f"答案原文含噪音：{answer}{trailing_noise}"
    return answer, note


def is_prompt_like_supplement(line: str) -> bool:
    compact = line.strip()
    if not compact:
        return False
    return bool(SUPPLEMENTARY_PROMPT_RE.search(compact))


def is_real_question(parsed: Question) -> bool:
    option_count = len([option for option in parsed.options if option.strip()])
    has_answer = bool(parsed.answer)
    has_exam_ref = contains_exam_ref(parsed.stem)
    has_analysis = bool(parsed.analysis.strip())
    looks_prompt = bool(QUESTION_HINT_RE.search(parsed.stem))
    looks_like_supplement = is_prompt_like_supplement(parsed.stem)

    if has_answer or has_exam_ref:
        return True
    if looks_like_supplement:
        return False
    if option_count >= 4 and (has_analysis or looks_prompt):
        return True
    if option_count >= 2 and has_analysis and looks_prompt:
        return True
    return False


def parse_question(lines: list[str], index: int) -> Question:
    stem_lines: list[str] = []
    options: list[str] = []
    analysis_lines: list[str] = []
    supplementary: list[tuple[str, list[str]]] = []
    footnotes: list[str] = []
    review_notes: list[str] = []
    answer: str | None = None

    current_mode = "stem"
    current_supp: tuple[str, list[str]] | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        marker = detect_supplementary_marker(line)
        if marker:
            if current_supp is not None:
                supplementary.append(current_supp)
            current_supp = (marker, [])
            current_mode = "supplementary"
            remainder = re.sub(r"^[^：:]*[:：]?", "", line).strip()
            if remainder:
                current_supp[1].append(remainder)
            continue

        answer_match = ANSWER_RE.search(line)
        if answer_match:
            answer, answer_note = normalize_answer(answer_match.group(1), answer_match.group(2))
            if answer_note:
                review_notes.append(answer_note)
            prefix = line[:answer_match.start()].strip("：: ，。")
            suffix = line[answer_match.end():].strip("：: ，。")
            if prefix and "答案" not in prefix:
                analysis_lines.append(prefix)
            if suffix:
                analysis_lines.append(suffix)
            current_mode = "analysis"
            continue

        if FOOTNOTE_LINE_RE.match(line):
            footnotes.append(line)
            continue

        if OPTION_LINE_RE.match(line):
            if len(options) >= 2 and OPTION_COMMENTARY_RE.search(line):
                current_mode = "analysis"
                analysis_lines.append(line)
                continue
            marker_match = re.search(r"(［分析|【分析|\[分析|本题考查|综上所述)", line)
            if marker_match:
                option_part = line[:marker_match.start()].strip()
                analysis_part = line[marker_match.start():].strip()
                if option_part:
                    options.append(option_part.replace("．", ".").replace("、", "."))
                if analysis_part:
                    current_mode = "analysis"
                    analysis_lines.append(analysis_part)
                continue
            current_mode = "options"
            options.append(line.replace("．", ".").replace("、", "."))
            continue

        if current_mode == "options":
            if line.startswith(("［分析", "【分析", "[分析")) or "本题考查" in line or "综上所述" in line:
                current_mode = "analysis"
                analysis_lines.append(line)
            elif len(options) >= 2 and ANALYSIS_START_RE.search(line):
                current_mode = "analysis"
                analysis_lines.append(line)
            elif current_supp is not None:
                current_supp[1].append(line)
            elif options:
                options[-1] = f"{options[-1]} {line}".strip()
            else:
                stem_lines.append(line)
            continue

        if current_mode == "supplementary" and current_supp is not None:
            current_supp[1].append(line)
            continue

        if current_mode == "analysis":
            analysis_lines.append(line)
            continue

        cleaned = cleanup_question_stem(line) if not stem_lines else line
        cleaned = normalize_exam_ref_in_stem(cleaned)
        stem_lines.append(cleaned)

    if current_supp is not None:
        supplementary.append(current_supp)

    stem = " ".join(stem_lines).strip()
    stem = re.sub(r"\s+", " ", stem)
    stem = normalize_exam_ref_in_stem(stem)

    analysis = "\n".join(clean_analysis_lines(analysis_lines))
    supplementary_blocks = [(label, "\n".join(clean_analysis_lines(content))) for label, content in supplementary if content]

    if not answer:
        review_notes.append("未识别出明确答案，建议二轮人工抽查。")

    return Question(
        index=index,
        stem=stem,
        options=options,
        analysis=analysis,
        answer=answer,
        supplementary=supplementary_blocks,
        footnotes=footnotes,
        review_notes=review_notes,
    )


def clean_analysis_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[［\[]?分析(?:与思路)?[】\]］]?\s*", "", line)
        line = line.replace("〔命题思路与常见错误分析］", "")
        line = line.replace("［命题思路与常见错误分析］", "")
        line = line.strip()
        if line:
            cleaned.append(line)
    return cleaned


def parse_topics(lines: list[str]) -> list[Topic]:
    topics: list[Topic] = []
    topic_index = -1
    current_topic: Topic | None = None
    current_section_title = "专题前导"
    current_question_lines: list[str] | None = None
    current_question_has_supplementary = False
    question_index = 0

    def ensure_section(topic: Topic, title: str) -> Section:
        for section in topic.sections:
            if section.title == title:
                return section
        section = Section(title=title)
        topic.sections.append(section)
        return section

    def flush_question() -> None:
        nonlocal current_question_lines, current_question_has_supplementary, question_index
        if current_topic is None or not current_question_lines:
            current_question_lines = None
            current_question_has_supplementary = False
            return
        parsed = parse_question(current_question_lines, 0)
        looks_real = is_real_question(parsed)
        if looks_real:
            question_index += 1
            parsed.index = question_index
            section = ensure_section(current_topic, current_section_title)
            section.questions.append(parsed)
        else:
            bucket = current_topic.intro_sections.setdefault(current_section_title, [])
            if parsed.stem:
                bucket.append(parsed.stem)
            for _, content in parsed.supplementary:
                if content:
                    bucket.extend(content.splitlines())
            bucket.extend(parsed.footnotes)
        current_question_lines = None
        current_question_has_supplementary = False

    for idx, line in enumerate(lines):
        next_lines = lines[idx + 1: idx + 8]
        if looks_like_topic(line, topic_index + 1):
            flush_question()
            topic_index += 1
            current_topic = Topic(title=normalize_topic_title(line, topic_index))
            topics.append(current_topic)
            current_section_title = "专题前导"
            continue

        if current_topic is None:
            continue

        if is_section_heading(line):
            flush_question()
            current_section_title = normalize_section_title(line)
            continue

        if line == "考点必背":
            flush_question()
            current_section_title = "考点必背"
            continue

        if looks_like_question_start(line, next_lines):
            if (
                current_question_lines is not None
                and current_question_has_supplementary
                and is_prompt_like_supplement(line)
                and not contains_exam_ref(line)
            ):
                current_question_lines.append(line)
                continue
            flush_question()
            current_question_lines = [line]
            current_question_has_supplementary = False
            continue

        if current_question_lines is not None:
            current_question_lines.append(line)
            if detect_supplementary_marker(line):
                current_question_has_supplementary = True
        else:
            current_topic.intro_sections.setdefault(current_section_title, []).append(line)

    flush_question()
    return topics


def render_topics(topics: list[Topic], source_name: str) -> str:
    out: list[str] = [
        "# 民诉真金题（第一遍整理版）",
        "",
        f"> 整理说明：本文件由 `{source_name}` 清洗整理而来，保留专题结构、题干/选项/解析/答案，以及背诵提示、命题思路、深度拓展、举一反三、脚注等附属内容；本轮不切块、不入库。",
        "",
    ]

    for topic_idx, topic in enumerate(topics, start=1):
        out.append(f"### 专题{topic_idx} {topic.title}")
        out.append("")

        for title, notes in topic.intro_sections.items():
            cleaned_notes = [line for line in notes if line]
            if not cleaned_notes:
                continue
            heading = title if title != "专题前导" else "专题前导"
            out.append(f"#### {heading}")
            out.append("")
            for line in cleaned_notes:
                out.append(line)
            out.append("")

        for section in topic.sections:
            out.append(f"#### {section.title}")
            out.append("")
            for note in section.notes:
                out.append(note)
            for question in section.questions:
                out.extend(render_question(question))
            out.append("")

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def render_question(question: Question) -> list[str]:
    out = [f"##### 第{question.index:03d}题", ""]

    out.append(f"【题干】{question.stem}")
    out.append("")

    out.append("【选项】")
    for option in question.options:
        out.append(option)
    out.append("")

    if question.analysis:
        out.append("【解析】")
        out.extend(question.analysis.splitlines())
        out.append("")

    if question.answer:
        out.append(f"【答案】{question.answer}")
        out.append("")

    for label, content in question.supplementary:
        out.append(label)
        out.extend(content.splitlines())
        out.append("")

    if question.footnotes:
        out.append("【脚注】")
        out.extend(question.footnotes)
        out.append("")

    if question.review_notes:
        out.append("【待核】")
        for note in question.review_notes:
            out.append(note)
        out.append("")

    return out


def main() -> None:
    source = find_source_docx()
    raw_lines = iter_docx_paragraphs(source)
    lines = preprocess_lines(raw_lines)
    topics = parse_topics(lines)
    markdown = render_topics(topics, source.name)
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    print(f"输出文件：{OUTPUT_PATH}")
    print(f"专题数：{len(topics)}")
    print(f"题目数：{sum(len(section.questions) for topic in topics for section in topic.sections)}")


if __name__ == "__main__":
    main()
