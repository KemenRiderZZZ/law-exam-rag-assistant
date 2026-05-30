#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""孟献贵《民法》OCR 清洗脚本。"""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "OCR原稿" / "孟献贵《民法》.md"
DST = PROJECT_ROOT / "整理后文本" / "孟献贵民法_整理版.md"

BOOK_TITLE = "孟献贵民法专题讲座精讲卷（2026版）"

PART_TITLES = {
    1: "总则编",
    2: "物权编",
    3: "债法总则",
    4: "合同编",
    5: "人格权编",
    6: "婚姻家庭编",
    7: "继承编",
    8: "侵权责任编",
}

TOPIC_TITLES = {
    1: "民事法律关系的基本原理",
    2: "民事主体",
    3: "民事法律行为",
    4: "代理",
    5: "诉讼时效",
    6: "物权的基本原理",
    7: "所有权",
    8: "用益物权",
    9: "担保物权",
    10: "占有",
    11: "债的基本原理",
    12: "合同的基本原理",
    13: "缔约过失责任",
    14: "合同的订立",
    15: "合同（债）的履行",
    16: "合同（债）的保全",
    17: "合同（债）的变更和转让",
    18: "合同（债）的权利义务终止",
    19: "违约责任",
    20: "买卖合同",
    21: "供用电、水、气、热力合同",
    22: "赠与合同",
    23: "借款合同",
    24: "保证合同",
    25: "租赁合同",
    26: "融资租赁合同",
    27: "保理合同",
    28: "承揽合同",
    29: "建设工程合同",
    30: "运输合同",
    31: "技术合同",
    32: "保管合同",
    33: "仓储合同",
    34: "委托合同",
    35: "物业服务合同",
    36: "行纪合同",
    37: "中介合同",
    38: "合伙合同",
    39: "旅游合同",
    40: "人格权",
    41: "婚姻家庭",
    42: "收养",
    43: "继承",
    44: "侵权责任的基本原理",
    45: "损害赔偿",
    46: "七类特殊主体责任",
    47: "七类典型侵权责任",
    48: "民法的基本原则",
    49: "民事权利",
}

CN_NUM = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

END_PUNCT = "。！？；：,，、）)]\"'』」》"
NO_MERGE_START = re.compile(
    r"^\s*("
    r"#{1,6}\s+|"
    r"\d+[\.。]|"
    r"[（(][\d一二三四五六七八九十]+[)）]|"
    r"[一二三四五六七八九十]+、|"
    r"[①②③④⑤⑥⑦⑧⑨⑩]|"
    r"[-\*>]|"
    r"\||"
    r"\+[-:=+]+|"
    r"【|"
    r"第[一二三四五六七八九十百零〇\d]+[章节条款]|"
    r"专题[一二三四五六七八九十百零〇\d]"
    r")"
)

JUNK_LINE_PATTERNS = [
    r"^\s*[口▲□■¬]\s*$",
    r"^\s*[LJI]\s*$",
    r"^\s*[%\\^]+\s*$",
    r"^\s*\*+\s*$",
    r"^\s*-+\s*$",
    r"^\s*\d{1,4}\s*$",
    r"^\s*[IVXLCDM]{1,6}\s*$",
    r"^\s*Meng Xian Gui\s*$",
    r"^\s*CHINA ECONOMIC PUBLISHING HOUSE\s*$",
]


def remove_pandoc_artifacts(text: str) -> str:
    text = re.sub(r"\[([^\[\]]*?)\]\{\.underline\}", r"\1", text)
    text = re.sub(r"\[([^\[\]]*?)\]\{\.smallcaps\}", r"\1", text)
    text = re.sub(r"\[\]\{#bookmark\d+\s*\.anchor\}", "", text)
    text = re.sub(r"\{\.[a-zA-Z][\w-]*\}", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+?)\]\(#bookmark\d+\)", r"\1", text)
    return text


def remove_meaningless_bold(text: str) -> str:
    pattern = re.compile(
        r"\*\*("
        r"[\d\w\.\,\-\+\(\)\[\]（）【】、，：；,/／\s]{1,16}?"
        r")\*\*"
    )

    def repl(m):
        inner = m.group(1)
        if re.search(r"[一-鿿]", inner):
            return m.group(0)
        return inner

    text = pattern.sub(repl, text)
    text = re.sub(r"\*\*([（(][\d一二三四五六七八九十]+[)）])\*\*", r"\1", text)
    text = re.sub(r"\*\*(\d+)\*\*", r"\1", text)
    text = re.sub(r"\*\*([A-Za-z])\*\*", r"\1", text)
    text = re.sub(r"\*\*([①②③④⑤⑥⑦⑧⑨⑩])\*\*", r"\1", text)
    text = re.sub(r"第\*\*(\d+)\*\*", r"第\1", text)
    return text


def fix_quotes(text: str) -> str:
    return text.replace('\\"', '"').replace("\\'", "'")


def remove_junk_lines(text: str) -> str:
    out = []
    for line in text.split("\n"):
        if any(re.match(pat, line) for pat in JUNK_LINE_PATTERNS):
            continue
        out.append(line)
    return "\n".join(out)


def cn_to_int(s: str) -> int | None:
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    s = s.replace("|", "十").replace("丨", "十").replace("I", "十").replace("l", "十")
    s = s.replace("—", "一").replace("-", "一").replace("－", "一")
    s = s.replace(" ", "")
    if s == "十":
        return 10
    if "十" in s:
        left, right = s.split("十", 1)
        tens = 1 if left == "" else CN_NUM.get(left)
        ones = 0 if right == "" else CN_NUM.get(right)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    return CN_NUM.get(s)


def normalize_common_typos(text: str) -> str:
    replacements = {
        "遗亡": "遗产",
        "诉讼时敷": "诉讼时效",
        "除斥期问": "除斥期间",
        "民事权利能方": "民事权利能力",
        "民事行为能方": "民事行为能力",
        "担保物杈": "担保物权",
        "继承杈": "继承权",
        "物杈": "物权",
        "债杈": "债权",
        "所有杈": "所有权",
        "抵押杈": "抵押权",
        "质押杈": "质押权",
        "留置杈": "留置权",
        "侵杈": "侵权",
        "无因管埋": "无因管理",
        "不当得刮": "不当得利",
        "法矗继承": "法定继承",
        "法走继承": "法定继承",
        "缔约过夭责任": "缔约过失责任",
        "蔺）中固付浒文属。": "",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    text = re.sub(r"第七章绥（第161", "第七章代理（第161", text)
    text = re.sub(r"\bL(?=技术合同|保管合同|中介合同)", "1.", text)
    text = re.sub(r"^\s*([0-9]+)\.\s+\.", r"\1.", text, flags=re.M)
    text = text.replace("（-）", "（一）")
    text = text.replace("(-)", "（一）")
    text = text.replace("(-\")", "（一）")
    return text


def normalize_markers(text: str) -> str:
    marker_map = {
        "图释": "图释",
        "例": "例",
        "萌主点拨": "萌主点拨",
        "注意": "注意",
        "提示": "提示",
        "总结": "总结",
        "随堂练习": "随堂练习",
        "因随堂练习": "随堂练习",
        "答案": "答案",
        "问题": "问题",
    }
    for raw, target in marker_map.items():
        text = re.sub(rf"[\[［【(（]\s*{raw}\s*[\]］】)）]", f"【{target}】", text)
    text = re.sub(r"题(\d+)\s*[,，]", r"题\1：", text)
    text = re.sub(r"例(\d+)\s*[,，]", r"例\1：", text)
    return text


def normalize_year_refs(text: str) -> str:
    text = re.sub(r"（(\d{4})\s*年", r"（\1年", text)
    text = re.sub(r"\(\s*(\d{4})\s*年", r"（\1年", text)
    text = re.sub(r"(\d{4})\s+年", r"\1年", text)
    text = re.sub(r"第\s*(\d+)\s+条", r"第\1条", text)
    text = re.sub(r"第\s*(\d+)\s+款", r"第\1款", text)
    text = re.sub(r"第(\d+)\s*---\s*(\d+)条", r"第\1—\2条", text)
    return text


def normalize_malformed_markers(text: str) -> str:
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if re.fullmatch(r"[A-Za-z0-9IltfoqQ口■□\[\]［］【】（）()\\/\*\s]*随堂练习[A-Za-z0-9IltfoqQ口■□\[\]［］【】（）()\\/\*\s]*", s):
            out.append("【随堂练习】")
            continue
        line = re.sub(
            r"^[A-Za-z0-9IltfoqQ口■□\[\]［］【】（）()\\/\*\s]*随堂练习[A-Za-z0-9IltfoqQ口■□\[\]［］【】（）()\\/\*\s]*",
            "【随堂练习】",
            line,
        )
        line = re.sub(r"^[I1l|口■□\[\]［］【】\\/\*\s]*萌主点拨[】］\]\s]*", "【萌主点拨】", line)
        line = re.sub(r"^[I1l|口■□\[\]［］【】\\/\*\s]*例[】］\]\s]*", "【例】", line)
        out.append(line)
    return "\n".join(out)


def normalize_ocr_artifacts(text: str) -> str:
    replacements = {
        "相应.的": "相应地",
        "死者的7项人格利益（姓名、肖像、飨、荣誉、隐私、遗体和遗骨）": "死者的7项人格利益（姓名、肖像、名誉、荣誉、隐私、遗体和遗骨）",
        "和也金公去\n利益": "和社会公共利益",
        "和也金公去 |\n| | 利益": "和社会公共利益 |",
        "和也金公去": "和社会公共利益",
        "《民法典像权责任编解释（一）》递10条": "《民法典侵权责任编解释（一）》第10条",
        "8W 人 \\<18": "8≤人<18",
        "8W 人 <18": "8≤人<18",
        "人\\<8": "人<8",
        "人N18": "人≥18",
        "即不可以解底市■而者对使用条件亦无讨价还价之余地醒彘面冠这些企业订立合同": "即不可以拒绝订约，而消费者对使用条件亦无讨价还价之余地，只能与这些企业订立合同",
        "即不可以解底市而者对使用条件亦无讨价还价之余地醒彘面冠这些企业订立合同": "即不可以拒绝订约，而消费者对使用条件亦无讨价还价之余地，只能与这些企业订立合同",
        "造成用电人函疏「应当承担赔偿责任": "造成用电人损失的，应当承担赔偿责任",
        "供电人未按照国家规定的供电质量标准和约定安全供电，造成用电人损失的，应当承担赔偿责任「S3X亩确裴\n薪百函%俞祕:5胸萩羸无瓦施薪亩「^?面供电时": "供电人未按照国家规定的供电质量标准和约定安全供电，造成用电人损失的，应当承担赔偿责任。供电人因计划检修、临时检修等原因需要中断供电时",
        "用电人应当按照国家有关规定和当函痴定£5:^5^s^^57^51^?i百家有关\n规定和当事人的约定围曳，造成供电人损失的，应当承担赔偿责任": "用电人应当按照国家有关规定和当事人的约定安全用电。用电人未按照国家有关规定和当事人的约定安全用电，造成供电人损失的，应当承担赔偿责任",
        "或者接 **^SXS^7^?5S^ik**。": "或者接受相对人履行的，视为对合同的追认。",
        "无须经保证人书面同^SZ\\*^W\\*»Z%<\\*WWWZ\\\\ZS^W>»\\*WWVW%\\*W\"»\\*ZSZS^ZW<%X»ZX\n\n意。": "无须经保证人书面同意。",
        "到捷楚费": "支付电费",
        "「萌主点拨1": "【萌主点拨】",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    text = text.replace("\\<", "<").replace("\\>", ">").replace("\\.", ".").replace("\\^", "^")
    text = re.sub(
        r"即不可以解.{0,4}?而者对使用条件亦无讨价还价之余地.{0,8}?这些企业订立合同",
        "即不可以拒绝订约，而消费者对使用条件亦无讨价还价之余地，只能与这些企业订立合同",
        text,
    )
    text = re.sub(
        r"供电人未按照国家规定的供电质量标准和约定安全供电，造成用电人损失的，应当承担赔偿责任[^。\n]{0,80}?面供电时",
        "供电人未按照国家规定的供电质量标准和约定安全供电，造成用电人损失的，应当承担赔偿责任。供电人因计划检修、临时检修等原因需要中断供电时",
        text,
    )
    text = re.sub(
        r"用电人应当按照国家有关规定和当[^。\n]{0,80}?百家有关\n规定和当事人的约定[^，。\n]{0,10}，造成供电人损失的，应当承担赔偿责任",
        "用电人应当按照国家有关规定和当事人的约定安全用电。用电人未按照国家有关规定和当事人的约定安全用电，造成供电人损失的，应当承担赔偿责任",
        text,
    )
    text = re.sub(r"或者接\s*\*\*[^\n]{6,40}?\*\*。", "或者接受相对人履行的，视为对合同的追认。", text)
    text = re.sub(r"无须经保证人书面同[^\n]*\n\s*\n\s*意。", "无须经保证人书面同意。", text)
    text = re.sub(
        r"债权人和债务人协商缩短主债权期限的，减轻了保证人的责任，无须经保证人书面同[\s\S]{0,180}?意。保证人仍对变更后的债务承担保证责任。",
        "债权人和债务人协商缩短主债权期限的，减轻了保证人的责任，无须经保证人书面同意。保证人仍对变更后的债务承担保证责任。",
        text,
    )
    text = re.sub(r"[¥■□▲¬]+", "", text)
    text = re.sub(r"[\^~»«•'\*_<>/\\]{8,}", "", text)
    text = re.sub(r"(?<=[一-鿿])[A-Za-z0-9¥\^~»«•'\*_<>/\\]{7,}(?=[一-鿿，。；、）])", "", text)
    text = re.sub(r"(?<=[一-鿿，。；、）])\s*[A-Za-z0-9¥£%\^~»«•'\*_<>/\\]{10,}\s*$", "", text, flags=re.M)
    text = re.sub(r"(?<=[一-鿿，。；、）])\s*[A-Za-z0-9¥£%\^~»«•'\*_<>/\\]{10,}(?=\s*[\n。；，])", "", text)
    text = re.sub(r"\*\*[A-Za-z0-9¥£%\^~»«•'\*_<>/\\]{6,}\*\*", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def is_pipe_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def is_pipe_separator_line(line: str) -> bool:
    s = line.strip()
    if not is_pipe_table_line(s):
        return False
    cells = [c.strip() for c in s.strip("|").split("|")]
    return bool(cells) and any("-" in c for c in cells) and all(not c or re.fullmatch(r":?-{3,}:?", c) for c in cells)


def is_empty_pipe_row(line: str) -> bool:
    s = line.strip()
    if not is_pipe_table_line(s):
        return False
    return all(not c.strip() for c in s.strip("|").split("|"))


def split_table_cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def make_table_row(cells: list[str], cols: int) -> str:
    fixed = cells[:cols] + [""] * max(0, cols - len(cells))
    return "| " + " | ".join(fixed) + " |"


def table_separator_for(row: str) -> str:
    cols = max(1, len(split_table_cells(row)))
    return "| " + " | ".join(["---"] * cols) + " |"


def normalize_markdown_tables(text: str) -> str:
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if not is_pipe_table_line(lines[i]):
            out.append(lines[i])
            i += 1
            continue

        block = []
        while i < len(lines) and is_pipe_table_line(lines[i]):
            block.append(lines[i])
            i += 1

        content_rows = [line for line in block if not is_pipe_separator_line(line) and not is_empty_pipe_row(line)]
        if content_rows:
            rows = [split_table_cells(row) for row in content_rows]
            cols = max(len(row) for row in rows)
            normalized = [make_table_row(row, cols) for row in rows]
            out.append(normalized[0])
            out.append("| " + " | ".join(["---"] * cols) + " |")
            out.extend(normalized[1:])
        else:
            out.extend(block)
    return "\n".join(out)


def remove_ocr_noise_lines(text: str) -> str:
    out = []
    topic_residue = re.compile(
        r"[oO0-9A-Za-zQJqj\*/\\\s\.\?\^~¥■□▲¬|丨Il—－-]*题[一二三四五六七八九十百零〇\d|丨Il—－-]+[oO0-9A-Za-zQJqj\*/\\\s\.\?\^~¥■□▲¬|丨Il—－-]*"
    )
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            out.append(line)
            continue
        if topic_residue.fullmatch(s):
            continue
        if len(s) <= 30 and re.search(r"题[一二三四五六七八九十百零〇\d]+[|丨Il—－-]", s):
            continue
        if s in {"兆", "/"}:
            continue
        if len(s) <= 3 and re.fullmatch(r"[/\\\^~*¥■□▲¬]+", s):
            continue
        if len(s) <= 20 and re.fullmatch(r"[A-Za-z0-9¥£%\^~»«•'\*_<>/\\\s-]+", s) and re.search(r"[\^~»«¥£%\*_<>/\\]", s):
            continue
        if len(s) >= 8 and not re.search(r"[一-鿿]", s):
            symbol_count = sum(1 for ch in s if not ch.isalnum() and not ch.isspace())
            if symbol_count / len(s) > 0.45:
                continue
        out.append(line)
    return "\n".join(out)


def extract_body(raw: str) -> str:
    lines = raw.split("\n")
    for i in range(450, len(lines)):
        s = lines[i].strip()
        if s == "第一部分":
            for j in range(i + 1, min(i + 8, len(lines))):
                if lines[j].strip() == "总则编":
                    return "\n".join(lines[i:])
        if "第一部分总则编" in s:
            return "\n".join(lines[i:])
    return raw


def is_topic_line(s: str) -> int | None:
    if "专题" not in s and "法律关系的基本原理" not in s:
        return None
    compact = re.sub(r"\s+", "", s)
    if "法律关系的基本原理" in compact and "专题" not in compact and len(compact) < 40:
        return 1
    m = re.search(r"专题\s*([一二三四五六七八九十百零〇\|丨Il\-—－]+)", s)
    if not m:
        return None
    num = cn_to_int(m.group(1))
    if num is None or num not in TOPIC_TITLES:
        return None
    if len(s) > 90 and not re.match(r"^\s*[\/\\0-9A-Za-zqQ：:「JvV\s]*专题", s):
        return None
    return num


def normalize_section_title(s: str) -> str | None:
    m = re.match(r"^第([一二三四五六七八九十百零〇\d]+)节\s*(.+?)\s*$", s)
    if not m:
        return None
    title = m.group(2).strip()
    title = re.sub(r"\s*[/／]\s*[A-Za-zH\d]+\s*$", "", title)
    title = re.sub(r"\s*\d+\s*$", "", title)
    title = title.strip(" /／")
    if not title or len(title) > 50:
        return None
    return f"第{m.group(1)}节 {title}"


def rebuild_headings(text: str) -> str:
    lines = text.split("\n")
    out = []
    skip_next_part_name = None

    for line in lines:
        s = line.strip()
        if not s:
            out.append(line)
            continue

        if skip_next_part_name and re.sub(r"\s+", "", s).strip("：:") == skip_next_part_name:
            skip_next_part_name = None
            continue
        skip_next_part_name = None

        compact = re.sub(r"\s+", "", s)

        m = re.search(r"第([一二三四五六七八])部分", compact)
        if m and len(compact) < 30 and "备考方法论" not in compact and "体系化认知" not in compact:
            num = cn_to_int(m.group(1))
            if num in PART_TITLES:
                out.append("")
                out.append(f"## 第{m.group(1)}部分 {PART_TITLES[num]}")
                out.append("")
                if compact == f"第{m.group(1)}部分":
                    skip_next_part_name = PART_TITLES[num]
                continue

        topic_num = is_topic_line(s)
        if topic_num:
            out.append("")
            out.append(f"### 专题{int_to_cn(topic_num)} {TOPIC_TITLES[topic_num]}")
            out.append("")
            continue

        section = normalize_section_title(s)
        if section:
            out.append("")
            out.append(f"#### {section}")
            out.append("")
            continue

        m = re.match(r"^([一二三四五六七八九十]+)、\s*(.+?)$", s)
        if m and len(s) < 70 and not re.search(r"[，。；]", m.group(2)):
            title = m.group(2).strip()
            title = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]+$", "", title).strip()
            out.append("")
            out.append(f"##### {m.group(1)}、{title}")
            out.append("")
            continue

        out.append(line)

    return "\n".join(out)


def has_recent_topic_heading(lines: list[str]) -> bool:
    seen = 0
    for line in reversed(lines):
        s = line.strip()
        if not s:
            continue
        seen += 1
        if re.match(r"^###\s+专题[一二三四五六七八九十]+\s+", s):
            return True
        if seen >= 3:
            return False
    return False


def remove_topic_title_noise(lines: list[str]) -> None:
    while lines and not lines[-1].strip():
        lines.pop()
    removed = 0
    while lines and removed < 3:
        s = lines[-1].strip()
        if not s or s.startswith(("#", ">", "|")):
            break
        if len(s) > 45 or re.search(r"[。；：:]|答案|答：|《|》", s):
            break
        lines.pop()
        removed += 1
    lines.append("")


def add_missing_topic_headings(text: str) -> str:
    lines = text.split("\n")
    out = []
    current_topic = 0

    for i, line in enumerate(lines):
        s = line.strip()
        m = re.match(r"^###\s+专题([一二三四五六七八九十]+)\s+", s)
        if m:
            num = cn_to_int(m.group(1))
            if num:
                current_topic = num
            out.append(line)
            continue

        if s.rstrip("：:") == "复习提要" and not has_recent_topic_heading(out):
            lookahead = "".join(x.strip() for x in lines[i + 1:i + 5])
            if "本专题" in lookahead:
                next_topic = current_topic + 1
                if next_topic in TOPIC_TITLES:
                    remove_topic_title_noise(out)
                    out.append(f"### 专题{int_to_cn(next_topic)} {TOPIC_TITLES[next_topic]}")
                    out.append("")
                    current_topic = next_topic

        out.append(line)

    return "\n".join(out)


def add_missing_part_headings(text: str) -> str:
    lines = text.split("\n")
    out = []
    current_part = None

    for line in lines:
        s = line.strip()
        m = re.match(r"^##\s+(第[一二三四五六七八]部分\s+.+)$", s)
        if m:
            current_part = re.sub(r"\s+", "", m.group(1))
            out.append(line)
            continue

        compact = re.sub(r"\s+", "", s)
        if compact.startswith("婚姻家庭编（第1040") and current_part != "第六部分婚姻家庭编":
            out.append("")
            out.append("## 第六部分 婚姻家庭编")
            out.append("")
            current_part = "第六部分婚姻家庭编"
        elif compact.startswith("继承编（第1119") and current_part != "第七部分继承编":
            out.append("")
            out.append("## 第七部分 继承编")
            out.append("")
            current_part = "第七部分继承编"

        out.append(line)

    return "\n".join(out)


def int_to_cn(n: int) -> str:
    if n <= 10:
        return "十" if n == 10 else "一二三四五六七八九"[n - 1]
    tens, ones = divmod(n, 10)
    left = "" if tens == 1 else "一二三四五六七八九"[tens - 1]
    if ones == 0:
        return left + "十"
    return left + "十" + "一二三四五六七八九"[ones - 1]


def convert_pandoc_tables(text: str) -> str:
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*\+[-:=+]+", line):
            block = []
            j = i
            while j < len(lines) and (re.match(r"^\s*[+|]", lines[j]) or lines[j].strip() == ""):
                if lines[j].strip() == "" and j + 1 < len(lines) and not re.match(r"^\s*[+|]", lines[j + 1]):
                    break
                block.append(lines[j])
                j += 1
            md_table = parse_pandoc_table(block)
            if md_table:
                out.append("")
                out.append(md_table)
                out.append("")
            else:
                out.extend(block)
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def parse_pandoc_table(block: list[str]) -> str | None:
    rows = []
    for ln in block:
        if re.match(r"^\s*\+[-:=+]+", ln) or not ln.strip():
            continue
        parts = [p.strip() for p in ln.strip().strip("|").split("|")]
        if any(parts):
            rows.append(parts)
    if not rows:
        return None
    ncol = max(len(r) for r in rows)
    if ncol < 2:
        return None
    norm_rows = []
    for row in rows:
        row = row + [""] * (ncol - len(row))
        norm_rows.append([re.sub(r"\*\*", "", c).replace("\n", "<br>") for c in row])
    md = ["| " + " | ".join(norm_rows[0]) + " |", "| " + " | ".join(["---"] * ncol) + " |"]
    for row in norm_rows[1:]:
        md.append("| " + " | ".join(row) + " |")
    return "\n".join(md)


def normalize_footnotes(text: str) -> str:
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]", s) and len(s) > 8:
            out.append("> " + s)
        else:
            out.append(line)
    return "\n".join(out)


def merge_paragraphs(text: str) -> str:
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if (
            cur.strip()
            and i + 1 < len(lines)
            and lines[i + 1].strip()
            and not cur.startswith("#")
            and not cur.startswith("-")
            and not cur.startswith(">")
            and not cur.startswith("|")
            and not cur.startswith("```")
            and not NO_MERGE_START.match(lines[i + 1])
        ):
            last = cur.rstrip()
            if last and last[-1] not in END_PUNCT and last[-1] not in ".!?":
                out.append(cur.rstrip() + lines[i + 1].lstrip())
                i += 2
                continue
        out.append(cur)
        i += 1
    return "\n".join(out)


def normalize_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    body = extract_body(raw)

    body = remove_pandoc_artifacts(body)
    body = fix_quotes(body)
    body = remove_meaningless_bold(body)
    body = remove_junk_lines(body)
    body = normalize_common_typos(body)
    body = normalize_year_refs(body)
    body = normalize_markers(body)
    body = normalize_malformed_markers(body)
    body = normalize_ocr_artifacts(body)
    body = convert_pandoc_tables(body)
    body = rebuild_headings(body)
    body = add_missing_topic_headings(body)
    body = add_missing_part_headings(body)
    body = normalize_footnotes(body)
    body = merge_paragraphs(body)
    body = normalize_ocr_artifacts(body)
    body = remove_ocr_noise_lines(body)
    body = normalize_markdown_tables(body)
    body = normalize_blank_lines(body)

    out = (
        f"# {BOOK_TITLE}\n\n"
        "> 整理说明：本文件根据 OCR 扫描原稿《孟献贵〈民法〉》批量清洗，统一专题/节标题层级、清理 OCR 噪音与 pandoc 残留，供切块入库与法考问答系统使用。\n\n"
        "---\n\n"
        f"{body}"
    )
    DST.write_text(out, encoding="utf-8")

    topic_count = len(re.findall(r"^### 专题", out, flags=re.M))
    part_count = len(re.findall(r"^## 第[一二三四五六七八]部分", out, flags=re.M))
    section_count = len(re.findall(r"^#### 第", out, flags=re.M))
    subsection_count = len(re.findall(r"^##### [一二三四五六七八九十]+、", out, flags=re.M))
    print(f"输出：{DST}")
    print(f"字符数：{len(out)}")
    print(f"行数：{len(out.splitlines())}")
    print(f"部分标题：{part_count}")
    print(f"专题标题：{topic_count}")
    print(f"节标题：{section_count}")
    print(f"小标题：{subsection_count}")


if __name__ == "__main__":
    main()
