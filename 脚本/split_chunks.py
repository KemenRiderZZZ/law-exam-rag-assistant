#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
柏浪涛刑法书_整理版.md 二次切块脚本

策略：
1. 先按 markdown 标题（## ### #### #####）建立层级路径
2. 在每个最细标题块内：
   - 如果总长 <= 800 字符，整块作为一个 chunk
   - 如果超过 800 字符，按段落/列表项/表格边界二次切分
   - 切分时保持 overlap=100 字符
3. 输出 JSONL，每行一个 chunk，含 id/text/metadata
4. metadata 包含：book/chapter/section/subsection/subsub/source_line
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / '整理后文本' / '柏浪涛刑法书_整理版.md'
DST = PROJECT_ROOT / '切块' / '柏浪涛刑法书_chunks.jsonl'

CHUNK_SIZE = 800
OVERLAP = 100
MIN_CHUNK_SIZE = 100  # 太短的块尝试和上一个合并


def parse_headings(text: str):
    """
    扫描全文，输出每行的标题层级路径 (chapter, section, subsection, subsub, subsubsub)
    返回 [(line_no, line_text, path_dict), ...]
    """
    lines = text.split("\n")
    state = {
        "book": None,
        "chapter": None,    # ##
        "section": None,    # ###
        "subsection": None, # ####
        "subsub": None,     # #####
    }
    out = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,5})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 1:
                state["book"] = title
                state["chapter"] = None
                state["section"] = None
                state["subsection"] = None
                state["subsub"] = None
            elif level == 2:
                state["chapter"] = title
                state["section"] = None
                state["subsection"] = None
                state["subsub"] = None
            elif level == 3:
                state["section"] = title
                state["subsection"] = None
                state["subsub"] = None
            elif level == 4:
                state["subsection"] = title
                state["subsub"] = None
            elif level == 5:
                state["subsub"] = title
        out.append((i + 1, line, dict(state)))
    return out


def split_into_blocks(parsed):
    """
    按"最深标题块"分组：每个最深标题（##### 或 #### 或 ### 或 ## 一级及以下）下的连续行作为一个 block
    返回 [(start_line, end_line, path_dict, body_lines), ...]
    """
    blocks = []
    current = None
    for ln, line, state in parsed:
        # 标题行本身开启新块
        if re.match(r"^#{1,5}\s+", line):
            if current is not None:
                blocks.append(current)
            current = {
                "start": ln,
                "end": ln,
                "path": state,
                "lines": [line],
            }
        else:
            if current is None:
                current = {
                    "start": ln,
                    "end": ln,
                    "path": state,
                    "lines": [line],
                }
            else:
                current["lines"].append(line)
                current["end"] = ln
    if current is not None:
        blocks.append(current)
    return blocks


def split_long_block(block, max_size=CHUNK_SIZE, overlap=OVERLAP):
    """
    把单个超长 block 按段落边界二次切分。
    优先在以下边界切：
      1. 空行（段落分隔）
      2. 列表项开头（数字./- /（数字））
      3. 【xxx】结构化标记
      4. 表格分隔（|）
      5. 例N/题N
    """
    body = "\n".join(block["lines"]).strip()
    if len(body) <= max_size:
        return [body]

    # 取出标题行（##### xxx），作为每段的前缀以保留语境
    head = ""
    body_lines = block["lines"]
    if body_lines and re.match(r"^#{1,5}\s+", body_lines[0]):
        head = body_lines[0]
        body_lines = body_lines[1:]
    body_text = "\n".join(body_lines).strip()

    # 按"段落边界"分块：以连续两个换行为天然分块点
    paragraphs = re.split(r"\n\n+", body_text)

    chunks_text = []
    cur = head + "\n\n" if head else ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 如果加进当前块还没超：加进去
        if len(cur) + len(para) + 2 <= max_size:
            cur = cur + para + "\n\n"
        else:
            # 当前块成形
            if len(cur.strip()) > MIN_CHUNK_SIZE:
                chunks_text.append(cur.strip())
            # 单个 para 自身超了，硬切
            if len(para) > max_size:
                # 按句号/分号切
                sentences = re.split(r"(?<=[。！？；])", para)
                cur2 = head + "\n\n" if head else ""
                for s in sentences:
                    if len(cur2) + len(s) <= max_size:
                        cur2 += s
                    else:
                        if len(cur2.strip()) > MIN_CHUNK_SIZE:
                            chunks_text.append(cur2.strip())
                        # overlap：保留尾部 100 字符
                        tail = cur2[-overlap:] if len(cur2) > overlap else ""
                        cur2 = (head + "\n\n" if head else "") + tail + s
                if cur2.strip() and len(cur2.strip()) > MIN_CHUNK_SIZE:
                    chunks_text.append(cur2.strip())
                cur = head + "\n\n" if head else ""
            else:
                # overlap：从上一块尾部取 100 字符跟到新块前面
                tail = cur[-overlap:] if len(cur) > overlap else ""
                cur = (head + "\n\n" if head else "") + tail + para + "\n\n"

    if cur.strip() and len(cur.strip()) > MIN_CHUNK_SIZE:
        chunks_text.append(cur.strip())

    return chunks_text


def make_chunk_id(meta, idx):
    parts = []
    if meta.get("chapter"):
        parts.append(meta["chapter"][:8].replace(" ", ""))
    if meta.get("section"):
        parts.append(meta["section"][:8].replace(" ", ""))
    if meta.get("subsub"):
        parts.append(meta["subsub"][:6].replace(" ", ""))
    parts.append(f"{idx:04d}")
    return "::".join(parts)


def main():
    text = SRC.read_text(encoding="utf-8")
    parsed = parse_headings(text)
    blocks = split_into_blocks(parsed)

    chunks = []
    chunk_idx = 0
    for blk in blocks:
        path = blk["path"]
        # 过滤无 chapter 的（如目录、知识体系前的导言）
        sub_chunks = split_long_block(blk)
        for sc in sub_chunks:
            chunk_idx += 1
            meta = {
                "book": path.get("book") or "柏浪涛刑法专题讲座精讲卷（2026版）",
                "chapter": path.get("chapter"),
                "section": path.get("section"),
                "subsection": path.get("subsection"),
                "subsub": path.get("subsub"),
                "source_line_start": blk["start"],
                "source_line_end": blk["end"],
                "char_count": len(sc),
            }
            chunks.append({
                "id": make_chunk_id(meta, chunk_idx),
                "text": sc,
                "metadata": meta,
            })

    # 写入 JSONL
    with DST.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 统计
    sizes = [len(c["text"]) for c in chunks]
    print(f"共生成 chunks：{len(chunks)}")
    print(f"平均字符：{sum(sizes) / len(sizes):.0f}")
    print(f"最大块：{max(sizes)} 字符")
    print(f"最小块：{min(sizes)} 字符")
    buckets = {"<300": 0, "300-600": 0, "600-900": 0, "900-1200": 0, ">1200": 0}
    for s in sizes:
        if s < 300: buckets["<300"] += 1
        elif s < 600: buckets["300-600"] += 1
        elif s < 900: buckets["600-900"] += 1
        elif s < 1200: buckets["900-1200"] += 1
        else: buckets[">1200"] += 1
    print("分布：")
    for k, v in buckets.items():
        print(f"  {k}: {v}")
    print(f"输出：{DST}")


if __name__ == "__main__":
    main()
