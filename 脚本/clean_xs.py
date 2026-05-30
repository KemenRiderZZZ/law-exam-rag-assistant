#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""左宁《刑诉法》OCR 清洗脚本。"""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "OCR原稿" / "左宁《刑诉法》.md"
DST = PROJECT_ROOT / "整理后文本" / "左宁刑诉法_整理版.md"
RULES_DOC = PROJECT_ROOT / "整理后文本" / "左宁刑诉法_修正说明.md"

BOOK_TITLE = "左宁刑事诉讼法专题讲座精讲卷（2026版）"
PART_RE = re.compile(r"^第[一二三四五六七八九十百]+编")
TOPIC_RE = re.compile(r"^专题([一二三四五六七八九十百]+)\s*(.+)$")
SECTION_RE = re.compile(r"^第([一二三四五六七八九十百]+)节\s*(.+)$")
MAIN_HEADING_RE = re.compile(r"^[一二三四五六七八九十]+、")
SUB_HEADING_RE = re.compile(r"^（[一二三四五六七八九十]+）")
OPTION_RE = re.compile(r"^[A-DＡ-Ｄ][\.\、]")
LIST_RE = re.compile(r"^\d+\.")
QUOTE_RE = re.compile(r"^>")
TABLE_RE = re.compile(r"^\|")
TABLE_BORDER_RE = re.compile(r"^[\|\+\-\=\s:]+$")
END_PUNCT = "。！？；：…"
JOIN_END_PUNCT = "，、）】》”\"」』："

MARKER_NAMES = [
    "记忆逻辑",
    "图释",
    "例",
    "萌主点拨",
    "注意",
    "提示",
    "总结",
    "题角度",
    "题角图",
    "命题角度",
    "命题角图",
    "国关联法条",
    "随堂练习",
    "策科会试",
    "切策科会试",
    "画策科会试",
]

PHRASE_REPLACEMENTS = {
    "人民迭圆": "人民法院",
    "人民朝": "人民法院",
    "人民驱": "人民法院",
    "检察脸": "检察院",
    "中国礴局": "中国海警局",
    "公望吐": "公安机关",
    "（Z）": "（二）",
    "法露端蠢原则": "法律为准绳原则",
    "诃•诉讼法典": "刑事诉讼法典",
    "看森标窥亲和立释": "有关法律规定和立法解释",
    "鞋。这是刑事诉讼法的重要渊源。": "宪法。这是刑事诉讼法的重要渊源。",
    "直丑": "有罪",
    "无霏": "无罪",
    "考杳": "考查",
    "近照": "按照",
    "和解薇书": "和解协议书",
    "诉讼权利0": "诉讼权利。",
    "天民法院不予支寤": "人民法院不予支持",
    "丕鲤咆履行全部赔偿义务": "不能即时履行全部赔偿义务",
    "处募冕森顺序": "最先顺序",
    "一**S57S**定代理人": "法定代理人",
    "本专题平均每年考查1~2分，每年必考的基本原则有2个：自愿认罪认罚从宽处理原则和具有法定情形不予追究刑事责任原则。": (
        "本专题平均每年考查1~2分，每年必考的基本原则有2个：自愿认罪认罚从宽处理原则和具有法定情形不予追究刑事责任原则。"
    ),
}

LINE_REPLACEMENTS = {
    "刑事诉讼法的渊源是指刑事诉讼法律规范的存在形式。": "刑事诉讼法的渊源是指刑事诉讼法律规范的存在形式。",
    "刑事诉讼法对于刑法而言，既具有工具价值，又具有自身的独立价值。": "刑事诉讼法对于刑法而言，既具有工具价值，又具有自身的独立价值。",
    "### 第九节 未经人民法院依法判决，": "### 第九节 未经人民法院依法判决，对任何人都不得确定有罪",
    "各民族公区都有用本民族语言文字进行诉讼的权利。人民法院、人民检察院和公安机关对于不通晓当地通用的语言文字的诉讼参与人，屋当为他们翅译。": "各民族公民都有用本民族语言文字进行诉讼的权利。人民法院、人民检察院和公安机关对于不通晓当地通用的语言文字的诉讼参与人，应当为他们翻译。",
    "在少数民族聚居或者多民族杂居的也匹，鼓用当地通用的语言进行审讯，用当地通用的文字发布判决书、布告和其他文件。": "在少数民族聚居或者多民族杂居的地区，应当用当地通用的语言进行审讯，用当地通用的文字发布判决书、布告和其他文件。",
    "适用阶段［命窗庙面审前阶段拒绝认罪认罚，审判阶段认罪认罚，可以适用认罪认罚从宽制度；审前阶段认罪认罚，审判阶段拒绝认罪认罚，不适用认罪认罚从宽制度": "适用阶段：审前阶段拒绝认罪认罚、审判阶段认罪认罚的，可以适用认罪认罚从宽制度；审前阶段认罪认罚、审判阶段拒绝认罪认罚的，不适用认罪认罚从宽制度。",
    "双方当事人可以就赔偿损失、赔礼道歉等尽贵贵任事项进行和解，并且可以就被害人及其法定代理人或者近亲属是否要求或者同意而误、人民检察院、人民法院对犯罪嫌疑人依法丛逊理进行协商，但不得对案件的事实认定、证据采信、法律适用和定罪量刑等依法属玄莉关、人民检察院、人民法院职权范围的事宜进行协商。": "双方当事人可以就赔偿损失、赔礼道歉等承担责任事项进行和解，并且可以就被害人及其法定代理人或者近亲属是否要求或者同意人民检察院、人民法院对犯罪嫌疑人依法从宽处理进行协商，但不得对案件的事实认定、证据采信、法律适用和定罪量刑等依法属于公安机关、人民检察院、人民法院职权范围的事宜进行协商。",
    "和解协议已经全部履行，当事人反悔的「天民法院不予支寤「但有证据证明和解违反自愿、合法原则的除外（《刑诉解释》第593条）。": "和解协议已经全部履行，当事人反悔的，人民法院不予支持；但有证据证明和解违反自愿、合法原则的除外（《刑诉解释》第593条）。",
    "被害人或者其法定代理人、近亲属提起附带民事诉讼后，双方愿意和解，但被告人丕鲤咆履行全部赔偿义务的，人民法院应当制作附带民事调解书。": "被害人或者其法定代理人、近亲属提起附带民事诉讼后，双方愿意和解，但被告人不能即时履行全部赔偿义务的，人民法院应当制作附带民事调解书。",
    "被害人死亡的，其近亲属可以与被告人和解。近亲属有多人的，达成和解协议，应当经处募冕森顺序的所有近亲属同意。被害人系无行为能力或者限制行为能力人的，其法定代理人、近亲属可以代为和解。": "被害人死亡的，其近亲属可以与被告人和解。近亲属有多人的，达成和解协议，应当经最先顺序的所有近亲属同意。被害人系无行为能力人或者限制行为能力人的，其法定代理人、近亲属可以代为和解。",
    "一**S57S**定代理人、近亲属依照前述规定代为和解的，和解协议约定的赔礼道歉等事项，应当由被告人本人履行。": "法定代理人、近亲属依照前述规定代为和解的，和解协议约定的赔礼道歉等事项，应当由被告人本人履行。",
}

ANSWER_TOKEN_MAP = {
    "%": "X",
    "％": "X",
    "*": "X",
    "x": "X",
    "乂": "X",
    "V„": "V",
    "\"": "X",
    "K": "X",
    "{": "X",
    "八": "A",
}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ")
    text = re.sub(r"\[([^\[\]]*?)\]\{\.underline\}", r"\1", text)
    text = re.sub(r"\[([^\[\]]*?)\]\{\.smallcaps\}", r"\1", text)
    text = re.sub(r"\[\]\{#bookmark\d+\s*\.anchor\}", "", text)
    text = re.sub(r"\[([^\]]+?)\]\(#bookmark\d+\)", r"\1", text)
    text = re.sub(r"\{\.[a-zA-Z][\w-]*\}", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = text.replace('\\"', '"').replace("\\'", "'")
    text = text.replace("\\*", "*").replace("\\[", "[").replace("\\]", "]")
    text = text.replace("\\(", "(").replace("\\)", ")")
    text = text.replace("\\-", "-")
    text = re.sub(r"\*+/([0-9IVXL]+)\*+", "", text)
    text = re.sub(r"\*+([0-9IVXL]+)\*+", r"\1", text)
    text = text.replace("**.**", "")
    text = text.replace("※", "")
    text = text.replace("Contents", "目录")
    for wrong, right in PHRASE_REPLACEMENTS.items():
        text = text.replace(wrong, right)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def clean_catalog_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\*+/?[0-9IVXL]+(?:[~\-–][0-9IVXL]+)?\*+", "", line)
    line = re.sub(r"/\d{1,3}$", "", line)
    line = re.sub(r"\s+[0-9IVXL]+$", "", line)
    line = line.replace("※", "")
    line = re.sub(r"\s{2,}", " ", line).strip(" -")
    return line


def parse_catalog(lines: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    compact: list[str] = ["## 目录", ""]
    sections: list[tuple[str, str]] = []
    current_topic = ""
    last_entry_index: int | None = None

    for raw in lines:
        line = clean_catalog_line(raw)
        if not line or line == "目录":
            continue
        if line.startswith("刑事诉讼三大逻辑"):
            compact.append(f"- {line}")
            last_entry_index = None
            continue
        if PART_RE.match(line):
            compact.append(f"- {line}")
            last_entry_index = None
            continue
        topic_match = TOPIC_RE.match(line)
        if topic_match:
            current_topic = f"专题{topic_match.group(1)} {topic_match.group(2).strip()}"
            compact.append(f"- {current_topic}")
            last_entry_index = None
            continue
        section_match = SECTION_RE.match(line)
        if section_match and current_topic:
            section = f"第{section_match.group(1)}节 {section_match.group(2).strip()}"
            sections.append((current_topic, section))
            compact.append(f"- {section}")
            last_entry_index = len(compact) - 1
            continue
        if line.startswith("（") and last_entry_index is not None:
            compact[last_entry_index] = compact[last_entry_index] + f" {line}"

    compact.append("")
    return compact, sections


def is_garbage_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s in {"画", "I", "J", "L"}:
        return True
    if TABLE_BORDER_RE.fullmatch(s) and not TABLE_RE.match(s):
        return True
    if re.fullmatch(r"[\^\\/*~><%A-Za-z0-9\"'=,.\-_:|]{12,}", s):
        return True
    if re.search(r"(\\\^|~\^|\^\^)", s) and len(re.findall(r"[\\\^~*><%]", s)) >= 6:
        return True
    return False


def normalize_marker_line(line: str) -> str:
    stripped = line.strip("[]［］【】()（） ")
    for name in MARKER_NAMES:
        if name in stripped:
            return f"**【{name}】**"
    if "关联法条" in stripped:
        return "**【国关联法条】**"
    if stripped == "本专题重点":
        return "**本专题重点**"
    return line


def strip_inline_noise(line: str) -> str:
    line = re.sub(r"[\\\^~><%]{4,}", "", line)
    line = re.sub(r"[A-Za-z]*\\\^[A-Za-z0-9\\\^*><%\"']*", "", line)
    line = re.sub(r"\*{0,2}[A-Za-z]*\^[A-Za-z0-9\^*><%\"']*", "", line)
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip()


def normalize_enumeration(line: str) -> str:
    line = re.sub(r"^(\d+)\.\s+\*\*[\.,，]?\*\*\s*", r"\1. ", line)
    line = re.sub(r"^(\d+)\.\s+\*\*\d+\)\*\*\s*", r"\1. ", line)
    line = re.sub(r"^(\d+)\.\s+[.,，]\s*", r"\1. ", line)
    line = re.sub(r"^\*\*(\d+)[,，]\*\*\s*", r"\1. ", line)
    line = re.sub(r"([①②③④⑤⑥⑦⑧⑨⑩])\s*\*\*\.\*\*\s*", r"\1 ", line)
    line = re.sub(r"([。！？）】》”\"])\s*\*\*\.\*\*\s*", r"\1 ", line)
    line = re.sub(r"^([A-DＡ-Ｄ])[\.\、]\s*", lambda m: f"**{m.group(1)}.** ", line)
    line = re.sub(r"^答案[：:]\s*", "**【答案】** ", line)
    line = re.sub(r"^解析[：:]\s*", "**【解析】** ", line)
    line = re.sub(r"^(\d+)\.\s*答案[：:]\s*", r"\1. **【答案】** ", line)
    line = re.sub(r"^(\d+)\.\s*解析[：:]\s*", r"\1. **【解析】** ", line)
    line = re.sub(r"([①②③④⑤⑥⑦⑧⑨⑩])答案[：:]\s*", r"\1 **【答案】** ", line)
    line = re.sub(r"([①②③④⑤⑥⑦⑧⑨⑩])解析[：:]\s*", r"\1 **【解析】** ", line)
    return line.strip()


def normalize_heading_text(line: str) -> str:
    line = strip_inline_noise(line)
    line = line.replace(" .", ".")
    line = line.replace("（法院专属定罪权原则）", "（法院专属定罪权原则）")
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip()


def classify(line: str) -> str:
    if not line:
        return "blank"
    if line.startswith("#"):
        return "heading"
    if line.startswith("**【") or line == "**本专题重点**":
        return "marker"
    if TABLE_RE.match(line):
        return "table"
    if QUOTE_RE.match(line):
        return "quote"
    if OPTION_RE.match(line.replace("*", "")) or line.startswith("**A.") or line.startswith("**B.") or line.startswith("**C.") or line.startswith("**D."):
        return "list"
    if LIST_RE.match(line) or MAIN_HEADING_RE.match(line) or SUB_HEADING_RE.match(line):
        return "list"
    return "text"


def should_join(prev: str, cur: str) -> bool:
    if not prev or not cur:
        return False
    if classify(prev) != "text" or classify(cur) != "text":
        return False
    if len(prev) < 12:
        return False
    prev = prev.rstrip()
    if prev.endswith(tuple(END_PUNCT)):
        return False
    if cur.startswith(("“", "（", "《")):
        return True
    return prev.endswith(tuple(JOIN_END_PUNCT)) or not prev.endswith(tuple(END_PUNCT))


def clean_line(line: str) -> str:
    line = normalize_marker_line(line)
    line = strip_inline_noise(line)
    line = normalize_enumeration(line)
    if line in LINE_REPLACEMENTS:
        return LINE_REPLACEMENTS[line]
    line = re.sub(r"\s{2,}", " ", line).strip()
    return line


def normalize_answer_token(token: str) -> str:
    token = token.strip()
    token = token.replace("~0~", "").replace("~O~", "").replace("~o~", "")
    token = token.replace("„", "").replace("。", "").replace(".", "")
    token = token.replace("**", "")
    token = token.strip("（）()[]{}<> ")
    for wrong, right in ANSWER_TOKEN_MAP.items():
        token = token.replace(wrong, right)
    token = token.replace("Bo", "B").replace("Bo", "B")
    token = token.upper()
    token = re.sub(r"[^ABCDXV]", "", token)
    return token


def looks_like_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if "VX" in s or "QQ" in s or "2953780020" in s:
        return True
    if s in {"7", "7 后3J蜜匿", "i«", "续表", "»标沫］", "»« rtrtrtrtrtrt*\"S*", "履3命函倚度I"}:
        return True
    if re.fullmatch(r"[①②③④⑤⑥⑦⑧⑨⑩]+", s):
        return True
    if re.fullmatch(r"[@¥\-\}\{\]\[\^\|\\/A-Za-z0-9 ]{3,}", s) and not re.search(r"[一-龥]", s):
        return True
    if len(re.findall(r"[■\^~*_<>@¥]", s)) >= max(4, len(s) // 3):
        return True
    return False


def fix_answer_line(line: str) -> str:
    match = re.match(r"^(?P<prefix>(?:\d+\.\s+|[①②③④⑤⑥⑦⑧⑨⑩]\s+)?)\*\*【答案】\*\*\s*(?P<token>[A-Za-z％%*\"乂八{~0~„\.\-]+)(?P<tail>.*)$", line)
    if not match:
        return line
    token = normalize_answer_token(match.group("token"))
    if not token:
        return line.replace(match.group("token"), "").replace("  ", " ").strip()
    wrapped = token if token in {"X", "V"} else f"**{token}**"
    tail = match.group("tail")
    return f"{match.group('prefix')}**【答案】** {wrapped}{tail}".strip()


def is_empty_option_line(line: str) -> bool:
    return bool(re.fullmatch(r"\*\*[A-D]\.\*\*", line.strip()))


def cleanup_ascii_table_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    in_ascii_table = False
    for line in lines:
        stripped = line.strip()
        if TABLE_RE.match(stripped) and "+-" in stripped:
            in_ascii_table = True
            continue
        if in_ascii_table:
            if not stripped:
                cleaned.append("")
                in_ascii_table = False
                continue
            if TABLE_RE.match(stripped):
                compact = [seg.strip() for seg in stripped.strip("|").split("|")]
                compact = [seg for seg in compact if seg and not TABLE_BORDER_RE.fullmatch(seg)]
                if compact:
                    cleaned.append("- " + " | ".join(compact))
                continue
            in_ascii_table = False
        cleaned.append(line)
    return cleaned


def format_pipe_row(line: str) -> str | None:
    cells = [seg.strip() for seg in line.strip().strip("|").split("|")]
    cells = [cell for cell in cells if cell and not TABLE_BORDER_RE.fullmatch(cell)]
    if not cells:
        return None
    if all(looks_like_noise(cell) for cell in cells):
        return None
    if len(cells) == 1:
        return f"- {cells[0]}"
    if len(cells) == 2:
        return f"- {cells[0]}：{cells[1]}"
    head = " / ".join(cells[:-1])
    return f"- {head}：{cells[-1]}"


def flatten_pipe_tables(lines: list[str]) -> list[str]:
    flattened: list[str] = []
    for line in lines:
        if line.strip().startswith("|"):
            bullet = format_pipe_row(line)
            if bullet:
                flattened.append(bullet)
            continue
        flattened.append(line)
    return flattened


def rebuild_plain_option_blocks(lines: list[str]) -> list[str]:
    output: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        output.append(line)
        if "（多选）①" in line or "（单选）①" in line or "下列哪一选项是正确的？" in line:
            j = i + 1
            option_texts: list[str] = []
            while j < len(lines) and len(option_texts) < 4:
                cur = lines[j].strip()
                if not cur:
                    j += 1
                    continue
                if cur.startswith(("**【", "### ", "#### ", "##### ")):
                    break
                if cur.startswith("**") and re.match(r"^\*\*[A-D]\.\*\*", cur):
                    option_texts = []
                    break
                if cur.startswith(("1.", "2.", "3.", "4.", "5.")):
                    break
                option_texts.append(cur)
                j += 1
            if len(option_texts) == 4:
                output.extend(
                    [
                        f"**A.** {option_texts[0]}",
                        f"**B.** {option_texts[1]}",
                        f"**C.** {option_texts[2]}",
                        f"**D.** {option_texts[3]}",
                    ]
                )
                i = j - 1
        i += 1
    return output


def rebuild_orphan_options(lines: list[str]) -> list[str]:
    output: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i + 7 < len(lines) and all(is_empty_option_line(lines[i + j]) for j in (0, 2, 4, 6)):
            option_texts = [lines[i + 1].strip(), lines[i + 3].strip(), lines[i + 5].strip(), lines[i + 7].strip()]
            if all(option_texts):
                for idx, option in enumerate(("A", "B", "C", "D")):
                    output.append(f"**{option}.** {option_texts[idx]}")
                i += 8
                continue
        if is_empty_option_line(line):
            i += 1
            continue
        output.append(line)
        i += 1
    return output


def postprocess_output(lines: list[str]) -> list[str]:
    patched: list[str] = []
    skip_garbage = {"OMi本原则", "**S**", "体系结构", "体系解说", "**¥］**"}

    for raw in lines:
        line = raw.strip()
        if line in skip_garbage:
            continue
        if looks_like_noise(line):
            continue
        if "关联法条" in line and not line.startswith("**【国关联法条】**"):
            patched.append("**【国关联法条】**")
            continue
        if "命题篇" in line or ("命题" in line and "角度" in line):
            patched.append("**【题角度】**")
            continue
        if "策莉函" in line or "策同会试" in line or "策科含点" in line or "策科会试" in line:
            patched.append("**【策科会试】**")
            continue
        if line.startswith("### 第九节 未经人民法院依法判决"):
            patched.append("### 第九节 未经人民法院依法判决，对任何人都不得确定有罪")
            continue
        if line == "对任何人都不得确定有罪（法院专属定罪权原则）":
            continue
        if line.startswith("刑诉法的基本原则--各民族公民有权使用本民族语言文字进行诉讼"):
            patched.append("刑诉法的基本原则：各民族公民有权使用本民族语言文字进行诉讼")
            continue
        if line.startswith("《刑诉法》第14条第1款人民法院、人民检察院和公安机关"):
            patched.append("《刑诉法》第14条第1款 人民法院、人民检察院和公安机关应当保障犯罪嫌疑人、被告人和其他诉讼参与人依法享有的辩护权和其他诉讼权利。")
            continue
        if line.startswith("《刑诉法》第**i2**条"):
            patched.append("《刑诉法》第12条 未经人民法院依法判决，对任何人都不得确定有罪。")
            continue
        if line.startswith("1. 明确规定了确定被告人"):
            patched.append("1. 明确规定了确定被告人有罪的权力由人民法院统一行使，其他任何机关、团体和个人都无权行使。定罪权是刑事审判权的核心，人民法院作为我国唯一的审判机关，代表国家统一独立行使刑事审判权。")
            continue
        if line.startswith("2. 人民法院判决被告人有罪"):
            patched.append("2. 人民法院判决被告人有罪，必须严格依照法定程序，在保障被告人享有充分辩护权的基础上，依法组成审判庭进行公正、公开的审理。")
            continue
        if "提起公近辰始称为刑事被告人" in line:
            patched.append("1. 区分犯罪嫌疑人与刑事被告人。公诉案件在提起公诉前将被追诉人称为犯罪嫌疑人，提起公诉后始称为刑事被告人。简言之，犯嫌、被告，公诉为界。")
            continue
        if line == "诉讼阶段 立案后 侦查中 审查起诉时 决定起诉 审判时 执行":
            patched.append("- 诉讼阶段：立案后、侦查中、审查起诉时、决定起诉、审判时、执行")
            continue
        if line == "诉讼身份 犯罪嫌疑人 犯罪嫌疑人 犯罪嫌疑人 被告人 被告人 罪犯":
            patched.append("- 诉讼身份：犯罪嫌疑人、犯罪嫌疑人、犯罪嫌疑人、被告人、被告人、罪犯")
            continue
        if line.startswith("3. 法院专属定罪权原则体现了无罪推定") or line.startswith("3. 法院专属定罪权原则体现了无霏推定"):
            patched.append("3. 法院专属定罪权原则体现了无罪推定的精神，但与疑罪从无的裁判要求并不相同。")
            continue
        if line.startswith("5. 关于认罪认罚从宽原则，下列表述正确的有？"):
            patched.append("5. 关于认罪认罚从宽原则，下列表述正确的有？（多选）⑤")
            continue
        if line.startswith("8. 对于穷凶极恶的杀人犯") or line.startswith("B. 对于穷凶极恶的杀人犯"):
            patched.append("**B.** 对于穷凶极恶的杀人犯，即使其认罪认罚、积极赔偿并取得了被害人亲属谅解，也可不对其从宽处罚")
            continue
        if line.startswith("A,**对甲虽然不适用认罪认罚从宽原则") or ("认罪部分仍可以适度从宽处罚" in line and "认罪认罚从宽原则适用于侦查、起诉、审判各诉讼阶段" in line):
            patched.append("5. **【答案】** **BD**。**A,**对甲虽然不适用认罪认罚从宽原则，但对其认罪部分仍可以适度从宽处罚。**C,**认罪认罚从宽原则适用于侦查、起诉、审判各诉讼阶段。")
            continue
        if line.startswith("1. 诉讼权利是诉讼参与人享有的法定权利"):
            patched.append("1. 诉讼权利是诉讼参与人享有的法定权利，法律应予以保护，公安司法机关不得加以剥夺。诉讼参与人在诉讼权利受到侵害时，有权通过控告或者请求公安司法机关予以制止等方式保护自己的诉讼权利，有关机关对于侵犯公民诉讼权利的行为应当认真查处。")
            continue
        if line.startswith("2. 公安司法机关"):
            patched.append("2. 公安司法机关有义务保障诉讼参与人充分行使诉讼权利，对于妨碍诉讼参与人行使诉讼权利的各种行为，有义务采取措施予以制止。")
            continue
        if line.startswith("3. 诉讼参与人除了享有诉讼权利"):
            patched.append("3. 诉讼参与人除了享有诉讼权利，还应当承担法律规定的诉讼义务。公安司法机关有权要求诉讼参与人履行相应的诉讼义务。")
            continue
        if line == "@¥}-":
            continue
        if line.startswith("适用阶段［命窗庙面审前阶段拒绝认罪认罚"):
            patched.append("适用阶段：审前阶段拒绝认罪认罚、审判阶段认罪认罚的，可以适用认罪认罚从宽制度；审前阶段认罪认罚、审判阶段拒绝认罪认罚的，不适用认罪认罚从宽制度。")
            continue
        if line.startswith("双方当事人和解的，公安机关、人民检察院、人民法院应当近照"):
            patched.append("双方当事人和解的，公安机关、人民检察院、人民法院应当按照当事人和其他有关人员的意见，对和解的自愿性、合法性进行审查，并主持制作和解协议书。")
            continue
        if line.startswith("B,**属于自诉案件，不是不能和解，而是不适用公除件的和解程序"):
            patched.append("**【答案】** **AC**。**B,**属于自诉案件，不是不能和解，而是不适用公诉案件的和解程序。**D,**不属于民间纠纷，不能和解。")
            continue
        if "斐过大俊的积极赔偿" in line:
            patched.append("1. 大俊因涉嫌盗窃被立案侦查，由于犯罪情节轻微，公安机关对大俊适用当事人和解的公诉案件诉讼程序，经过大俊的积极赔偿，侦查机关可以对大俊撤销案件（）⑤。")
            continue
        if "又能真诚悔霏" in line:
            patched.append("2. 大汪因涉嫌诈骗被某县公安机关立案侦查，侦查终结移送某县检察院审查起诉。某县检察院认为大汪犯罪情节轻微，又能真诚悔罪，积极赔偿，对大汪适用当事人和解的公诉案件诉讼程序，若某县检察院认为对大汪不需要判处刑罚的，可以作出不起诉决定（）⑥。")
            continue
        if "其为定的赔偿损失内容可分期履行" in line:
            patched.append("**D.** 如甲与丙达成刑事和解，其约定的赔偿损失内容不可分期履行")
            continue
        if "51寸查封、扣押、冻结的财物及其孳息的处理" in line:
            patched.append("#### 三、对查封、扣押、冻结的财物及其孳息的处理（熟悉即可）")
            continue
        if "法足不越诉" in line and "能红参近" in line:
            patched.append("情节\"显著轻微\"，与《刑诉法》第177条第2款中酌定不起诉所对应的犯罪情节\"轻微\"并不相同。情节\"显著轻微\"意味着违法行为存在但尚不构成犯罪，因此根据《刑法》不认为是犯罪的，应当作出法定不起诉处理；如果认为犯罪情节\"轻微\"，依照《刑法》规定不需要判处刑罚或者免除刑罚的，则可以作出酌定不起诉处理。")
            continue
        if "赦血否夭痴福我国只有特赦" in line:
            patched.append("我国只有特赦，且须由全国人民代表大会常务委员会决定。这种特赦命令具有终止刑事追究的法律效力。")
            continue
        if "被告人枣上近、人民检察院未抗诉" in line:
            patched.append("##### （一）被告人未上诉、人民检察院未抗诉的，在上诉、抗诉期满后三日内报请上一级人民法院复核。")
            continue
        if "《刑诉解释》第417条对在法定刑以下判处刑罚的案件" in line:
            patched.append("《刑诉解释》第417条 对在法定刑以下判处刑罚的案件，最高人民法院予以核准的，应当作出核准裁定书；不予核准的，应当作出不核准裁定书，并撤销原判决、裁定，发回原审人民法院重新审判或者指定其他下级人民法院重新审判。")
            continue
        if "依照本解释第四百一十四条、第四百一十七条规定发回第二更人民法院重新审判" in line:
            patched.append("依照本解释第四百一十四条、第四百一十七条规定发回第二审人民法院重新审判的案件，第二审人民法院可以直接改判；必须通过开庭查清事实、核实证据或者纠正原审程序违法的，应当开庭审理。")
            continue
        if "和解协议已经全部履行，当事人反悔的「天民法院不予支寤" in line:
            patched.append("和解协议已经全部履行，当事人反悔的，人民法院不予支持；但有证据证明和解违反自愿、合法原则的除外（《刑诉解释》第593条）。")
            continue
        if "被告人丕鲤咆履行全部赔偿义务" in line:
            patched.append("被害人或者其法定代理人、近亲属提起附带民事诉讼后，双方愿意和解，但被告人不能即时履行全部赔偿义务的，人民法院应当制作附带民事调解书。")
            continue
        if "处募冕森顺序的所有近亲属同意" in line:
            patched.append("被害人死亡的，其近亲属可以与被告人和解。近亲属有多人的，达成和解协议，应当经最先顺序的所有近亲属同意。被害人系无行为能力人或者限制行为能力人的，其法定代理人、近亲属可以代为和解。")
            continue
        if "一**S57S**定代理人、近亲属依照前述规定代为和解" in line:
            patched.append("法定代理人、近亲属依照前述规定代为和解的，和解协议约定的赔礼道歉等事项，应当由被告人本人履行。")
            continue
        if line == "7 后3J蜜匿":
            continue
        if line.startswith("答案；"):
            line = line.replace("答案；", "**【答案】** ", 1)
        if line.startswith("答案:") or line.startswith("答案："):
            line = re.sub(r"^答案[：:]\s*", "**【答案】** ", line)
        if re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]答案[；：:]", line):
            line = re.sub(r"^([①②③④⑤⑥⑦⑧⑨⑩])答案[；：:]\s*", r"\1 **【答案】** ", line)
        line = line.replace("~0~", "").replace("~O~", "").replace("~o~", "")
        line = line.replace("）~", "）")
        line = re.sub(r"/\d{1,3}$", "", line)
        line = line.replace("答案；", "**【答案】** ")
        line = re.sub(r"(?<=\*\*【答案】\*\*\s)\*\*([a-dxv]+)\*\*", lambda m: f"**{m.group(1).upper()}**", line)
        line = re.sub(r"(?<=\*\*【答案】\*\*\s)([a-dxv]+)(?=[。．\s])", lambda m: m.group(1).upper(), line)
        line = re.sub(r"(\*\*【答案】\*\*\s(?:\*\*[A-DXV]+\*\*|[XV]))(?=[一-龥])", r"\1。", line)
        line = re.sub(r"([①②③④⑤⑥⑦⑧⑨⑩])\s*\*\*【答案】\*\*", r"\1 **【答案】**", line)
        line = fix_answer_line(line)
        patched.append(line)

    patched = rebuild_orphan_options(patched)
    patched = rebuild_plain_option_blocks(patched)
    patched = cleanup_ascii_table_lines(patched)
    patched = flatten_pipe_tables(patched)

    deduped: list[str] = []
    prev_blank = False
    for line in patched:
        if not line.strip():
            if prev_blank:
                continue
            deduped.append("")
            prev_blank = True
            continue
        if deduped and line.strip() == "也可不对其从宽处罚" and deduped[-1].strip().endswith("也可不对其从宽处罚"):
            continue
        if deduped and line == "7 后3J蜜匿":
            continue
        if deduped and line.strip() == "履3命函倚度I":
            continue
        deduped.append(line)
        prev_blank = False
    return deduped


def rebuild_body(lines: list[str], section_flow: list[tuple[str, str]]) -> list[str]:
    output: list[str] = []
    current_topic = ""
    flow_index = 0

    for raw in lines:
        line = clean_line(raw)
        if not line or is_garbage_line(line):
            if output and output[-1] != "":
                output.append("")
            continue

        topic_match = TOPIC_RE.match(line)
        if topic_match:
            topic = f"专题{topic_match.group(1)} {normalize_heading_text(topic_match.group(2))}"
            if output and output[-1] != "":
                output.append("")
            output.append(f"## {topic}")
            output.append("")
            current_topic = topic
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            section = f"第{section_match.group(1)}节 {normalize_heading_text(section_match.group(2))}"
            matched_topic = current_topic
            lookahead = section_flow[flow_index:flow_index + 8]
            for offset, (topic, expected_section) in enumerate(lookahead):
                if section == expected_section:
                    matched_topic = topic
                    flow_index += offset + 1
                    break
            if matched_topic and matched_topic != current_topic:
                if output and output[-1] != "":
                    output.append("")
                output.append(f"## {matched_topic}")
                output.append("")
                current_topic = matched_topic
            if output and output[-1] != "":
                output.append("")
            output.append(f"### {section}")
            output.append("")
            continue

        if MAIN_HEADING_RE.match(line):
            if output and output[-1] != "":
                output.append("")
            output.append(f"#### {normalize_heading_text(line)}")
            output.append("")
            continue

        if SUB_HEADING_RE.match(line):
            if output and output[-1] != "":
                output.append("")
            output.append(f"##### {normalize_heading_text(line)}")
            output.append("")
            continue

        if line == "**本专题重点**":
            if output and output[-1] != "":
                output.append("")
            output.append(line)
            output.append("")
            continue

        if TABLE_RE.match(line):
            output.append(line)
            continue

        if TABLE_BORDER_RE.fullmatch(line):
            continue

        if output and should_join(output[-1], line):
            output[-1] = output[-1] + line
        else:
            output.append(line)

    while output and output[-1] == "":
        output.pop()
    return output


def build_rules_doc() -> str:
    return """# 左宁刑诉法修正说明

- 输入输出固定为：`OCR原稿/左宁《刑诉法》.md -> 整理后文本/左宁刑诉法_整理版.md`
- 本次自动修正重点覆盖：
  - 清理 `{.underline}`、bookmark anchor、无意义加粗、转义引号、目录页码与 `※`
  - 重建 `## 专题 / ### 第X节 / #### 一、 / ##### （一）` 的 Markdown 层级
  - 规范题目选项、答案、解析、提示类标记，保留题目与口诀等教学内容
  - 合并 OCR 硬断行，删除明显乱码噪声行，保留大部分表格信息
- 仍建议人工重点复核：
  - 目录页与前置页
  - 多列表格和跨行表格
  - 特别程序、法条引用、答案解析密集段
  - 少量 OCR 错字和局部句子不顺处
- 可复用到其他书的规则：
  - Pandoc 残留清理
  - 题目/答案块规范
  - 标题层级重建
  - 断行合并与乱码行过滤
"""


def main() -> None:
    text = normalize_text(SRC.read_text(encoding="utf-8"))
    lines = text.split("\n")

    contents_index = next((i for i, line in enumerate(lines) if line.strip() == "目录"), None)
    body_start = next((i for i, line in enumerate(lines) if "在学习刑事诉讼法之前" in line), None)
    if contents_index is None or body_start is None or body_start <= contents_index:
        raise RuntimeError("未能定位目录区或正文起点。")

    preface_lines = [clean_line(line) for line in lines[:contents_index] if clean_line(line) and not is_garbage_line(clean_line(line))]
    catalog_lines = lines[contents_index:body_start]
    body_lines = lines[body_start:]

    compact_toc, section_flow = parse_catalog(catalog_lines)
    cleaned_body = rebuild_body(body_lines, section_flow)

    merged_preface: list[str] = []
    for line in preface_lines:
        if not merged_preface:
            merged_preface.append(line)
            continue
        prev = merged_preface[-1]
        if len(prev) >= 40 and len(line) >= 20 and should_join(prev, line):
            merged_preface[-1] = prev + line
        else:
            merged_preface.append(line)

    output_lines = [f"# {BOOK_TITLE}", ""]
    output_lines.extend(merged_preface)
    output_lines.extend(["", "---", ""])
    output_lines.extend(compact_toc)
    output_lines.extend(cleaned_body)
    output_lines = postprocess_output(output_lines)

    final_text = "\n".join(output_lines)
    final_text = final_text.replace("\n\n\n", "\n\n")
    final_text = re.sub(r"\n{3,}", "\n\n", final_text).strip() + "\n"

    DST.write_text(final_text, encoding="utf-8")
    RULES_DOC.write_text(build_rules_doc(), encoding="utf-8")

    print(f"source={SRC}")
    print(f"output={DST}")
    print(f"rules={RULES_DOC}")
    print(f"lines={final_text.count(chr(10))}")


if __name__ == "__main__":
    main()
