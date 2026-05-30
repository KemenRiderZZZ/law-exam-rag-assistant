#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""戴鹏《民诉》OCR 清洗脚本。"""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "OCR原稿" / "戴鹏《民诉》.md"
DST = PROJECT_ROOT / "整理后文本" / "戴鹏民诉_整理版.md"

BOOK_TITLE = "戴鹏民事诉讼法专题讲座精讲卷（2026版）"

SMALL_TOPIC_TITLES = [
    "民法中的形成权与民事诉讼中的形成之诉（实体法融合考点）",
    "劳动纠纷的调解与仲裁",
    "一些特殊的主管与管辖问题",
    "实体法的规定与当事人适格",
    "证券纠纷特别代表人诉讼（与《证券法》融合考查）",
    "《民法典》相关司法解释中关于证明责任的规定（与民法融合考查）",
    "证明的逻辑",
    "鉴定人、有专门知识的人、司法技术人员",
    "撤诉在实体法上的效果（与民法的融合考查）",
    "判决的效力——执行力、形成力、既判力",
    "确认婚姻效力案件的程序问题（与民法的融合考查）",
    "《民法典》中关于遗产管理人的相关规定（与民法融合考查）",
    "案外人救济制度",
    "仲裁协议与代位权诉讼、股东代表诉讼",
]

TOPIC_TITLES = {
    1: "民事诉讼与民事诉讼法",
    2: "诉的基本理论",
    3: "基本原则与基本制度",
    4: "主管与管辖",
    5: "当事人",
    6: "共同诉讼",
    7: "第三人",
    8: "诉讼代理人",
    9: "证明",
    10: "证据",
    11: "证明程序",
    12: "保全与先予执行",
    13: "对妨碍诉讼的强制措施",
    14: "期间与送达",
    15: "调解",
    16: "一审普通程序",
    17: "简易程序",
    18: "公益诉讼程序",
    19: "第三人撤销之诉",
    20: "二审程序",
    21: "审判监督程序",
    22: "特别程序",
    23: "非讼程序之督促程序",
    24: "非讼程序之公示催告程序",
    25: "执行程序",
    26: "涉外民事诉讼程序",
    27: "仲裁概述",
    28: "仲裁协议",
    29: "仲裁程序",
    30: "司法与仲裁",
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

NO_MERGE_START = re.compile(
    r"^\s*("
    r"#{1,6}\s+|"
    r"【|"
    r">|"
    r"\||"
    r"[-*]\s+|"
    r"\d+[\.．、]|"
    r"[（(][\d一二三四五六七八九十]+[)）]|"
    r"[一二三四五六七八九十]+、|"
    r"[①②③④⑤⑥⑦⑧⑨⑩]|"
    r"第[一二三四五六七八九十百零〇\d]+节"
    r")"
)

END_PUNCT = "。！？；：,，、）)]\"'》】"


def int_to_cn(n: int) -> str:
    if n <= 10:
        return "十" if n == 10 else "一二三四五六七八九"[n - 1]
    tens, ones = divmod(n, 10)
    left = "" if tens == 1 else "一二三四五六七八九"[tens - 1]
    if ones == 0:
        return left + "十"
    return left + "十" + "一二三四五六七八九"[ones - 1]


def cn_to_int(s: str) -> int | None:
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    s = (
        s.replace("丨", "十")
        .replace("|", "十")
        .replace("+", "十")
        .replace("■", "一")
        .replace("I", "一")
        .replace("l", "一")
        .replace("－", "")
        .replace("-", "")
        .replace("—", "")
        .replace("◎", "")
        .replace("©", "")
        .replace("/", "")
        .replace("_", "")
        .replace(" ", "")
    )
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


def normalize_text(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2009": " ",
        "\u3000": " ",
        "\ufeff": "",
        "［": "[",
        "］": "]",
        "“": "\"",
        "”": "\"",
        "‘": "'",
        "’": "'",
        "—-": "——",
        "--": "——",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return text


def extract_body(text: str) -> list[str]:
    lines = text.splitlines()
    start = None
    for i in range(200, len(lines)):
        if is_knowledge_system(lines[i].strip()):
            start = i
            break
    if start is None:
        start = 0
    return lines[start:]


def extract_outline(text: str) -> list[dict[str, str | int]]:
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if is_knowledge_system(line.strip()):
            body_start = i
            break

    outline: list[dict[str, str | int]] = []
    topic_idx = 0
    in_toc = False

    for raw in lines[:body_start]:
        s = clean_toc_line(raw)
        if not s:
            continue
        if "专题一" in s:
            in_toc = True
        if not in_toc:
            continue

        if re.match(r"^专题", s):
            topic_idx += 1
            if topic_idx in TOPIC_TITLES:
                outline.append({"kind": "topic", "num": topic_idx, "title": TOPIC_TITLES[topic_idx]})
            continue

        m_small = re.match(r"^[【\[\［]小专题[】\]\］]\s*(.+)$", s)
        if m_small:
            outline.append({"kind": "small_topic", "title": m_small.group(1).strip()})
            continue

        m_section = re.match(r"^第([一二三四五六七八九十百零〇\d]+)节\s*(.+)$", s)
        if m_section:
            outline.append(
                {
                    "kind": "section",
                    "num": m_section.group(1),
                    "title": m_section.group(2).strip(),
                }
            )

    return outline


def clean_line(line: str) -> str:
    line = line.rstrip()
    line = re.sub(r"\[([^\]]+)\]\(#bookmark\d+[^)]*\)", r"\1", line)
    line = re.sub(r"\*+\s*/\s*\d+\s*\*+", "", line)
    line = line.replace("{.underline}", "")
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip()


def clean_toc_line(line: str) -> str:
    line = clean_line(line)
    line = re.sub(r"^[\[\(]+", "", line)
    line = re.sub(r"[\]\)]+$", "", line)
    line = re.sub(r"\s*/\s*\d+\s*$", "", line)
    line = re.sub(r"\*+", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_knowledge_system(s: str) -> bool:
    compact = re.sub(r"\s+", "", s)
    compact = compact.replace("I", "").replace("力", "").replace("讨", "")
    return "知识体系" in compact


def is_noise_line(s: str) -> bool:
    if not s:
        return False
    exact = {
        "目录",
        "Contents",
        "Preface",
        "序百",
        "Dai Peng",
        "戴鹏",
        "＜编著＞",
        "精 讲",
        "卷",
        "民事诉讼法 专题讲座",
        "考点精讲",
        "国",
        "画",
        "®",
        "»",
        "«",
        "◎",
        "■",
    }
    if s in exact:
        return True
    if "石化出版社" in s or "CIP" in s or "精讲卷" in s or "CHINA ECONOMIC PUBLISHING HOUSE" in s:
        return True
    if "纸质书购买" in s or "解密VX" in s or "一手更新整理法考资料" in s:
        return True
    if re.fullmatch(r"[*_/\\\-~^]+", s):
        return True
    if re.fullmatch(r"[0-9 ]+", s):
        return True
    if len(s) <= 12 and re.fullmatch(r"[A-Za-z0-9_/\-+|■◎© ]+", s):
        return True
    if len(s) <= 24 and re.fullmatch(r"[A-Za-z0-9_/\-+|■◎© .]+", s):
        return True
    if len(s) <= 20 and not re.search(r"[一-鿿]", s) and re.search(r"[@^¥©®«»]", s):
        return True
    if len(s) >= 8 and not re.search(r"[一-鿿]", s):
        symbol_count = sum(1 for ch in s if not ch.isalnum() and not ch.isspace())
        if symbol_count / len(s) > 0.35:
            return True
    return False


def normalize_marker(s: str) -> str | None:
    if not s:
        return None
    if is_knowledge_system(s):
        return "【知识体系】"
    if "考点精讲" in s:
        return "【考点精讲】"
    if "原理与逻辑" in s:
        return "【原理与逻辑】"
    if "总结与归纳" in s:
        return "【总结与归纳】"
    marker_map = {
        "分析与思路": "分析与思路",
        "分析": "分析",
        "结论": "结论",
        "注意": "注意",
        "命题思路与常见错误分析": "命题思路与常见错误分析",
        "常见错误": "常见错误",
        "萌主点拨": "萌主点拨",
    }
    for raw, target in marker_map.items():
        if raw in s and len(s) <= 40:
            return f"【{target}】"
    m = re.match(r"^\[?例\s*\**(\d+|[A-Z])\**\]?", s)
    if m:
        return f"【例{m.group(1)}】"
    return None


def normalize_match_text(s: str) -> str:
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("——", "").replace("—", "")
    s = s.replace("之——", "之").replace("之—一", "之").replace("之一", "之")
    s = s.replace("主 管", "主管").replace("期 间", "期间").replace("送 达", "送达")
    s = s.replace("事人", "当事人") if s in {"事人", "专题五事人"} else s
    s = s.replace("巾裁", "仲裁").replace("寺别", "特别")
    s = s.replace("审程序", "二审程序") if s == "审程序" else s
    s = re.sub(r"专题[一二三四五六七八九十百零〇\d+|■Iil/◎©_-]+", "", s)
    s = re.sub(r"[【】\[\]［］()（）<>《》“”\"'`*_#|/\\\-+◎©■®.]", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def is_small_topic_marker(s: str) -> bool:
    compact = normalize_match_text(s)
    return compact == "小专题"


def lines_look_similar(line: str, title: str) -> bool:
    left = normalize_match_text(line)
    right = normalize_match_text(title)
    if not left or not right:
        return False
    return left == right or right.endswith(left) or left.endswith(right)


def match_topic_line(s: str, entry: dict[str, str | int]) -> bool:
    topic_num = entry["num"]
    if detect_topic_number(s) == topic_num:
        return True
    compact = normalize_match_text(s)
    title = normalize_match_text(str(entry["title"]))
    if compact and len(compact) <= 18 and compact == title:
        return True
    return False


def match_section_line(s: str, entry: dict[str, str | int]) -> bool:
    compact = re.sub(r"\s+", "", s)
    m = re.match(r"^第([一二三四五六七八九十百零〇\d]+)节(.+)$", compact)
    if not m:
        return False
    if m.group(1) != entry["num"]:
        return False
    return lines_look_similar(m.group(2), str(entry["title"]))


def match_small_topic_line(s: str, entry: dict[str, str | int]) -> bool:
    if is_small_topic_marker(s):
        return False
    return lines_look_similar(s, str(entry["title"]))


def normalize_inline_typos(text: str) -> str:
    replacements = {
        "丕县直型地行力": "不具有强制执行力",
        "丕县直型地 行力": "不具有强制执行力",
        "丕迄用": "不适用",
        "史提出反诉": "中提出反诉",
        "二审史提出反诉": "二审中提出反诉",
        "支村本金": "支付本金",
        "避专题原告": "特殊情况下的原告",
        "拖见": "拖欠",
        "不迄用": "不适用",
        "到决例外": "判决书例外",
        "诉冷学年": "诉讼案件",
        "调解协议仅有合同为束力": "调解协议仅有合同约束力",
        "民惠秀玲迭适用的主体": "民事诉讼法适用的主体",
        "氐惠褰使咨律差系": "民事实体法律关系",
        "诉论请求": "诉讼请求",
        "公益诉论": "公益诉讼",
        "公盘诉讼": "公益诉讼",
        "诉衿逑序": "诉讼程序",
        "并人再审程序": "并入再审程序",
        "再申程序": "再审程序",
        "诉论维护": "诉讼维护",
        "撤错之诉": "撤销之诉",
        "撤箱": "撤销",
        "命强思路与常见错误分析": "命题思路与常见错误分析",
        "法院菅落": "法院管辖",
        "法院慈第三人诉讼请求并入再审程序": "法院将第三人诉讼请求并入再审程序",
        "再重的对象:": "再审的对象：",
        "再重的对象：": "再审的对象：",
        "磬定不予受理": "裁定不予受理",
        "法院启动再审一调解书确有错误。": "法院启动再审——调解书确有错误。",
        "当事人申请再审^_■调解书违反自愿、合法原则。": "当事人申请再审——调解书违反自愿、合法原则。",
        "JS丽瓦施二\"": "基础而已。",
        "电画仲裁协议": "书面仲裁协议",
        "受理申靖": "受理申请",
        "再审申清": "再审申请",
        "申靖": "申请",
        "申清": "申请",
        "法津规定": "法律规定",
        "取责": "职责",
        "平筝地位": "平等地位",
        "涉处民事诉讼": "涉外民事诉讼",
        "巾裁协议": "仲裁协议",
        "寺别程序": "特别程序",
        "@^理写至葡一": "",
        "i¥557~": "",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    text = re.sub(r"第([一二三四五六七八九十]+)节\s*([一-鿿])\s+([一-鿿])", r"第\1节 \2\3", text)
    text = re.sub(r"【例([0-9A-Z])】\s*", r"【例\1】", text)
    text = re.sub(r"\*\*([0-9]+)\s*\*\*\s*\*\*\.", r"\1.", text)
    text = re.sub(r"\*\*([0-9]+)\*\*\s*\.\s*", r"\1. ", text)
    text = re.sub(r"\*\*([0-9]+)\*\*", r"\1", text)
    text = re.sub(r"\*\*([A-Z])\*\*", r"\1", text)
    text = re.sub(r"\[\s*注意\s*\*\*[A-Z]+\s*\*\*\s*\]", "【注意】", text)
    text = re.sub(r"\[\s*注意\s*\]", "【注意】", text)
    text = re.sub(r"\[\s*例\s*\*\*([0-9A-Z])\s*\*\*\s*\]", r"【例\1】", text)
    text = re.sub(r"\s+([，。；：])", r"\1", text)
    text = re.sub(r"([（(])\s+", r"\1", text)
    text = re.sub(r"\s+([）)])", r"\1", text)
    text = re.sub(r"(?m)^(\d+)\.\*\*(.+)$", r"\1. \2", text)
    text = re.sub(r"(?m)^\*\*(\d+)\*\*\s*[\.．、]\s*", r"\1. ", text)
    text = re.sub(r"(?m)^(\d+)\.\s*\*\*(.+)$", r"\1. \2", text)
    text = re.sub(r"(?m)^([A-Z])\.\*\*(.+)$", r"\1. \2", text)
    text = text.replace("**", "")
    text = re.sub(r"(?m)^.*亟偏题备凰[-—]*\s*$", "【命题角度】", text)
    text = re.sub(r"(?m)^.*0意结与归纳:J\.\s*", "【总结与归纳】", text)
    text = re.sub(r"(?m)^.*电厩写睛[-—\s\.\u2026]*", "【原理与逻辑】\n", text)
    text = re.sub(r"(?m)^.*Iff葡示例[:：]\s*", "【真题示例】\n\n", text)
    text = re.sub(r"(?m)^.*gj命题标｝.*$", "【命题角度】", text)
    text = re.sub(r"(?m)^.*AjS\*>S\^S.*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def postprocess_output(text: str) -> str:
    for title in SMALL_TOPIC_TITLES:
        text = re.sub(
            rf"(?m)^(?!#### 小专题 ){re.escape(title)}$",
            f"#### 小专题 {title}",
            text,
        )
        text = re.sub(
            rf"(?m)^(?!#### 小专题 )({re.escape(title)})(?=[一二三四五六七八九十0-9A-Z（(【])",
            rf"#### 小专题 \1\n",
            text,
        )

    noise_patterns = [
        r"(?m)^0\^\^缶基本理论$",
        r"(?m)^专题五事人$",
        r"(?m)^_1_\s*1/\s*-审普通程序$",
        r"(?m)^0 A/专题二十六NCA涉外民事诉讼程序$",
        r"(?m)^/ O/_专题二十九_仲裁程序$",
        r"(?m)^094\^$",
        r"(?m)^7 Q/w题十九Y 第三人撤销之诉$",
        r"(?m)^7 7%题十七J /简易程序$",
        r"(?m)^0 题二十三N J非讼程序之——督促程序$",
        r"(?m)^o r/\^题二十七 _乙_仲裁概述$",
        r"(?m)^真题示例）$",
        r"(?m)^e也命题角圜.*$",
        r"(?m)^累8命题错蔗】.*$",
        r"(?m)^■深度拓展、，$",
        r"(?m)^命题角度】.*$",
        r"(?m)^[A-Za-z0-9^■□※* ]*命题角度】.*$",
        r"(?m)^噩＞颠角:度:.*$",
        r"(?m)^国原理写逻辑】.*$",
        r"(?m)^国度度画展J.*$",
        r"(?m)^用原理写逻程;.*$",
        r"(?m)^用原理与度辑】$",
        r"(?m)^HJ原理与瘦辑:.*$",
        r"(?m)^E原理与逻编.*$",
        r"(?m)^总原理写逻僦一.*$",
        r"(?m)^tn真题前n.*$",
        r"(?m)^血直蒜雨.*$",
        r"(?m)^AjS\*>S\^S.*$",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text)

    text = re.sub(
        r"(?m)^(?!\|)\s*[^\n|]{0,16}命题[^\n|]{0,4}角[^\n|]{0,4}[度圜圆鱼赖鳞】:]?\s*[—\-\.。…:：]*\s*",
        "【命题角度】\n\n",
        text,
    )
    text = re.sub(
        r"(?m)^(?!\|)\s*[^\n|]{0,16}原理[^\n|]{0,4}逻[^\n|]{0,4}[辑福编鹿阊度】:]?\s*[—\-\.。…:：]*\s*",
        "【原理与逻辑】\n\n",
        text,
    )
    text = re.sub(
        r"(?m)^(?!\|)\s*[^\n|]{0,16}总结[^\n|]{0,4}归[^\n|]{0,4}[纳缅绷】:]?\s*[—\-\.。…:：]*\s*",
        "【总结与归纳】\n\n",
        text,
    )
    text = re.sub(
        r"(?m)^(?!\|)\s*[^\n|]{0,16}真题[^\n|]{0,6}示例[^\n|]{0,4}[】:]?\s*",
        "【真题示例】\n\n",
        text,
    )
    text = text.replace("室命题角度】", "【命题角度】")
    text = text.replace("m值命题角度】", "【命题角度】")
    text = text.replace("E8命题版】", "【命题角度】")
    text = text.replace("图命题角圉", "【命题角度】")
    text = text.replace("jfl前越角度】", "【命题角度】")
    text = text.replace("ffl真题示施", "【真题示例】")
    text = text.replace("瓜真题宗函", "【真题示例】")
    text = text.replace("盯真画示例】", "【真题示例】")
    text = text.replace("【Q真题亲切", "【真题示例】")
    text = text.replace("G1.真 mn", "【真题示例】")
    text = text.replace("Hi真题示例I", "【真题示例】")
    text = text.replace("| 画睡睡噩I |  |", "| 文书类型 | 说明 |")
    text = text.replace("|画睡睡噩I|   |", "| 文书类型 | 说明 |")
    text = text.replace("【分析与思路j", "【分析与思路】")
    text = text.replace("【分析与思路】本题考查第三人撤销之诉", "【分析与思路】本题考查第三人撤销之诉")
    text = text.replace("故此时法院慈第三人诉讼请求并入再审程序", "故此时法院将第三人诉讼请求并入再审程序")
    text = text.replace("和第三人撤销之诉虽然是为了纠错", "再审和第三人撤销之诉虽然是为了纠错")
    text = text.replace("| 当事人申 请检察建 议或抗诉 |", "| 当事人申请检察建议或抗诉 |")
    text = re.sub(r"\| 上诉与二审 \|([^|\n]*)<br><br>AjS\*>S\^S[^<]*<br><br>", r"| 上诉与二审 |\1<br><br>", text)
    text = text.replace("（-,）起诉主体", "（一）起诉主体")
    text = text.replace("依法履行取责", "依法履行职责")
    text = text.replace("其取责有二", "其职责有二")
    text = text.replace("平筝地位", "平等地位")
    text = text.replace("法院慈第三人 诉讼请求并入再审程序", "法院将第三人诉讼请求并入再审程序")
    text = text.replace("法院慈第三人诉讼请求并入再审程序", "法院将第三人诉讼请求并入再审程序")
    text = text.replace("涉处民事诉讼的一些原则", "涉外民事诉讼的一些原则")

    text = text.replace("专题五 事人", "专题五 当事人")
    text = text.replace("专题二十四 非讼程序之—一公示催告程序", "专题二十四 非讼程序之公示催告程序")
    text = text.replace("专题二十三 非讼程序之——督促程序", "专题二十三 非讼程序之督促程序")
    text = text.replace("专题十六 _1_ 1/ -审普通程序", "专题十六 一审普通程序")
    text = text.replace("专题二十八 巾裁协议", "专题二十八 仲裁协议")
    text = text.replace("专题二十二特别程序", "### 专题二十二 特别程序")
    text = text.replace("专题二十四非讼程序之—一公示催告程序", "### 专题二十四 非讼程序之公示催告程序")
    text = text.replace("专题二十五执行程序", "### 专题二十五 执行程序")
    text = text.replace("专题二十八仲裁协议", "### 专题二十八 仲裁协议")
    text = text.replace("专题二十七仲裁概述", "### 专题二十七 仲裁概述")
    text = text.replace("专题二十六涉外民事诉讼程序", "### 专题二十六 涉外民事诉讼程序")
    text = text.replace("专题三十司法与仲裁", "### 专题三十 司法与仲裁")
    text = text.replace("专题二十九 仲裁程序", "### 专题二十九 仲裁程序")
    text = text.replace("专题十八公益诉讼程序", "### 专题十八 公益诉讼程序")
    text = text.replace("专题二+/I/二审程序", "### 专题二十 二审程序")
    text = text.replace("Y 第三人撤销之诉", "### 专题十九 第三人撤销之诉")
    text = re.sub(
        r"(?m)^(\| 起诉主体 \| 法律规定的机关和有关组织 \|)$",
        "### 专题十八 公益诉讼程序\n\n【知识体系】\n\n\\1",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^### 专题十八 公益诉讼程序\s*\n\s*【知识体系】\s*\n\s*\| 概念 \| ?（有独三、无独三）",
        "### 专题十九 第三人撤销之诉\n\n【知识体系】\n\n| 概念 | （有独三、无独三）",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^### 专题十八 公益诉讼程序\s*\n### 专题二十 二审程序\s*\n\s*### 专题十九 第三人撤销之诉$",
        "### 专题二十 二审程序",
        text,
    )
    text = re.sub(
        r"(?m)^### 专题十九 第三人撤销之诉\s*\n\s*【知识体系】\s*\n\s*##### 一、上诉的提起$",
        "### 专题二十 二审程序\n\n【知识体系】\n\n##### 一、上诉的提起",
        text,
    )
    text = text.replace("【例1】【例2】【例1】#### 第二节 再审的启动", "#### 第二节 再审的启动")
    text = re.sub(
        r"(?m)^#### 第二节 再审的启动\s*\n\s*### 专题二十 二审程序\s*\n\s*【知识体系】$",
        "#### 第二节 再审的启动\n\n【知识体系】",
        text,
    )
    text = re.sub(
        r"(?m)^### 专题二十 二审程序\s*\n\s*【知识体系】\s*\n\s*1\. 本院院长认为本院已生效的判决、裁定和调解书确有错误，需要再审的，提交审判委员 法院启动 会讨论决定\。",
        "#### 第二节 再审的启动\n\n【知识体系】\n\n1. 本院院长认为本院已生效的判决、裁定和调解书确有错误，需要再审的，提交审判委员 法院启动 会讨论决定。",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^#### 第三节 再审的审理程序\s*\n\s*### 专题二十一 审判监督程序\s*\n\s*【知识体系】$",
        "#### 第三节 再审的审理程序\n\n【知识体系】",
        text,
    )
    text = re.sub(
        r"(?m)^### 专题二十一 审判监督程序\s*\n\s*【知识体系】\s*\n\s*\| 审理法院 \|",
        "#### 第三节 再审的审理程序\n\n【知识体系】\n\n| 审理法院 |",
        text,
        count=1,
    )
    text = re.sub(r"(?m)^#### 第一节 审判监督程序概述$", "### 专题二十一 审判监督程序\n\n#### 第一节 审判监督程序概述", text)
    text = re.sub(r"(?m)^### 专题二十一 审判监督程序\s*\n\s*#### 第二节 再审的启动", "### 专题二十一 审判监督程序\n\n#### 第二节 再审的启动", text)
    text = re.sub(r"(?m)^### 专题二十一 审判监督程序\s*\n\s*#### 第三节 再审的审理程序", "### 专题二十一 审判监督程序\n\n#### 第三节 再审的审理程序", text)
    text = re.sub(r"(?m)^### 专题二十一 审判监督程序\s*\n\s*### 专题二十二", "### 专题二十二", text)
    text = re.sub(r"(?m)^劳动纠纷的调解与仲裁在", "#### 小专题 劳动纠纷的调解与仲裁\n\n在", text)
    text = re.sub(r"(?m)^#### 小专题 劳动纠纷的调解与仲裁在", "#### 小专题 劳动纠纷的调解与仲裁\n\n在", text)
    text = re.sub(r"(?m)^#### 小专题 实体法的规定与当事人适格\(与实体法的融合\)$", "#### 小专题 实体法的规定与当事人适格（与实体法的融合）", text)
    text = re.sub(r"(?m)^实体法的规定与当事人适格\(与实体法的融合\)$", "#### 小专题 实体法的规定与当事人适格（与实体法的融合）", text)
    text = re.sub(r"(?m)^证明的逻辑在", "#### 小专题 证明的逻辑\n\n在", text)
    text = re.sub(r"(?m)^鉴定人、有专门知识的人、司法技术人员在", "#### 小专题 鉴定人、有专门知识的人、司法技术人员\n\n在", text)
    text = re.sub(r"(?m)^《民法典》中关于遗产管理人的相关规定\(与民法融合考查\)$", "#### 小专题 《民法典》中关于遗产管理人的相关规定（与民法融合考查）", text)
    text = re.sub(r"(?m)^遗产管理人违反遗产管理职责.*《民法典》中关于遗产管理人的相关规定\(与民法融合考查\)$", "#### 小专题 《民法典》中关于遗产管理人的相关规定（与民法融合考查）", text)
    text = re.sub(r"(?m)^案外人救济制度在", "#### 小专题 案外人救济制度\n\n在", text)
    text = re.sub(
        r"(?m)^【知识体系】\s*\n\s*\| 基本原则 \| 1\.适用我国《民事诉讼法》",
        "### 专题二十六 涉外民事诉讼程序\n\n【知识体系】\n\n| 基本原则 | 1.适用我国《民事诉讼法》",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^【知识体系】\s*\n\s*\| 仲裁范围 \| 可以仲裁 \| 财产纠纷",
        "### 专题二十七 仲裁概述\n\n【知识体系】\n\n| 仲裁范围 | 可以仲裁 | 财产纠纷",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^\| 回避后果 \| 1\.重新选定或者指定仲裁员。",
        "### 专题二十九 仲裁程序\n\n【知识体系】\n\n| 回避后果 | 1.重新选定或者指定仲裁员。",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^#### 第一节 司法对仲裁的支持——仲裁裁决的执行$",
        "### 专题三十 司法与仲裁\n\n#### 第一节 司法对仲裁的支持——仲裁裁决的执行",
        text,
        count=1,
    )
    text = re.sub(r"(?m)^### 专题二十七 仲裁概述\s*\n\s*【知识体系】", "### 专题二十七 仲裁概述\n\n【知识体系】", text)
    text = re.sub(r"(?m)^### 专题二十二 特别程序\s*\n\s*【知识体系】\s*\n\s*### 专题二十四", "### 专题二十三 非讼程序之督促程序\n\n【知识体系】\n\n### 专题二十四", text)
    text = re.sub(r"(?m)^### 专题二十五 执行程序$", "### 专题二十五 执行程序", text)
    text = re.sub(r"(?m)^### 专题二十六 涉外民事诉讼程序$", "### 专题二十六 涉外民事诉讼程序", text)
    text = re.sub(r"(?m)^【知识体系】\n\n### 专题", "### 专题", text)
    text = re.sub(r"(?m)^### 专题二十二 特别程序\s*\n\s*### 专题二十二 特别程序", "### 专题二十二 特别程序", text)
    text = re.sub(
        r"(?m)^/ 7/\^题二\+\-_/ 1/_申判监督程序\s*$",
        "### 专题二十一 审判监督程序",
        text,
    )
    text = re.sub(r"(?m)^.*命题版】\s*$", "【命题角度】", text)
    text = re.sub(r"(?m)^.*命题角[度圉】].*$", "【命题角度】", text)
    text = re.sub(r"(?m)^.*真题示[例施].*$", "【真题示例】", text)
    text = re.sub(r"(?m)^.*#### 第二节 再审的启动\s*$", "#### 第二节 再审的启动", text)
    text = re.sub(
        r"(?ms)^#### 第二节 再审的启动\s*\n\s*### 专题二十 二审程序\s*\n\s*【知识体系】",
        "#### 第二节 再审的启动\n\n【知识体系】",
        text,
        count=1,
    )
    text = re.sub(r"(?m)^(专题十八|公益诉讼程序|专题二\+|/I/二审程序|知识体系|考点精讲I|专题二十八|巾裁协议|画)$", "", text)
    text = re.sub(r"(?m)^### 专题([一二三四五六七八九十]+ .+)\n(?:### 专题\1\n)+", r"### 专题\1\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def detect_topic_number(s: str) -> int | None:
    compact = re.sub(r"\s+", "", s)
    m = re.search(r"专题([一二三四五六七八九十百零〇\d+|■Iil/◎©_-]+)", s)
    if not m:
        return None
    num = cn_to_int(m.group(1))
    if num and num in TOPIC_TITLES:
        return num
    return None


def normalize_section_heading(s: str) -> str | None:
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^第([一二三四五六七八九十百零〇\d]+)节(.+)$", s)
    if not m:
        return None
    title = m.group(2)
    title = re.sub(r"[0-9]+$", "", title)
    title = title.strip("：:")
    if not title or len(title) > 40:
        return None
    return f"#### 第{m.group(1)}节 {title}"


def normalize_subheading(s: str) -> str | None:
    m = re.match(r"^([一二三四五六七八九十]+)、\s*(.+)$", s)
    if not m:
        return None
    title = m.group(2).strip()
    if len(title) > 50:
        return None
    return f"##### {m.group(1)}、{title}"


def is_pipe_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


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
        rows = []
        for row in block:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if any(cells):
                rows.append(cells)
        if not rows:
            continue
        cols = max(len(row) for row in rows)
        normalized = []
        for row in rows:
            row = row + [""] * (cols - len(row))
            normalized.append("| " + " | ".join(row) + " |")
        out.append(normalized[0])
        out.append("| " + " | ".join(["---"] * cols) + " |")
        out.extend(normalized[1:])
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
            and not NO_MERGE_START.match(cur)
            and not NO_MERGE_START.match(lines[i + 1])
            and not is_pipe_table_line(cur)
            and not is_pipe_table_line(lines[i + 1])
        ):
            last = cur.rstrip()
            if last and last[-1] not in END_PUNCT:
                out.append(last + lines[i + 1].lstrip())
                i += 2
                continue
        out.append(cur)
        i += 1
    return "\n".join(out)


def build_body(lines: list[str], outline: list[dict[str, str | int]]) -> str:
    out: list[str] = []
    outline_idx = 0
    pending_small_topic = False
    last_heading_title = ""
    duplicate_budget = 0
    awaiting_knowledge_after_topic = False

    def emit_heading(entry: dict[str, str | int]) -> None:
        nonlocal last_heading_title, duplicate_budget, awaiting_knowledge_after_topic
        kind = entry["kind"]
        if kind == "topic":
            line = f"### 专题{int_to_cn(int(entry['num']))} {entry['title']}"
            awaiting_knowledge_after_topic = True
        elif kind == "section":
            line = f"#### 第{entry['num']}节 {entry['title']}"
        else:
            line = f"#### 小专题 {entry['title']}"
        if out:
            out.extend(["", line, ""])
        else:
            out.extend([line, ""])
        last_heading_title = str(entry["title"])
        duplicate_budget = 3

    for raw in lines:
        s = clean_line(raw)
        if not s:
            continue
        if is_noise_line(s):
            continue

        if duplicate_budget > 0 and lines_look_similar(s, last_heading_title) and len(normalize_match_text(s)) <= 20:
            duplicate_budget -= 1
            continue
        if duplicate_budget > 0:
            duplicate_budget -= 1

        if pending_small_topic and outline_idx < len(outline) and outline[outline_idx]["kind"] == "small_topic":
            entry = outline[outline_idx]
            emit_heading(entry)
            outline_idx += 1
            pending_small_topic = False
            if match_small_topic_line(s, entry) or is_noise_line(s):
                continue

        if is_small_topic_marker(s):
            pending_small_topic = True
            continue

        if outline_idx < len(outline):
            entry = outline[outline_idx]
            if entry["kind"] == "topic" and match_topic_line(s, entry):
                emit_heading(entry)
                outline_idx += 1
                continue
            if entry["kind"] == "section" and match_section_line(s, entry):
                emit_heading(entry)
                outline_idx += 1
                continue
            if entry["kind"] == "small_topic" and match_small_topic_line(s, entry):
                emit_heading(entry)
                outline_idx += 1
                continue

        if (
            outline_idx + 1 < len(outline)
            and outline[outline_idx]["kind"] == "topic"
            and outline[outline_idx + 1]["kind"] == "section"
            and match_section_line(s, outline[outline_idx + 1])
        ):
            emit_heading(outline[outline_idx])
            outline_idx += 1
            emit_heading(outline[outline_idx])
            outline_idx += 1
            continue

        if (
            outline_idx + 1 < len(outline)
            and outline[outline_idx]["kind"] == "topic"
            and outline[outline_idx + 1]["kind"] == "small_topic"
            and match_small_topic_line(s, outline[outline_idx + 1])
        ):
            emit_heading(outline[outline_idx])
            outline_idx += 1
            emit_heading(outline[outline_idx])
            outline_idx += 1
            continue

        if is_knowledge_system(s):
            if (
                not awaiting_knowledge_after_topic
                and outline_idx < len(outline)
                and outline[outline_idx]["kind"] == "topic"
            ):
                emit_heading(outline[outline_idx])
                outline_idx += 1
            awaiting_knowledge_after_topic = False
            out.extend(["", "【知识体系】", ""])
            continue

        marker = normalize_marker(s)
        if marker:
            out.extend(["", marker, ""])
            continue

        section = normalize_section_heading(s)
        if section:
            out.extend(["", section, ""])
            continue

        subsection = normalize_subheading(s)
        if subsection:
            out.extend(["", subsection, ""])
            continue

        s = s.replace("[", "【").replace("]", "】")
        s = re.sub(r"\s+", " ", s)
        out.append(s)

    return "\n".join(out)


def main() -> None:
    raw = normalize_text(SRC.read_text(encoding="utf-8"))
    outline = extract_outline(raw)
    body_lines = extract_body(raw)
    body = build_body(body_lines, outline)
    body = normalize_inline_typos(body)
    body = merge_paragraphs(body)
    body = normalize_inline_typos(body)
    body = normalize_markdown_tables(body)
    body = postprocess_output(body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"

    out = (
        f"# {BOOK_TITLE}\n\n"
        "> 整理说明：本文件根据 OCR 扫描原稿《戴鹏〈民诉〉》批量清洗，统一专题/节标题层级，清理 OCR 噪音、目录残片与 pandoc 残留，供切块入库与法考问答系统使用。\n\n"
        "---\n\n"
        f"{body}"
    )
    DST.write_text(out, encoding="utf-8")

    print(f"输出：{DST}")
    print(f"字符数：{len(out)}")
    print(f"行数：{len(out.splitlines())}")
    print(f"专题数：{len(re.findall(r'^### 专题', out, flags=re.M))}")
    print(f"节数：{len(re.findall(r'^#### 第', out, flags=re.M))}")
    print(f"小专题数：{len(re.findall(r'^#### 小专题', out, flags=re.M))}")


if __name__ == "__main__":
    main()
