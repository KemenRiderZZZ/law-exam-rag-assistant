#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
柏浪涛刑法书 OCR 清洗脚本
输入：柏浪涛刑法书.md（OCR 原稿）
输出：追加到 柏浪涛刑法书_整理版.md（v1 已含前 4 讲）

处理步骤详见 plan 文件 v2 方案。
"""

import re
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / 'OCR原稿' / '柏浪涛刑法书.md'
DST = PROJECT_ROOT / '整理后文本' / '柏浪涛刑法书_整理版.md'

# v1 已经人工整理了第一讲~第四讲（源文件第 1~1813 行）
# 脚本从第五讲起处理，源文件起始行号约 1814 行（"五讲" 标题位置）
START_LINE = 1813  # 0-indexed offset; 第 1814 行起


# ============== 1. pandoc 残留 ==============
def remove_pandoc_artifacts(text: str) -> str:
    # [文字]{.underline} -> 文字
    text = re.sub(r"\[([^\[\]]*?)\]\{\.underline\}", r"\1", text)
    # []{#bookmarkN .anchor}
    text = re.sub(r"\[\]\{#bookmark\d+\s*\.anchor\}", "", text)
    # {.smallcaps}, {.anchor}, {.xxx} 类
    text = re.sub(r"\{\.[a-zA-Z][\w-]*\}", "", text)
    # <!-- xxx --> 整体注释
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


# ============== 2. 去无意义加粗 ==============
def remove_meaningless_bold(text: str) -> str:
    """
    去掉只包裹数字、字母、单符号、括号序号、半个括号、单字标点的 **xxx**
    """
    # **数字** / **字母** / **数字字母组合** / **括号序号** 等
    pattern = re.compile(
        r"\*\*("
        r"[\d\w\.\,\-\+\(\)\[\]（）【】、，：；,\.\s]{1,12}?"
        r")\*\*"
    )

    def repl(m):
        inner = m.group(1)
        # 如果包含汉字，保留加粗
        if re.search(r"[一-鿿]", inner):
            return m.group(0)
        return inner

    text = pattern.sub(repl, text)

    # 处理半括号情形 **（1）** 这种本身整体就是序号
    text = re.sub(r"\*\*([（(][\d一二三四五六七八九十]+[)）])\*\*", r"\1", text)
    text = re.sub(r"\*\*(\d+)\*\*", r"\1", text)
    text = re.sub(r"\*\*([A-Za-z])\*\*", r"\1", text)
    text = re.sub(r"\*\*([①②③④⑤⑥⑦⑧⑨⑩])\*\*", r"\1", text)

    # **N年**、**N月**、**N日** 数字单位
    text = re.sub(r"\*\*(\d+)\*\*\s*年", r"\1年", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*月", r"\1月", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*日", r"\1日", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*周岁", r"\1周岁", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*岁", r"\1岁", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*题", r"\1题", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*条", r"\1条", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*款", r"\1款", text)
    text = re.sub(r"第\*\*(\d+)\*\*", r"第\1", text)

    return text


# ============== 3. 修引号 ==============
def fix_quotes(text: str) -> str:
    # 反斜杠引号 \" \' 直接替换
    # 简化处理：成对替换，奇左偶右；先全部转成中文引号
    # 由于难以判断左右，先全部转 \" -> "，\' -> '，让 markdown 处理；后续手工微调
    text = text.replace("\\\"", "\"")
    text = text.replace("\\'", "'")
    return text


# ============== 4. 删常见乱码片段 ==============
JUNK_LINE_PATTERNS = [
    r"^\s*[口▲□¬]\s*$",
    r"^\s*[小]\s*$",
    r"^\s*[%]\s*$",
    r"^\s*L\s*$",
    r"^\s*J\s*$",
    r"^\s*\\\s*$",
    r"^\s*\^\s*$",
    r"^\s*\^.{0,3}\s*$",
    r"^\s*[\*]+\s*$",
    r"^\s*△0/.*?讲\s*$",
    r"^\s*U/\^.*$",
    r"^\s*\*0了\*.*$",
    r"^\s*Aft-\s*$",
    r"^\s*[，,]\s*\[.*\]\{\.underline\}\s*$",
    r"^\s*\+冢\s*$",
    r"^\s*&：\s*然?\s*$",
    r"^\s*£Q.*$",
    r"^\s*[，,]\s*工\s*$",
    r"^\s*-\\?'?\s*$",
    r"^\s*第一\s*\*\*T\*\*\s*$",
    r"^\s*刑法[•\^].*精讲[卷善]?\s*$",
    r"^\s*刑法支卷讲座精讲善\s*$",
    r"^\s*刑法围题进座值进堂\s*$",
    r"^\s*总论_+.*罪论_+\s*$",
    r"^\s*[A-Z]\s*[a-z]+\s*$",  # 单独的英文残留
    r"^\s*Cz鬼\s*$",
    r"^\s*\^\s*\d+\s*\^\s*$",
    r"^\s*~v~\^.*?\^\s*$",
    r"^\s*~[A-Za-z0-9]+~\s*$",
    r"^\s*\(D\s*$",
    r"^\s*\.\\\s*$",
    r"^\s*：\s*$",
    r"^\s*-+\s*$",  # 单纯连字符行（除 markdown 分割线，这里如果不在表格上下文一般是垃圾）
    r"^\s*[一-鿿]\s*$",  # 单汉字行（独立的"口"、"小"等）—— 太宽，慎用，先注释掉
]
# 取消单汉字行规则（容易误删合法标题，例如"口"）
JUNK_LINE_PATTERNS = [p for p in JUNK_LINE_PATTERNS if not p.endswith(r"]\s*$")
                      or "[\\u4e00" not in p]


def remove_junk_lines(text: str) -> str:
    out = []
    for line in text.split("\n"):
        is_junk = False
        for pat in JUNK_LINE_PATTERNS:
            if re.match(pat, line):
                is_junk = True
                break
        if is_junk:
            continue
        out.append(line)
    return "\n".join(out)


# ============== 5. OCR 错别字字典 ==============
TYPO_MAP = {
    "畚见": "参见",
    "运密车": "运钞车",
    "刑善": "刑法",
    "蠢痴": "实害",
    "褪破": "根据",
    "丈滋": "艾滋",
    "Cz鬼": "",
    "碗定": "确定",
    "鼠应": "自由主义",
    "支卷": "·专",
    "失取": "失职",
    "为犯": "为罪",  # 有些"...为犯罪行为"被识别错
    "未符": "未将",
    "项": None,  # 仅"欲驾项"特殊处理
    "符甲": "将甲",
    "符乙": "将乙",
    "符丙": "将丙",
    "符其": "将其",
    "财病人": "对病人",
    "贪读": "贪污",
    "感慨惚": "恍恍惚",
    "恍慨惚惚": "恍恍惚惚",
    "活语权": "话语权",
    "瓦特": "瓦特",  # 保留
    "婴儿": "婴儿",
    "象竞合": "象竞合",
    "罪未遂": "罪未遂",
    "罪既遂": "罪既遂",
    "罪致人": "罪致人",
    "罪论处": "罪论处",
    "拿走小": "拿走小",
    "婚配": "婚配",
    "尊致": "导致",
    "尊重": "尊重",  # 保留
    "蓝律主义": "罪刑法定中的法律主义",
    "苑例": "范例",
    "诀私枉法": "徇私枉法",
    "狗私枉法": "徇私枉法",
    "狗番": "狗蛋",
    "雷": "蛋",  # 慎，仅在"狗雷"上下文
    "无知": "无知",
    "棉吴而": "",
    "瓦特": "瓦特",
    "脑子瓦特": "脑子瓦特",
    "干工程": "工程",
    "马克思T程": "马工程",
    "电热炉煮面": "电热炉煮面",
    "刺佛": "刺向",
    "练过散打的乙招甲制服": "练过散打的乙将甲制服",
    "扭送至": "扭送至",
}

# 罪名错字（结合上下文）：xxx霏/聚/兼/繇/睾/蕤/犀/晕 → xxx罪
ROUMING_TYPOS = ["霏", "聚", "兼", "繇", "睾", "蕤", "犀", "晕"]


def fix_typos(text: str) -> str:
    for wrong, right in TYPO_MAP.items():
        if wrong == "项" or right is None:
            continue
        text = text.replace(wrong, right)

    # "欲驾项" -> "欲驾车"
    text = text.replace("欲驾项", "欲驾车")

    # 罪名错字：在"xx罪"语境下，例如"故意杀人霏"，把霏换罪
    # 启发式：紧跟在"罪"高频词后的这些字
    # 简单做法：所有这些字都视为可能的"罪"，但需上下文校验。先做最常见组合：
    rou_keywords = [
        "故意杀人", "故意伤害", "强奸", "抢劫", "抢夺", "盗窃", "诈骗", "侵占",
        "敲诈勒索", "贪污", "受贿", "行贿", "挪用公款", "走私", "绑架",
        "拐卖妇女", "拐卖儿童", "非法拘禁", "非法侵入住宅", "故意毁坏财物",
        "组织卖淫", "传播淫秽物品", "传播性病", "破坏交通工具", "劫持汽车",
        "信用卡诈骗", "贷款诈骗", "妨害公务", "妨害司法", "脱逃",
        "玩忽职守", "滥用职权", "刑讯逼供", "徇私枉法", "诬告陷害",
        "侮辱", "诽谤", "遗弃", "虐待", "招摇撞骗", "聚众斗殴",
        "寻衅滋事", "强制猥亵", "强制侮辱", "组织黑社会", "参加黑社会",
        "帮助信息网络犯罪", "掩饰隐瞒犯罪所得", "持有假币", "非法持有毒品",
        "非法持有枪支", "非法获取国家秘密", "故意泄露国家秘密",
        "为境外非法提供国家秘密", "叛逃", "投放危险物质", "放火",
        "爆炸", "决水", "以危险方法危害公共安全", "交通肇事",
        "危险驾驶", "重大责任事故", "重大劳动安全事故", "工程重大安全事故",
        "生产销售假药", "生产销售劣药", "生产销售伪劣产品",
        "妨害药品管理", "非法经营", "组织领导传销", "合同诈骗",
        "集资诈骗", "票据诈骗", "保险诈骗", "票据诈骗", "金融凭证诈骗",
        "有价证券诈骗", "骗取贷款", "高利转贷", "洗钱", "组织出卖人体器官",
        "组织他人偷越国境", "组织运送他人偷越国境", "偷越国境",
        "妨害国境管理", "妨害国边境管理", "非法行医", "非法采矿",
        "破坏环境", "污染环境", "走私武器", "走私弹药", "走私假币",
        "走私淫秽物品", "走私文物", "走私贵重金属", "走私废物",
        "走私国家禁止进出口的货物物品", "走私普通货物物品",
        "贿赂", "斡旋受贿", "利用影响力受贿", "私分国有资产",
        "巨额财产来源不明", "隐瞒境外存款", "丢失枪支不报",
        "拒不支付劳动报酬", "拒不执行判决", "不解救被拐卖绑架的妇女儿童",
        "组织未成年人进行违反治安管理活动", "聚众淫乱", "组织淫秽表演",
        "拒绝提供间谍犯罪", "失职致使在押人员脱逃",
        "暴力干涉婚姻自由", "破坏军婚",
        "侮辱尸体", "盗窃尸体", "盗掘古墓葬", "盗掘古文化遗址",
        "倒卖文物", "故意损毁文物",
        "冒充军警人员抢劫", "事后抢劫", "转化抢劫",
    ]

    for kw in rou_keywords:
        for typo in ROUMING_TYPOS:
            text = text.replace(kw + typo, kw + "罪")

    # 简单单独的"该罪"、"本罪"、"成立XX罪"等带错字
    # 在"成立"、"构成"、"触犯"、"以"、"该"、"本"后面的错字罪
    for verb in ["成立", "构成", "触犯", "犯", "定", "为"]:
        for typo in ROUMING_TYPOS:
            # 形如"构成霏" "成立霏"
            text = re.sub(verb + r"([一-鿿]{1,8})" + typo + r"([，。；、\s])",
                          verb + r"\1罪\2", text)

    return text


# ============== 6. 重建标题层级 ==============
def rebuild_headings(text: str) -> str:
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.strip()

        # 第N讲：处理"第N讲 xxx数字"或"第N讲 xxx **数字**"或"第N讲xxx"
        m = re.match(
            r"^第([一二三四五六七八九十百零\d]+)讲\s*(.+?)\s*(?:\*\*\d+\*\*|\d+)?$",
            s
        )
        if m and len(s) < 60 and "讲" in s[:8]:
            num = m.group(1)
            title = m.group(2).strip()
            # 去尾部页码数字残留
            title = re.sub(r"\s*\d+\s*$", "", title)
            title = re.sub(r"^\s*[一二三四五六七八九十]+、?\s*", "", title)
            if title:
                out.append("")
                out.append(f"## 第{num}讲 {title}")
                out.append("")
                continue

        # 第N节：节标题
        m = re.match(r"^第([一二三四五六七八九十百零\d]+)节\s*(.+?)$", s)
        if m and len(s) < 50 and not re.search(r"^\s*[（(]", s):
            num = m.group(1)
            title = m.group(2).strip()
            # 移除尾部 /数字
            title = re.sub(r"\s*[/／]\s*\*?\*?\d+\*?\*?\s*$", "", title)
            title = re.sub(r"\s*\d+\s*$", "", title)
            if title:
                out.append("")
                out.append(f"### 第{num}节 {title}")
                out.append("")
                continue

        # 一、 二、 ... 节内一级
        m = re.match(r"^([一二三四五六七八九十]+)、\s*(.+?)$", s)
        if m and len(s) < 60 and not s.startswith("（"):
            ch = m.group(1)
            title = m.group(2).strip()
            # 排除"一、二人构成..."这类正文
            if not re.search(r"[，。；：]", title):
                out.append("")
                out.append(f"#### {ch}、{title}")
                out.append("")
                continue

        # （一）（二）...
        m = re.match(r"^[（(]([一二三四五六七八九十]+)[)）]\s*(.+?)$", s)
        if m and len(s) < 50:
            ch = m.group(1)
            title = m.group(2).strip()
            if not re.search(r"[，。；]", title):
                out.append("")
                out.append(f"##### （{ch}）{title}")
                out.append("")
                continue

        out.append(line)

    return "\n".join(out)


# ============== 7. 结构标记规范化 ==============
def normalize_markers(text: str) -> str:
    # ［问题］ [问题] :问题: ：问题： 等 → 【问题】
    markers = ["问题", "注意", "提示", "总结", "巩固练习", "结论",
               "特别提示", "典型真题", "答案", "比较", "引申", "练习",
               "注意1", "注意2", "提示1", "提示2", "班固练习"]
    for m in markers:
        # ［m］ [m] :m: ：m：
        target = "练习" if m == "班固练习" else m  # OCR 错字
        for left in ["［", "[", "：", ":"]:
            for right in ["］", "]", "：", ":"]:
                text = text.replace(f"{left}{m}{right}", f"【{target}】")
    # 例**N** -> 例N（在 remove_meaningless_bold 之后基本已经处理）
    # 题**N**, -> 题N：
    text = re.sub(r"题(\d+)\s*[,，]", r"题\1：", text)
    text = re.sub(r"例(\d+)\s*[,，]", r"例\1：", text)
    return text


# ============== 8. 试题年份引用 ==============
def normalize_year_refs(text: str) -> str:
    # **（YYYY**年第**N**题） 已被去加粗后变 （YYYY年第N题），可能残余空格
    text = re.sub(r"（(\d{4})\s*年", r"（\1年", text)
    text = re.sub(r"\(\s*(\d{4})\s*年", r"(\1年", text)
    text = re.sub(r"\((\d{4})年", r"（\1年", text)
    text = re.sub(r"(\d{4})\s+年", r"\1年", text)
    text = re.sub(r"年\s+第\s*(\d+)", r"年第\1", text)
    text = re.sub(r"第\s*(\d+)\s+题", r"第\1题", text)
    text = re.sub(r"年试\s*题", "年试题", text)
    return text


# ============== 9. 段落合并 ==============
END_PUNCT = "。！？；：,，、）)]\"'』」"
NO_MERGE_START = re.compile(
    r"^\s*("
    r"\d+[\.。]|"
    r"[（(][\d一二三四五六七八九十]+[)）]|"
    r"[一二三四五六七八九十]+、|"
    r"[①②③④⑤⑥⑦⑧⑨⑩]|"
    r"[#\-\*>]|"
    r"\||"
    r"例\d+|"
    r"题\d+|"
    r"【|"
    r"\+|"
    r"第[一二三四五六七八九十百零\d]+[讲节条款]"
    r")"
)


def merge_paragraphs(text: str) -> str:
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        # 当前行非空，且行尾不是终止标点，且下一行非空且不以列表/标题/特殊起始符开头
        if (cur.strip() and i + 1 < len(lines)
                and lines[i + 1].strip()
                and not cur.startswith("#")
                and not cur.startswith("-")
                and not cur.startswith(">")
                and not cur.startswith("|")
                and not cur.startswith("```")
                and not NO_MERGE_START.match(lines[i + 1])):
            last = cur.rstrip()
            if last and last[-1] not in END_PUNCT and last[-1] not in ".!?":
                # 合并
                out.append(cur.rstrip() + lines[i + 1].lstrip())
                i += 2
                continue
        out.append(cur)
        i += 1
    return "\n".join(out)


# ============== 10. 表格转换 ==============
def convert_pandoc_tables(text: str) -> str:
    """
    把 +----+ 形式的 pandoc 表格转 markdown 表格。
    简化处理：识别整个表格块（从首行 +---+ 到末行 +---+），
    提取所有非 +---+ 的 | xxx | 行，作为单元格行。
    遇到嵌套结构暂用 <!-- TODO: 复杂表格 --> 标记。
    """
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 表格起始：+----+ 或 +:----+ 或 +----+----+
        if re.match(r"^\s*\+[-:=+]+", line):
            # 收集到下一个非表格行
            block = []
            j = i
            while j < len(lines) and (
                re.match(r"^\s*[\+\|]", lines[j]) or lines[j].strip() == ""
            ):
                if lines[j].strip() == "" and j + 1 < len(lines) and not re.match(
                    r"^\s*[\+\|]", lines[j + 1]
                ):
                    break
                block.append(lines[j])
                j += 1
            # 解析 block
            md_table = parse_pandoc_table(block)
            if md_table:
                out.append("")
                out.append(md_table)
                out.append("")
            else:
                out.append("<!-- TODO: 复杂表格，待手工修订 -->")
                for b in block:
                    out.append(b)
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def parse_pandoc_table(block):
    """简单 pandoc 表格转 markdown。无法解析则返回 None。"""
    rows = []
    for ln in block:
        if re.match(r"^\s*\+[-:=+]+", ln):
            continue
        if not ln.strip():
            continue
        # 单元格分隔
        parts = [p.strip() for p in ln.strip().strip("|").split("|")]
        if any(parts):
            rows.append(parts)
    if not rows:
        return None
    # 列数
    ncol = max(len(r) for r in rows)
    if ncol < 2:
        return None
    # 多行单元格合并：相邻 rows 列数相同，逐列合并到非空
    # 简化：直接每行作为一行输出
    norm_rows = []
    for r in rows:
        if len(r) < ncol:
            r = r + [""] * (ncol - len(r))
        # 单元格内 ** 干掉
        r = [re.sub(r"\*\*", "", c).replace("\n", "<br>") for c in r]
        norm_rows.append(r)
    # 假设第一行是表头
    md = ["| " + " | ".join(norm_rows[0]) + " |",
          "| " + " | ".join(["---"] * ncol) + " |"]
    for r in norm_rows[1:]:
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)


# ============== 11. 脚注处理 ==============
def normalize_footnotes(text: str) -> str:
    # 行首 ① 标号 - 简化：保持原样，只在前面加 > 形成 quote
    out = []
    for line in text.split("\n"):
        if re.match(r"^\s*[①②③④⑤⑥⑦⑧⑨⑩]", line) and len(line) > 10:
            out.append("> " + line.strip())
        else:
            out.append(line)
    return "\n".join(out)


# ============== 12. 空行规范化 ==============
def normalize_blank_lines(text: str) -> str:
    # 多个连续空行压缩为 1
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ============== 主流程 ==============
def main():
    raw = SRC.read_text(encoding="utf-8")
    lines = raw.split("\n")
    # 取第 1814 行起（0-indexed 1813）
    body = "\n".join(lines[START_LINE:])

    # 按顺序处理
    body = remove_pandoc_artifacts(body)
    body = fix_quotes(body)
    body = remove_meaningless_bold(body)
    body = remove_junk_lines(body)
    body = fix_typos(body)
    body = normalize_year_refs(body)
    body = normalize_markers(body)
    body = convert_pandoc_tables(body)
    body = rebuild_headings(body)
    body = normalize_footnotes(body)
    body = merge_paragraphs(body)
    body = normalize_blank_lines(body)

    # 追加到目标文件
    existing = DST.read_text(encoding="utf-8") if DST.exists() else ""
    sep = "\n\n---\n\n" if existing and not existing.endswith("\n\n") else ""
    out = existing + sep + body

    DST.write_text(out, encoding="utf-8")
    print(f"已追加 {len(body)} 字符到 {DST}")
    print(f"目标文件总行数：{len(out.split(chr(10)))}")


if __name__ == "__main__":
    main()
