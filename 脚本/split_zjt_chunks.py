#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
柏浪涛真金题切块脚本

策略：以【考点】作为题目边界。
- 文件以"## 第N讲"组织
- 每段【考点】到下一段【考点】（或下一讲标题）之间是一道题
- 题号无需精确识别，按出现顺序编号 Q1~Q305
- 从题前文本中抽取考号、年份、题型
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / '整理后文本' / '柏浪涛真金题_整理版.md'
DST = PROJECT_ROOT / '切块' / '柏浪涛真金题_chunks.jsonl'


def parse_questions(text):
    lines = text.split("\n")

    # 第一步：标注每行的章节路径
    state = {"chapter": None, "section": None}
    line_paths = []
    for ln in lines:
        m2 = re.match(r"^##\s+(.+?)$", ln)
        m3 = re.match(r"^###\s+(.+?)$", ln)
        if m2:
            state["chapter"] = m2.group(1).strip()
            state["section"] = None
        elif m3:
            state["section"] = m3.group(1).strip()
        line_paths.append(dict(state))

    # 第二步：找每个【考点】所在行号
    kpt_lines = [i for i, ln in enumerate(lines) if "【考点】" in ln]
    if not kpt_lines:
        return []

    # 第三步：找每个 **【答案】X** 行号
    ans_lines = [i for i, ln in enumerate(lines)
                 if re.match(r"^\*\*【答案】[A-D]+\*\*", lines[i].strip())]

    # 切块逻辑：
    # 每道题的"题干起点" = 上一题的"答案行 +1"，但跳过空行/标题/章节起点
    # 题文 = [题干起点, 当前题的答案行]
    # 题的【考点】= 必须在 [题干起点, 答案行] 之间

    questions = []
    title_starts = set()  # 章节标题行号
    for i, ln in enumerate(lines):
        if re.match(r"^#+\s", ln):
            title_starts.add(i)
        # 引用块/分隔行也跳
        if ln.strip() in ("---", "") or ln.strip().startswith(">"):
            pass

    # 每个【考点】配对一个最近的下游答案行（有就有，没有就到下一考点前）
    # 题号按【考点】顺序编号
    used_ans = set()

    prev_end = -1  # 上一题的答案行号

    for q_idx, kpt_line in enumerate(kpt_lines):
        # 起点：从 prev_end+1 开始，跳过空行/章节标题/引用块/分隔线
        start = prev_end + 1
        while start < kpt_line:
            s = lines[start].strip()
            if not s:
                start += 1
                continue
            if start in title_starts:
                start += 1
                continue
            if s.startswith(">") or s == "---":
                start += 1
                continue
            break

        # 终点：找 kpt_line 之后的第一个答案行（且不超过下一考点）
        if q_idx + 1 < len(kpt_lines):
            next_kpt = kpt_lines[q_idx + 1]
        else:
            next_kpt = len(lines)

        # 在 (kpt_line, next_kpt) 之间找答案行
        end = next_kpt
        for a in ans_lines:
            if kpt_line < a < next_kpt and a not in used_ans:
                end = a + 1  # 包含答案行
                used_ans.add(a)
                break

        # 收集
        q_lines = lines[start:end]
        q_text = "\n".join(q_lines).strip()
        # 移除题文里嵌入的标题（# 开头）和引用说明
        q_text = re.sub(r"^#+\s.+?\n", "", q_text, flags=re.M)
        q_text = re.sub(r"^>\s.+?\n", "", q_text, flags=re.M)
        q_text = re.sub(r"^---\s*\n", "", q_text, flags=re.M)
        q_text = re.sub(r"\n\n+", "\n\n", q_text).strip()

        path = line_paths[kpt_line]

        if not q_text or len(q_text) < 30:
            prev_end = end - 1
            continue

        questions.append({
            "q_idx": q_idx + 1,
            "start_line": start + 1,
            "end_line": end,
            "text": q_text,
            "chapter": path.get("chapter"),
            "section": path.get("section"),
        })
        prev_end = end - 1

    return questions


def extract_metadata(q):
    """从题文抽取考号、年份、题型、答案、考点。"""
    text = q["text"]
    meta = {}

    # 先把题文头部 OCR 残留修一下，便于匹配
    head = text[:600]
    head = head.replace("金矗", "金题").replace("金題", "金题")
    head = re.sub(r"金\s*题?\s*[:：]", "金题-", head)  # 金: 金题:
    head = re.sub(r"(\d{4})-(\d)[:：](\d+)", r"\1-\2-\3", head)  # 2017-2:15 -> 2017-2-15
    head = re.sub(r"(\d{4})\s*[:：]\s*(\d)\s*-", r"\1-\2-", head)

    # 真题：YYYY-X-NN
    m_real = re.search(
        r"[（(]\s*(20\d{2})\s*[-–—]\s*(\d)\s*[-–—]\s*(\d{1,3})\s*[,，.\s]*([多单任主])",
        head
    )
    # 金题：YYYY金题-X-X-NN
    m_gold = re.search(
        r"[（(]?\s*(20\d{2})\s*金\s*题\s*[-–—]?\s*(\d)\s*[-–—]\s*(\d)\s*[-–—]\s*(\d{1,3})\s*[,，.\s]*([多单任主])",
        head
    )

    if m_real and (not m_gold or m_real.start() < m_gold.start()):
        meta["exam_year"] = int(m_real.group(1))
        meta["exam_id"] = f"{m_real.group(1)}-{m_real.group(2)}-{m_real.group(3)}"
        type_char = m_real.group(4)
    elif m_gold:
        meta["exam_year"] = int(m_gold.group(1))
        meta["exam_id"] = f"{m_gold.group(1)}金题-{m_gold.group(2)}-{m_gold.group(3)}-{m_gold.group(4)}"
        type_char = m_gold.group(5)
    else:
        meta["exam_year"] = None
        meta["exam_id"] = None
        type_char = None

    type_map = {"多": "多选", "单": "单选", "任": "案例题", "主": "主观题"}
    meta["question_type"] = type_map.get(type_char) if type_char else None

    # 答案
    m3 = re.search(r"\*\*【答案】([A-D]+)\*\*", text)
    if m3:
        meta["answer"] = m3.group(1)
    else:
        m3b = re.search(r"本题答案[为是：]\s*([A-D]+)", text)
        meta["answer"] = m3b.group(1) if m3b else None

    # 考点
    m4 = re.search(r"【考点】\s*([^\n【]+)", text)
    if m4:
        meta["knowledge_point"] = m4.group(1).strip().rstrip("，。 ")
    else:
        meta["knowledge_point"] = None

    return meta


def make_id(q, meta):
    chap = q.get("chapter") or "未知"
    chap_slug = re.sub(r"[\s第讲第节]", "", chap)[:12]
    return f"真金题::{chap_slug}::Q{q['q_idx']:03d}"


def main():
    text = SRC.read_text(encoding="utf-8")
    questions = parse_questions(text)
    print(f"识别题数: {len(questions)}")

    # 写出 JSONL
    chunks = []
    for q in questions:
        meta = extract_metadata(q)
        chunk = {
            "id": make_id(q, meta),
            "text": q["text"],
            "metadata": {
                "book": "柏浪涛刑法专题讲座真金题卷（2026版）",
                "doc_type": "真题解析",
                "chapter": q.get("chapter"),
                "section": q.get("section"),
                "question_index": q["q_idx"],
                "exam_id": meta.get("exam_id"),
                "exam_year": meta.get("exam_year"),
                "question_type": meta.get("question_type"),
                "answer": meta.get("answer"),
                "knowledge_point": meta.get("knowledge_point"),
                "source_line_start": q["start_line"],
                "source_line_end": q["end_line"],
                "char_count": len(q["text"]),
            },
        }
        chunks.append(chunk)

    with DST.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 统计
    sizes = [c["metadata"]["char_count"] for c in chunks]
    if sizes:
        print(f"平均: {sum(sizes)/len(sizes):.0f} 字符")
        print(f"最大: {max(sizes)}, 最小: {min(sizes)}")
        buckets = {"<500": 0, "500-1000": 0, "1000-1500": 0, "1500-2500": 0, ">2500": 0}
        for s in sizes:
            if s < 500: buckets["<500"] += 1
            elif s < 1000: buckets["500-1000"] += 1
            elif s < 1500: buckets["1000-1500"] += 1
            elif s < 2500: buckets["1500-2500"] += 1
            else: buckets[">2500"] += 1
        print("分布：")
        for k, v in buckets.items():
            print(f"  {k}: {v}")

    # 元数据完整度
    has_year = sum(1 for c in chunks if c["metadata"]["exam_year"])
    has_eid = sum(1 for c in chunks if c["metadata"]["exam_id"])
    has_ans = sum(1 for c in chunks if c["metadata"]["answer"])
    has_kp = sum(1 for c in chunks if c["metadata"]["knowledge_point"])
    print(f"\n元数据完整度（共 {len(chunks)} 题）：")
    print(f"  exam_year: {has_year}")
    print(f"  exam_id:   {has_eid}")
    print(f"  answer:    {has_ans}")
    print(f"  考点:      {has_kp}")

    print(f"\n输出: {DST}")


if __name__ == "__main__":
    main()
