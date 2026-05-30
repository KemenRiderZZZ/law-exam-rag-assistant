#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真金题清洗第二轮：补题号、补讲标题、补空行。"""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DST = PROJECT_ROOT / '整理后文本' / '柏浪涛真金题_整理版.md'
text = DST.read_text(encoding="utf-8")

# 1. 合并跨行的讲标题：
# 第N讲\n\nXXXX -> ## 第N讲 XXXX
def merge_chapter_title(text):
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        # 形如 "第N讲" 单独成行（无标题文本，OCR 拆行）
        m = re.match(r"^第([一二三四五六七八九十百零\d]+)讲\s*$", s)
        if m:
            num = m.group(1)
            # 找下一非空行作为标题
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                next_s = lines[j].strip()
                if len(next_s) < 30 and not re.match(r"^[*【\-]", next_s):
                    out.append("")
                    out.append(f"## 第{num}讲 {next_s}")
                    out.append("")
                    i = j + 1
                    continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)

text = merge_chapter_title(text)

# 2. 处理残留题号变体：
# `：2.关于...?` `:2.关于...?` `;3.关于...?` `'4...?` `:4 关于...?`
# 共同特征：行首乱字符 + 数字 + 题干中包含问号
# 题干常以"关于...？"、"...是？"、"...的是？"、"...有？"等结尾
patterns = [
    # `：N.xxx？(YYYY-...)` 或 `:N.xxx？` 等
    (r"^[\s]*[：:;'\"，,]\s*(\d{1,3})\.?\s*(.+?[?？].+?[）)])\s*$",
     r"\n\n**\1.** \2"),
    # `：N.xxx？` 简短题干
    (r"^[\s]*[：:;'\"，,]\s*(\d{1,3})\.\s*", r"\n\n**\1.** "),
    # `:4 xxx` 不带点
    (r"^[\s]*[：:;'\"，,]\s*(\d{1,3})\s+(.{4,})$", r"\n\n**\1.** \2"),
    # 混合形式 `**_'NN._**`
    (r"\*\*_'(\d{1,3})\._\*\*", r"**\1.**"),
    # `**_^NN._**`
    (r"\*\*_\^(\d{1,3})\._\*\*", r"**\1.**"),
]
for pat, repl in patterns:
    text = re.sub(pat, repl, text, flags=re.M)

# 3. 题号格式收尾：题号后跟解析时强制空行
text = re.sub(
    r"(\*\*【答案】[A-D]+\*\*)\s*\n([^*\n])",
    r"\1\n\n\2",
    text
)

# 4. 题号前强制空行
text = re.sub(r"([^\n])\n(\*\*\d{1,3}\.\*\*)", r"\1\n\n\2", text)

# 5. 删孤立的页码行 "/数字"
text = re.sub(r"^\s*/+\s*[A-Za-z\d]+\s*$", "", text, flags=re.M)

# 6. 删脚注尾巴的 ① 行（在题号紧前的）
# 比较多见：题号前面有个 ① 备注脚注
# 保留它，但放进引用块
text = re.sub(
    r"^([①②③④])\s*(.+?)$",
    r"> \1 \2",
    text,
    flags=re.M
)

# 7. 多余空行收敛
text = re.sub(r"\n{3,}", "\n\n", text)

DST.write_text(text, encoding="utf-8")
print("第二轮补丁完成")
print(f"行数：{text.count(chr(10))}")
