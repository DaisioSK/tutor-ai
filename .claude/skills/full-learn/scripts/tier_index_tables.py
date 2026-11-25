#!/usr/bin/env python3
"""
把章首索引表第三列"后面有几个知识点要用到它（数字）"换成三档"后面用得多不多（很多/一些/很少）"。

chapter 范式（2026-11-01 修订）规定该列只印三档，不印分量计数——冷读者看不懂"190"。
分档：≥15 很多，5–14 一些，<5 很少。

用法:
    python tier_index_tables.py <full-learn 工作区> [--dry-run]
"""

import glob
import os
import re
import sys

OLD_HEAD = re.compile(r"^(\|\s*§\s*\|[^|]*\|)\s*后面有几个知识点(?:要)?用到它\s*\|\s*$")


def tier(n):
    return "很多" if n >= 15 else ("一些" if n >= 5 else "很少")


def convert(text):
    lines = text.split("\n")
    changed = 0
    i = 0
    while i < len(lines):
        m = OLD_HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        lines[i] = m.group(1) + " 后面用得多不多 |"
        j = i + 2  # 跳过分隔行
        while j < len(lines) and lines[j].startswith("|"):
            cells = lines[j].rstrip().rstrip("|").split("|")
            last = cells[-1].strip()
            if re.fullmatch(r"\d+", last):
                cells[-1] = " " + tier(int(last)) + " "
                lines[j] = "|".join(cells) + "|"
                changed += 1
            j += 1
        i = j
    return "\n".join(lines), changed


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    total = 0
    for p in sorted(glob.glob(os.path.join(args[0], "book", "[0-9][0-9]-*.md"))):
        text = open(p, encoding="utf-8").read()
        new, n = convert(text)
        if n:
            total += n
            print(f"{os.path.basename(p)}: {n} 行")
            if "--dry-run" not in sys.argv:
                open(p, "w", encoding="utf-8").write(new)
    print(f"合计 {total} 行{'（dry-run 未写入）' if '--dry-run' in sys.argv else ''}")


if __name__ == "__main__":
    main()
