#!/usr/bin/env python3
"""
总范式（exercise_cheat.md）的覆盖检查：覆盖表里列到的每一道题，每一个小问都要归到某个范式，且那个范式真的存在。

用法:
    python3 check_cheat.py <drill_dir>
读 <drill_dir>/exercise_cheat.md 末尾的「## 覆盖」：每题一行 `- [题](组/文件.pdf)　(a)(i) → 道德化；(b) → d-分离：判两个点`。
查三件事：
  1. 题目 md 里每个 `### (x)` 小问都出现在该题的覆盖行里（不漏小问）；
  2. 覆盖行里的小问在题目 md 里真的存在（不写错）；
  3. 引用的关键字在文中有以它开头的 `### 关键字…` 标题。
全部通过打印 PASS；否则逐条列出，退出码 1。
"""
import re
import sys
from pathlib import Path

LABEL = re.compile(r"\([a-z]+\)(?:\([ivx]+\))?")


def main(root: Path) -> list:
    text = (root / "exercise_cheat.md").read_text(encoding="utf-8")
    section = text.split("## 覆盖", 1)[1]
    covered, refs = {}, set()
    for line in re.findall(r"^- (.+)$", section, re.M):
        link = re.search(r"\]\(([^)]+)\.pdf\)", line)
        if not link:
            continue
        labels = covered.setdefault(root / (link.group(1) + ".md"), set())
        for seg in line[link.end():].split("；"):
            ref = re.search(r"→\s*(.+?)\s*$", seg)
            labels.update(LABEL.findall(seg))
            if ref:
                refs.add(ref.group(1))
    probs = []
    for md, labels in covered.items():
        if not md.exists():
            probs.append(f"覆盖表指向不存在的题：{md.relative_to(root)}")
            continue
        subs = {LABEL.match(h).group(0) for h in re.findall(r"^### (.+)$", md.read_text(encoding="utf-8"), re.M)
                if LABEL.match(h)}
        probs += [f"{md.stem}：小问 {s} 没归到任何范式" for s in sorted(subs - labels)]
        probs += [f"{md.stem}：覆盖表写了 {s}，题里没有这一问" for s in sorted(labels - subs)]
    heads = re.findall(r"^### (.+)$", text.split("## 覆盖", 1)[0], re.M)
    for r in sorted(refs):
        if not any(h.startswith(r) for h in heads):
            probs.append(f"引用了「{r}」，正文没有以它开头的 ### 标题")
    print(f"覆盖 {len(covered)} 题")
    return probs


if __name__ == "__main__":
    probs = main(Path(sys.argv[1]))
    print("\n".join(probs) if probs else "PASS")
    sys.exit(1 if probs else 0)
