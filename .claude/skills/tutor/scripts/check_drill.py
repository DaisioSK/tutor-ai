#!/usr/bin/env python3
"""
练习题逐题拆解的结构检查：每一小问是否五块齐全、顺序对、关键图重新嵌入了。

用法:
    python3 check_drill.py <drill_dir>
对每份 `*/[0-9]*.md`：
  - 逐问解答里的每个 `### (x)` 小问，必须依次有 引用框题面、`#### 图`、`#### 中文拆解`、`#### 思路`、`#### English solution · 中文对照`；
  - 题目本身带图（英文原题里有图片）时，每一小问的 `#### 图` 里必须有图片；没有图的题，`#### 图` 里至少要有表格或已知量文字；
  - 题目有一节「## 通用思路」（这类题的通用做法，只讲一次）；每一小问的思路分「这一问的思路」「用它看这一问」两块，
    且不再重复通用做法；English solution 里要有 ↳ 中文对照行；
  - 题里只要有一处 `#### 傻瓜拆解（完全版）`，每一小问都要有，位置在思路之后、English solution 之前。
全部通过打印 PASS；否则逐条列出，退出码 1。
"""
import re
import sys
from pathlib import Path

BASE_PARTS = ["图", "中文拆解", "思路", "English solution"]
WALK_PARTS = ["图", "中文拆解", "思路", "傻瓜拆解", "English solution"]


def check(md: Path) -> list:
    text = md.read_text(encoding="utf-8")
    probs = []
    PARTS = WALK_PARTS if "#### 傻瓜拆解" in text else BASE_PARTS
    head, _, rest = text.partition("## 逐问解答")
    if not rest:
        return ["没有「## 逐问解答」"]
    has_fig = "![" in head.split("## 中文解释")[0]
    rest = rest.split("\n## ")[0]                      # 到下一个二级标题（易错点）为止
    subs = re.split(r"^### ", rest, flags=re.M)[1:]
    if not subs:
        return ["逐问解答里没有 ### 小问"]
    if "## 通用思路" not in head:
        probs.append("缺「## 通用思路」（放在考点分析之后、逐问解答之前）")
    for sub in subs:
        name = sub.split("\n", 1)[0].strip()[:30]
        heads = re.findall(r"^#### (.+)$", sub, re.M)
        seq = [next((p for p in PARTS if p in h), None) for h in heads]
        missing = [p for p in PARTS if p not in seq]
        if missing:
            probs.append(f"{name}：缺 {'、'.join(missing)}")
            continue
        if [p for p in seq if p] != PARTS:
            probs.append(f"{name}：顺序不对（{' → '.join(p or '?' for p in seq)}）")
        body = dict(zip(seq, re.split(r"^#### .+$", sub, flags=re.M)[1:]))
        if has_fig and "![" not in body["图"] and "<img" not in body["图"]:
            probs.append(f"{name}：#### 图 里没有重新嵌入图片")
        if not has_fig and len(body["图"].strip()) < 10:
            probs.append(f"{name}：#### 图 是空的")
        if "这一问的思路" not in body["思路"] or "用它看这一问" not in body["思路"]:
            probs.append(f"{name}：思路没有分「这一问的思路」「用它看这一问」两块")
        if "通用快速判法" in body["思路"]:
            probs.append(f"{name}：思路里又重复了通用做法（应放到 ## 通用思路）")
        if "↳" not in body["English solution"]:
            probs.append(f"{name}：English solution 没有 ↳ 中文对照")
        if not re.search(r"^>\s*\S", sub.split("#### ")[0], re.M):
            probs.append(f"{name}：小问开头没有英文题面引用框")
    return probs


if __name__ == "__main__":
    root = Path(sys.argv[1])
    bad = 0
    files = sorted(root.glob("*/[0-9]*.md"))
    for md in files:
        probs = check(md)
        if probs:
            bad += 1
            print(f"✗ {md.relative_to(root)}")
            for p in probs:
                print(f"    {p}")
    print(f"{len(files) - bad}/{len(files)} 份通过")
    print("PASS" if not bad else "")
    sys.exit(1 if bad else 0)
