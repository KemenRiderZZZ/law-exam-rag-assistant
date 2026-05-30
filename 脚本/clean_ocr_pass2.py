#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二次清洗：补 v1 脚本未处理的细节。"""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DST = PROJECT_ROOT / '整理后文本' / '柏浪涛刑法书_整理版.md'

text = DST.read_text(encoding="utf-8")

# 1. 双点列表项：1.  .xxx → 1. xxx ；2.  .xxx → 2. xxx
text = re.sub(r"(\n\d+)\.\s+\.\s*", r"\1. ", text)
# 1. **.**xxx 残留情形（如果 v1 脚本漏处理）
text = re.sub(r"(\n\d+)\.\s+\*\*\.\*\*\s*", r"\1. ", text)
# 单独空白前缀
text = re.sub(r"(\n\d+)、\*\*\.\*\*", r"\1、", text)

# 2. 替代危险条目内的 （-） → （一）
text = re.sub(r"（-）", "（一）", text)
text = re.sub(r"\(-\)", "（一）", text)

# 3. 表内或行内 OCR "*■" -> 顿号或省略
text = text.replace("*■", "")

# 4. 对孤立的章节标题做补救：如 "五讲 客观要件一：行为" → "## 第五讲 客观要件一：行为"
chapter_kw = {
    "五讲": "第五讲",
    "六讲": "第六讲",
    "七讲": "第七讲",
    "八讲": "第八讲",
    "九讲": "第九讲",
    "十讲": "第十讲",
    "十一讲": "第十一讲",
    "十二讲": "第十二讲",
    "十三讲": "第十三讲",
    "十四讲": "第十四讲",
    "十五讲": "第十五讲",
    "十六讲": "第十六讲",
    "十七讲": "第十七讲",
    "十八讲": "第十八讲",
    "十九讲": "第十九讲",
    "二十讲": "第二十讲",
    "二十一讲": "第二十一讲",
    "二十二讲": "第二十二讲",
    "二十三讲": "第二十三讲",
    "二十四讲": "第二十四讲",
    "二十五讲": "第二十五讲",
}

# 找形如 "\n五讲 xxx\n" 这种没带 "第" 字的孤立讲标题
for short, full in chapter_kw.items():
    # 匹配行首独立的"五讲 客观要件一：行为"
    pat = re.compile(r"\n" + short + r"\s+([^\n]+)\n")
    text = pat.sub(lambda m: f"\n\n## {full} {m.group(1).strip()}\n\n", text)

# 5. 删除一些常见残留乱码：单引号孤立 ' 的尾巴
text = re.sub(r"\n\s*'\s*\n", "\n", text)

# 6. 多余空行收敛
text = re.sub(r"\n{3,}", "\n\n", text)

# 7. 列表前的空行：把 "段落\n1. xxx" 之间确保有空行
text = re.sub(r"([^\n])\n(\d+\.\s)", r"\1\n\n\2", text)

DST.write_text(text, encoding="utf-8")
lines = text.count("\n")
print(f"二次清洗完成，文件行数：{lines}")
