"""前瞻章节的"全"：每一集、每一个 §小节，都能在前瞻里对号入座。

用法：python3 preview_check.py <O>
读 O/src/work/section-index.md（preview_index.py 生成）和 O/parts/1-preview.md。
查三件事：
  1. 每一集都有 `#### 第 N 集` 标题，且标题括号里的课件页与小节索引一致；
  2. 每一个 §小节都在前瞻里被指到（"§1.5–1.8" 这种区间算覆盖其中每一节）；
  3. 前瞻指到的 § 都在小节索引里（不指向不存在的节）。
全部通过打印 PASS；否则逐条列出，退出码 1。
"""
import re
import sys
from pathlib import Path

O = Path(sys.argv[1])
index = (O / "src" / "work" / "section-index.md").read_text(encoding="utf-8")
text = (O / "parts" / "1-preview.md").read_text(encoding="utf-8")

ep_pages = {int(m.group(1)): m.group(2).strip()
            for m in re.finditer(r"^\| (\d+) \| [^|]+ \| §[^|]+ \| ([^|]*) \|$", index, re.M)}
sec_ep = {m.group(2): int(m.group(1))
          for m in re.finditer(r"^\| (\d+) \| §(\d+\.\d+) \|", index, re.M)}


def expand(a: str, b: str, c: str, d: str) -> list:
    """§a.b 或 §a.b–(c.)d → 小节编号列表；跨章区间按小节索引里实有的节展开。"""
    if not d:
        return [f"{a}.{b}"]
    lo, hi = (int(a), int(b)), (int(c or a), int(d))
    return [s for s in sec_ep if lo <= tuple(map(int, s.split("."))) <= hi]


cited = set()
for a, b, c, d in re.findall(r"§(\d+)\.(\d+)(?:\s*[–-]\s*(?:(\d+)\.)?(\d+))?", text):
    cited.update(expand(a, b, c, d))

problems = []
heads = {int(m.group(1)): m.group(2) for m in re.finditer(r"^#### 第 (\d+) 集.*?（([^）]*)）\s*$", text, re.M)}
for n, pages in sorted(ep_pages.items()):
    if n not in heads:
        problems.append(f"缺集：第 {n} 集没有 `#### 第 {n} 集` 标题")
    elif pages and heads[n] != pages:
        problems.append(f"课件页不符：第 {n} 集标题写 {heads[n]}，小节索引是 {pages}")
missing = [s for s in sec_ep if s not in cited]
if missing:
    by = {}
    for s in missing:
        by.setdefault(sec_ep[s], []).append("§" + s)
    problems += [f"没指到：第 {n} 集 {'、'.join(ss)}" for n, ss in sorted(by.items())]
problems += [f"指向不存在的节：§{s}" for s in sorted(cited - set(sec_ep))]

print(f"集 {len(heads)}/{len(ep_pages)}，§小节 {len(sec_ep) - len(missing)}/{len(sec_ep)} 被指到")
print("\n".join(problems) if problems else "PASS")
sys.exit(1 if problems else 0)
