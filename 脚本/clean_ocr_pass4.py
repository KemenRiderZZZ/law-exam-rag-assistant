#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮：清理 OCR 公式残片、孤立残骸行、错位列表序号。"""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DST = PROJECT_ROOT / '整理后文本' / '柏浪涛刑法书_整理版.md'
text = DST.read_text(encoding="utf-8")

# 1. 删除以单字符或纯符号成行（明显垃圾）
def is_garbage_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # 全是 ascii 标点/符号/单数字（不含中文也不含 markdown 元素）
    if re.fullmatch(r"[\W\d_]+", s) and not s.startswith("#") and \
       not s.startswith("-") and not s.startswith(">") and \
       not s.startswith("|") and not s.startswith("*") and \
       not s == "---":
        # 长度 >=3 才删（避免删掉合法的"。"）
        if len(s) >= 2 and not re.search(r"[一-鿿]", s):
            return True
    # 大量 \^ ** 混合的纯垃圾
    if re.fullmatch(r"[\\\^\*\d\sA-Za-z]+", s) and "\\^" in s:
        return True
    # 极短的胡乱单词残片
    return False

# 2. 删除常见 OCR 公式残片（行内片段，用空字符串替换）
JUNK_INLINE = [
    r"\*\*[A-Za-z]*\\?\^[\w\d\\\^=\|\-\?]*\*\*",   # **xxx\^yyy**
    r"\*\*[A-Za-z\d\\\^]+\*\*",  # **\^xxx**
    r"\\\^[\d\w]*",  # \^123
    r"\\_+",  # \_\_
    r"\^[\d\w]+\^",  # ^123^
    r"~[\d\w]+~",  # ~123~
    r"[？\?]『",  # 残骸开头
    r"\\<\^?",  # \<
]

# 删行
new_lines = []
for line in text.split("\n"):
    if is_garbage_line(line):
        continue
    new_lines.append(line)
text = "\n".join(new_lines)

# 行内清理
for pat in JUNK_INLINE:
    text = re.sub(pat, "", text)

# 3. 修正"##### （九）》所增设\]"这种错位列表序号（实际是脚注）
text = re.sub(
    r"##### （九）》所增设\\?\]",
    "（《刑法修正案（九）》增设）",
    text
)

# 4. 修复脱拉的"特别提示"散标题：合并到引文块
# 例如：## 第N讲 xxx\n\n特别提示\n\n... 已经在 pass3 处理过
# 这里再保险一次：把孤立的"特别提示"行（不带【】）转成 markdown 引文
text = re.sub(r"\n特别提示\n", "\n\n【特别提示】\n\n", text)
text = re.sub(r"\n答案：", "\n\n> 答案：", text)

# 5. 错别字补丁第二轮
typo_more = {
    "教唳犯": "教唆犯",
    "罪罪分子": "犯罪分子",
    "犯罪所得收益刑事为案件": "犯罪所得收益刑事案件",
    "防卫装": "防卫装",  # 保留
    "财产犯": "财产犯",
    "回援性": "间接性",
    "白五": "",
    "犯器形态": "犯罪形态",
    "犯菲": "犯罪",
    "罪罪": "罪",  # OCR 把"该罪"识别成"该罪罪"等
    "成立罪": "成立",  # 慎，但有些"成立霏"已被前面替换
    "支耻住": "支配性",
    "直甦": "直接",
    "改窕": "犯罪",
    "工具，甲": "工具，甲",
    "饬亡": "伤亡",
    "贵": "责",  # "负贵"→"负责"
}
# 但 "贵" 是常见字，不能简单全替换。仅在"负贵"等少量上下文替换
text = text.replace("负贵", "负责")
text = text.replace("教唳犯", "教唆犯")
text = text.replace("罪罪分子", "犯罪分子")
text = text.replace("回援性", "间接性")
text = text.replace("犯器形态", "犯罪形态")
text = text.replace("饬亡", "伤亡")
text = text.replace("支耻住", "支配性")
text = text.replace("直甦", "直接")
text = text.replace("改窕", "犯罪")
text = text.replace("罪罪肯定成立", "罪肯定成立")

# 6. 多余空行收敛
text = re.sub(r"\n{3,}", "\n\n", text)

DST.write_text(text, encoding="utf-8")
print("第四轮补丁完成")
print(f"文件总行数：{text.count(chr(10))}")
