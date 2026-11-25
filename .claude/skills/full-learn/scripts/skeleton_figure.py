#!/usr/bin/env python3
"""
skeleton_figure.py — 骨架图（章骨架 / 卷骨架 / 全书骨架）的解析与离线渲染
（chapter PARADIGM 理论 5、方法 1「本章骨架」；book PARADIGM 方法 1「大图 = 全书骨架」；render 方法 3）。

骨架 mermaid 的约定（首行 `%% skeleton`）:
    subgraph A["大概念"]            每个大概念一个 subgraph，标签是概念名
      A1["子题短名 · §21.1"]        叶子: `短名 · §N.M` / `§N.M–N.K` / `§a, §b`；卷/全书骨架用 `第N章` / `第a–b章`
      A2["子题短名 · §21.2"]:::core 承重的叶子
    end
    A -->|递进：短语| B             大概念之间的边带「关系词：短语」；并列 / 对比用 -.->

一层一张图（book PARADIGM 方法 6 后；L1 全书图 / L2 卷内图 / L3 块内图）另有:
    V1a["缺了：慢不成数"]           没有「· §」「· 第N章」引用的行 = 说明行：不画项目点，前缀 补：/交出：/缺了： 小号粗体
    V1c["第1–3章"]                  整行只是章范围 → 记章号（verify 的 L1 章覆盖靠它）
    class V3 here / class V1,V2 dim 作用于 subgraph：here 加粗描边 + 强调底 +「你在这里」；dim 整框与相连的边变浅灰；
                                    done 实色底 + 深绿描边 +「✓ 已点亮」（拼图进度图：本章之前的块，由 compile 自动设）
    L1–L3 的单链会把相邻两层并成一行横排（A → B），标签压线居中、碰到别的边就挪到线侧。

这里做三件事:
  1. parse_skeleton(src)  —— 解析成 {groups, edges, ...}；verify_book.py#skeleton / #book_skeleton 与编译器共用；
  2. draw_png(sk, out, font) —— matplotlib 离线出 PNG（不联网、不跑 JS、无 graphviz）。画法: 每个大概念一个圆角框，
     框顶是概念名（粗体），框内逐行列子题（:::core 用强调色 + ★）；概念之间画箭头并标「关系词 + 短语」（-.-> 画虚线）；
     用有向边（包含/递进/因果/前提/应用）做最长路分层，并列/对比放同层。flowchart LR 时层横排、TB 时竖排；
     概念 > 4 个、有同层或跨层关系、或 A5 正文宽放不下时自动换 TB。图宽 = A5 正文宽 124mm，字号按印刷尺寸给，
     最小 8.5pt（正文 10pt 的 85%）。
  3. render_card_html(sk) —— matplotlib 不可用时退化为 HTML 卡片。

单独调试:
    python3 skeleton_figure.py <含骨架 mermaid 的 md> [输出目录]
"""
import html as html_mod
import math
import re
import sys
from pathlib import Path

REL_WORDS = ("包含", "递进", "并列", "因果", "对比", "前提", "应用")
DIRECTED = {"包含", "递进", "因果", "前提", "应用"}
SAME_LAYER = {"并列", "对比"}

# ---------------------------------------------------------------- 解析

SUBGRAPH_RE = re.compile(r'^subgraph\s+([\w-]+)\s*(?:\[\s*"?(.*?)"?\s*\])?\s*$')
NODE_RE = re.compile(r'^([\w-]+)\s*[\[\(\{]+\s*"?(.*?)"?\s*[\]\)\}]+\s*(?::::([\w-]+))?\s*$')
EDGE_RE = re.compile(r'^([\w-]+)(?::::[\w-]+)?\s*(-\.->|-\.-|==>|-->|---)\s*(?:\|\s*"?(.*?)"?\s*\|)?\s*'
                     r'([\w-]+)(?::::[\w-]+)?\s*$')
CLASS_RE = re.compile(r'^class\s+([\w,\s-]+?)\s+([\w-]+)\s*$')
SEC_REF_RE = re.compile(r'§\s*(\d+)\.(\d+)(?:\s*[–—~-]\s*(?:§\s*)?(?:(\d+)\.)?(\d+))?')
CH_REF_RE = re.compile(r'第\s*(\d+)\s*(?:[–—~-]\s*(\d+)\s*)?章')
REL_SPLIT_RE = re.compile(r'^\s*([^：:]{1,6}?)\s*[：:]\s*(.*)$')
PURE_CH_RE = re.compile(r'^第\s*\d+\s*(?:[–—~-]\s*\d+\s*)?章$')          # 整行只是章范围（L1 框内的「第a–b章」）
CH_TITLE_RE = re.compile(r'^第\s*(\d+)\s*章')                            # L3 框标题「第N章 章短名」
DESC_PREFIX_RE = re.compile(r'^(补|交出|缺了|留下)\s*[：:]\s*(.*)$')    # 说明行前缀（留下：🌳 块小结里该章的一句话）


def is_skeleton(src: str) -> bool:
    first = next((ln.strip() for ln in src.split("\n") if ln.strip()), "")
    return first == "%% skeleton"


def parse_ref(ref: str):
    """'§21.1–21.3' / '§21.1, §21.4' → 节号列表；'第4–5章' → 章号列表。"""
    secs, chs = [], []
    for m in SEC_REF_RE.finditer(ref or ""):
        a, b = int(m.group(1)), int(m.group(2))
        if m.group(4):
            a2 = int(m.group(3)) if m.group(3) else a
            b2 = int(m.group(4))
            if a2 == a and b2 >= b:
                secs += [f"{a}.{k}" for k in range(b, b2 + 1)]
                continue
        secs.append(f"{a}.{b}")
    for m in CH_REF_RE.finditer(ref or ""):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        chs += list(range(a, b + 1)) if b >= a else [a]
    return secs, chs


def split_leaf(label: str):
    """'子题短名 · §21.2' → ('子题短名', '§21.2')；只有「· §…」「· 第…章」算引用分隔，普通中点照常是文字。"""
    lab = label.replace("<br/>", " ").replace("<br>", " ").strip()
    for m in reversed(list(re.finditer(r"·", lab))):
        rest = lab[m.end():].strip()
        if rest.startswith("§") or re.match(r"第\s*\d", rest):
            return lab[:m.start()].strip(), rest
    return lab, ""


def split_rel(label: str):
    """'递进：从均值走到分布' → ('递进', '从均值走到分布')；无冒号时整串当关系词。"""
    label = (label or "").strip()
    m = REL_SPLIT_RE.match(label)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return label, ""


def parse_skeleton(src: str) -> dict:
    sk = {"direction": "TB", "groups": [], "edges": [], "loose": [], "unparsed": [], "here": set(), "dim": set(),
          "done": set()}
    gby, leaf_by, cur = {}, {}, None
    core_ids = set()
    for raw in src.split("\n"):
        line = raw.strip().rstrip(";").strip()
        if not line or line.startswith(("%%", "classDef", "style ", "linkStyle", "direction", "click ")):
            continue
        m = re.match(r"^(flowchart|graph)\s*(TB|TD|BT|LR|RL)?", line)
        if m:
            d = m.group(2) or "TB"
            sk["direction"] = "LR" if d in ("LR", "RL") else "TB"
            continue
        if line == "end":
            cur = None
            continue
        m = SUBGRAPH_RE.match(line)
        if m:
            g = {"id": m.group(1), "label": (m.group(2) or m.group(1)).strip(), "leaves": []}
            _s, gref = split_leaf(g["label"])
            g["chs"] = parse_ref(gref)[1] if gref else []
            mt = CH_TITLE_RE.match(g["label"])
            if not g["chs"] and mt:
                g["chs"] = [int(mt.group(1))]
            sk["groups"].append(g)
            gby[g["id"]] = g
            cur = g
            continue
        m = CLASS_RE.match(line)
        if m:
            ids = {x for x in re.split(r"[,\s]+", m.group(1).strip()) if x}
            if m.group(2) == "core":
                core_ids |= ids
            elif m.group(2) in ("here", "dim", "done"):   # 作用于 subgraph：高亮当前位置 / 变淡 / 已点亮
                sk[m.group(2)] |= ids
            continue
        m = EDGE_RE.match(line)
        if m:
            a, op, lab, b = m.group(1), m.group(2), m.group(3) or "", m.group(4)
            rel, phrase = split_rel(lab)
            sk["edges"].append({"a": a, "b": b, "op": op, "dashed": op.startswith("-.") or op == "---",
                                "label": lab.strip(), "rel": rel, "phrase": phrase})
            continue
        m = NODE_RE.match(line)
        if m:
            nid, text, cls = m.group(1), m.group(2), m.group(3)
            short, ref = split_leaf(text)
            secs, chs = parse_ref(ref)
            # 说明行：没有「· §」「· 第N章」引用 → 按说明文字排（L1–L3 框内）；整行只是「第a–b章」时记章号
            desc = not ref
            chref = desc and bool(PURE_CH_RE.match(short))
            if chref:
                chs = parse_ref(short)[1]
            mp = DESC_PREFIX_RE.match(short) if desc else None
            leaf = {"id": nid, "label": text, "short": short, "ref": ref, "secs": secs, "chs": chs,
                    "core": cls == "core", "group": cur["id"] if cur else None,
                    "desc": desc, "chref": chref, "prefix": mp.group(1) if mp else "",
                    "text": mp.group(2) if mp else short}
            leaf_by[nid] = leaf
            (cur["leaves"] if cur else sk["loose"]).append(leaf)
            continue
        sk["unparsed"].append(line)
    for nid in core_ids:
        if nid in leaf_by:
            leaf_by[nid]["core"] = True
    for g in sk["groups"]:
        g["here"] = g["id"] in sk["here"]
        g["dim"] = g["id"] in sk["dim"] and not g["here"]
        g["done"] = g["id"] in sk["done"] and not g["here"] and not g["dim"]
    for e in sk["edges"]:
        e["ga"] = e["a"] if e["a"] in gby else (leaf_by.get(e["a"]) or {}).get("group")
        e["gb"] = e["b"] if e["b"] in gby else (leaf_by.get(e["b"]) or {}).get("group")
    return sk


def figure_kind(sk: dict) -> str:
    """'book'（subgraph 标签都以「卷」开头）/ 'chapters'（L3：框标题「第N章 …」）/
    'blocks'（L2：框标题「块名 · 第a–b章」、框内是说明行）/ 'volume'（叶子标的是第N章）/ 'chapter'。"""
    gs = sk["groups"]
    if gs and all(g["label"].startswith("卷") for g in gs):
        return "book"
    if gs and all(CH_TITLE_RE.match(g["label"]) for g in gs):
        return "chapters"
    leaves = [l for g in gs for l in g["leaves"]]
    if gs and all(g["chs"] and "·" in g["label"] for g in gs) and not any(l["chs"] for l in leaves):
        return "blocks"
    if leaves and all(l["chs"] and not l["secs"] for l in leaves):
        return "volume"
    return "chapter"


def level(sk: dict):
    """一层一张图（book PARADIGM 方法 6 后）：'L1' 全书图（框 = 卷，框内是说明行）/ 'L2' 卷内图 / 'L3' 块内图；
    旧式全书骨架、卷骨架、章骨架 → None。"""
    kind = figure_kind(sk)
    if kind == "book":
        leaves = [l for g in sk["groups"] for l in g["leaves"]]
        return "L1" if leaves and all(l["desc"] for l in leaves) else None
    return {"blocks": "L2", "chapters": "L3"}.get(kind)


def is_blocksum(sk: dict) -> bool:
    """🌳 块小结的小树：L3 图（框 = 章），框内每行都是「留下：…」。"""
    leaves = [l for g in sk["groups"] for l in g["leaves"]]
    return figure_kind(sk) == "chapters" and bool(leaves) and all(l["prefix"] == "留下" for l in leaves)


def caption(sk: dict, volume_name: str = "") -> str:
    kind, lv = figure_kind(sk), level(sk)
    here = any(g["here"] for g in sk["groups"])
    if lv == "L1":
        return ("全书一张图：每框一卷，框内是它补的那片拼图、缺了它哪里会断、对应哪几章；箭头上是卷与卷的交接。"
                + ("高亮的是本卷所在的一片。" if here else ""))
    if lv == "L2":
        return ("卷内一张图：每框一块，框内是它补什么、交出什么；箭头上是块与块的交接。"
                + ("高亮的是本块。" if here else ""))
    if lv == "L3" and is_blocksum(sk):
        return "块小结一张图：每框一章，框内是它留下的一句话；箭头上是章与章的接力。合起来就是上面卡片里的答案。"
    if lv == "L3":
        return ("块内一张图：每框一章，框内是该章的大概念；箭头上是章与章的接力。"
                + ("高亮的是本章。" if here else ""))
    if kind == "book":
        return "全书骨架：框是卷，框内是块与对应的章；箭头上是它们的关系。"
    if kind == "volume" and all(g["label"][:1] in "①②③④⑤⑥⑦⑧⑨" for g in sk["groups"]):
        # 总纲卷的目标树：subgraph = 拼图（子目标，「② 描述输入」），子题 = 补它的卷与块
        return "目标树：框是终极目标的一片拼图，框内是补它的卷与块；箭头上是片与片的关系。"
    if kind == "volume":
        name = f"{volume_name}骨架" if volume_name else "卷骨架"
        return f"{name}：框是块，框内是章；箭头上是它们的关系。"
    return "本章骨架：框是大概念，框内是子题与对应的节；箭头上是它们的关系。"


# ---------------------------------------------------------------- 量字

FIG_W = 124.0            # mm：A5 正文宽 = 148 − 2 × 12（与 compile_story_pdf 的 @page 边距耦合）
PT = 25.4 / 72           # 1pt 的毫米数
FS_TITLE, FS_LEAF, FS_EDGE = 9.6, 8.6, 8.5   # 最小 8.5pt = 正文 10pt 的 85%
LH = 1.36                # 行高倍数
PADX, PADT, PADB = 2.4, 1.7, 1.8
SEP = 1.6                # 标题与子题之间
LEAF_SP = 0.5            # 子题之间
COLGAP = 4.0
REFGAP = 1.6
HGAP = 6.0
DUMMY_W = 3.0

FS_PRE = 7.8             # 说明行前缀「补：」「交出：」「缺了：」（小号粗体）
FS_BADGE = 7.8           # 「▶ 你在这里」
BADGE = "你在这里"
BADGE_TRI = 1.9          # mm：badge 前的实心三角（矢量画）

COL = {
    "box_fc": "#f4f8fc", "box_ec": "#1a4a85", "title": "#1a4a85", "sep": "#b9cbe0",
    "leaf": "#24313d", "ref": "#6b7a8c", "core": "#b42318", "bullet": "#9aaabb",
    "edge": "#4b5563", "rel": "#1a4a85", "phrase": "#374151", "pre": "#4f6f96",
}
# 高亮（class X here）：加粗描边 + 强调色底；变淡（class X dim）：整框与相连的边降为浅灰
COL_HERE = dict(COL, box_fc="#fff3e3", box_ec="#c2570c", sep="#f0c9a0", badge="#c2570c", pre="#a2480c")
COL_DIM = dict(COL, box_fc="#f8f9fa", box_ec="#cfd5db", title="#a3abb4", sep="#e4e7eb", leaf="#a9b0b8",
               ref="#b9c0c7", core="#a9b0b8", bullet="#c9cfd5", pre="#b0b7bf",
               edge="#c9ced4", rel="#a9b0b8", phrase="#b3b9c0")


# 已点亮（class X done，拼图进度图里本章之前的块）：实色底 + 深色描边 + 「✓ 已点亮」
COL_DONE = dict(COL, box_fc="#d8eedd", box_ec="#2e7d32", title="#1b5e20", sep="#9ccaa5", badge="#2e7d32",
                pre="#2e6b3a", leaf="#1f3b26", ref="#4b6b52", bullet="#6fa57b", core="#1b5e20")
BADGE_DONE = "已点亮"


def pal(g):
    return (COL_HERE if g.get("here") else COL_DIM if g.get("dim") else
            COL_DONE if g.get("done") else COL)


class Meter:
    def __init__(self, font_path):
        from matplotlib import font_manager
        from matplotlib.textpath import TextToPath
        self.fm = font_manager
        self.ttp = TextToPath()
        self.font = font_path
        self.bold = None
        if font_path:
            for cand in (font_path.replace("msyh.ttc", "msyhbd.ttc"), font_path.replace("simhei", "simhei")):
                if cand != font_path and Path(cand).exists():
                    self.bold = cand
                    break
        self.cache = {}

    def fp(self, size, bold=False):
        p = self.bold if (bold and self.bold) else self.font
        if p:
            return self.fm.FontProperties(fname=p, size=size)
        return self.fm.FontProperties(size=size, weight="bold" if bold else "normal")

    def w(self, s, size, bold=False):
        """宽度（mm）。"""
        if not s:
            return 0.0
        key = (s, size, bold)
        if key not in self.cache:
            try:
                wpt, _h, _d = self.ttp.get_text_width_height_descent(s, self.fp(size, bold), ismath=False)
            except Exception:  # noqa: BLE001
                wpt = sum((1.0 if ord(c) > 0x2E80 else 0.58) for c in s) * size
            self.cache[key] = wpt * PT
        return self.cache[key]

    def wrap(self, s, size, maxw, bold=False):
        maxw += 0.3          # 浮点误差：恰好等宽的那一行不该被折
        if self.w(s, size, bold) <= maxw:
            return [s]
        out, line, ls = [], "", 0          # ls：line 在 s 里的起点
        spans = [(m.start(), m.end()) for m in NOBREAK_RE.finditer(s)]
        for i, ch in enumerate(s):
            if not line:
                ls = i
            if line and self.w(line + ch, size, bold) > maxw:
                # 「第a–b章」「§N.M」不拆：断点落在它中间时，整段挪到下一行
                sp = next(((a, b) for a, b in spans if a < i < b and a > ls), None)
                m = re.search(r"[A-Za-z0-9/.+-]+$", line)
                if sp:
                    cut = sp[0] - ls
                # 不在拉丁词中间断开
                elif m and m.start() > 0 and re.match(r"[A-Za-z0-9/.+-]", ch):
                    cut = m.start()
                else:
                    cut = len(line)
                out.append(line[:cut].rstrip())
                line, ls = line[cut:], ls + cut
                while line and line[0].isspace():
                    line, ls = line[1:], ls + 1
                if not line:
                    ls = i
            line += ch
        if line.strip():
            out.append(line.strip())
        return out


NOBREAK_RE = re.compile(r"第\s*\d+\s*(?:[–—~-]\s*\d+\s*)?章|§\s*\d+(?:\.\d+)?(?:\s*[–—~-]\s*(?:§\s*)?\d+(?:\.\d+)?)?")


def kinsoku(lines):
    """行首不放「，、；：。）」：挪回上一行末尾（略超宽也比孤零零的标点好看）。"""
    out = []
    for t in lines:
        while out and t and t[0] in "，、；：。）)！？":
            out[-1], t = out[-1] + t[0], t[1:].lstrip()
        if t:
            out.append(t)
    return out


def wrap_bal(meter, s, size, maxw, bold=False):
    """折行但各行均分（末行不只剩一两个字）；在标点后断优先。"""
    lines = meter.wrap(s, size, maxw, bold)
    if len(lines) < 2:
        return lines
    bw = meter.w(s, size, bold) / len(lines)
    while bw < maxw:
        cand = meter.wrap(s, size, bw, bold)
        if len(cand) == len(lines):
            lines = cand
            break
        bw += 0.8
    # 断点前后 2 字内有「，、；」就挪到标点后
    out = list(lines)
    for k in range(len(out) - 1):
        a, b = out[k], out[k + 1]
        for j in (1, 2):
            if len(b) > j and b[j - 1] in "，、；" and meter.w(a + b[:j], size, bold) <= maxw + 0.3:
                out[k], out[k + 1] = a + b[:j], b[j:]
                break
        else:
            for j in (1, 2):
                if len(a) > j and a[-j - 1] in "，、；" and meter.w(a[-j:] + b, size, bold) <= maxw + 0.3:
                    out[k], out[k + 1] = a[:-j], a[-j:] + b
                    break
    return kinsoku([x for x in out if x])


def wrap_title(meter, label, maxw):
    """框标题：「块名 · 第a–b章」放不下时在「 · 」处断——块名一行（必要时再折），章范围单独一行。"""
    if meter.w(label, FS_TITLE, True) <= maxw + 0.3:
        return [label]
    name, ref = split_leaf(label)
    if ref:
        return meter.wrap(name, FS_TITLE, maxw, bold=True) + meter.wrap(ref, FS_TITLE, maxw, bold=True)
    return meter.wrap(label, FS_TITLE, maxw, bold=True)


def lh(size):
    return size * PT * LH


# ---------------------------------------------------------------- 框

def build_box(meter, g, max_w, ncols=1):
    inner_max = max(20.0, max_w - 2 * PADX)
    title = wrap_title(meter, g["label"], inner_max)
    title_w = max(meter.w(t, FS_TITLE, True) for t in title)
    badge_h = 0.0
    if g.get("here") or g.get("done"):
        title_w = max(title_w, meter.w(BADGE if g.get("here") else BADGE_DONE, FS_BADGE, True) + BADGE_TRI + 0.8)
        badge_h = lh(FS_BADGE)
    bullet_w = meter.w("★ ", FS_LEAF)
    leaves = g["leaves"]

    def lead(l):          # 说明行：★（承重时）+ 前缀；子题行：项目点
        if not l.get("desc"):
            return bullet_w
        return (bullet_w if l["core"] else 0.0) + (meter.w(l["prefix"] + "：", FS_PRE, True) if l["prefix"] else 0.0)
    nat = [(lead(l) + meter.w(l["text"], FS_LEAF, l["core"])) if l.get("desc") else
           (bullet_w + meter.w(l["short"], FS_LEAF, l["core"]) + REFGAP + meter.w(l["ref"], FS_LEAF))
           for l in leaves] or [0.0]
    ncols = max(1, min(ncols, len(leaves) or 1))
    colw = min(max(nat), (inner_max - (ncols - 1) * COLGAP) / ncols)
    items = []
    for l in leaves:
        if l.get("desc"):
            ind = lead(l)
            lines = wrap_bal(meter, l["text"], FS_LEAF, max(10.0, colw - ind), bold=l["core"])
            items.append({"leaf": l, "lines": lines, "ref_own_line": False, "indent": ind,
                          "h": len(lines) * lh(FS_LEAF) + LEAF_SP})
            continue
        ref_w = meter.w(l["ref"], FS_LEAF)
        avail = max(10.0, colw - bullet_w - REFGAP - ref_w)
        lines = meter.wrap(l["short"], FS_LEAF, avail, bold=l["core"])
        if len(lines) > 1 and colw - bullet_w < ref_w + 14:   # 引用太长：引用另起一行
            lines = meter.wrap(l["short"], FS_LEAF, colw - bullet_w, bold=l["core"])
            items.append({"leaf": l, "lines": lines, "ref_own_line": True,
                          "h": (len(lines) + 1) * lh(FS_LEAF) + LEAF_SP})
        else:
            items.append({"leaf": l, "lines": lines, "ref_own_line": False,
                          "h": len(lines) * lh(FS_LEAF) + LEAF_SP})
    per = math.ceil(len(items) / ncols) if items else 0
    cols = [items[k * per:(k + 1) * per] for k in range(ncols)] if items else []
    col_h = max([sum(i["h"] for i in c) for c in cols] or [0.0])
    inner_w = max(title_w, ncols * colw + (ncols - 1) * COLGAP)
    h = PADT + badge_h + len(title) * lh(FS_TITLE) + SEP + col_h + PADB - (LEAF_SP if items else 0)
    return {"id": g["id"], "g": g, "w": inner_w + 2 * PADX, "h": h, "title": title, "cols": cols,
            "colw": colw, "ncols": ncols, "dummy": False, "badge_h": badge_h}


def draw_box(ax, meter, b):
    from matplotlib.patches import FancyBboxPatch, Polygon
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    P = pal(b["g"])
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.8",
                                fc=P["box_fc"], ec=P["box_ec"], lw=2.0 if b["g"].get("here") else 1.4 if b["g"].get("done") else 1.0,
                                zorder=3))
    ty = y + PADT
    if b.get("badge_h"):          # 三角 / 对勾用矢量画（▶ ✓ 在微软雅黑里不一定有），文字居中
        text = BADGE if b["g"].get("here") else BADGE_DONE
        tw = meter.w(text, FS_BADGE, True)
        x0 = x + w / 2 - (tw + BADGE_TRI + 0.8) / 2
        cy_ = ty - 0.2 + lh(FS_BADGE) / 2 - 0.35
        s = BADGE_TRI
        if b["g"].get("here"):
            ax.add_patch(Polygon(
                [(x0, cy_ - s * 0.55), (x0, cy_ + s * 0.55), (x0 + s, cy_)], closed=True,
                fc=P["badge"], ec="none", zorder=5))
        else:
            ax.plot([x0, x0 + s * 0.38, x0 + s], [cy_, cy_ + s * 0.45, cy_ - s * 0.55], color=P["badge"],
                    lw=1.3, zorder=5, solid_capstyle="round", solid_joinstyle="round")
        ax.text(x0 + s + 0.8, ty - 0.2, text, ha="left", va="top", color=P["badge"], zorder=5,
                fontproperties=meter.fp(FS_BADGE, True), fontweight="bold" if not meter.bold else "normal")
        ty += b["badge_h"]
    for t in b["title"]:
        ax.text(x + w / 2, ty, t, ha="center", va="top", color=P["title"],
                fontproperties=meter.fp(FS_TITLE, True), zorder=5,
                fontweight="bold" if not meter.bold else "normal")
        ty += lh(FS_TITLE)
    sy = ty + SEP * 0.35
    ax.plot([x + 1.2, x + w - 1.2], [sy, sy], color=P["sep"], lw=0.6, zorder=4)
    top = ty + SEP
    bullet_w = meter.w("★ ", FS_LEAF)
    for k, col in enumerate(b["cols"]):
        cx = x + PADX + k * (b["colw"] + COLGAP)
        cy = top
        for it in col:
            l = it["leaf"]
            color = P["core"] if l["core"] else P["ref"] if l.get("chref") else P["leaf"]
            if l.get("desc"):          # 说明行：不画项目点，左对齐；前缀小号粗体，续行与正文对齐
                px = cx
                if l["core"]:
                    ax.text(px, cy, "★", ha="left", va="top", zorder=5, color=P["core"],
                            fontproperties=meter.fp(FS_LEAF))
                    px += bullet_w
                if l["prefix"]:
                    ax.text(px, cy + (lh(FS_LEAF) - lh(FS_PRE)) * 0.55, l["prefix"] + "：", ha="left", va="top",
                            zorder=5, color=P["pre"], fontproperties=meter.fp(FS_PRE, True),
                            fontweight="bold" if not meter.bold else "normal")
                ly = cy
                for t in it["lines"]:
                    ax.text(cx + it["indent"], ly, t, ha="left", va="top", color=color, zorder=5,
                            fontproperties=meter.fp(FS_LEAF, l["core"]))
                    ly += lh(FS_LEAF)
                cy += it["h"]
                continue
            ax.text(cx, cy, "★" if l["core"] else "•", ha="left", va="top", zorder=5,
                    color=P["core"] if l["core"] else P["bullet"], fontproperties=meter.fp(FS_LEAF))
            ly = cy
            for t in it["lines"]:
                ax.text(cx + bullet_w, ly, t, ha="left", va="top", color=color, zorder=5,
                        fontproperties=meter.fp(FS_LEAF, l["core"]))
                ly += lh(FS_LEAF)
            ry = ly if it["ref_own_line"] else ly - lh(FS_LEAF)
            if l["ref"]:
                ax.text(cx + b["colw"], ry, l["ref"], ha="right", va="top", color=P["ref"], zorder=5,
                        fontproperties=meter.fp(FS_LEAF))
            cy += it["h"]


# ---------------------------------------------------------------- 分层

def group_edges(sk):
    """大概念之间的边（叶子端点映射到所在大概念；同一概念内部的边不画）。"""
    out = []
    gby = {g["id"]: g for g in sk["groups"]}
    for e in sk["edges"]:
        a, b = e.get("ga"), e.get("gb")
        if a in gby and b in gby and a != b:
            # 连着变淡的框、又不连高亮框的边一起变淡
            dim = (gby[a].get("dim") or gby[b].get("dim")) and not (gby[a].get("here") or gby[b].get("here"))
            out.append(dict(e, ga=a, gb=b, dim=bool(dim)))
    return out


def compact_layers(meter, sk, edges, layers):
    """一层一张图（L1–L3）的节点少、常是单链：相邻两层都只有一个框、且上面那个只连下面这个时，
    并成一行横排（A → B），把细长的竖链折成二维的 DAG；放不下 A5 正文宽就不并。"""
    gby = {g["id"]: g for g in sk["groups"]}
    out_deg = {}
    for e in edges:
        out_deg[e["ga"]] = out_deg.get(e["ga"], 0) + 1
    new, k = [], 0
    while k < len(layers):
        if k + 1 < len(layers) and len(layers[k]) == 1 and len(layers[k + 1]) == 1:
            a, b = layers[k][0], layers[k + 1][0]
            e = next((e for e in edges if e["ga"] == a and e["gb"] == b), None)
            if e and out_deg.get(a, 0) == 1:
                gap = label_block(meter, e, H_LABEL_W, stack=True)["w"] + H_LABEL_PAD
                bw = (FIG_W - gap) / 2
                nat = [build_box(meter, gby[n], FIG_W, 1) for n in (a, b)]
                fit = [build_box(meter, gby[n], bw, 1) for n in (a, b)]
                if all(f["w"] <= bw + 0.01 and f["h"] <= n["h"] + lh(FS_LEAF) * 1.01 for f, n in zip(fit, nat)):
                    new.append([a, b])
                    k += 2
                    continue
        new.append(layers[k])
        k += 1
    return new


def layering(sk, edges):
    gids = [g["id"] for g in sk["groups"]]
    parent = {g: g for g in gids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for e in edges:
        if e["rel"] in SAME_LAYER:
            ra, rb = find(e["ga"]), find(e["gb"])
            if ra != rb:
                parent[rb] = ra
    reps = list(dict.fromkeys(find(g) for g in gids))
    succ = {r: set() for r in reps}
    for e in edges:
        directed = e["rel"] in DIRECTED or (e["rel"] not in SAME_LAYER and not e["dashed"])
        a, b = find(e["ga"]), find(e["gb"])
        if directed and a != b:
            succ[a].add(b)
    indeg = {r: 0 for r in reps}
    for a in reps:
        for b in succ[a]:
            indeg[b] += 1
    layer = {r: 0 for r in reps}
    queue = [r for r in reps if indeg[r] == 0]
    seen = set()
    while queue:
        n = queue.pop(0)
        seen.add(n)
        for m in succ[n]:
            layer[m] = max(layer[m], layer[n] + 1)
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    top = max(layer.values(), default=0)
    for r in reps:
        if r not in seen:      # 环：放到最后一层之后
            layer[r] = top + 1
    lay = {g: layer[find(g)] for g in gids}
    nl = max(lay.values(), default=0) + 1
    layers = [[g for g in gids if lay[g] == k] for k in range(nl)]
    layers = [l for l in layers if l]
    return layers


def order_layers(layers, edges):
    """重心法排序 + 同层关系的两端挨着放。"""
    pos = {}
    for k, l in enumerate(layers):
        if k:
            prev = {n: i for i, n in enumerate(layers[k - 1])}
            orig = {n: i for i, n in enumerate(l)}   # list.sort 期间 l 被清空，不能在 key 里 l.index

            def bary(n, orig=orig, prev=prev):
                xs = [prev[e["ga"]] for e in edges if e["gb"] == n and e["ga"] in prev] + \
                     [prev[e["gb"]] for e in edges if e["ga"] == n and e["gb"] in prev]
                return sum(xs) / len(xs) if xs else orig[n]
            l.sort(key=bary)
        for e in edges:
            if e["ga"] in l and e["gb"] in l:
                ia, ib = l.index(e["ga"]), l.index(e["gb"])
                if abs(ia - ib) > 1:
                    l.remove(e["gb"])
                    l.insert(l.index(e["ga"]) + 1, e["gb"])
        for i, n in enumerate(l):
            pos[n] = (k, i)
    return layers


# ---------------------------------------------------------------- 边标签

def label_block(meter, e, maxw, stack=False, bal=False):
    """stack=True：关系词独占第一行、短语在下（横向边夹在两框之间时用，窄而高）。"""
    rel = e["rel"] or ""
    phrase = e["phrase"] or ("" if rel else e["label"])
    rel_txt = rel + ("：" if rel and phrase else "")
    rw = meter.w(rel_txt, FS_EDGE, True)
    if stack and rel_txt and phrase:
        lines = wrap_bal(meter, phrase, FS_EDGE, maxw)
        w = max([rw] + [meter.w(t, FS_EDGE) for t in lines])
        return {"rel": rel_txt, "rw": rw, "lines": lines, "w": w + 1.6,
                "h": (1 + len(lines)) * lh(FS_EDGE) + 0.8, "stack": True, "dim": e.get("dim", False)}
    lines = meter.wrap(phrase, FS_EDGE, max(12.0, maxw - rw)) if phrase else []
    if len(lines) > 1:  # 第一行之后可以用满宽
        rest = "".join(lines[1:])
        lines = lines[:1] + meter.wrap(rest, FS_EDGE, maxw)
    if bal and len(lines) > 1:   # 各行均分（含行首的关系词），末行不只剩一两个字
        n, tw = len(lines), (rw + meter.w(phrase, FS_EDGE)) / len(lines)
        while tw < maxw:
            first = meter.wrap(phrase, FS_EDGE, max(6.0, tw - rw))[0]
            rest = phrase[len(first):].strip()
            cand = [first] + (meter.wrap(rest, FS_EDGE, tw) if rest else [])
            if len(cand) <= n:
                lines = kinsoku(cand)
                break
            tw += 0.8
    w = max([rw + (meter.w(lines[0], FS_EDGE) if lines else 0.0)] +
            [meter.w(t, FS_EDGE) for t in lines[1:]])
    h = max(1, len(lines)) * lh(FS_EDGE)
    return {"rel": rel_txt, "rw": rw, "lines": lines, "w": w + 1.6, "h": h + 0.8, "stack": False,
            "dim": e.get("dim", False)}


def draw_label(ax, meter, lb, cx, cy):
    from matplotlib.patches import FancyBboxPatch
    P = COL_DIM if lb.get("dim") else COL
    x0, y0 = cx - lb["w"] / 2, cy - lb["h"] / 2
    ax.add_patch(FancyBboxPatch((x0, y0), lb["w"], lb["h"], boxstyle="round,pad=0,rounding_size=0.8",
                                fc="white", ec="none", alpha=0.96, zorder=6))
    tx, ty = x0 + 0.8, y0 + 0.4
    if lb["rel"]:
        ax.text(tx, ty, lb["rel"], ha="left", va="top", color=P["rel"], zorder=7,
                fontproperties=meter.fp(FS_EDGE, True), fontweight="bold" if not meter.bold else "normal")
    off = 1 if lb.get("stack") else 0
    for k, t in enumerate(lb["lines"]):
        ax.text(tx + (lb["rw"] if k == 0 and not off else 0), ty + (k + off) * lh(FS_EDGE), t, ha="left",
                va="top", color=P["phrase"], zorder=7, fontproperties=meter.fp(FS_EDGE))


def draw_path(ax, pts, dashed, dim=False):
    color = COL_DIM["edge"] if dim else COL["edge"]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ls = (0, (3.2, 2.0)) if dashed else "-"
    ax.plot(xs, ys, color=color, lw=1.0, ls=ls, zorder=2, solid_capstyle="butt")
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    d = math.hypot(x2 - x1, y2 - y1) or 1.0
    k = min(2.6, d) / d
    ax.annotate("", xy=(x2, y2), xytext=(x2 - (x2 - x1) * k, y2 - (y2 - y1) * k), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0, shrinkA=0, shrinkB=0,
                                mutation_scale=8))


# ---------------------------------------------------------------- 布局: TB（层竖排）

H_LABEL_W = 24.0         # 横向边（两框并排）标签的最大宽
H_LABEL_PAD = 8.0        # 标签两侧给线和箭头留的空


def layout_tb(meter, sk, edges, layers):
    gby = {g["id"]: g for g in sk["groups"]}
    stacked = bool(level(sk))      # 一层一张图：横向边的标签竖叠、压在线上居中
    lay_of = {g: k for k, l in enumerate(layers) for g in l}
    # 跨层边插哑点
    rows = [list(l) for l in layers]
    chains = []
    for idx, e in enumerate(edges):
        la, lb_ = lay_of[e["ga"]], lay_of[e["gb"]]
        chain = [e["ga"]]
        step = 1 if lb_ > la else -1
        for k in range(la + step, lb_, step) if abs(lb_ - la) > 1 else []:
            d = f"__d{idx}_{k}"
            # 哑点放在该层离两端重心最近的一侧
            rows[k].append(d)
            chain.append(d)
        chain.append(e["gb"])
        chains.append(chain)
    # 同层不相邻的关系 → U 形（走下方的间隙）
    same = [i for i, e in enumerate(edges) if lay_of[e["ga"]] == lay_of[e["gb"]]]

    def row_items(k, ncols_single=True):
        items = []
        boxes = [n for n in rows[k] if not n.startswith("__d")]
        for n in rows[k]:
            if n.startswith("__d"):
                items.append({"id": n, "w": DUMMY_W, "h": 0.0, "dummy": True})
            else:
                nc = 2 if (ncols_single and len(boxes) == 1 and len(gby[n]["leaves"]) >= 4) else 1
                items.append(build_box(meter, gby[n], FIG_W, nc))
        return items

    def gaps_of(k, items):
        gs = []
        for i in range(len(items) - 1):
            a, b = items[i]["id"], items[i + 1]["id"]
            g = HGAP
            for j in same:
                e = edges[j]
                if {e["ga"], e["gb"]} == {a, b}:
                    if stacked:
                        g = max(g, label_block(meter, e, H_LABEL_W, stack=True)["w"] + H_LABEL_PAD)
                    else:
                        g = max(g, label_block(meter, e, 30.0)["w"] + 5.0)
            gs.append(g)
        return gs

    placed = []
    for k in range(len(rows)):
        items = row_items(k)
        gs = gaps_of(k, items)
        tot = sum(i["w"] for i in items) + sum(gs)
        if tot > FIG_W:
            nb = sum(1 for i in items if not i["dummy"])
            fixed = sum(i["w"] for i in items if i["dummy"]) + sum(gs)
            mw = (FIG_W - fixed) / max(1, nb)
            items = [i if i["dummy"] else build_box(meter, gby[i["id"]], mw, 1) for i in items]
            tot = sum(i["w"] for i in items) + sum(gs)
        x = max(0.4, (FIG_W - tot) / 2)
        for i, it in enumerate(items):
            it["x"] = x
            x += it["w"] + (gs[i] if i < len(gs) else 0)
        placed.append(items)
    item = {it["id"]: it for row in placed for it in row}
    # 每层哑点按两端位置重排到合适的一侧（宽度不变，只交换顺序会改 x；这里简单处理: 保持）
    # 端口: 每个框的上/下边按另一端 x 排序分配
    segs = []   # (row_gap_index, chain_idx, seg_idx, a_id, b_id, going_down)
    for ci, ch in enumerate(chains):
        if ci in same:
            continue
        for si in range(len(ch) - 1):
            a, b = ch[si], ch[si + 1]
            down = lay_of_item(a, lay_of, chains) < lay_of_item(b, lay_of, chains)
            segs.append((ci, si, a, b, down))
    ports = {}
    side = {}
    for ci, si, a, b, down in segs:
        side.setdefault((a, "bottom" if down else "top"), []).append((ci, si, b))
        side.setdefault((b, "top" if down else "bottom"), []).append((ci, si, a))
    for (n, sd), lst in side.items():
        it = item[n]
        lst.sort(key=lambda t: (item[t[2]]["x"] + item[t[2]]["w"] / 2, t[0]))
        for j, (ci, si, other) in enumerate(lst):
            if it.get("dummy"):
                px = it["x"] + it["w"] / 2
            else:
                inset = min(6.0, it["w"] * 0.2)
                span = it["w"] - 2 * inset
                px = it["x"] + inset + span * (j + 1) / (len(lst) + 1)
            ports[(n, sd, ci, si)] = px
    # 竖向: 行高、间隙（间隙里按带放标签）
    nrows = len(placed)
    row_h = [max([i["h"] for i in r if not i["dummy"]] or [4.0]) for r in placed]
    gap_labels = [[] for _ in range(nrows)]       # gap k 在 row k 与 row k+1 之间；最后一个给 U 形
    for ci, ch in enumerate(chains):
        e = edges[ci]
        if ci in same:
            ia = [x["id"] for x in placed[lay_of[e["ga"]]]]
            if abs(ia.index(e["ga"]) - ia.index(e["gb"])) == 1:
                continue              # 相邻：标签放在两框之间的横向间隙
            gap_labels[lay_of[e["ga"]]].append(ci)
            continue
        la, lb_ = lay_of[e["ga"]], lay_of[e["gb"]]
        gap_labels[min(la, la + (1 if lb_ > la else -1))].append(ci)
    labels = {ci: (label_block(meter, edges[ci], 40.0, bal=True) if stacked
                                    else label_block(meter, edges[ci], 64.0)) for ci in range(len(edges))}
    if stacked:
        for ci in same:
            labels[ci] = label_block(meter, edges[ci], H_LABEL_W, stack=True)
    bands = {}
    gap_h = []
    for k in range(nrows):
        lst = gap_labels[k]
        band_rows = []
        for ci in sorted(lst, key=lambda c: est_x(c, chains, item, ports, edges, lay_of, same)):
            lb = labels[ci]
            cx = est_x(ci, chains, item, ports, edges, lay_of, same)
            iv = (cx - lb["w"] / 2 - 1.5, cx + lb["w"] / 2 + 1.5)
            for bi, br in enumerate(band_rows):
                if all(iv[1] < o[0] or iv[0] > o[1] for o in br["iv"]):
                    br["iv"].append(iv)
                    br["h"] = max(br["h"], lb["h"])
                    bands[ci] = (k, bi)
                    break
            else:
                band_rows.append({"iv": [iv], "h": lb["h"]})
                bands[ci] = (k, len(band_rows) - 1)
        if k == nrows - 1 and not band_rows:
            gap_h.append(0.0)
        else:
            gap_h.append((3.2 + sum(b["h"] + 1.2 for b in band_rows) + 2.6) if band_rows else 7.0)
        gap_labels[k] = band_rows
    y = 0.6
    row_top = []
    for k in range(nrows):
        row_top.append(y)
        for it in placed[k]:
            it["y"] = y + (row_h[k] - it["h"]) / 2 if not it["dummy"] else y
            if it["dummy"]:
                it["h"] = row_h[k]
        y += row_h[k] + gap_h[k]
    H = y + 0.6
    band_y = {}
    for ci, (k, bi) in bands.items():
        top = row_top[k] + row_h[k] + 3.2
        top += sum(b["h"] + 1.2 for b in gap_labels[k][:bi])
        band_y[ci] = top + gap_labels[k][bi]["h"] / 2
    return {"H": H, "items": item, "placed": placed, "chains": chains, "ports": ports, "labels": labels,
            "band_y": band_y, "same": same, "stacked": stacked, "row_top": row_top, "row_h": row_h, "lay_of": lay_of}


def lay_of_item(n, lay_of, chains):
    if n in lay_of:
        return lay_of[n]
    return int(n.rsplit("_", 1)[1])


def est_x(ci, chains, item, ports, edges, lay_of, same):
    ch = chains[ci]
    if ci in same:
        a, b = item[ch[0]], item[ch[-1]]
        return (a["x"] + a["w"] / 2 + b["x"] + b["w"] / 2) / 2
    a, b = ch[0], ch[1]
    down = lay_of_item(a, lay_of, chains) < lay_of_item(b, lay_of, chains)
    xa = ports.get((a, "bottom" if down else "top", ci, 0), item[a]["x"] + item[a]["w"] / 2)
    xb = ports.get((b, "top" if down else "bottom", ci, 0), item[b]["x"] + item[b]["w"] / 2)
    return (xa + xb) / 2


def draw_tb(ax, meter, L, edges):
    item, ports = L["items"], L["ports"]
    for row in L["placed"]:
        for it in row:
            if not it["dummy"]:
                draw_box(ax, meter, it)
    lay_of = L["lay_of"]
    paths, pending, level_mode = {}, [], L.get("stacked", False)
    for ci, ch in enumerate(L["chains"]):
        e = edges[ci]
        lb = L["labels"][ci]
        if ci in L["same"]:
            a, b = item[e["ga"]], item[e["gb"]]
            left, right = (a, b) if a["x"] < b["x"] else (b, a)
            if ci not in L["band_y"]:                  # 相邻：横线 + 标签在两框之间
                xa = a["x"] + a["w"] if a is left else a["x"]
                xb = b["x"] if b is right else b["x"] + b["w"]
                mx = (left["x"] + left["w"] + right["x"]) / 2
                if lb.get("stack"):                    # 竖叠标签压在线中间（两框重叠高度的中线）
                    yy = (max(a["y"], b["y"]) + min(a["y"] + a["h"], b["y"] + b["h"])) / 2
                    draw_path(ax, [(xa, yy), (xb, yy)], e["dashed"], e.get("dim"))
                    paths[ci] = [(xa, yy), (xb, yy)]
                    draw_label(ax, meter, lb, mx, yy)
                else:
                    yy = max(a["y"], b["y"]) + min(a["h"], b["h"]) / 2 + 2.0
                    draw_path(ax, [(xa, yy), (xb, yy)], e["dashed"], e.get("dim"))
                    draw_label(ax, meter, lb, mx, yy - lb["h"] / 2 - 1.0)
            else:                                      # 不相邻：走下方间隙的 U 形
                by = L["band_y"][ci] + lb["h"] / 2 + 0.8
                xa, xb = a["x"] + a["w"] / 2, b["x"] + b["w"] / 2
                draw_path(ax, [(xa, a["y"] + a["h"]), (xa, by), (xb, by), (xb, b["y"] + b["h"])], e["dashed"],
                          e.get("dim"))
                draw_label(ax, meter, lb, (xa + xb) / 2, L["band_y"][ci] - 0.4)
            continue
        pts = []
        for si in range(len(ch) - 1):
            a, b = ch[si], ch[si + 1]
            down = lay_of_item(a, lay_of, L["chains"]) < lay_of_item(b, lay_of, L["chains"])
            ia, ib = item[a], item[b]
            xa = ports[(a, "bottom" if down else "top", ci, si)]
            xb = ports[(b, "top" if down else "bottom", ci, si)]
            ya = (ia["y"] + ia["h"]) if down else ia["y"]
            yb = ib["y"] if down else (ib["y"] + ib["h"])
            if si == 0:
                pts.append((xa, ya))
            elif abs(pts[-1][0] - xa) > 0.01 or abs(pts[-1][1] - ya) > 0.01:
                pts.append((xa, ya))
            pts.append((xb, yb))
        draw_path(ax, pts, e["dashed"], e.get("dim"))
        paths[ci] = pts
        if ci in L["band_y"]:
            (x1, y1), (x2, y2) = pts[0], pts[1]
            yy = L["band_y"][ci]
            t = 0.5 if abs(y2 - y1) < 1e-6 else (yy - y1) / (y2 - y1)
            cx = x1 + (x2 - x1) * t
            pending.append((ci, lb, cx, yy))
    placed_lb = []
    for ci, lb, cx, yy in pending:
        cands = [cx]
        if level_mode:        # 一层一张图：标签压到别的边上时，改放到自己这条线的左侧或右侧
            cands += [cx - lb["w"] / 2 - 1.0, cx + lb["w"] / 2 + 1.0]
        best = None
        for k, c in enumerate(cands):
            c = min(max(c, lb["w"] / 2 + 0.3), FIG_W - lb["w"] / 2 - 0.3)
            r = (c - lb["w"] / 2, yy - lb["h"] / 2, c + lb["w"] / 2, yy + lb["h"] / 2)
            hit = sum(1 for cj, p in paths.items() if cj != ci and path_hits_rect(p, r))
            ov = sum(1 for q in placed_lb if not (r[2] < q[0] or r[0] > q[2] or r[3] < q[1] or r[1] > q[3]))
            score = (ov * 10 + hit, k)
            if best is None or score < best[0]:
                best = (score, c, r)
        placed_lb.append(best[2])
        draw_label(ax, meter, lb, best[1], yy)


def path_hits_rect(pts, r, step=0.5):
    """折线是否穿过矩形 r = (x0, y0, x1, y1)（沿线取点近似）。"""
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / step))
        for i in range(n + 1):
            x, y = x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n
            if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
                return True
    return False


# ---------------------------------------------------------------- 布局: LR（层横排）

LR_BOX_MAX = 42.0
LR_LABEL_W = 24.0


def layout_lr(meter, sk, edges, layers):
    """只处理简单情形（无同层、无跨层、无回边）；放不下返回 None，由调用方换 TB。"""
    gby = {g["id"]: g for g in sk["groups"]}
    lay_of = {g: k for k, l in enumerate(layers) for g in l}
    for e in edges:
        if lay_of[e["gb"]] - lay_of[e["ga"]] != 1:
            return None
    cols = [[build_box(meter, gby[n], LR_BOX_MAX, 1) for n in l] for l in layers]
    labels = {ci: label_block(meter, e, LR_LABEL_W) for ci, e in enumerate(edges)}
    gap_w = []
    for k in range(len(cols) - 1):
        ws = [labels[ci]["w"] for ci, e in enumerate(edges) if lay_of[e["ga"]] == k]
        gap_w.append(max([8.0] + [w + 4.0 for w in ws]))
    tot = sum(max(b["w"] for b in c) for c in cols) + sum(gap_w)
    if tot > FIG_W:
        return None
    VG = 5.0
    col_h = [sum(b["h"] for b in c) + VG * (len(c) - 1) for c in cols]
    H0 = max(col_h)
    x = (FIG_W - tot) / 2
    item = {}
    col_x = []
    for k, c in enumerate(cols):
        cw = max(b["w"] for b in c)
        col_x.append((x, cw))
        y = (H0 - col_h[k]) / 2
        for b in c:
            b["x"], b["y"] = x + (cw - b["w"]) / 2, y
            y += b["h"] + VG
            item[b["id"]] = b
        x += cw + (gap_w[k] if k < len(gap_w) else 0)
    # 端口（右边/左边，按另一端 y 排序）
    side = {}
    for ci, e in enumerate(edges):
        side.setdefault((e["ga"], "r"), []).append((ci, e["gb"]))
        side.setdefault((e["gb"], "l"), []).append((ci, e["ga"]))
    ports = {}
    for (n, sd), lst in side.items():
        it = item[n]
        lst.sort(key=lambda t: (item[t[1]]["y"] + item[t[1]]["h"] / 2, t[0]))
        for j, (ci, _o) in enumerate(lst):
            inset = min(4.0, it["h"] * 0.2)
            ports[(n, sd, ci)] = it["y"] + inset + (it["h"] - 2 * inset) * (j + 1) / (len(lst) + 1)
    # 标签: 间隙中线处，按线的 y 放，重叠就往下推
    place = {}
    for k in range(len(cols) - 1):
        cx = col_x[k][0] + col_x[k][1] + gap_w[k] / 2
        lst = []
        for ci, e in enumerate(edges):
            if lay_of[e["ga"]] != k:
                continue
            xa = item[e["ga"]]["x"] + item[e["ga"]]["w"]
            xb = item[e["gb"]]["x"]
            ya, yb = ports[(e["ga"], "r", ci)], ports[(e["gb"], "l", ci)]
            t = (cx - xa) / ((xb - xa) or 1)
            lst.append([ya + (yb - ya) * t, ci])
        lst.sort()
        last = -1e9
        for p in lst:
            h = labels[p[1]]["h"]
            p[0] = max(p[0] - h / 2, last + 1.0) + h / 2
            last = p[0] + h / 2
            place[p[1]] = (cx, p[0])
    lo = min([0.0] + [y - labels[ci]["h"] / 2 for ci, (_x, y) in place.items()])
    hi = max([H0] + [y + labels[ci]["h"] / 2 for ci, (_x, y) in place.items()])
    shift = 0.6 - lo
    for b in item.values():
        b["y"] += shift
    ports = {k: v + shift for k, v in ports.items()}
    place = {ci: (x_, y + shift) for ci, (x_, y) in place.items()}
    return {"H": hi - lo + 1.2, "items": item, "ports": ports, "labels": labels, "place": place}


def draw_lr(ax, meter, L, edges):
    item = L["items"]
    for b in item.values():
        draw_box(ax, meter, b)
    for ci, e in enumerate(edges):
        a, b = item[e["ga"]], item[e["gb"]]
        pa = (a["x"] + a["w"], L["ports"][(e["ga"], "r", ci)])
        pb = (b["x"], L["ports"][(e["gb"], "l", ci)])
        draw_path(ax, [pa, pb], e["dashed"], e.get("dim"))
        cx, cy = L["place"][ci]
        draw_label(ax, meter, L["labels"][ci], cx, cy)


# ---------------------------------------------------------------- 入口

def draw_png(sk: dict, out_png: Path, font_path: str | None) -> bool:
    if not sk.get("groups"):
        return False
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        meter = Meter(font_path)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠  matplotlib 不可用 ({e})，骨架图退化为卡片", file=sys.stderr)
        return False
    try:
        edges = group_edges(sk)
        layers = layering(sk, edges)
        if level(sk):
            layers = compact_layers(meter, sk, edges, layers)
        layers = order_layers(layers, edges)
        L, mode = None, "TB"
        if sk["direction"] == "LR" and len(sk["groups"]) <= 4:
            L = layout_lr(meter, sk, edges, layers)
            mode = "LR" if L else "TB"
        if L is None:
            L = layout_tb(meter, sk, edges, layers)
        H = L["H"]
        fig = plt.figure(figsize=(FIG_W / 25.4, H / 25.4), dpi=300)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, FIG_W)
        ax.set_ylim(H, 0)
        ax.axis("off")
        (draw_lr if mode == "LR" else draw_tb)(ax, meter, L, edges)
        fig.savefig(str(out_png), dpi=300)
        plt.close(fig)
        sk["_mode"], sk["_height_mm"] = mode, H
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠  骨架图绘制失败 ({type(e).__name__}: {e})，退化为卡片", file=sys.stderr)
        return False


def render_card_html(sk: dict) -> str:
    """离线出图不可用时的退化形态：每个大概念一张卡片 + 关系列表。"""
    name = {g["id"]: g["label"] for g in sk["groups"]}
    out = ['<div class="skel-cards">']
    for g in sk["groups"]:
        lis = "".join(
            f'<li class="{"skel-core" if l["core"] else ""}">{"★ " if l["core"] else ""}'
            f'{html_mod.escape(l["short"])}<span class="skel-ref">{html_mod.escape(l["ref"])}</span></li>'
            for l in g["leaves"])
        out.append(f'<div class="skel-card"><div class="skel-gt">{html_mod.escape(g["label"])}</div>'
                   f'<ul>{lis}</ul></div>')
    rels = []
    for e in group_edges(sk):
        arrow = "⇢" if e["dashed"] else "→"
        rels.append(f'<li>{html_mod.escape(name[e["ga"]])} {arrow} {html_mod.escape(name[e["gb"]])}'
                    f'：<b>{html_mod.escape(e["rel"])}</b>{("，" + html_mod.escape(e["phrase"])) if e["phrase"] else ""}</li>')
    if rels:
        out.append('<ul class="skel-rels">' + "".join(rels) + "</ul>")
    out.append("</div>")
    return "\n".join(out)


MERMAID_RE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)

if __name__ == "__main__":
    md = Path(sys.argv[1]).read_text(encoding="utf-8")
    outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    outdir.mkdir(parents=True, exist_ok=True)
    font = next((p for p in ("/mnt/c/Windows/Fonts/msyh.ttc", "/mnt/c/Windows/Fonts/simhei.ttf",
                             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
                 if Path(p).exists()), None)
    k = 0
    for m in MERMAID_RE.finditer(md):
        if not is_skeleton(m.group(1)):
            continue
        k += 1
        sk = parse_skeleton(m.group(1))
        out = outdir / f"skeleton-{k}.png"
        if draw_png(sk, out, font):
            print(f"✓ {out}  ({sk.get('_mode')}, {sk.get('_height_mm', 0):.0f}mm) {caption(sk)}")
        else:
            print(render_card_html(sk))
