"""节与节的承接线索：给各幕作者写「↩ 承接」用。
用法：python3 links.py <full-learn 工作区> <起章> <止章> [out.md]
  对每个 `## §N.M`，从书和科技树里抽三样，作者据此写一句承接：
    依赖    该节标的科技树节点（`<!-- nodes: … -->`）在 tree.json 里 requires 的节点，落在前面哪几节   ← 机制上靠谁
    回指    正文里点名的前面的 §                                                                ← 书自己说用到了谁
    开场    🗺️ 路线行 + 第一段含"上一节 / 前面 / 刚才 / §"的过渡句                                ← 书自己怎么接上的
  只列在它前面的节；同一章的上一节总会列出，承接最常见的就是它。"""
import json
import re
import sys
from pathlib import Path

ws, a, b = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
out = Path(sys.argv[4]) if len(sys.argv) > 4 else None
book = ws / "book"
tree = json.loads((ws / "tree.json").read_text(encoding="utf-8"))
nodes = tree["nodes"] if isinstance(tree["nodes"], list) else list(tree["nodes"].values())
req = {n["id"]: n.get("requires", []) for n in nodes}
name = {n["id"]: n.get("name", "") for n in nodes}

key = lambda s: tuple(map(int, s.split(".")))  # noqa: E731
secs = []                                      # [(§, 标题, 正文)]
for f in sorted(book.glob("[0-9][0-9]-*.md")):
    parts = re.split(r"^## §(\d+\.\d+)\s+(.*)$", f.read_text(encoding="utf-8"), flags=re.M)
    for k in range(1, len(parts) - 2, 3):
        secs.append((parts[k], parts[k + 1].strip(), parts[k + 2]))
secs.sort(key=lambda x: key(x[0]))
host = {}                                      # 节点 → 首次出现的节
for s, _, body in secs:
    for nid in re.findall(r"N-\d+", (re.search(r"<!--\s*nodes:([^>]*)-->", body) or [None, ""])[1] if re.search(r"<!--\s*nodes:", body) else ""):
        host.setdefault(nid, s)

lines = []
prev = None
for s, title, body in secs:
    ch = key(s)[0]
    if a <= ch <= b:
        m = re.search(r"<!--\s*nodes:([^|>]*)", body)
        mine = re.findall(r"N-\d+", m.group(1)) if m else []
        dep = sorted({host[r] for n in mine for r in req.get(n, []) if r in host and key(host[r]) < key(s)}, key=key)
        dep_txt = "；".join(f"§{h}（{'、'.join(dict.fromkeys(name[r][:18] for n in mine for r in req.get(n, []) if host.get(r) == h))}）" for h in dep)
        back = sorted({x for x in re.findall(r"§(\d+\.\d+)", body) if key(x) < key(s)}, key=key)
        route = (re.search(r"^> 🗺️\s*(.+)$", body, re.M) or [None, ""])[1]
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip() and not p.lstrip().startswith((">", "<!--", "|", "$$", "#"))]
        bridge = next((p for p in paras[:4] if re.search(r"上一节|上一章|前面|刚才|上面|§\d", p)), paras[0] if paras else "")
        lines += [f"### §{s} {title}",
                  f"- 上一节：§{prev}" if prev else "- 上一节：（无，全书第一节）",
                  f"- 依赖（科技树）：{dep_txt or '无'}",
                  f"- 回指（正文点名）：{'、'.join('§' + x for x in back) or '无'}",
                  f"- 路线：{route[:220]}",
                  f"- 开场过渡：{re.sub(r'\s+', ' ', bridge)[:260]}", ""]
    prev = s
text = "\n".join(lines)
if out:
    out.write_text(text, encoding="utf-8")
    print(out, sum(1 for x in lines if x.startswith("### ")), "节")
else:
    print(text)
