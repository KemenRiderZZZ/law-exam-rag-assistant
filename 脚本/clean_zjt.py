#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
柏浪涛真金题 OCR 清洗脚本
"""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / 'OCR原稿' / '柏浪涛真金题.md'
DST = PROJECT_ROOT / '整理后文本' / '柏浪涛真金题_整理版.md'

# 真金题正文的起始位置：在 "PROJECT 01" 之后开始
# 通过查找第一个题号位置来定位
SKIP_BEFORE_FIRST_QUESTION = True


# ============== 1. pandoc 残留 ==============
def remove_pandoc_artifacts(text: str) -> str:
    text = re.sub(r"\[([^\[\]]*?)\]\{\.underline\}", r"\1", text)
    text = re.sub(r"\[\]\{#bookmark\d+\s*\.anchor\}", "", text)
    text = re.sub(r"\{\.[a-zA-Z][\w-]*\}", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


# ============== 2. 修引号 ==============
def fix_quotes(text: str) -> str:
    text = text.replace("\\\"", "\"")
    text = text.replace("\\'", "'")
    return text


# ============== 3. 题号格式化（核心） ==============
def normalize_question_numbers(text: str) -> str:
    """
    把所有 OCR 出的乱七八糟题号统一为 **N.** 形式。
    特征：紧跟着是题干文字+(年份-...)
    """
    # 多种题号变体（行首 + 紧跟数字 + 各种污染 + 题干）
    # 这些 pattern 都尝试匹配并归一为 **N.**
    patterns = [
        # **_N_** **_._** -> **N.**
        (r"\*\*_(\d{1,3})_\*\*\s*\*\*_\._\*\*", r"**\1.**"),
        # **_N._** -> **N.**
        (r"\*\*_(\d{1,3})\._\*\*", r"**\1.**"),
        # **_'N._** -> **N.**
        (r"\*\*_'(\d{1,3})\._\*\*", r"**\1.**"),
        # **_^N._** -> **N.**
        (r"\*\*_\^(\d{1,3})\._\*\*", r"**\1.**"),
        # **_N_** **_'._** -> **N.**
        (r"\*\*_(\d{1,3})_\*\*\s*\*\*_['\"^]?\._\*\*", r"**\1.**"),
        # 行首形如：MN. / :N. / SN. / ;N. / 'N. / "N. / =N. / ftN.
        # 这些都是 OCR 把斜体首字符识别错的产物
        # 题号必须紧跟 . 或空格 + 题干汉字
        (r"^[\s]*[MS:;'\"=ft（M]\s*(\d{1,3})\.\s*", r"\n\n**\1.** "),
        # 行首形如 "N N." 中间被错误插入空格
        (r"^[\s]*(\d)\s+(\d)\s*\.\s+", lambda m: f"\n\n**{m.group(1)}{m.group(2)}.** "),
        # 行首形如 "3 5." -> "**35.**"
        (r"^[\s]*(\d)\s+(\d)\.\s+", lambda m: f"\n\n**{m.group(1)}{m.group(2)}.** "),
    ]

    for pat, repl in patterns:
        if callable(repl):
            text = re.sub(pat, repl, text, flags=re.M)
        else:
            text = re.sub(pat, repl, text, flags=re.M)

    # 清理多余空格
    text = re.sub(r"\*\*(\d{1,3})\.\*\*\s+\*\*\.\*\*", r"**\1.**", text)
    text = re.sub(r"\*\*(\d{1,3})\.\*\*\s+\.\s*", r"**\1.** ", text)

    return text


# ============== 4. 删无意义加粗 ==============
def remove_meaningless_bold(text: str) -> str:
    # 注意：要保留题号 **N.** 形式
    # 排除题号格式后再处理其他加粗

    # 暂时把题号占位
    placeholders = []
    def stash(m):
        placeholders.append(m.group(0))
        return f"@@QNUM{len(placeholders) - 1}@@"

    text = re.sub(r"\*\*\d{1,3}\.\*\*", stash, text)

    # 现在处理其他加粗
    # **数字** **字母**
    text = re.sub(r"\*\*(\d+)\*\*", r"\1", text)
    text = re.sub(r"\*\*([A-Za-z])\*\*", r"\1", text)
    text = re.sub(r"\*\*([①②③④⑤⑥⑦⑧⑨⑩])\*\*", r"\1", text)
    text = re.sub(r"\*\*([（(][\d一二三四五六七八九十]+[)）])\*\*", r"\1", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*年", r"\1年", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*月", r"\1月", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*日", r"\1日", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*周岁", r"\1周岁", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*题", r"\1题", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*条", r"\1条", text)
    text = re.sub(r"\*\*(\d+)\*\*\s*款", r"\1款", text)
    text = re.sub(r"第\*\*(\d+)\*\*", r"第\1", text)

    # 包裹只有数字、字母、括号、点等的 **xxx**
    pattern = re.compile(
        r"\*\*([\d\w\.\,\-\+\(\)\[\]（）【】、，：；,\.\s]{1,12}?)\*\*"
    )
    def repl(m):
        inner = m.group(1)
        if re.search(r"[一-鿿]", inner):
            return m.group(0)
        return inner
    text = pattern.sub(repl, text)

    # 还原题号占位
    for i, ph in enumerate(placeholders):
        text = text.replace(f"@@QNUM{i}@@", ph)

    return text


# ============== 5. 删页眉页脚污染 ==============
JUNK_LINE_PATTERNS = [
    r"^\s*$",  # 空行后面再统一收敛
    r"^\s*PROJECT\s*\d+\s*$",
    r"^\s*Contents\s*$",
    r"^\s*Preface\s*$",
    r"^\s*刑法专题讲座[息真].金题卷\s*\d*\s*$",
    r"^\s*刑法专题讲座.金题卷.*$",
    r"^\s*△a\s*[・・•]?\s*▲?\s*$",
    r"^\s*[△□▲口]+\s*$",
    r"^\s*刖B\s*$",
    r"^\s*[LIJ]\s*$",
    r"^\s*[Bb][o0]\s*$",  # "Bo" 这种结尾
    r"^\s*\(竹马APP下载\).*$",
    r"^\s*抬浪涛\s*$",  # OCR 把"柏浪涛"误识别
    r"^\s*\d{4}年\d{1,2}月\s*$",  # 孤立的年月
]

def remove_junk_lines(text: str) -> str:
    out = []
    for line in text.split("\n"):
        is_junk = False
        s = line.strip()
        if not s:
            out.append(line)
            continue
        for pat in JUNK_LINE_PATTERNS:
            if re.match(pat, line):
                is_junk = True
                break
        if not is_junk:
            out.append(line)
    return "\n".join(out)


# ============== 6. 错别字字典 ==============
def fix_typos(text: str) -> str:
    typo_map = {
        "符甲": "将甲", "符乙": "将乙", "符丙": "将丙", "符其": "将其",
        "贪读": "贪污",
        "罪罪": "罪",
        "饬亡": "伤亡",
        "裁奸": "强奸",
        "畚见": "参见",
        "运密车": "运钞车",
        "刑善": "刑法",
        "蠢痴": "实害",
        "丈滋": "艾滋",
        "感慨惚": "恍恍惚",
        "恍慨惚惚": "恍恍惚惚",
        "另充": "冒充",
        "都助犯": "帮助犯",
        "教唳": "教唆",
        "犯器形态": "犯罪形态",
        "回援性": "间接性",
        "支耻住": "支配性",
        "改窕": "犯罪",
        "支卷": "·专",
        "失取": "失职",
        "栏": "罪",  # 个别情形，慎
    }
    # 仅特定上下文的错字
    text = text.replace("欲驾项", "欲驾车")
    text = text.replace("负贵", "负责")

    for w, r in typo_map.items():
        if w == "栏":
            continue
        text = text.replace(w, r)

    # 句末错乱小写字母（OCR 把"。"误识为"o"）
    # 只在"X项说法正确/错误"等典型场景修复
    text = re.sub(r"([A-DＡ-Ｄ]项说法[正错][确误])[oO0]([。\s])", r"\1。\2", text)
    text = re.sub(r"(本题答案为[A-D]+)[oO]\b", r"\1", text)
    text = re.sub(r"答案：?[B][o0]\s*$", r"答案：B。", text, flags=re.M)

    # 试题年份点号修正：(2015-2-89.任) -> (2015-2-89,任)
    text = re.sub(r"(\(\d{4}-\d-\d+)\.([多单任主])", r"\1,\2", text)

    return text


# ============== 7. 结构标记规范化 ==============
def normalize_markers(text: str) -> str:
    # 考点
    text = re.sub(r"[［\[(]\s*考\s*点\s*[］\]j)]", "【考点】", text)
    # 解析 - 包括各种错乱：[解析] [侥析] (解析j 「便析］
    text = re.sub(r"[「［\[(]\s*[侥便例解]\s*析\s*[］\]j」]", "【解析】", text)
    text = re.sub(r"[（(]\s*解析\s*j", "【解析】", text)
    # 答案
    text = re.sub(r"[［\[]\s*答\s*案\s*[］\]]", "【答案】", text)
    # 引申总结/对比总结/引申练习/总结结论/提示/原型案例
    for kw in ["引申总结", "对比总结", "引申练习", "总结结论", "提示", "原型案例", "总结", "归纳"]:
        # 行首 "kw：" 或 "kw:" 或 "kw "
        text = re.sub(
            rf"^[\s]*{kw}\s*[:：]\s*",
            f"\n\n**{kw}**：",
            text,
            flags=re.M
        )
        text = re.sub(
            rf"\b{kw}\s*[:：z三]\s*",
            f"\n\n**{kw}**：",
            text
        )
    # 综上所述（答案行）
    text = re.sub(
        r"^综上所述[，,]\s*本题答案为\s*([A-D]+)[oO0。.]*\s*$",
        r"\n**【答案】\1**",
        text,
        flags=re.M
    )
    return text


# ============== 8. 试题年份引用 ==============
def normalize_year_refs(text: str) -> str:
    # (2015-2-51,多) 这种已经正确的不动
    # 处理被错误识别的：（2018 金题-1-2-1,多）-> （2018金题-1-2-1,多）
    text = re.sub(r"（(\d{4})\s+金题", r"（\1金题", text)
    text = re.sub(r"\((\d{4})\s+金题", r"(\1金题", text)
    # 全角->半角统一（保留中文括号）
    text = re.sub(r"\((\d{4}-)", r"（\1", text)
    text = re.sub(r"\((\d{4}金题)", r"（\1", text)
    # 收尾右括号
    text = re.sub(r"(,?[多单任主案例题选观])\s*\)", r"\1）", text)
    return text


# ============== 9. 段落合并 ==============
END_PUNCT = "。！？；：,，、）)]\"'』」"
NO_MERGE_START = re.compile(
    r"^\s*("
    r"\*\*\d+\.\*\*|"
    r"\d+[\.。]|"
    r"[（(][\d一二三四五六七八九十]+[)）]|"
    r"[一二三四五六七八九十]+、|"
    r"[①②③④⑤⑥⑦⑧⑨⑩]|"
    r"[#\-\*>]|"
    r"\||"
    r"[A-D]\.|"
    r"例\d+|"
    r"题\d+|"
    r"【|"
    r"\*\*[【一-龥]+\*\*|"
    r"第[一二三四五六七八九十百零\d]+[讲节条款]"
    r")"
)

def merge_paragraphs(text: str) -> str:
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if (cur.strip() and i + 1 < len(lines)
                and lines[i + 1].strip()
                and not cur.startswith("#")
                and not cur.startswith("-")
                and not cur.startswith(">")
                and not cur.startswith("|")
                and not cur.startswith("```")
                and not cur.startswith("**")  # 加粗起始/题号别合并
                and not NO_MERGE_START.match(lines[i + 1])):
            last = cur.rstrip()
            if last and last[-1] not in END_PUNCT and last[-1] not in ".!?":
                out.append(cur.rstrip() + lines[i + 1].lstrip())
                i += 2
                continue
        out.append(cur)
        i += 1
    return "\n".join(out)


# ============== 10. 章节标题层级重建 ==============
def rebuild_headings(text: str) -> str:
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.strip()

        # 第N讲：忽略目录里的（带页码的）和正文里有题号 ** 加粗的
        m = re.match(r"^第([一二三四五六七八九十百零\d]+)讲\s*(.+?)$", s)
        if m and len(s) < 40 and "/" not in s and "*" not in s:
            num = m.group(1)
            title = m.group(2).strip()
            title = re.sub(r"\s*\d+\s*$", "", title)
            if title:
                out.append("")
                out.append(f"## 第{num}讲 {title}")
                out.append("")
                continue

        # 一、xxx 节内分类（讲下的小节，只在不含案例描述时识别）
        m = re.match(r"^([一二三四五六七八九十]+)、\s*(.+?)$", s)
        if m and len(s) < 40 and not re.search(r"[，。；：]", m.group(2)):
            ch = m.group(1)
            title = m.group(2).strip()
            title = re.sub(r"\s*/\s*\S+$", "", title)  # 去 /XX 页码
            out.append("")
            out.append(f"### {ch}、{title}")
            out.append("")
            continue

        out.append(line)

    return "\n".join(out)


# ============== 11. 空行规范化 ==============
def normalize_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ============== 主流程 ==============
def main():
    raw = SRC.read_text(encoding="utf-8")

    # 跳过前面 282 行（封面+目录），从"PROJECT 01"或"第一讲"正文起
    # 第一道题在 285 行附近
    lines = raw.split("\n")
    # 找 "PROJECT 01" 的行，它后面是正文
    start_idx = 0
    for i, ln in enumerate(lines):
        if re.match(r"^\s*PROJECT\s*01\s*$", ln):
            start_idx = i + 1
            break

    # 留下封面前言部分作为头部
    head_lines = ["# 柏浪涛刑法专题讲座真金题卷（2026版）",
                  "",
                  '> 整理说明：本文件由 OCR 扫描原稿清洗而来，按"讲"组织，每道题独立成块。',
                  ""]

    body_text = "\n".join(lines[start_idx:])

    body = body_text
    body = remove_pandoc_artifacts(body)
    body = fix_quotes(body)
    body = normalize_question_numbers(body)
    body = remove_meaningless_bold(body)
    body = remove_junk_lines(body)
    body = fix_typos(body)
    body = normalize_year_refs(body)
    body = normalize_markers(body)
    body = rebuild_headings(body)
    body = merge_paragraphs(body)
    body = normalize_blank_lines(body)

    out = "\n".join(head_lines) + body
    DST.write_text(out, encoding="utf-8")
    print(f"已写入 {DST}")
    print(f"总行数：{out.count(chr(10))}")
    print(f"总字符：{len(out)}")


if __name__ == "__main__":
    main()
