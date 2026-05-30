#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二次清理切块产物：
1. 删除目录块（纯导航不入库）
2. 合并孤标题块（标题+下一个正文块）
3. 把 900~2000 字符的少数超长块再切一次
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / '切块' / '柏浪涛刑法书_chunks.jsonl'
DST = PROJECT_ROOT / '切块' / '柏浪涛刑法书_chunks.jsonl'

CHUNK_SIZE = 800
MIN_KEEP = 50  # 小于这个字符的块直接合并到下一块

chunks = [json.loads(line) for line in SRC.open(encoding="utf-8")]
print(f"原始块数：{len(chunks)}")

# 1. 删除目录块（chapter == "目录" 或 text 主要是 "- 第 N 讲"）
def is_toc(c):
    if c["metadata"].get("chapter") == "目录":
        return True
    text = c["text"]
    # 目录的特征：连续的 "- 第N讲" 或 "  - 第N节"
    toc_lines = re.findall(r"^\s*-\s*第[一二三四五六七八九十百零\d]+[讲节]", text, re.M)
    if len(toc_lines) >= 3:
        return True
    return False

chunks = [c for c in chunks if not is_toc(c)]
print(f"删目录后：{len(chunks)}")

# 2. 合并孤标题块（< 50 字符且只是标题）到下一块
def is_lone_title(text):
    s = text.strip()
    # 只有一两行 # 开头
    lines = [l for l in s.split("\n") if l.strip()]
    if len(lines) <= 2 and all(l.startswith("#") for l in lines):
        return True
    if len(s) < MIN_KEEP and s.startswith("#"):
        return True
    return False

merged = []
i = 0
while i < len(chunks):
    c = chunks[i]
    if is_lone_title(c["text"]) and i + 1 < len(chunks):
        # 合并到下一块的前面
        next_c = chunks[i + 1]
        next_c["text"] = c["text"].strip() + "\n\n" + next_c["text"]
        next_c["metadata"]["source_line_start"] = c["metadata"]["source_line_start"]
        next_c["metadata"]["char_count"] = len(next_c["text"])
        merged.append(next_c)
        i += 2
    else:
        merged.append(c)
        i += 1
chunks = merged
print(f"合并孤标题后：{len(chunks)}")

# 3. 对 > 1000 字符的块再切一次
def re_split(text, max_size=CHUNK_SIZE, overlap=100):
    # 按段落切
    paragraphs = re.split(r"\n\n+", text)
    out = []
    cur = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(cur) + len(p) + 2 <= max_size:
            cur = (cur + "\n\n" + p) if cur else p
        else:
            if cur:
                out.append(cur)
                tail = cur[-overlap:] if len(cur) > overlap else ""
                cur = tail + p if len(tail) + len(p) <= max_size else p
            else:
                # 单段超大：句号切
                sents = re.split(r"(?<=[。！？；])", p)
                cur2 = ""
                for s in sents:
                    if len(cur2) + len(s) <= max_size:
                        cur2 += s
                    else:
                        if cur2:
                            out.append(cur2)
                        cur2 = (cur2[-overlap:] if len(cur2) > overlap else "") + s
                if cur2:
                    cur = cur2
    if cur:
        out.append(cur)
    return out

final = []
for c in chunks:
    if c["metadata"]["char_count"] > 1000:
        sub_texts = re_split(c["text"])
        if len(sub_texts) > 1:
            for j, t in enumerate(sub_texts):
                new_c = json.loads(json.dumps(c))  # deepcopy
                new_c["text"] = t
                new_c["metadata"]["char_count"] = len(t)
                new_c["id"] = c["id"] + f"-p{j+1}"
                final.append(new_c)
        else:
            final.append(c)
    else:
        final.append(c)

chunks = final
print(f"再切超长块后：{len(chunks)}")

# 4. 重新分配 id（按顺序）
for i, c in enumerate(chunks, start=1):
    # 保留语义化的 id 末尾，同时加全局序号
    c["chunk_index"] = i

# 写回
with DST.open("w", encoding="utf-8") as f:
    for c in chunks:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

# 统计
sizes = [len(c["text"]) for c in chunks]
print(f"\n=== 最终统计 ===")
print(f"块数：{len(chunks)}")
print(f"平均字符：{sum(sizes)/len(sizes):.0f}")
print(f"最大：{max(sizes)}")
print(f"最小：{min(sizes)}")

buckets = {"<200": 0, "200-400": 0, "400-600": 0, "600-800": 0, "800-1000": 0, ">1000": 0}
for s in sizes:
    if s < 200: buckets["<200"] += 1
    elif s < 400: buckets["200-400"] += 1
    elif s < 600: buckets["400-600"] += 1
    elif s < 800: buckets["600-800"] += 1
    elif s < 1000: buckets["800-1000"] += 1
    else: buckets[">1000"] += 1
print("分布：")
for k, v in buckets.items():
    print(f"  {k}: {v}")
