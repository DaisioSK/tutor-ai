"""概念名词核对：故事括号里注的概念，在技术要点里有没有"中文（English）"并且有解释。
用法：python3 concepts.py <story-table.md|parts/actNN.md> [--all-tables <story-table.md>]
  对每个文件里的行，取故事格括号里的中文概念，判三种：
    missing   全表技术要点都没提到这个词                         → 要补：名称（English）：解释
    no_en     技术要点提到了，但第一次出现处后面没跟英文括号      → 要补英文
    ok
  --all-tables：判"第一次出现"时看整张总表（并行修各幕时用）；不给就只看本文件。"""
import re
import sys
from pathlib import Path

args = sys.argv[1:]
full = Path(args[args.index("--all-tables") + 1]) if "--all-tables" in args else None
target = Path(args[0])


def rows_of(p):
    out = []
    for r in p.read_text(encoding="utf-8").split("\n"):
        if re.match(r"^\|\s*\*\*第", r):
            c = [x.strip() for x in re.split(r"(?<!\\)\|", r.strip())[1:-1]]
            if len(c) >= 4:
                out.append(c)
    return out


rows = rows_of(target)
allrows = rows_of(full) if full else rows
tech_all = [c[2] for c in allrows]
SKIP = re.compile(r"^[\d\s.,%×/=+\-−~≈<>≤≥ⁿ²ρλμ]+$|^第|^§|见|例|即|也就是|比如|约")
bad = {"missing": [], "no_en": []}
seen = set()
for c in rows:
    for term in re.findall(r"（([^（）]{2,16})）", c[1]):
        term = re.split(r"[，、,；;]", term)[0].strip()
        if not term or SKIP.search(term) or re.fullmatch(r"[A-Za-z0-9 ._/\-]+", term) or term in seen:
            continue
        seen.add(term)
        hit = next((t for t in tech_all if term in t), None)
        if hit is None:
            bad["missing"].append((c[0][:18], term))
            continue
        k = hit.index(term) + len(term)
        if not re.match(r"\s*[（(][^）)]*[A-Za-z]", hit[k:k + 40]):
            bad["no_en"].append((c[0][:18], term))
print(f"{target.name}: 故事概念 {len(seen)} · 技术要点没提到 {len(bad['missing'])} · 提到但首现没英文 {len(bad['no_en'])}")
for k, v in bad.items():
    if v:
        print(f"[{k}]", "；".join(f"{w.replace('**', '')}→{t}" for w, t in v))
