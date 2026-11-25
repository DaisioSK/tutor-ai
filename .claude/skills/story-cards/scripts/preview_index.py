"""前瞻章节的备料：每一集覆盖哪些 §小节、各在课件哪几页。

用法：python3 preview_index.py <O> <book_dir>
读 O/world.md 的「集表」（`| 集 | 幕（卷） | 章 | 情景标题 | 覆盖 § | …`）、
<book_dir>/NN-*.md 的节标题（`## §N.M 标题`）和 <book_dir>/../source-map.json（可选，§N.M → slides 页段或 Scribe 页），
写 O/src/work/section-index.md：先是集总表（集 | 幕 | §范围 | 课件页），再是逐节表。只依赖 world.md，各幕没写也能跑。
"""
import json
import re
import sys
from pathlib import Path

O, book = Path(sys.argv[1]), Path(sys.argv[2])
smap = book.parent / "source-map.json"
SRC = json.loads(smap.read_text(encoding="utf-8")) if smap.exists() else {}
TITLE = {m.group(1): m.group(2).strip()
         for f in sorted(book.glob("[0-9][0-9]-*.md"))
         for m in re.finditer(r"^## §(\d+\.\d+)\s+(.*?)(?:\s*\[[^\]]*\])?$", f.read_text(encoding="utf-8"), re.M)}


def secs_in(rng: str) -> list:
    """`§1.1–1.10` / `§11.14–11.17` / `§3.5` → 小节编号列表。"""
    out = []
    for a, b, c, d in re.findall(r"§(\d+)\.(\d+)(?:\s*[–-]\s*(?:(\d+)\.)?(\d+))?", rng):
        ch_end = int(c or a)
        for ch in range(int(a), ch_end + 1):
            lo = int(b) if ch == int(a) else 1
            hi = int(d or b) if ch == ch_end else max(int(k.split(".")[1]) for k in TITLE if k.startswith(f"{ch}."))
            out += [f"{ch}.{k}" for k in range(lo, hi + 1)]
    return out


def span(secs: list) -> str:
    """一组 §小节 → `L1 Slides p.5–44`；没有 slides 的讲给 Scribe 页。"""
    by = {}
    for s in secs:
        if s in SRC:
            by.setdefault(SRC[s]["lecture"], []).append(SRC[s])
    out = []
    for lec, rs in by.items():
        sl = [r["slides"] for r in rs if r.get("slides")]
        if sl:
            out.append(f"L{lec} Slides p.{min(a for a, _ in sl)}–{max(b for _, b in sl)}")
        else:
            ps = [r["scribe_page"] for r in rs]
            out.append(f"L{lec} Scribe p.{min(ps)}–{max(ps)}")
    return " · ".join(out)


world = (O / "world.md").read_text(encoding="utf-8").splitlines()
head = next(i for i, ln in enumerate(world) if ln.startswith("| 集 |"))
cols = [c.strip() for c in world[head].strip("|").split("|")]
ci, ca = cols.index("覆盖 §"), cols.index("幕（卷）")
eps = []
for ln in world[head + 2:]:
    if not ln.startswith("|"):
        break
    c = [x.strip() for x in ln.strip("|").split("|")]
    eps.append((c[0], c[ca].split("（")[0], c[ci], secs_in(c[ci])))

lines = ["# 小节索引（前瞻用：集的课件页、指路的 §编号）", "",
         "## 集总表", "", "| 集 | 幕 | §范围 | 课件页 |", "|---|---|---|---|"]
lines += [f"| {n} | {act} | {rng} | {span(ss)} |" for n, act, rng, ss in eps]
lines += ["", "## 逐节", "", "| 集 | 小节 | 标题 | 课件页 |", "|---|---|---|---|"]
lines += [f"| {n} | §{s} | {TITLE.get(s, '')} | {span([s])} |" for n, _, _, ss in eps for s in ss]
out = O / "src" / "work" / "section-index.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out, f"{len(eps)} 集，{sum(len(e[3]) for e in eps)} 节")
