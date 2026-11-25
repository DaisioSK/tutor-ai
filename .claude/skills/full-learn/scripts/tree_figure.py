#!/usr/bin/env python3
"""
tree_figure.py — 科技树图的离线渲染（render 方法 3「科技树图」）。

科技树是分层 DAG，章首地图那种"段里排卡片"画不出它。这里:
  1. 解析 mermaid flowchart（tree.md 里的那张，或书首里抄过去的那张）成图结构；
     没有 mermaid 时直接从 tree.json 的 requires / derives_from 建图；
  2. 用 tree.json 着色（生成元 → 根思想，kind=external → 材料外前置，分量前 25% → 高分量），
     mermaid 自带的类名（gen/root、ext、core/heavy/key）同样认；
  3. 最长路分层 + 重心法排序，matplotlib 画成 PNG（不联网、不跑 JS、无 graphviz 依赖）；
  4. matplotlib 不可用时退化成可读的分层列表 HTML（render_tree_list）。

图例只用读者的词（根思想 / 材料外前置），不印"生成元""external"这类内部代号。

单独调试:
    python3 tree_figure.py <full-learn 目录> [out.png]
"""
import html as html_mod
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 解析

EDGE_OP_RE = re.compile(r"\s*(<-->|-\.->|-\.-|==>|-->|---|--[ox])\s*(?:\|([^|]*)\|)?\s*")
EDGE_KIND = {"-->": "dep", "==>": "derive", "-.->": "compose", "-.-": "contrast",
             "---": "contrast", "<-->": "contrast", "--o": "compose", "--x": "dep"}
NODE_RE = re.compile(r"^([A-Za-z0-9_一-鿿.]+)\s*(.*?)\s*$", re.S)
CLASS_SUFFIX_RE = re.compile(r":::([\w-]+)\s*$")
SKIP_PREFIX = ("%%", "classDef", "style ", "linkStyle", "direction", "click ")


def norm_id(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", s.lower())


def _strip_shape(rest: str) -> str:
    rest = rest.strip()
    if not rest:
        return ""
    # [..] (..) ((..)) {..} [(..)] >..] [[..]] {{..}}
    m = re.match(r"^[\[\(\{>]+(.*?)[\]\)\}]+$", rest, re.S)
    lab = m.group(1) if m else rest
    lab = lab.strip().strip('"').strip("'").strip()
    return lab.replace("<br/>", "\n").replace("<br>", "\n")


def parse_mermaid_graph(src: str) -> dict:
    g = {"direction": "TB", "nodes": {}, "order": [], "edges": [], "groups": {}}
    cur_group = None

    def touch(tok: str):
        tok = tok.strip()
        if not tok:
            return None
        cls = None
        m = CLASS_SUFFIX_RE.search(tok)
        if m:
            cls = m.group(1)
            tok = tok[:m.start()].strip()
        m = NODE_RE.match(tok)
        if not m:
            return None
        nid, rest = m.group(1), m.group(2)
        node = g["nodes"].get(nid)
        if node is None:
            node = {"id": nid, "label": nid, "classes": set(), "group": cur_group}
            g["nodes"][nid] = node
            g["order"].append(nid)
        lab = _strip_shape(rest)
        if lab:
            node["label"] = lab
        if cls:
            node["classes"].add(cls)
        return nid

    for raw in src.split("\n"):
        line = raw.strip().rstrip(";")
        if not line or line.startswith(SKIP_PREFIX):
            continue
        m = re.match(r"^(flowchart|graph)\s*(TB|TD|BT|LR|RL)?", line)
        if m:
            g["direction"] = {"TD": "TB"}.get(m.group(2) or "TB", m.group(2) or "TB")
            continue
        if line == "end":
            cur_group = None
            continue
        m = re.match(r'^subgraph\s+([^\[\s]+)\s*(?:\[\s*"?(.*?)"?\s*\])?\s*$', line)
        if m:
            cur_group = m.group(2) or m.group(1)
            g["groups"].setdefault(cur_group, [])
            continue
        m = re.match(r"^class\s+([\w,\s.-]+?)\s+([\w-]+)$", line)
        if m:
            for n in re.split(r"[,\s]+", m.group(1).strip()):
                if n in g["nodes"]:
                    g["nodes"][n]["classes"].add(m.group(2))
            continue
        parts = EDGE_OP_RE.split(line)
        # parts = [lhs, op, label, rhs, op, label, rhs, ...]
        sides = parts[0::3]
        ops = parts[1::3]
        ids_per_side = [[touch(t) for t in s.split("&")] for s in sides]
        ids_per_side = [[i for i in side if i] for side in ids_per_side]
        for k, op in enumerate(ops):
            for a in ids_per_side[k]:
                for b in ids_per_side[k + 1] if k + 1 < len(ids_per_side) else []:
                    g["edges"].append((a, b, EDGE_KIND.get(op, "dep")))
        if cur_group:
            for side in ids_per_side:
                for i in side:
                    if g["nodes"][i]["group"] is None:
                        g["nodes"][i]["group"] = cur_group
    return g


def graph_from_tree_json(tree: dict) -> dict:
    g = {"direction": "BT", "nodes": {}, "order": [], "edges": [], "groups": {}}
    for n in tree.get("nodes", []):
        g["nodes"][n["id"]] = {"id": n["id"], "label": n.get("name", n["id"]),
                               "classes": set(), "group": None}
        g["order"].append(n["id"])
    for n in tree.get("nodes", []):
        for r in n.get("requires", []) or []:
            if r in g["nodes"]:
                g["edges"].append((r, n["id"], "dep"))
        for r in n.get("derives_from", []) or []:
            if r in g["nodes"] and (r, n["id"], "dep") not in g["edges"]:
                g["edges"].append((r, n["id"], "derive"))
    return g


def classify(g: dict, tree: dict | None) -> None:
    """给每个节点定一个视觉类: gen / heavy / ext / plain。"""
    by_norm = {}
    gens, heavy_cut = set(), None
    if tree:
        by_norm = {norm_id(n["id"]): n for n in tree.get("nodes", [])}
        gens = {norm_id(x) for x in tree.get("generators", [])}
        ws = sorted((n.get("weight", 0) for n in tree.get("nodes", [])
                     if n.get("kind") != "external"), reverse=True)
        if len(ws) >= 4:
            heavy_cut = ws[max(0, len(ws) // 4 - 1)]
    for nid, node in g["nodes"].items():
        cls = {c.lower() for c in node["classes"]}
        tn = by_norm.get(norm_id(nid))
        if tn and (node["label"] == nid or not node["label"]):
            node["label"] = tn.get("name", nid)
        vis = "plain"
        if tn and heavy_cut is not None and tn.get("weight", 0) >= heavy_cut and tn.get("kind") != "external":
            vis = "heavy"
        if any(k in c for c in cls for k in ("core", "heavy", "key")):
            vis = "heavy"
        if norm_id(nid) in gens or any(k in c for c in cls for k in ("gen", "root")):
            vis = "gen"
        if (tn and tn.get("kind") == "external") or any("ext" in c for c in cls):
            vis = "ext"
        node["vis"] = vis


def layer_graph(g: dict) -> list[list[str]]:
    nodes = list(g["order"])
    directed = [(a, b) for a, b, k in g["edges"] if k != "contrast" and a != b]
    indeg = {n: 0 for n in nodes}
    succ = {n: [] for n in nodes}
    for a, b in directed:
        succ[a].append(b)
        indeg[b] += 1
    layer = {n: 0 for n in nodes}
    queue = [n for n in nodes if indeg[n] == 0]
    seen = set()
    while queue:
        n = queue.pop(0)
        seen.add(n)
        for m in succ[n]:
            layer[m] = max(layer[m], layer[n] + 1)
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    # 环里的节点 (理论上 tree 门禁会拦) 放到最上层之后
    top = max(layer.values(), default=0)
    for n in nodes:
        if n not in seen:
            layer[n] = top + 1
    nl = max(layer.values(), default=0) + 1
    layers = [[n for n in nodes if layer[n] == k] for k in range(nl)]
    # 重心法减少交叉
    pred = {n: [] for n in nodes}
    for a, b in directed:
        pred[b].append(a)
    for it in range(8):
        rng = range(1, nl) if it % 2 == 0 else range(nl - 2, -1, -1)
        for k in rng:
            ref = layers[k - 1] if it % 2 == 0 else layers[k + 1]
            pos = {n: i for i, n in enumerate(ref)}
            nb = pred if it % 2 == 0 else succ
            own = {n: i for i, n in enumerate(layers[k])}

            def bary(n):
                xs = [pos[m] for m in nb[n] if m in pos]
                return sum(xs) / len(xs) if xs else own[n]
            layers[k].sort(key=bary)
    return [l for l in layers if l]


# ---------------------------------------------------------------- 画图

VIS_STYLE = {
    "gen":   dict(fc="#fde68a", ec="#b45309", ls="-",  lw=1.3, label="根思想"),
    "heavy": dict(fc="#fde2e1", ec="#b91c1c", ls="-",  lw=1.1, label="高分量（下游依赖多）"),
    "plain": dict(fc="#e8eef8", ec="#1a4a85", ls="-",  lw=0.9, label="概念 / 方法"),
    "ext":   dict(fc="#f3f4f6", ec="#6b7280", ls="--", lw=0.9, label="材料外前置"),
}
EDGE_STYLE = {
    "dep":      dict(color="#4b5563", lw=0.9, ls="-",  arrow="-|>", label="理解依赖（箭头指向依赖它的节点）"),
    "derive":   dict(color="#b45309", lw=2.0, ls="-",  arrow="-|>", label="推论 / 实现"),
    "compose":  dict(color="#6b7280", lw=0.9, ls=":",  arrow="-|>", label="组成使用"),
    "contrast": dict(color="#9ca3af", lw=0.9, ls="--", arrow="-",   label="对比并列"),
}


def _wrap(label: str, width: int) -> str:
    out = []
    for seg in label.split("\n"):
        line, w = "", 0
        for ch in seg:
            cw = 2 if ord(ch) > 0x2E80 else 1
            if w + cw > width and line:
                out.append(line)
                line, w = "", 0
            line += ch
            w += cw
        out.append(line)
    return "\n".join(out)


def draw_png(g: dict, out_png: Path, font_path: str | None) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠  matplotlib 不可用 ({e})，科技树退化为分层列表", file=sys.stderr)
        return False

    fp = None
    if font_path:
        try:
            font_manager.fontManager.addfont(font_path)
            fp = font_manager.FontProperties(fname=font_path)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠  科技树字体加载失败 ({e})", file=sys.stderr)

    layers = layer_graph(g)
    nl = len(layers)
    widest = max(len(l) for l in layers)
    horiz = g["direction"] in ("LR", "RL")
    # A5 横向 210 × 148 mm
    W, H = 8.27, 5.83
    fig = plt.figure(figsize=(W, H), dpi=220)
    ax = fig.add_axes([0.01, 0.13, 0.98, 0.86])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fs = 9 if widest <= 4 else 8 if widest <= 6 else 7 if widest <= 9 else 6
    wrap_w = max(8, int(70 / max(widest, 1)) * 2) if not horiz else 16

    pos = {}
    for k, layer in enumerate(layers):
        main = (k + 0.5) / nl
        for i, n in enumerate(layer):
            cross = (i + 0.5) / len(layer)
            if horiz:
                x = main if g["direction"] == "LR" else 1 - main
                pos[n] = (x, 1 - cross)
            else:
                y = main if g["direction"] == "BT" else 1 - main
                pos[n] = (cross, y)

    texts = {}
    for n, (x, y) in pos.items():
        node = g["nodes"][n]
        st = VIS_STYLE[node.get("vis", "plain")]
        t = ax.text(x, y, _wrap(node["label"], wrap_w), ha="center", va="center",
                    fontsize=fs, fontproperties=fp, zorder=3,
                    bbox=dict(boxstyle="round,pad=0.45", fc=st["fc"], ec=st["ec"],
                              lw=st["lw"], ls=st["ls"]))
        if fp is not None:
            t.set_fontsize(fs)
        texts[n] = t

    # 先画一次让文字框就位，箭头才能按框的边裁剪（否则箭头尖藏在框中心底下）
    fig.canvas.draw()
    layer_of = {n: k for k, l in enumerate(layers) for n in l}
    used_edges = set()
    for a, b, kind in g["edges"]:
        if a not in pos or b not in pos:
            continue
        es = EDGE_STYLE[kind]
        used_edges.add(kind)
        span = abs(layer_of[b] - layer_of[a])
        rad = 0.0 if span <= 1 else 0.18
        ax.annotate("", xy=pos[b], xytext=pos[a], zorder=2,
                    arrowprops=dict(arrowstyle=es["arrow"], color=es["color"], lw=es["lw"],
                                    ls=es["ls"], shrinkA=0, shrinkB=0,
                                    patchA=texts[a].get_bbox_patch(),
                                    patchB=texts[b].get_bbox_patch(),
                                    connectionstyle=f"arc3,rad={rad}", mutation_scale=9))

    used_vis = {g["nodes"][n].get("vis", "plain") for n in pos}
    handles = [Patch(fc=VIS_STYLE[v]["fc"], ec=VIS_STYLE[v]["ec"], ls=VIS_STYLE[v]["ls"],
                     label=VIS_STYLE[v]["label"]) for v in ("gen", "heavy", "plain", "ext") if v in used_vis]
    handles += [Line2D([0], [0], color=EDGE_STYLE[k]["color"], lw=EDGE_STYLE[k]["lw"],
                       ls=EDGE_STYLE[k]["ls"], label=EDGE_STYLE[k]["label"])
                for k in ("dep", "derive", "compose", "contrast") if k in used_edges]
    leg_fp = None
    if fp is not None:
        leg_fp = font_manager.FontProperties(fname=font_path, size=7)
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               prop=leg_fp if leg_fp else {"size": 7}, bbox_to_anchor=(0.5, 0.0))
    fig.savefig(str(out_png), dpi=220)
    plt.close(fig)
    return True


def render_tree_list(g: dict) -> str:
    """离线出图不可用时的退化形态：分层列表（底层在前）。"""
    layers = layer_graph(g)
    tag = {"gen": "根思想", "ext": "材料外前置", "heavy": "高分量"}
    out = ['<div class="tree-list">']
    for k, layer in enumerate(layers, 1):
        items = []
        for n in layer:
            node = g["nodes"][n]
            t = tag.get(node.get("vis"))
            items.append(html_mod.escape(node["label"].replace("\n", " "))
                         + (f' <span class="tree-tag">{t}</span>' if t else ""))
        out.append(f'<div class="tree-layer"><span class="tree-lk">第 {k} 层</span> '
                   + " · ".join(items) + "</div>")
    out.append('<p class="tree-note">下层是上层的前置：读懂下层，才看得懂上层。</p></div>')
    return "\n".join(out)


# ---------------------------------------------------------------- 入口

MERMAID_RE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)


def load_tree_graph(workspace: Path, mermaid_src: str | None = None) -> dict | None:
    """优先用传入的 mermaid（书首里那张），其次 tree.md 的 mermaid，最后 tree.json。"""
    tree = None
    tj = workspace / "tree.json"
    if tj.exists():
        try:
            tree = json.loads(tj.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠  tree.json 解析失败: {e}", file=sys.stderr)
    g = None
    if mermaid_src:
        g = parse_mermaid_graph(mermaid_src)
    if (g is None or not g["nodes"]) and (workspace / "tree.md").exists():
        m = MERMAID_RE.search((workspace / "tree.md").read_text(encoding="utf-8"))
        if m:
            g = parse_mermaid_graph(m.group(1))
    if (g is None or not g["nodes"]) and tree:
        g = graph_from_tree_json(tree)
    if g is None or not g["nodes"]:
        return None
    classify(g, tree)
    return g


if __name__ == "__main__":
    ws = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tree.png")
    graph = load_tree_graph(ws)
    if not graph:
        raise SystemExit("没有 tree.md mermaid 也没有 tree.json")
    font = next((p for p in ("/mnt/c/Windows/Fonts/msyh.ttc", "/mnt/c/Windows/Fonts/simhei.ttf",
                             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
                 if Path(p).exists()), None)
    if draw_png(graph, out, font):
        print(f"✓ {out}")
    else:
        print(render_tree_list(graph))
