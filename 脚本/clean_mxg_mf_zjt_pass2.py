#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""孟献贵民法真金题二次清洗脚本。

本轮目标：
1. 仅以 OCR 原稿为输入；
2. 直接产出可用于后续切块准备的二次清洗版；
3. 保留连续题库风格，不做民诉式重结构拆题；
4. 输出清洗说明与统计，不做切块、不做嵌入。
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "OCR原稿" / "孟献贵真金题2026.md"
DST = PROJECT_ROOT / "整理后文本" / "孟献贵民法真金题_二次清洗版.md"
RULES_DOC = PROJECT_ROOT / "整理后文本" / "孟献贵民法真金题_二次清洗说明.md"

TITLE = "# 孟献贵民法真金题（二次清洗版）"

PART_HEADINGS = {
    "总则编",
    "物权编",
    "合同编",
    "人格权编",
    "婚姻家庭编",
    "继承编",
    "侵权责任编",
}

LIGHT_LABELS = [
    "解题思路",
    "有体系",
    "核心法条链接",
    "命题思路",
    "深度拓展",
    "举一反三",
    "背下来",
    "常见错误分析",
    "懂原理",
    "萌主点拨",
]

LABEL_VARIANTS = {
    "解题思路": [
        r"［解题思路[’'`]?\］",
        r"【解题思路】",
        r"I解题思解I",
        r"I解题思路I",
        r"解题思路本题",
        r"【解题思解】",
        r"［解题思解］",
    ],
    "有体系": [
        r"［有体系］",
        r"【有体系】",
        r"'［有体系］",
        r"【有体糸】",
    ],
    "核心法条链接": [
        r"［核心法条链接］",
        r"【核心法条链接】",
        r"［核心法条链按］",
    ],
    "命题思路": [r"［命题思路］", r"【命题思路】", r"命题思路"],
    "深度拓展": [r"［深度拓展］", r"【深度拓展】", r"深度拓展"],
    "举一反三": [r"［举一反三］", r"【举一反三】", r"举一反三"],
    "背下来": [r"［背下来］", r"【背下来】", r"背下来"],
    "常见错误分析": [r"［常见错误分析］", r"【常见错误分析】"],
    "懂原理": [r"［懂原理］", r"【懂原理】"],
    "萌主点拨": [r"【萌主点拨】", r"萌主点拨"],
}

QUESTION_PATTERNS = [
    re.compile(r"^[：；,，.'\"`“”‘’]*\s*(?:\d+\.\s*)?\*{0,3}[A-Za-z]?\s*(\d{1,5})\.\*{0,3}\s*(.*)$"),
    re.compile(r"^[：；,，.'\"`“”‘’]*\s*(\d{1,5})\.\s*\*{3}\.\*{3}\s*(.*)$"),
    re.compile(r"^[：；,，.'\"`“”‘’]*\s*(\d{1,5})\.\s+\.\s*(.*)$"),
    re.compile(r"^[：；,，.'\"`“”‘’]*\s*(?:\d+\.\s*)?(\d{1,5})\.\s*(.*)$"),
]

OPTION_RE = re.compile(r"^[A-D][.．、]\s*(.*)$")
SECTION_RE = re.compile(r"^第([一二三四五六七八九十百零\d]+)节\s*(.+)$")
SUBPART_RE = re.compile(r"^第([一二三四五六七八九十百零\d]+)分编\s*(.+)$")
TOPIC_RE = re.compile(r"^专题")
ANSWER_RE = re.compile(r"^综上所述[，,]?\s*本题的?正确答案为\s*([A-D]{1,4})(?:[~〜oO0^\\\s]*)[。．.]?\s*$")
POINT_RE = re.compile(r"^考点\s*\*+\s*(\d+)\s*[:：]\s*(.+)$")
TRAILING_YEAR_RE = re.compile(r"[（(](?:19|20)\d{2}.*?[)）]")
HEADING_RE = re.compile(r"^(##|###|####)\s+")
REVIEW_TRIGGER_RE = re.compile(r"[~^]|[A-Za-z]{2,}\d|[■]|[\\/]{2,}")

DROP_NOISE_LINES = {
    r"4\~-.、",
    r"民法专题讲座■真金题卷）",
    r"\^0\^石痴\\\*关系人 院受理库/1葡死亡家破人亡",
    r"\^1\^-已成立一►",
    r"\^!\^，罂f自行承担后果",
}

EXACT_LINE_REPAIRS = {
    "■那些说法是错误的？（2018金题-2-1-3,多）": "哪些说法是错误的？（2018金题-2-1-3,多）",
    "■那些说法是错误的？（2018金胞-2-1-8,多）": "哪些说法是错误的？（2018金题-2-1-8,多）",
    "申请主体有关个人 ^1^组织（民政部门）": "申请主体：有关个人、组织（民政部门）",
    "^1^决议行为": "决议行为",
    "虚假的意思■示，又称虚伪表示或伪装表示。": "虚假的意思表示，又称虚伪表示或伪装表示。",
    "-主：无民事行为能力人独立实施 一意:双方通谋虚假意思■": "主：无民事行为能力人独立实施；意：双方通谋虚假意思表示",
    "^1^-恶意代理（代表）": "恶意代理（代表）",
}


@dataclass
class Stats:
    before_lines: int = 0
    after_lines: int = 0
    front_blocks_removed: int = 0
    appendix_blocks_removed: int = 0
    bookmark_removed: int = 0
    underline_removed: int = 0
    junk_lines_removed: int = 0
    qnum_normalized: int = 0
    qnum_repaired: int = 0
    topic_title_supplemented: int = 0
    answer_noise_fixed: int = 0
    review_count: int = 0
    topics_kept: int = 0
    questions_kept: int = 0
    topic_projects: list[int] = field(default_factory=list)
    label_counts: Counter = field(default_factory=Counter)
    noise_summary: Counter = field(default_factory=Counter)


def int_to_cn(num: int) -> str:
    digits = "零一二三四五六七八九"
    if num < 10:
        return digits[num]
    if num < 20:
        return "十" + (digits[num % 10] if num % 10 else "")
    if num < 100:
        tens = digits[num // 10] + "十"
        tail = digits[num % 10] if num % 10 else ""
        return tens + tail
    raise ValueError(f"暂不支持超过两位的数字：{num}")


def squeeze_blank_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    blank = False
    for line in lines:
        if line == "":
            if not blank:
                out.append("")
            blank = True
        else:
            out.append(line)
            blank = False
    while out and out[-1] == "":
        out.pop()
    return out


def count_non_empty_blocks(lines: list[str]) -> int:
    blocks = 0
    inside = False
    for line in lines:
        if line.strip():
            if not inside:
                blocks += 1
                inside = True
        else:
            inside = False
    return blocks


def parse_topic_catalog(lines: list[str]) -> dict[int, str]:
    topics: dict[int, str] = {}
    count = 0
    for raw in lines:
        line = raw.strip()
        if "附录本书答案速查" in line:
            break
        if "专题" not in line or "/" not in line:
            continue
        matched = re.search(r"专题(.+?)\s*/\d+", line)
        if not matched:
            continue
        body = matched.group(1)
        body = re.sub(r"^[\[\]#a-zA-Z0-9 ._-]+", "", body).strip()
        body = re.sub(r"^[一二三四五六七八九十百零\dHh■+\- ]+", "", body).strip()
        body = body.replace("民法（债）", "民法债")
        if not body:
            continue
        count += 1
        topics[count] = body
    return topics


def normalize_line_artifacts(line: str, stats: Stats) -> str:
    bookmark_hits = len(re.findall(r"\[\]\{#bookmark\d+\s*\.anchor\}", line))
    underline_hits = len(re.findall(r"\[([^\[\]]*?)\]\{\.underline\}", line))
    if bookmark_hits:
        stats.bookmark_removed += bookmark_hits
        stats.noise_summary["bookmark"] += bookmark_hits
    if underline_hits:
        stats.underline_removed += underline_hits
        stats.noise_summary["underline"] += underline_hits

    line = re.sub(r"\[\]\{#bookmark\d+\s*\.anchor\}", "", line)
    line = re.sub(r"\[([^\[\]]*?)\]\{\.underline\}", r"\1", line)
    line = re.sub(r"\{\.[a-zA-Z][\w-]*\}", "", line)
    line = line.replace("\\\"", "\"").replace("\\'", "'")
    line = line.replace("\u3000", " ")
    line = line.replace("------", " ")
    line = line.replace("——", "—")
    return line.rstrip()


def canonicalize_label_text(line: str) -> str:
    result = line
    result = re.sub(r"^[\[［【]?\s*(?:解题思路|霞思路|思路)[】］\]〕1IJ'`\"]*\s*", "【解题思路】", result)
    result = re.sub(r"^[\[［【]?\s*有体系[】］\]〕'`\"]*\s*", "【有体系】", result)
    result = re.sub(r"^[\[［【]?\s*核心法条链接[】］\]〕'`\"]*\s*", "【核心法条链接】", result)
    result = re.sub(r"^[\[［【]?\s*常见错误分析[】］\]〕'`\"]*\s*", "【常见错误分析】", result)
    result = re.sub(r"^[\[［【]?\s*懂原理[】］\]〕'`\"]*\s*", "【懂原理】", result)
    result = re.sub(r"^[\[［【]?\s*萌主点拨[】］\]〕'`\"]*\s*", "【萌主点拨】", result)
    for label, patterns in LABEL_VARIANTS.items():
        for pat in patterns:
            result = re.sub(pat, f"【{label}】", result)
    result = result.replace("【【", "【").replace("】】", "】").replace("】］", "】").replace("［【", "【")
    result = re.sub(r"^[，,;；:：\"'`]+(?=【)", "", result).strip()
    return result


def split_inline_labels(line: str) -> list[str]:
    if not line:
        return [""]
    text = canonicalize_label_text(line)
    text = re.sub(
        r"\s*(【(?:%s)】)" % "|".join(re.escape(label) for label in LIGHT_LABELS + ["待复核"]),
        r"\n\1",
        text,
    ).strip()
    return [chunk.strip() for chunk in text.split("\n") if chunk.strip()]


def clean_text_line(line: str) -> str:
    text = line.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[|:：;；]+", "", text)
    text = re.sub(r"[|]+$", "", text)
    text = text.replace(" ,", "，")
    text = text.replace(" .", "。")
    text = text.replace(" )", "）").replace("( ", "（")
    text = re.sub(r"\s+([，。！？；：）】》])", r"\1", text)
    text = re.sub(r"([（【《])\s+", r"\1", text)
    text = text.replace("“ ", "“").replace(" ”", "”")
    return text.strip()


def apply_exact_repairs(line: str) -> str | None:
    text = line.strip()
    if text in DROP_NOISE_LINES:
        return None
    if text in EXACT_LINE_REPAIRS:
        return EXACT_LINE_REPAIRS[text]
    if text.startswith("为。事实行为充分体现了造律期邕奥"):
        return (
            "行为。事实行为充分体现了法律效果不是当事人主动追求的（意欲发生的），"
            "而是法律直接规定的。典型的事实行为包括侵权行为和创作行为。"
            "侵权行为系事实行为，与侵权人的民事行为能力无关。因此，16周岁的王某将行人张某撞伤，"
            "依然要承担侵权责任，因王某为限制民事行为能力人，依法应由其监护人王某父母向被侵权人"
            "（受害人）张某承担侵权责任（监护人责任/替代责任）。故B项说法正确，当选。"
        )
    if text.startswith("-1方获益；（3） -■方受 损；（4）获益和受损之间存在因果关系。"):
        return (
            "一方获益；（3）一方受损；（4）获益和受损之间存在因果关系。"
            "本题中，乘客李某支付车费将80元错输成8080元，使司机在没有法律上原因的情况下获益8000元，"
            "构成不当得利。李某依法有权请求返还。故D项说法正确，当选。"
        )
    if text.startswith("#<\"~o~出题者就是想问你，该情形是否构成不当 得利。"):
        return "出题者就是想问你，该情形是否构成不当得利。"
    if text.startswith("对共有部分享有的共有和共同管理的权利二■并转 IL"):
        return (
            "对共有部分享有的共有和共同管理的权利一并转移（《民法典》第273条第2款）。"
            "因此，在牛某将房屋出卖给王某后，王某亦无义务支付电梯安装费用且可以免费使用。"
            "故A项说法错误，不当选；C、D项说法正确，当选。"
        )
    return line


def is_junk_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    junk_patterns = [
        r"^PROJECT\s*\d+$",
        r"^Contents$",
        r"^Preface$",
        r"^\(竹马APP下载\).*$",
        r"^[Bb][o0]$",
        r"^[△□▲口■]+$",
        r"^[LIJ]$",
        r"^[~^]+$",
        r"^\d{4}年\d{1,2}月$",
    ]
    if any(re.match(pat, s) for pat in junk_patterns):
        return True
    if s in {"：", ":", "；", ";", "|", ".", "．", "】", "【", "’：", "，", ","}:
        return True
    return False


def match_question_start(lines: list[str], idx: int) -> tuple[int, str] | None:
    current = lines[idx].strip()
    if not current or OPTION_RE.match(current) or current.startswith("【"):
        return None

    lookahead_parts = []
    option_hits = 0
    seen = 0
    blank_runs = 0
    for j in range(idx, min(idx + 28, len(lines))):
        nxt = lines[j].strip()
        if not nxt:
            blank_runs += 1
            if blank_runs >= 3 and lookahead_parts:
                break
            continue
        blank_runs = 0
        lookahead_parts.append(nxt)
        if OPTION_RE.match(nxt):
            option_hits += 1
        seen += 1
        if seen >= 20:
            break
    lookahead = " ".join(lookahead_parts)
    if not TRAILING_YEAR_RE.search(lookahead) and option_hits < 2:
        return None

    for pattern in QUESTION_PATTERNS:
        match = pattern.match(current)
        if match:
            num = int(match.group(1))
            body = clean_text_line(match.group(2))
            body = re.sub(r"^(?:\*{3}\.\*{3}\s*)+", "", body)
            body = re.sub(r"^[。．，,;；:：]+\s*", "", body)
            if body.startswith(tuple("ABCD")) and len(body) <= 3:
                return None
            return num, body
    return None


def normalize_question_number(raw_num: int, prev_num: int, stats: Stats) -> int:
    expected = 1 if prev_num == 0 else prev_num + 1
    normalized = raw_num
    if prev_num == 0:
        normalized = 1 if raw_num != 1 else raw_num
    elif raw_num != expected:
        if raw_num < prev_num or raw_num - expected > 1 or str(raw_num).endswith(str(expected)):
            normalized = expected
    if normalized != raw_num:
        stats.qnum_repaired += 1
        stats.noise_summary["qnum_repair"] += 1
    stats.qnum_normalized += 1
    return normalized


def normalize_topic_heading(line: str, project_num: int | None, topic_catalog: dict[int, str], stats: Stats) -> str | None:
    text = clean_text_line(line)
    if not TOPIC_RE.match(text):
        return None
    title = topic_catalog.get(project_num or 0)
    if title:
        stats.topic_title_supplemented += 1
        return f"### 专题{int_to_cn(project_num)} {title}"

    matched = re.match(r"^专题([一二三四五六七八九十百零\d]+)\s*(.*)$", text)
    if matched:
        return f"### 专题{matched.group(1)} {matched.group(2).strip()}".strip()
    return f"### {text}"


def normalize_answer_line(line: str, stats: Stats) -> tuple[str, str | None] | None:
    matched = ANSWER_RE.match(line.strip())
    if not matched:
        return None
    raw_answer = matched.group(1)
    cleaned = re.sub(r"[^A-D]", "", raw_answer)
    if raw_answer != cleaned or re.search(r"[~^oO0\\]", line):
        stats.answer_noise_fixed += 1
        stats.noise_summary["answer_noise"] += 1
    return f"综上所述，本题的正确答案为{cleaned}。", None


def normalize_point_line(line: str) -> str | None:
    matched = POINT_RE.match(line.strip())
    if not matched:
        return None
    title = clean_text_line(matched.group(2))
    title = title.lstrip("*").rstrip("*")
    return f"【考点】{matched.group(1)}：{title}"


def normalize_section_line(line: str) -> str | None:
    matched = SECTION_RE.match(line.strip())
    if matched:
        return f"#### 第{matched.group(1)}节 {clean_text_line(matched.group(2))}"
    matched = SUBPART_RE.match(line.strip())
    if matched:
        return f"#### 第{matched.group(1)}分编 {clean_text_line(matched.group(2))}"
    return None


def kind_of(line: str) -> str:
    if not line:
        return "blank"
    if line.startswith("## "):
        return "part"
    if line.startswith("### "):
        return "topic"
    if line.startswith("#### "):
        return "subheading"
    if re.match(r"^\*\*\d+\.\*\*", line):
        return "question"
    if OPTION_RE.match(line):
        return "option"
    if line.startswith("【"):
        return "label"
    if line.startswith("综上所述，本题的正确答案为"):
        return "answer"
    return "text"


def ends_sentence(line: str) -> bool:
    return line.endswith(("。", "！", "？", "；", "：", "）"))


def should_append_without_space(prev: str, current: str) -> bool:
    if prev.endswith(("“", "（", "【")):
        return True
    if current.startswith(("，", "。", "！", "？", "；", "：", "）", "】")):
        return True
    return True


def emit_line(out_lines: list[str], line: str, stats: Stats) -> None:
    if not line:
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        return

    line = clean_text_line(line)
    if not line:
        return

    if line.startswith("【"):
        label = re.match(r"^【([^】]+)】", line)
        if label:
            stats.label_counts[label.group(1)] += 1
            if label.group(1) == "待复核":
                stats.review_count += 1

    kind = kind_of(line)
    if kind in {"part", "topic", "subheading", "question", "label", "answer"}:
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        out_lines.append(line)
        return

    if kind == "option":
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        out_lines.append(line)
        return

    if not out_lines:
        out_lines.append(line)
        return

    prev = out_lines[-1]
    prev_kind = kind_of(prev)
    if prev == "":
        out_lines.append(line)
        return
    if prev_kind in {"question", "option", "label", "text"} and not ends_sentence(prev):
        out_lines[-1] = prev + ("" if should_append_without_space(prev, line) else " ") + line
        return
    out_lines.append(line)


def build_rules_doc(stats: Stats, review_examples: list[str]) -> str:
    label_lines = [
        f"- `【{label}】`：`{count}`"
        for label, count in sorted(stats.label_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    noise_lines = [
        f"- `{name}`：`{count}`"
        for name, count in sorted(stats.noise_summary.items(), key=lambda item: (-item[1], item[0]))
    ]
    review_lines = [f"- {item}" for item in review_examples] if review_examples else ["- 本轮未保留显式 `【待复核】` 片段。"]

    lines = [
        "# 孟献贵民法真金题二次清洗说明",
        "",
        "## 本轮范围",
        "",
        "- 输入文件：`OCR原稿/孟献贵真金题2026.md`",
        "- 输出文件：`整理后文本/孟献贵民法真金题_二次清洗版.md`",
        "- 脚本文件：`脚本/clean_mxg_mf_zjt_pass2.py`",
        "- 处理原则：延续柏浪涛真金题的连续题库风格，优先做结构修复、题号规范、轻标签统一和噪音压降。",
        "",
        "## 结构与内容处理",
        "",
        "- 正文起点固定从 `PROJECT 01` 后开始，封面、目录、课程说明和书签锚点全部排除。",
        "- 书末 `答案速查` 附录若存在则整段排除，不进入主整理稿。",
        "- 专题标题优先按目录顺序与 `PROJECT` 编号回填，修复 `专题七`、`专题三+运输合同`、`专题三H■-技术合同` 这类裂开标题。",
        "- 题号统一转为 `**N.**` 格式，并按全书连续顺序自动修复明显 OCR 错号。",
        "- `［解题思路］`、`［有体系］`、`［核心法条链接］` 等补充块统一转成轻标签，保留在对应题目语境内。",
        "- `综上所述，本题的正确答案为...` 继续保留为正文答案句，不额外拆出独立答案字段。",
        "",
        "## 统计结果",
        "",
        f"- 处理前总行数：`{stats.before_lines}`",
        f"- 处理后总行数：`{stats.after_lines}`",
        f"- 排除的前置非正文块数：`{stats.front_blocks_removed}`",
        f"- 排除的附录块数：`{stats.appendix_blocks_removed}`",
        f"- 识别并保留的专题数：`{stats.topics_kept}`",
        f"- 识别的题目数：`{stats.questions_kept}`",
        f"- 统一格式的题号数量：`{stats.qnum_normalized}`",
        f"- 自动修复的错号数量：`{stats.qnum_repaired}`",
        f"- 补齐或重建的专题标题数量：`{stats.topic_title_supplemented}`",
        f"- `【待复核】` 片段数：`{stats.review_count}`",
        "",
        "### 轻标签统计",
        "",
        *label_lines,
        "",
        "### 典型噪音处理摘要",
        "",
        *noise_lines,
        "",
        "## 待复核样例",
        "",
        *review_lines,
    ]
    return "\n".join(lines) + "\n"


def validate_output(text: str, stats: Stats) -> None:
    if "[]{#bookmark" in text or "{.underline}" in text:
        raise ValueError("输出仍残留 pandoc 书签或 underline 标记。")
    if "附录本书答案速查" in text:
        raise ValueError("输出仍包含答案速查附录。")
    if stats.topics_kept < 49:
        missing = [idx for idx in range(1, 50) if idx not in stats.topic_projects]
        raise ValueError(f"专题数异常：当前仅识别到 {stats.topics_kept} 个专题，缺少项目 {missing}。")
    if stats.questions_kept < 340:
        raise ValueError(f"题目数异常：当前仅识别到 {stats.questions_kept} 道题。")


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    stats = Stats(before_lines=raw.count("\n") + 1)

    all_lines = raw.split("\n")
    start_idx = next(
        (idx for idx, line in enumerate(all_lines) if re.match(r"^\s*PROJECT\s*01\s*$", line.strip())),
        None,
    )
    if start_idx is None:
        raise ValueError("未找到 PROJECT 01，无法定位正文起点。")

    appendix_idx = next(
        (idx for idx in range(start_idx + 1, len(all_lines)) if "附录本书答案速查" in all_lines[idx]),
        None,
    )

    stats.front_blocks_removed = count_non_empty_blocks(all_lines[:start_idx])
    if appendix_idx is not None:
        stats.appendix_blocks_removed = count_non_empty_blocks(all_lines[appendix_idx:])
        body_lines = all_lines[start_idx:appendix_idx]
    else:
        body_lines = all_lines[start_idx:]

    topic_catalog = parse_topic_catalog(all_lines[:start_idx])
    if len(topic_catalog) < 49:
        raise ValueError(f"目录专题提取不足，当前仅识别 {len(topic_catalog)} 个专题。")

    out_lines: list[str] = [
        TITLE,
        "",
        "> 整理说明：本文件直接基于 OCR 原稿进行二次清洗，保留连续题库风格，统一专题层级、题号样式与补充块轻标签，供后续切块和向量入库准备使用。",
        "",
    ]

    current_project: int | None = None
    pending_topic_from_project = False
    prev_qnum = 0
    review_examples: list[str] = []

    cleaned_lines: list[str] = []
    for raw_line in body_lines:
        line = normalize_line_artifacts(raw_line, stats)
        for piece in split_inline_labels(line):
            cleaned_lines.append(piece)

    idx = 0
    while idx < len(cleaned_lines):
        raw_line = cleaned_lines[idx]
        line = clean_text_line(raw_line)
        idx += 1

        if not line:
            emit_line(out_lines, "", stats)
            continue

        repaired = apply_exact_repairs(line)
        if repaired is None:
            stats.noise_summary["dropped_review_noise"] += 1
            continue
        line = clean_text_line(repaired)
        if not line:
            continue

        project_match = re.match(r"^PROJECT\s*(\d+)$", line)
        if project_match:
            current_project = int(project_match.group(1))
            pending_topic_from_project = True
            continue

        if is_junk_line(line):
            stats.junk_lines_removed += 1
            stats.noise_summary["junk_line"] += 1
            continue

        if line in PART_HEADINGS:
            emit_line(out_lines, f"## {line}", stats)
            continue

        section_line = normalize_section_line(line)
        if section_line:
            emit_line(out_lines, section_line, stats)
            continue

        topic_heading = normalize_topic_heading(line, current_project, topic_catalog, stats)
        if topic_heading:
            emit_line(out_lines, topic_heading, stats)
            stats.topics_kept += 1
            if current_project is not None:
                stats.topic_projects.append(current_project)
            pending_topic_from_project = False
            continue

        if pending_topic_from_project and current_project in topic_catalog:
            synthesized = f"### 专题{int_to_cn(current_project)} {topic_catalog[current_project]}"
            emit_line(out_lines, synthesized, stats)
            stats.topics_kept += 1
            stats.topic_projects.append(current_project)
            stats.topic_title_supplemented += 1
            pending_topic_from_project = False

            expected_title = clean_text_line(topic_catalog[current_project]).replace(" ，", "").strip()
            normalized_current = line.replace("，", "").strip()
            if normalized_current == expected_title:
                continue

        point_line = normalize_point_line(line)
        if point_line:
            emit_line(out_lines, point_line, stats)
            continue

        answer_line = normalize_answer_line(line, stats)
        if answer_line:
            emit_line(out_lines, answer_line[0], stats)
            if answer_line[1]:
                emit_line(out_lines, answer_line[1], stats)
                if len(review_examples) < 12:
                    review_examples.append(answer_line[1])
            continue

        question_match = match_question_start(cleaned_lines, idx - 1)
        if question_match:
            normalized_num = normalize_question_number(question_match[0], prev_qnum, stats)
            prev_qnum = normalized_num
            stats.questions_kept += 1
            emit_line(out_lines, f"**{normalized_num}.** {question_match[1]}".rstrip(), stats)
            continue

        if OPTION_RE.match(line):
            option = OPTION_RE.match(line)
            emit_line(out_lines, f"{line[0]}. {clean_text_line(option.group(1))}", stats)
            continue

        line = canonicalize_label_text(line)
        if re.match(r"^【[^】]+】", line):
            emit_line(out_lines, line, stats)
            if line.startswith("【待复核】") and len(review_examples) < 12:
                review_examples.append(line)
            continue

        if REVIEW_TRIGGER_RE.search(line) and "【待复核】" not in line and len(review_examples) < 12:
            review = f"【待复核】{line}"
            emit_line(out_lines, review, stats)
            review_examples.append(review)
            continue

        emit_line(out_lines, line, stats)

    out_lines = squeeze_blank_lines(out_lines)
    final_text = "\n".join(out_lines) + "\n"
    stats.after_lines = final_text.count("\n")
    validate_output(final_text, stats)

    DST.write_text(final_text, encoding="utf-8")
    RULES_DOC.write_text(build_rules_doc(stats, review_examples), encoding="utf-8")

    print(f"已写入：{DST}")
    print(f"已写入：{RULES_DOC}")
    print(f"专题数：{stats.topics_kept}")
    print(f"题目数：{stats.questions_kept}")
    print(f"待复核：{stats.review_count}")


if __name__ == "__main__":
    main()
