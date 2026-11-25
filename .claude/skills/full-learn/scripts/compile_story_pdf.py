#!/usr/bin/env python3
"""
compile_story_pdf.py — 把 full-learn 工作区的 book/*.md 编成一本 A5 书（render 模块 compile）。

用法（只在 WSL 里跑）:
    python3 compile_story_pdf.py output/<课>/full-learn            # 或直接给 .../full-learn/book
        → output/<课>/full-learn/book.pdf                            全书
    ... --only 3 | 03 | 03-<slug>.md [--with-front]                  单章预览（⏸2 样章审阅）
        → output/<课>/full-learn/book-ch03.pdf                       不覆盖全书
    ... -o <path.pdf>                                                 自定输出路径
    ... --no-goals                                                    不印 ✅ 目标块（MD 照留）
    ... --no-gate                                                     跳过编前门禁（只用于调试，会大声提示）
    ... --no-verify                                                   编完不自动跑 verify_pdf.py
    ... --volumes                                                     整本 book.pdf 之外，按 spine 的卷划分再出
出手块（chapter 理论 6）: ⚔️ 押一注 → 挑战卡；`<!-- reveal -->` 后的「**揭晓**」块另起一页；🗺️ → 节首细路线条；
`🤔 先猜` → 小卡片 + 下方留白；🧠 心智卡 → 卡片（锚点 card-<章号>，⚔️ 的跳关链接整本 / 分卷都可点）；
🌳 块小结 → 青色卡片，下接的小树图（框内「留下：…」）用块小结图注；
**本章 boss** / **现在去打** / **先回忆** / **世界模型 vN** → 徽章行；收章自动插拼图进度图（不写进 MD）：放在
世界模型 vN 段之后（没有就在 🧠 之后），图 = 本卷卷串讲「## 卷骨架」的 L2 图，本章所在块 here、之前 done、之后 dim。
        → book-vol<K>.pdf（第 K 卷各章 + 卷串讲）× 卷数 + book-map.pdf（总纲卷）   各册都过 verify_pdf

成书结构: 封面（书名 + 课程名）→ 可点目录（带页码）→ 全书一览（章 / 解锁能力 / 阅读时间 / 最重节）
→ 书首 00-front → 各章 NN-*（按 NN，每章新起一页；卷串讲 NNv-* 紧跟第 NN 章）→ 总纲卷 98-map
→ 书尾 99-back → 术语索引（由 tree.json 生成）。PDF 书签 = h1/h2（卷串讲、总纲的 h1 是一级、不编号 h2 是二级）；
页眉面包屑 = "第N章 短名 · <大概念> · §N.M 中文"（大概念取本章骨架里该节所在的 subgraph 标签；没有骨架就退回
"第N章 短名 · §N.M 中文"；超长先截大概念）；卷串讲 "第三卷串讲 · <h2>"，总纲 "总纲 · <h2>"。
节点级科技树不进书（book PARADIGM 方法 1）：MD 里残留非骨架、非 § 地图的 mermaid 只报 WARN，不画。
分卷册里指向本册之外的引用降为纯文本：§N.M → "第 N 章 §N.M"（前文已写第 N 章则只留 §N.M；总纲册只留 §N.M），
指向册外文件的 MD 链接只留文字，不留死链。

编译器自带的门与生成（audit 脚本注册表）:
    #gate        编前跑 layout_check（verify_teach.check_pdf_layout）+ 读 audit/*.md 的 FAIL 行，任一 FAIL 拒编
    #output_path 默认输出 <full-learn>/book.pdf，课程名取 book_dir.parent.parent.name
    #collect     00-front → NN 按序（NNv 紧跟 NN）→ 98-map → 99-back；空目录退出；打印清单、页数与大小
    #volumes     spine 卷行 `# 第 K 卷 <标题> — 解锁: …` → 分卷册 book-vol<K>.pdf 与 book-map.pdf（E-BOOK-32）
    #tree_figure （停用）节点级科技树不再进书；tree_figure.py 只留给 tree.html 等书外用途
    #skeleton_figure 首行 `%% skeleton` 的 mermaid（章骨架 / 卷骨架 / 全书骨架）→ 骨架图 PNG
                 （skeleton_figure.py，无 matplotlib 时退化为 HTML 卡片）；旧格式（§ 开头标签）的章首地图仍渲成分段卡片
    #term_index  tree.json 节点中英文名 → 所在节，书尾自动索引

依赖: pip install --user --break-system-packages markdown weasyprint pymdown-extensions matplotlib pymupdf
"""

import argparse
import html as html_mod
import json
import math
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import markdown
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    import pymdownx  # noqa: F401
except ImportError as _e:
    print(f"✗ 缺依赖: {_e}\n  pip install --user --break-system-packages "
          "markdown weasyprint pymdown-extensions", file=sys.stderr)
    sys.exit(2)

from latex_to_html import convert_math_blocks, MATH_CSS   # noqa: E402
from block_roles import BLOCK_ROLES, INLINE_MARKS          # noqa: E402
import tree_figure                                          # noqa: E402
import skeleton_figure                                      # noqa: E402
from verify_spine import parse_volumes, int_to_cn, cn_to_int  # noqa: E402


# =====================================================================
# 字体
# =====================================================================

CJK_CANDIDATES = [
    ("/mnt/c/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
    ("/mnt/c/Windows/Fonts/simhei.ttf", "SimHei"),
    ("/mnt/c/Windows/Fonts/simsun.ttc", "SimSun"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK SC"),
    ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "WenQuanYi Micro Hei"),
    ("/usr/share/fonts/truetype/arphic/uming.ttc", "AR PL UMing CN"),
]
EMOJI_CANDIDATES = [
    "/mnt/c/Windows/Fonts/seguiemj.ttf",
    str(Path.home() / ".local/share/fonts/NotoColorEmoji.ttf"),
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
]


def find_cjk_font():
    for p, name in CJK_CANDIDATES:
        if Path(p).exists():
            print(f"✓ CJK 字体: {name} ({p})", file=sys.stderr)
            return name, p
    print("⚠  找不到 CJK 字体，中文可能排成方块。装 fonts-noto-cjk 或挂载 Windows 字体。",
          file=sys.stderr)
    return None, None


def find_emoji_font():
    return next((p for p in EMOJI_CANDIDATES if Path(p).exists()), None)


# =====================================================================
# collect — 组书
# =====================================================================

CH_FILE_RE = re.compile(r"^(\d{2})-.+\.md$")
SYN_FILE_RE = re.compile(r"^(\d{2})v-.+\.md$")        # 卷串讲：紧跟第 NN 章（CONTRACTS T4）
MAP_FILE = "98-map.md"                                  # 总纲卷：书尾之前
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
CH_H1_RE = re.compile(r"第\s*(\d+)\s*章\s*(.*)$")
SYN_H1_RE = re.compile(r"第\s*([一二三四五六七八九十\d]+)\s*卷串讲\s*[:：]?\s*(.*)$")
SEC_MD_RE = re.compile(r"^##\s+§\s*(\d+)\.(\d+)\s+(.+?)\s*$", re.M)
NODES_COMMENT_RE = re.compile(r"<!--\s*nodes:\s*([^|>]*?)\s*(?:\|\s*sources:\s*(.*?))?\s*-->")
EN_SUFFIX_RE = re.compile(r"\s*[（(][^（()）]*[A-Za-z][^（()）]*[)）]\s*$")
FENCE_LINE_RE = re.compile(r"^\s*(```|~~~)")


def strip_en(title: str) -> str:
    """'流量平衡 (Flow Balance)' → '流量平衡'。面包屑与页眉不带英文副标题。"""
    return EN_SUFFIX_RE.sub("", title).strip()


def resolve_book_dir(p: Path) -> Path:
    p = p.resolve()
    if (p / "book").is_dir():
        return p / "book"
    if p.is_dir():
        return p
    raise SystemExit(f"不是目录: {p}")


def collect(book_dir: Path):
    """返回 parts 列表（front → 各章，卷串讲 NNv 紧跟第 NN 章 → 总纲 98-map → back），每个 part 是 dict。"""
    mds = sorted(book_dir.glob("*.md"))
    if not mds:
        raise SystemExit(f"{book_dir} 下没有 MD 文件，不编译")
    front, back, maps, chapters, ignored = [], [], [], [], []
    for f in mds:
        sm = SYN_FILE_RE.match(f.name)
        if sm:
            chapters.append((int(sm.group(1)), 1, f))     # 同号时排在章之后
            continue
        if f.name == MAP_FILE:
            maps.append(f)
            continue
        m = CH_FILE_RE.match(f.name)
        if not m:
            ignored.append(f.name)
            continue
        nn = int(m.group(1))
        if nn == 0:
            front.append(f)
        elif nn == 99:
            back.append(f)
        else:
            chapters.append((nn, 0, f))
    chapters.sort(key=lambda x: (x[0], x[1]))
    for name in ignored:
        hint = "（book/ 不该有 index.md：目录由编译器生成）" if name == "index.md" else ""
        print(f"⚠  忽略不符合 NN-<slug>.md 的文件: {name}{hint}", file=sys.stderr)

    parts = []
    for f in front:
        parts.append(_part("front", f, 0))
    for nn, is_syn, f in chapters:
        parts.append(_part("synth" if is_syn else "chapter", f, nn))
    for f in maps:
        parts.append(_part("map", f, 98))
    for f in back:
        parts.append(_part("back", f, 99))
    return parts


def _part(kind: str, path: Path, nn: int) -> dict:
    md = path.read_text(encoding="utf-8")
    body_md = _outside_fences(md)
    h1 = H1_RE.search(body_md)
    h1_text = h1.group(1).strip() if h1 else path.stem
    part = {"kind": kind, "path": path, "nn": nn, "md": md, "h1": h1_text,
            "sections": [], "nodes": {}}
    if kind == "chapter":
        m = CH_H1_RE.search(h1_text)
        part["ch"] = int(m.group(1)) if m else nn
        part["short"] = strip_en(m.group(2)) if m else strip_en(h1_text)
        if m and int(m.group(1)) != nn:
            print(f"⚠  {path.name}: 文件号 {nn:02d} 与标题「第 {m.group(1)} 章」不一致，锚点按标题",
                  file=sys.stderr)
        if not m:
            print(f"⚠  {path.name}: 章标题不是「# 第 N 章 <标题>」，按文件号当第 {nn} 章",
                  file=sys.stderr)
        part["anchor"] = f"ch-{part['ch']}"
        part["concept_of"] = skeleton_concepts(md)
    elif kind == "synth":
        m = SYN_H1_RE.search(h1_text)
        if not m:
            print(f"⚠  {path.name}: 卷串讲标题不是「# 第 K 卷串讲：<卷标题>」", file=sys.stderr)
        part["vol"] = m.group(1) if m else "?"
        part["vol_title"] = m.group(2).strip() if m else h1_text
        part["anchor"] = f"syn-{nn}"
        part["short"] = f"第{part['vol']}卷串讲"
    elif kind == "map":
        if not h1_text.startswith("总纲"):
            print(f"⚠  {path.name}: 总纲卷标题不是「# 总纲：全书归位」", file=sys.stderr)
        part["anchor"] = "map"
        part["short"] = "总纲"
    else:
        part["anchor"] = kind
        part["short"] = "书首" if kind == "front" else "书尾"
    lines = body_md.split("\n")
    for i, ln in enumerate(lines):
        m = SEC_MD_RE.match(ln)
        if not m:
            continue
        n, mm, title = int(m.group(1)), int(m.group(2)), m.group(3)
        nodes = []
        for nxt in lines[i + 1:i + 4]:
            c = NODES_COMMENT_RE.search(nxt)
            if c:
                nodes = [x.strip() for x in c.group(1).split(",") if x.strip()]
                break
        sec = {"n": n, "m": mm, "title": title, "cn": strip_en(title),
               "anchor": f"sec-{n}-{mm}", "nodes": nodes}
        part["sections"].append(sec)
    return part


def skeleton_concepts(md: str) -> dict:
    """本章骨架（首个 `%% skeleton` mermaid）→ {'21.3': '稳态分布'}：每节所在的大概念，喂给面包屑。"""
    for m in MERMAID_FENCE_RE.finditer(md):
        if skeleton_figure.is_skeleton(m.group(1)):
            sk = skeleton_figure.parse_skeleton(m.group(1))
            return {x: g["label"] for g in sk["groups"] for l in g["leaves"] for x in l["secs"]}
    return {}


def _outside_fences(md: str) -> str:
    """把围栏代码块内容换成空行（保持行号），解析结构时不被代码里的 # 骗到。"""
    out, inf = [], False
    for ln in md.split("\n"):
        if FENCE_LINE_RE.match(ln):
            inf = not inf
            out.append("")
            continue
        out.append("" if inf else ln)
    return "\n".join(out)


# =====================================================================
# gate — 编前门禁
# =====================================================================

def run_gate(parts, workspace: Path) -> bool:
    ok = True
    try:
        import verify_teach as vt
    except Exception as e:  # noqa: BLE001
        print(f"⚠  layout_check 不可用 ({e})，排版门禁未跑", file=sys.stderr)
        vt = None
    if vt is not None:
        for p in parts:
            vt.fails.clear(); vt.warns.clear(); vt.infos.clear()
            vt.check_pdf_layout(p["md"].split("\n"))
            for w in vt.warns:
                print(f"  ⚠  layout {p['path'].name}: {w}", file=sys.stderr)
            if vt.fails:
                ok = False
                print(f"  ✗ layout FAIL {p['path'].name}:", file=sys.stderr)
                for f in vt.fails[:20]:
                    print(f"      {f}", file=sys.stderr)
    audit = workspace / "audit"
    if not audit.is_dir():
        print("⚠  没有 audit/ 报告：内容门禁未经验证（E-RENDER-01）。先跑 audit 再出正式 PDF。",
              file=sys.stderr)
    else:
        for f in sorted(audit.glob("*.md")):
            n = sum(1 for ln in f.read_text(encoding="utf-8").split("\n")
                    if re.match(r"^\|\s*E-[\w-]+\s*\|\s*FAIL\s*\|", ln))
            if n:
                ok = False
                print(f"  ✗ audit/{f.name} 有 {n} 条 FAIL", file=sys.stderr)
    return ok


# =====================================================================
# MD → HTML
# =====================================================================

TOKEN_TAG_RE = re.compile(r'<(/?(?:s|eos|bos|pad|cls|sep|unk|mask))>', re.IGNORECASE)
_CODE_SPLIT_RE = re.compile(r'(```[\s\S]*?```|`[^`\n]+`)')
COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")


def escape_token_tags(text: str) -> str:
    parts = _CODE_SPLIT_RE.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = TOKEN_TAG_RE.sub(lambda m: f'`<{m.group(1)}>`', parts[i])
    return "".join(parts)


def strip_comments(text: str) -> str:
    """机读注释（<!-- nodes: … | sources: … -->）与其它 HTML 注释不进正文。代码块内不动。"""
    parts = re.split(r"(```[\s\S]*?```)", text)
    for i in range(0, len(parts), 2):
        parts[i] = COMMENT_RE.sub("", parts[i])
    return "".join(parts)


# ---------- mermaid: 章首地图（§ 卡片）与 科技树（分层图） ----------
MERMAID_FENCE_RE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
_MMD_SUBGRAPH = re.compile(r'^\s*subgraph\s+(\w+)\s*\[\s*"?(.*?)"?\s*\]\s*$')
_MMD_NODE = re.compile(r'^\s*(\w+)\s*[\[\(\{]+\s*"?(.*?)"?\s*[\]\)\}]+\s*(?::::(\w+))?\s*$')
_MMD_EDGE = re.compile(r'^\s*(\w+)\s*-{2,3}>?\s*(?:\|\s*(.*?)\s*\|)?\s*(\w+)\s*$')
_MMD_CLASS = re.compile(r'^\s*class\s+([\w,\s]+?)\s+(\w+)\s*$')
MMD_TIER = {
    "core": ("mmd-core", "★ "), "key": ("mmd-core", "★ "),
    "normal": ("mmd-normal", ""), "mid": ("mmd-normal", ""),
    "bg": ("mmd-bg", ""), "background": ("mmd-bg", ""),
    "skip": ("mmd-skip", "— "), "out": ("mmd-skip", "— "),
}


def is_section_map(src: str) -> bool:
    """章首地图: 节点标签以 §N.M 开头。否则当作一般依赖图（科技树）。"""
    return bool(re.search(r'[\[\(\{]\s*"?\s*§\s*\d', src))


def is_stage_map(src: str) -> bool:
    """章末进度图：节点标签以「第N章」开头（粒度到章，不是节点级科技树）。"""
    return bool(re.search(r'[\[\(\{]\s*"?\s*第\s*\d', src))


def render_section_map(src: str) -> str:
    """章首地图 mermaid（subgraph + § 节点 + 边 + class）→ 分段卡片。不认识的行忽略。"""
    groups, order, cls_of, label_of = {}, [], {}, {}
    edges, cur, seq = [], None, []
    for raw in src.split("\n"):
        line = raw.strip()
        if not line or line.startswith("%%") or line.startswith("classDef"):
            continue
        if re.match(r"^(flowchart|graph)\b", line):
            continue
        if line == "end":
            cur = None
            continue
        m = _MMD_SUBGRAPH.match(line)
        if m:
            cur = m.group(1)
            groups[cur] = {"label": m.group(2), "nodes": []}
            order.append(cur)
            continue
        m = _MMD_CLASS.match(line)
        if m:
            for n in re.split(r"[,\s]+", m.group(1).strip()):
                if n:
                    cls_of[n] = m.group(2)
            continue
        m = _MMD_NODE.match(line)
        if m:
            nid, text, cls = m.group(1), m.group(2), m.group(3)
            label_of[nid] = text
            if cls:
                cls_of[nid] = cls
            (groups[cur]["nodes"] if cur else seq).append(nid)
            continue
        m = _MMD_EDGE.match(line)
        if m:
            edges.append((m.group(1), m.group(3), m.group(2) or ""))
    if not groups and not seq:
        return ""

    def chip(nid):
        cls, badge = MMD_TIER.get(cls_of.get(nid, "normal"), ("mmd-normal", ""))
        text = html_mod.escape(label_of.get(nid, nid)).replace("&lt;br/&gt;", "<br>").replace("&lt;br&gt;", "<br>")
        return f'<span class="mmd-node {cls}">{badge}{text}</span>'

    out = ['<div class="mmd">']
    between = {(a, b): lab for a, b, lab in edges if a in groups and b in groups}
    for i, gid in enumerate(order):
        g = groups[gid]
        out.append(f'<div class="mmd-group"><div class="mmd-gt">{html_mod.escape(g["label"])}</div>'
                   f'<div class="mmd-row">' + "".join(chip(n) for n in g["nodes"]) + "</div></div>")
        if i + 1 < len(order):
            lab = between.get((gid, order[i + 1]), "")
            out.append(f'<div class="mmd-arrow">▼ {html_mod.escape(lab)}</div>' if lab
                       else '<div class="mmd-arrow">▼</div>')
    if seq:
        out.append('<div class="mmd-row mmd-loose">' + "".join(chip(n) for n in seq) + "</div>")
    out.append("</div>")
    return "\n".join(out)


class TreeRenderer:
    """科技树（及任何非 § 的依赖图 mermaid）→ 离线 PNG；画不出时退化为分层列表。"""

    def __init__(self, workspace: Path, cjk_path: str | None, tmpdir: Path):
        self.workspace, self.cjk_path, self.tmpdir = workspace, cjk_path, tmpdir
        self.count = 0          # 生成的图片张数（verify_pdf 用来扣除非原图图片）
        self.degraded = False

    def render(self, mermaid_src: str | None, landscape: bool) -> str:
        g = tree_figure.load_tree_graph(self.workspace, mermaid_src)
        if g is None:
            return ""
        png = self.tmpdir / f"tree-{self.count + 1}.png"
        if tree_figure.draw_png(g, png, self.cjk_path):
            self.count += 1
            cls = "tree-page" if landscape else "tree-inline"
            body = (f'<figure class="tree-fig"><img src="{png.as_uri()}" alt="科技树">'
                    f'<figcaption>科技树：下层是上层的前置，箭头指向依赖它的节点。</figcaption></figure>')
        else:
            self.degraded = True
            cls = "tree-page-list" if landscape else "tree-inline"
            body = tree_figure.render_tree_list(g)
        if landscape:
            return (f'<section class="{cls}" id="tree"><h1 class="tree-title">科技树</h1>{body}</section>')
        return f'<div class="{cls}">{body}</div>'


VOL_HEAD_RE = re.compile(r"^#{1,6}\s+(.*)$", re.M)
VOL_NAME_RE = re.compile(r"卷\s*([一二三四五六七八九十\d]+)|第\s*([一二三四五六七八九十\d]+)\s*卷")


class SkeletonRenderer:
    """`%% skeleton` mermaid（章骨架 / 卷骨架 / 全书骨架）→ 离线 PNG；画不出时退化为 HTML 卡片。"""

    def __init__(self, cjk_path: str | None, tmpdir: Path):
        self.cjk_path, self.tmpdir = cjk_path, tmpdir
        self.count = 0          # 生成的骨架图张数（verify_pdf 扣除非原图图片）
        self.degraded = False

    def render(self, src: str, before: str = "") -> str:
        sk = skeleton_figure.parse_skeleton(src)
        if not sk["groups"]:
            return ""
        vol = ""
        if skeleton_figure.figure_kind(sk) == "volume":   # 卷名取图前最近的带卷号标题（「## 卷三 …」「# 第三卷串讲」）
            heads = VOL_HEAD_RE.findall(before)
            m = VOL_NAME_RE.search(heads[-1]) if heads else None
            if not m and heads and "卷串讲" in heads[0]:
                m = VOL_NAME_RE.search(heads[0])
            if m:
                vol = f"第{m.group(1) or m.group(2)}卷"
        cap = skeleton_figure.caption(sk, vol)
        if any(l["core"] for g in sk["groups"] for l in g["leaves"]):
            cap += "★ 标出承重的一行。" if skeleton_figure.level(sk) else "★ 标出承重的子题。"
        png = self.tmpdir / f"skeleton-{self.count + 1}.png"
        if skeleton_figure.draw_png(sk, png, self.cjk_path):
            self.count += 1
            return (f'<figure class="skel-fig"><img src="{png.as_uri()}" alt="{html_mod.escape(cap.split("：")[0])}">'
                    f'<figcaption>{html_mod.escape(cap)}</figcaption></figure>')
        self.degraded = True
        return (f'<figure class="skel-fig skel-fallback">{skeleton_figure.render_card_html(sk)}'
                f'<figcaption>{html_mod.escape(cap)}</figcaption></figure>')


TREE_ABSORB_RE = re.compile(
    r'<h2([^>]*)>((?:(?!<h2)[\s\S])*?)</h2>\s*<section class="(tree-page[\w-]*)" id="tree"><h1 class="tree-title"[^>]*>科技树</h1>')


def absorb_tree_heading(html: str) -> str:
    """书首里「## 科技树」紧跟 mermaid 时，把这个 h2 移进横版科技树页当页标题，
    否则 h2 会孤零零留在上一页页底（整页只剩标题）。"""
    return TREE_ABSORB_RE.sub(
        lambda m: f'<section class="{m.group(3)}" id="tree"><h2{m.group(1)} class="tree-title">{m.group(2)}</h2>',
        html)


# ---------- 预处理 ----------

def split_adjacent_blockquotes(md_text: str) -> str:
    """只隔一个空行的两个引用块，Python-Markdown 会并成一个；强制拆开、各自着色。"""
    lines = md_text.split("\n")
    out, in_fence = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if (not in_fence and line.strip() == "" and out
                and out[-1].lstrip().startswith(">")):
            nxt = next((l for l in lines[i + 1:] if l.strip() != ""), "")
            if nxt.lstrip().startswith(">"):
                out.append("")
                out.append("<!-- bq-split -->")
                continue
        out.append(line)
    return "\n".join(out)


def fix_blockquote_lists(md_text: str) -> str:
    """引用块内文字行后紧跟列表项时补空 '>' 行，否则列表塌成一段。"""
    out = []
    for line in md_text.split("\n"):
        st = line.lstrip()
        if st.startswith(">") and out:
            body = st[1:].lstrip()
            prev = out[-1].lstrip()
            prev_body = prev[1:].lstrip() if prev.startswith(">") else None

            def is_item(s):
                return s.startswith(("- ", "* ", "+ ")) or (s[:1].isdigit() and s[1:3] in (". ", ".\t"))
            if is_item(body) and prev_body not in (None, "") and not is_item(prev_body):
                out.append(">")
        out.append(line)
    return "\n".join(out)


NO_GOALS = False
GOAL_BQ_RE = re.compile(r"^>\s*✅.*(?:\n>.*)*\n?", re.M)


def md_to_html(md_text: str, tree: TreeRenderer, landscape_tree: bool,
               skel: "SkeletonRenderer | None" = None, label: str = "") -> str:
    """tree / landscape_tree 只为旧调用方保留：节点级科技树已不进书（见 _stash_mermaid）。"""
    stash = []

    def _stash_mermaid(m):
        src = m.group(1)
        if skel is not None and skeleton_figure.is_skeleton(src):
            stash.append(skel.render(src, m.string[:m.start()]))
        elif is_section_map(src):
            stash.append(render_section_map(src))
        elif is_stage_map(src):
            # 章末进度图（标签以「第N章」开头、粒度到章）：照旧离线出图，不算节点级科技树
            stash.append(tree.render(src, landscape=False))
        else:
            # 节点级科技树不进书（book PARADIGM 方法 1；E-BOOK-31）：不画，提示删掉
            first = next((x.strip() for x in src.split("\n") if x.strip()), "")
            print(f"  ⚠  {label or '?'}: 非骨架、非 § 地图的 mermaid（{first[:30]}）按节点级科技树处理："
                  "不进书。它的职能由总纲卷 98-map 的层级总目录接手，请从 MD 删掉", file=sys.stderr)
            stash.append("")
        return f"\n\nMERMAIDBLOCK{len(stash) - 1}ENDMERMAID\n\n"

    if NO_GOALS:
        md_text = GOAL_BQ_RE.sub("", md_text)
    md_text = strip_comments(md_text)
    md_text = MERMAID_FENCE_RE.sub(_stash_mermaid, md_text)
    md_text = escape_token_tags(md_text)
    md_text, unknown = convert_math_blocks(md_text)
    if unknown:
        print('  ⚠  未识别的 LaTeX 命令: ' + ', '.join(sorted(unknown)), file=sys.stderr)
    md_text = split_adjacent_blockquotes(md_text)
    md_text = fix_blockquote_lists(md_text)
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "attr_list", "sane_lists",
                    "pymdownx.superfences", "footnotes"],
        extension_configs={"footnotes": {"BACKLINK_TEXT": ""}},
        output_format="html5")
    html = md.convert(md_text)
    for i, block in enumerate(stash):
        html = re.sub(rf"<p>\s*MERMAIDBLOCK{i}ENDMERMAID\s*</p>", lambda _m: block, html)
        html = html.replace(f"MERMAIDBLOCK{i}ENDMERMAID", block)
    return html


# ---------- 脚注: Markdown 脚注 → 页脚注（WeasyPrint float: footnote） ----------
FN_DIV_RE = re.compile(r'<div class="footnote">[\s\S]*?</div>\s*$')
FN_LI_RE = re.compile(r'<li id="fn:([^"]+)">([\s\S]*?)</li>')
FN_REF_RE = re.compile(r'<sup id="fnref\d*:([^"]+)"><a class="footnote-ref" href="#fn:[^"]+">\d+</a></sup>')
FN_RESIDUE_RE = re.compile(r"\[\^[^\]\s]+\]")


def convert_footnotes(html: str, label: str) -> str:
    defs = {}
    m = FN_DIV_RE.search(html)
    if m:
        for key, body in FN_LI_RE.findall(m.group(0)):
            body = re.sub(r'<a class="footnote-backref"[^>]*>.*?</a>', "", body, flags=re.S)
            body = re.sub(r"&#160;", " ", body).strip()
            body = re.sub(r"^<p>([\s\S]*)</p>$", r"\1", body).strip()
            defs[key] = body
        html = html[:m.start()]

    def repl(mm):
        content = defs.get(mm.group(1))
        if content is None:
            return mm.group(0)
        return f'<span class="fn">{content}</span>'
    html = FN_REF_RE.sub(repl, html)
    residue = FN_RESIDUE_RE.findall(re.sub(r"<(pre|code)[\s\S]*?</\1>", "", html))
    if residue:
        print(f"  ⚠  {label}: 脚注引用没有定义，会原样印出: {', '.join(sorted(set(residue)))}",
              file=sys.stderr)
    return html


# ---------- 图: 课件原图 / 自绘 ----------
IMG_PARA_RE = re.compile(r'<p>\s*(<img\b[^>]*>)\s*</p>')
SLIDE_ALT_RE = re.compile(r"课件\s*[A-Za-z][\w.\-]*\s*p\s*\d")


def wrap_figures(html: str, book_dir: Path, label: str, stats: dict) -> str:
    def repl(m):
        img = m.group(1)
        alt = html_mod.unescape((re.search(r'\balt="([^"]*)"', img) or [None, ""])[1])
        src = html_mod.unescape((re.search(r'\bsrc="([^"]*)"', img) or [None, ""])[1])
        if src and not re.match(r"^[a-z]+:", src) and not (book_dir / src).resolve().exists():
            print(f"  ✗ {label}: 图片文件不存在 {src}（相对 book/ 解析）", file=sys.stderr)
            stats["missing"] += 1
        if SLIDE_ALT_RE.search(alt):
            cls, chip = "fig fig-slide", "课件原图"
            stats["slide"] += 1
        elif alt.strip().startswith("自绘"):
            cls, chip = "fig fig-own", "自绘"
            alt = re.sub(r"^自绘\s*[·:：]?\s*", "", alt.strip())
            stats["own"] += 1
        else:
            cls, chip = "fig fig-plain", ""
            stats["plain"] += 1
            print(f"  ⚠  {label}: 图注既不含「课件 <短名> p<N>」也不以「自绘」开头: {alt[:40]}",
                  file=sys.stderr)
        chip_html = f'<span class="fig-chip">{chip}</span>' if chip else ""
        return (f'<figure class="{cls}">{img}<figcaption>{chip_html}'
                f'{html_mod.escape(alt)}</figcaption></figure>')
    return IMG_PARA_RE.sub(repl, html)


# ---------- 块类型 ----------
BQ_OPEN_RE = re.compile(r'<blockquote>(\s*<p>\s*)', re.DOTALL)


def tag_blockquote_roles(html: str) -> str:
    def repl(m):
        head = html[m.end():m.end() + 40]
        role = next((r for mk, r, _n, _l in BLOCK_ROLES if head.startswith(mk)), None)
        if role is None and head.startswith("<strong>揭晓</strong>"):
            role = "reveal"                       # ⚔️ 的揭晓块：没有块标记，靠「**揭晓**」开头认
        extra = " bq-guess" if role == "think" and re.match(r"🤔\s*先猜", head) else ""
        cls = f' class="bq bq-{role}{extra}"' if role else ''
        return f'<blockquote{cls}>{m.group(1)}'
    return BQ_OPEN_RE.sub(repl, html)


# ---------- 出手（chapter 理论 6）：挑战 / 揭晓 / 路线 / 心智卡 / boss 徽章 / 拼图进度图 ----------
REVEAL_RE = re.compile(r"^[ \t]*<!--\s*reveal\s*-->[ \t]*$", re.M)
PROGRESS_MARK = "GAMEPROGRESSFIG"
WORLD_LINE_RE = re.compile(r"^\*\*世界模型\s*v\d+")
BADGE_P_RE = re.compile(r"<p>\s*<strong>(本章 boss|现在去打|世界模型\s*v\d+|先回忆[^<]{0,12})</strong>[\s　]*")
ROUTE_BQ_RE = re.compile(r'(<blockquote class="bq bq-route">)([\s\S]*?)(</blockquote>)')


def game_markup_md(md: str) -> str:
    """MD 层：`<!-- reveal -->` → 分页标记（strip_comments 之前换掉）；收章里插拼图进度图占位
    （有 `**世界模型 vN**` 段就放在它之后，否则放在 🧠 心智卡之后；两者都没有就不放）。"""
    md = REVEAL_RE.sub('<div class="reveal-break"></div>', md)
    lines, body = md.split("\n"), _outside_fences(md).split("\n")
    last_sec = max((i for i, ln in enumerate(body) if SEC_MD_RE.match(ln)), default=None)
    if last_sec is None:
        return md
    close = next((i for i in range(last_sec + 1, len(body)) if body[i].startswith("## ")), None)
    if close is None:
        return md
    end = next((i for i in range(close + 1, len(body)) if body[i].startswith("## ")), len(body))
    at = None
    wi = next((i for i in range(close + 1, end) if WORLD_LINE_RE.match(body[i])), None)
    if wi is not None:
        at = next((i for i in range(wi, end) if not body[i].strip()), end)
        # 标题行紧跟拼图列表（不空行）时补一个空行，否则 Python-Markdown 把列表塌进段落
        if wi + 1 < at and re.match(r"^\s*[-*+]\s", body[wi + 1]):
            return "\n".join(lines[:wi + 1] + [""] + lines[wi + 1:at] + ["", PROGRESS_MARK, ""] + lines[at:])
    else:
        ci = next((i for i in range(close + 1, end) if re.match(r"^>\s*🧠", body[i])), None)
        if ci is not None:
            at = next((i for i in range(ci, end) if not body[i].lstrip().startswith(">")), end)
    if at is None:
        return md
    return "\n".join(lines[:at] + ["", PROGRESS_MARK, ""] + lines[at:])


def game_markup_html(html: str, part: dict, progress_html: str) -> str:
    """HTML 层：心智卡锚点 card-N（⚔️ 的跳关链接指向它）、路线箭头、boss / 现在去打 徽章、进度图。"""
    if part["kind"] == "chapter":
        html = html.replace('<blockquote class="bq bq-card">',
                            f'<blockquote class="bq bq-card" id="card-{part["ch"]}">', 1)
    html = ROUTE_BQ_RE.sub(lambda m: m.group(1) + m.group(2).replace("→", '<span class="route-arrow">→</span>')
                           + m.group(3), html)

    def badge(m):
        kind = "boss" if m.group(1) in ("本章 boss", "现在去打") else "world"
        return f'<p class="badge-line badge-{kind}"><strong class="badge">{m.group(1)}</strong>'
    html = BADGE_P_RE.sub(badge, html)
    # 世界模型 vN 后紧跟的拼图列表：本章新增（加粗）要一眼看出来
    html = re.sub(r'(<p class="badge-line badge-world"><strong class="badge">世界模型[^<]*</strong>[\s\S]*?</p>\s*)<ul>',
                  r'\1<ul class="wm-list">', html)
    # 心智卡里 ❌ / ✅ 行：记号放进定宽格，折行与正文对齐
    html = re.sub(r'(<blockquote class="bq bq-card"[\s\S]*?</blockquote>)',
                  lambda m: re.sub(r"<li>\s*(❌|✅)\s*", r'<li><span class="card-mk">\1</span>', m.group(1)), html)
    html = re.sub(rf"<p>\s*{PROGRESS_MARK}\s*</p>", lambda _m: progress_html, html)
    return html.replace(PROGRESS_MARK, progress_html)


class GameProgress:
    """拼图进度图：本章所在卷的 L2 卷内图（卷串讲「## 卷骨架」里那张 `%% skeleton`），
    本章所在的块 here、之前的块 done（已点亮）、之后的块 dim。"""

    def __init__(self, parts_all, workspace: Path):
        self.chapters = [p["ch"] for p in parts_all if p["kind"] == "chapter"]
        spine = workspace / "spine.md"
        self.vols = parse_volumes(spine.read_text(encoding="utf-8")) if spine.exists() else []
        self.vol_src = {}
        for v in self.vols:
            syn = next((p for p in parts_all if p["kind"] == "synth"
                        and (p["nn"] in v["chs"] or cn_to_int(str(p.get("vol", ""))) == v["k"])), None)
            if syn:
                src = self._volume_skeleton(syn["md"])
                if src:
                    self.vol_src[v["k"]] = src

    @staticmethod
    def _volume_skeleton(md: str):
        m = re.search(r"^##\s+卷骨架\s*$", md, re.M)
        if not m:
            return None
        nxt = re.search(r"^##\s", md[m.end():], re.M)
        seg = md[m.end():m.end() + nxt.start()] if nxt else md[m.end():]
        for f in MERMAID_FENCE_RE.finditer(seg):
            if skeleton_figure.is_skeleton(f.group(1)):
                return f.group(1)
        return None

    def figure(self, part, skel_r) -> str:
        ch = part["ch"]
        v = next((v for v in self.vols if ch in v["chs"]), None)
        if not v or v["k"] not in self.vol_src:
            print(f"  ⚠  第 {ch} 章: 找不到所在卷的卷串讲「## 卷骨架」图，拼图进度图不画", file=sys.stderr)
            return ""
        sk = skeleton_figure.parse_skeleton(self.vol_src[v["k"]])
        gs = sk["groups"]
        cur = next((g for g in gs if ch in g["chs"]), None)
        if cur is None:
            print(f"  ⚠  第 {ch} 章: 卷骨架里没有哪个块标了它的章号，拼图进度图不画", file=sys.stderr)
            return ""
        for g in gs:
            here = g is cur
            done = not here and bool(g["chs"]) and max(g["chs"]) < ch
            g["here"], g["done"], g["dim"] = here, done, not here and not done
        a = sum(1 for g in gs if g["done"]) + (1 if ch == max(cur["chs"]) else 0)
        idx = self.chapters.index(ch) + 1 if ch in self.chapters else ch
        cap = (f"拼图进度：第{int_to_cn(v['k'])}卷，已完成 {a}/{len(gs)} 块 · 全书 {idx}/{len(self.chapters)} 章。"
               "绿框已点亮，橙框是本章所在的块，灰框还没走到。")
        png = skel_r.tmpdir / f"progress-{ch}.png"
        if skeleton_figure.draw_png(sk, png, skel_r.cjk_path):
            skel_r.count += 1
            return (f'<figure class="skel-fig progress-fig"><img src="{png.as_uri()}" alt="拼图进度">'
                    f'<figcaption>{html_mod.escape(cap)}</figcaption></figure>')
        skel_r.degraded = True
        return (f'<figure class="skel-fig progress-fig skel-fallback">{skeleton_figure.render_card_html(sk)}'
                f'<figcaption>{html_mod.escape(cap)}</figcaption></figure>')


# ---------- 标题 id / 面包屑 ----------
HEADING_RE = re.compile(r'<h([1-6])\b([^>]*)>([\s\S]*?)</h\1>')
TAG_RE = re.compile(r'<[^>]+>')
SEC_HTML_RE = re.compile(r'^\s*§\s*(\d+)\.(\d+)')


# 页眉一行的容量（em）：A5 正文宽 124mm ÷ 页眉 7.5pt（≈2.65mm/em）≈ 46em，留余量取 42。
# 与 build_css 的 @page 边距、@top-center 字号耦合；章短名 ≤ 8 字、节标题 ≤ 12 字（render 方法 1）不变，
# 多出来的大概念名超长时先被截。
CRUMB_MAX_EM = 42.0


def _em(s: str) -> float:
    return sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in s)


def chapter_crumb(part: dict, n: int, mm: int, cn: str) -> str:
    """'第21章 多台服务器 · 稳态分布 · §21.3 M/M/m 的稳态分布'；超长先截大概念名（至少留 2 字 + …），仍超就去掉它。"""
    head, tail = f"第{part['ch']}章 {part['short']}", f"§{n}.{mm} {cn}"
    concept = (part.get("concept_of") or {}).get(f"{n}.{mm}", "")
    if not concept:
        return f"{head} · {tail}"
    full = f"{head} · {concept} · {tail}"
    if _em(full) <= CRUMB_MAX_EM:
        return full
    room = CRUMB_MAX_EM - _em(f"{head} ·  · {tail}") - 1.0   # 1em 给省略号
    cut_c = ""
    for ch in concept:
        if _em(cut_c + ch) > room:
            break
        cut_c += ch
    if len(cut_c) >= 2:
        return f"{head} · {cut_c}… · {tail}"
    return f"{head} · {tail}"


def stamp_headings(html: str, part: dict) -> str:
    """章 h1 → ch-N，节 h2 → sec-N-M，其余标题 → <part>-hK；节标题前插面包屑。"""
    counter = [0]
    first_h1 = [True]
    sec_titles = {(s["n"], s["m"]): s for s in part["sections"]}

    def repl(m):
        lvl, attrs, inner = int(m.group(1)), m.group(2), m.group(3)
        attrs = re.sub(r'\s+id="[^"]*"', "", attrs)
        text = html_mod.unescape(TAG_RE.sub("", inner)).strip()
        pre = ""
        if lvl == 1 and first_h1[0]:
            first_h1[0] = False
            hid = part["anchor"]
            crumb = (f"第{part['ch']}章 {part['short']}" if part["kind"] == "chapter"
                     else part["short"])
            attrs += f' data-crumb="{html_mod.escape(crumb)}" class="part-title"'
            if part["kind"] == "synth" and part.get("vol") != "?":
                # 「# 第 一 卷串讲：…」与「# 第一卷串讲：…」都认；书签统一成无空格写法
                inner = html_mod.escape(f"{part['short']}：{part['vol_title']}")
        elif lvl == 2 and SEC_HTML_RE.match(text):
            sm = SEC_HTML_RE.match(text)
            n, mm = int(sm.group(1)), int(sm.group(2))
            hid = f"sec-{n}-{mm}"
            sec = sec_titles.get((n, mm))
            cn = sec["cn"] if sec else strip_en(text)
            cn = re.sub(r"^§\s*\d+\.\d+\s*", "", cn)
            if part["kind"] == "chapter":
                crumb = chapter_crumb(part, n, mm, cn)
            else:
                crumb = f"{part['short']} · §{n}.{mm} {cn}"
            pre = f'<p class="crumb">{html_mod.escape(crumb)}</p>'
        elif lvl == 2 and part["kind"] in ("synth", "map"):
            # 卷串讲 / 总纲的不编号小节：面包屑「第三卷串讲 · <h2>」「总纲 · <h2>」，书签二级
            counter[0] += 1
            hid = f"{part['anchor']}-h{counter[0]}"
            pre = f'<p class="crumb">{html_mod.escape(part["short"] + " · " + strip_en(text))}</p>'
        else:
            counter[0] += 1
            hid = f"{part['anchor']}-h{counter[0]}"
        return f'{pre}<h{lvl}{attrs} id="{hid}">{inner}</h{lvl}>'
    return HEADING_RE.sub(repl, html)


# ---------- 交叉引用 ----------
PROTECT_RE = re.compile(
    r'(<pre[\s\S]*?</pre>'
    r'|<code[\s\S]*?</code>'
    r'|<a\s[\s\S]*?</a>'
    r'|<h[1-6][\s\S]*?</h[1-6]>'
    r'|<span class="fn">[\s\S]*?</span>'
    r'|<p class="crumb">[\s\S]*?</p>'
    r'|<figure class="tree-fig">[\s\S]*?</figure>'
    r'|<figure class="skel-fig[^"]*">[\s\S]*?</figure>'
    r'|<[^>]+>)',
    re.IGNORECASE,
)
REF_CH_RE = re.compile(r'第\s*(\d+)\s*章')
REF_SEC_RE = re.compile(r'§\s*(\d+)\.(\d+)')
REF_NODE_RE = re.compile(r'(?<![\w-])(N-\d+)(?![\w-])')
MDLINK_RE = re.compile(r'href="([^"#:]+\.md)(#[^"]*)?"')


MD_A_RE = re.compile(r'<a\s[^>]*href="([^"#:]+\.md)(#[^"]*)?"[^>]*>([\s\S]*?)</a>')


class XRef:
    """out_mode: 指向本册之外的引用怎么写。None = 整本/单章预览（保持原文，不加链接）；
    'vol' = 分卷册：§N.M 降为纯文本并补「（见第 N 章）」（前文已点明第 N 章时只留纯文本）；
    'map' = 总纲册：降为纯文本（层级目录里章号就在上一层，不再补注）。"""

    def __init__(self, parts_all, parts_in, out_mode=None):
        self.out_mode = out_mode
        self.outside = 0      # 降为纯文本的册外引用数
        self.included = set()
        self.all_ids = set()
        self.file_anchor = {}
        self.node_sec = {}
        for p in parts_all:
            self.all_ids.add(p["anchor"])
            self.file_anchor[p["path"].name] = p["anchor"]
            for s in p["sections"]:
                self.all_ids.add(s["anchor"])
                for nid in s["nodes"]:
                    self.node_sec.setdefault(nid, s["anchor"])
        for p in parts_in:
            self.included.add(p["anchor"])
            for s in p["sections"]:
                self.included.add(s["anchor"])
        self.dangling = []    # 指向全书不存在的目标
        self.links = 0

    def _link(self, target, text):
        if target in self.included:
            self.links += 1
            return f'<a class="xref" href="#{target}">{text}</a>'
        if target not in self.all_ids:
            self.dangling.append(text)
        elif self.out_mode:
            self.outside += 1
        return text

    def _sec(self, m, text):
        target = f"sec-{m.group(1)}-{m.group(2)}"
        out = self._link(target, m.group(0))
        if (self.out_mode == "vol" and target not in self.included and target in self.all_ids
                and not re.search(rf"第\s*{m.group(1)}\s*章[^。；\n]{{0,6}}$", text[:m.start()])):
            # 「（§12.3）」→「（第 12 章 §12.3）」：册外的节只能按章号去整本里找，纯文本、不留死链
            out = f'<span class="xref-out">第 {m.group(1)} 章 </span>{out}'
        return out

    def link_text(self, text: str) -> str:
        hold = {}

        def stash(frag):
            key = f"\x00X{len(hold)}\x01"
            hold[key] = frag
            return key
        text = REF_SEC_RE.sub(lambda m: stash(self._sec(m, text)), text)
        text = REF_CH_RE.sub(lambda m: stash(self._link(f"ch-{m.group(1)}", m.group(0))), text)

        def node(m):
            t = self.node_sec.get(m.group(1))
            if not t:
                self.dangling.append(m.group(1))
                return m.group(0)
            return stash(self._link(t, m.group(0)))
        text = REF_NODE_RE.sub(node, text)
        for mk in INLINE_MARKS:
            text = text.replace(mk, stash(f'<span class="ext-mark">{mk}</span>'))
        for k, v in hold.items():
            text = text.replace(k, v)
        return text

    def apply(self, html: str) -> str:
        def md_anchor(m):        # 指向册外文件的 MD 链接整条降为文字（不留 href="#" 空链）
            anchor = self.file_anchor.get(Path(m.group(1)).name)
            target = (m.group(2) or "")[1:] or anchor
            if target and target in self.included:
                return m.group(0)
            if target and target in self.all_ids:
                self.outside += 1
                return m.group(3)
            return m.group(0)
        if self.out_mode:
            html = MD_A_RE.sub(md_anchor, html)

        def md_link(m):
            anchor = self.file_anchor.get(Path(m.group(1)).name)
            frag = (m.group(2) or "")[1:]
            target = frag or anchor
            if target and target in self.included:
                return f'href="#{target}"'
            self.dangling.append(m.group(1) + (m.group(2) or ""))
            return 'href="#"'
        html = MDLINK_RE.sub(md_link, html)
        parts = PROTECT_RE.split(html)
        return "".join(self.link_text(p) if i % 2 == 0 else p for i, p in enumerate(parts))


# =====================================================================
# 书级生成: 目录 / 全书一览 / 术语索引
# =====================================================================

def build_toc(parts, tree_pos: str, has_overview: bool, has_index: bool) -> str:
    """tree_pos: 'page'（目录后独立页）/ 'front'（书首里原位）/ ''（没有）。"""
    out = ['<section class="toc-page" id="toc">', '<h1 class="toc-title">目录</h1>']

    def entry(cls, href, text, sub=""):
        sub_html = f' <span class="toc-en">{html_mod.escape(sub)}</span>' if sub else ""
        out.append(f'<div class="{cls}"><a href="#{href}">{html_mod.escape(text)}{sub_html}</a></div>')
    if has_overview:
        entry("toc-top", "overview", "全书一览")
    if tree_pos == "page":
        entry("toc-top", "tree", "科技树")
    for p in parts:
        if p["kind"] == "front" and tree_pos == "front":
            entry("toc-top", p["anchor"], "书首 · " + p["h1"] if p["h1"] != "书首" else p["h1"])
            entry("toc-sec", "tree", "科技树")
            continue
        if p["kind"] == "chapter":
            entry("toc-ch", p["anchor"], f"第 {p['ch']} 章  {p['short']}")
            for s in p["sections"]:
                en = s["title"][len(s["cn"]):].strip().strip("()（）")
                entry("toc-sec", s["anchor"], f"§{s['n']}.{s['m']} {s['cn']}", en)
        elif p["kind"] == "synth":
            entry("toc-part", p["anchor"], f"{p['short']}：{p['vol_title']}")
        elif p["kind"] == "map":
            entry("toc-part", p["anchor"], p["h1"])
        else:
            entry("toc-top", p["anchor"], ("书首 · " if p["kind"] == "front" else "书尾 · ") + p["h1"]
                  if p["h1"] not in ("书首", "书尾") else p["h1"])
    if has_index:
        entry("toc-top", "index", "术语索引")
    out.append("</section>")
    return "\n".join(out)


def load_tree_json(workspace: Path):
    f = workspace / "tree.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"⚠  tree.json 解析失败: {e}", file=sys.stderr)
        return None


SPINE_CH_RE = re.compile(r"^##\s+第\s*(\d+)\s*章\s*(.*?)\s*[—–-]+\s*解锁[:：]\s*(.+?)\s*$", re.M)


def reading_minutes(md: str) -> int:
    """devices 时长口径（中速 250 字/分）+ 每张表/ASCII 图 +1 分钟。只数正文，不数代码与注释。"""
    body = strip_comments(_outside_fences(md))
    chars = len(re.findall(r"[一-鿿]", body)) + len(re.findall(r"[A-Za-z]+", body))
    tables = len(re.findall(r"^\|[\s:|-]+\|\s*$", md, re.M))
    return max(1, math.ceil(chars / 250) + tables)


def build_overview(parts, workspace: Path, tree) -> str:
    chapters = [p for p in parts if p["kind"] == "chapter"]
    if not chapters:
        return ""
    unlock = {}
    spine = workspace / "spine.md"
    if spine.exists():
        for m in SPINE_CH_RE.finditer(spine.read_text(encoding="utf-8")):
            unlock[int(m.group(1))] = m.group(3)
    else:
        print("⚠  没有 spine.md：全书一览的「解锁能力」列留空", file=sys.stderr)
    weight = {n["id"]: n.get("weight", 0) for n in (tree or {}).get("nodes", [])}
    rows = []
    total = 0
    for p in chapters:
        mins = reading_minutes(p["md"])
        total += mins
        best = max(p["sections"], key=lambda s: max([weight.get(x, 0) for x in s["nodes"]] or [0]),
                   default=None)
        best_html = (f'<a class="xref" href="#{best["anchor"]}">§{best["n"]}.{best["m"]} '
                     f'{html_mod.escape(best["cn"])}</a>') if best and weight else "—"
        rows.append(f'<tr><td><a class="xref" href="#{p["anchor"]}">第 {p["ch"]} 章</a><br>'
                    f'{html_mod.escape(p["short"])}</td>'
                    f'<td>{html_mod.escape(unlock.get(p["ch"], "—"))}</td>'
                    f'<td>{mins} 分钟</td><td>{best_html}</td></tr>')
    return ('<section class="overview" id="overview"><h1 class="ov-title">全书一览</h1>'
            f'<p class="ov-sum">{len(chapters)} 章 · 通读约 {total} 分钟</p>'
            '<table class="ov-table"><thead><tr><th>章</th><th>解锁能力</th><th>阅读</th><th>最重节</th>'
            '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></section>')


def build_term_index(parts, tree) -> str:
    if not tree:
        return ""
    sec_of, sec_label = {}, {}
    for p in parts:
        for s in p["sections"]:
            sec_label[s["anchor"]] = f"§{s['n']}.{s['m']}"
            for nid in s["nodes"]:
                sec_of.setdefault(nid, []).append(s["anchor"])
    items = []
    for n in tree.get("nodes", []):
        secs = sec_of.get(n["id"])
        if not secs:
            continue
        en = n.get("en", "")
        key = (en or n.get("name", "")).lower()
        links = ", ".join(f'<a class="xref" href="#{a}">{sec_label[a]}</a>' for a in dict.fromkeys(secs))
        items.append((key, f'<div class="ix-item"><span class="ix-name">{html_mod.escape(n.get("name", ""))}</span>'
                      + (f' <span class="ix-en">{html_mod.escape(en)}</span>' if en else "")
                      + f'<span class="ix-at">{links}</span></div>'))
    if not items:
        return ""
    items.sort(key=lambda x: x[0])
    return ('<section class="term-index" id="index"><h1 class="part-title" data-crumb="术语索引">术语索引</h1>'
            + "\n".join(i for _k, i in items) + "</section>")


# =====================================================================
# 组装
# =====================================================================

LIST_LINE_RE = re.compile(r"^( +)((?:[-*+]|\d+[.)])\s)")


def normalize_list_indent(md: str) -> str:
    """层级总目录常按 2 空格缩进写嵌套列表；Python-Markdown 要 4 空格，否则层级会被压平。
    只在出现 2 空格级缩进（缩进 ≡ 2 mod 4）时把列表行缩进翻倍。围栏内不动。"""
    lines, infence, odd = md.split("\n"), False, False
    for ln in lines:
        if FENCE_LINE_RE.match(ln):
            infence = not infence
        elif not infence:
            m = LIST_LINE_RE.match(ln)
            if m and len(m.group(1)) % 4 == 2:
                odd = True
                break
    if not odd:
        return md
    out, infence = [], False
    for ln in lines:
        if FENCE_LINE_RE.match(ln):
            infence = not infence
        m = None if infence else LIST_LINE_RE.match(ln)
        out.append(" " * (2 * len(m.group(1))) + ln[len(m.group(1)):] if m else ln)
    return "\n".join(out)


def build_document(parts_all, parts, book_dir: Path, workspace: Path, course: str,
                   only: bool, cjk_path, tmpdir: Path, volume: dict | None = None):
    """volume: 分卷册 {"kind": "vol"|"map", "k": 3, "title": "…"}；None = 整本或单章预览。"""
    tree = load_tree_json(workspace)
    tree_r = TreeRenderer(workspace, cjk_path, tmpdir)   # 节点级科技树已不进书，只为接口保留
    skel_r = SkeletonRenderer(cjk_path, tmpdir)
    xref = XRef(parts_all, parts, out_mode=volume["kind"] if volume else None)
    fig_stats = {"slide": 0, "own": 0, "plain": 0, "missing": 0}
    has_front = any(p["kind"] == "front" for p in parts)

    game = GameProgress(parts_all, workspace)
    bodies = []
    for p in parts:
        md = normalize_list_indent(p["md"]) if p["kind"] in ("synth", "map") else p["md"]
        progress = ""
        if p["kind"] == "chapter":
            md = game_markup_md(md)
            if PROGRESS_MARK in md:
                progress = game.figure(p, skel_r)
        html = md_to_html(md, tree_r, landscape_tree=False, skel=skel_r, label=p["path"].name)
        html = convert_footnotes(html, p["path"].name)
        html = wrap_figures(html, book_dir, p["path"].name, fig_stats)
        html = tag_blockquote_roles(html)
        html = game_markup_html(html, p, progress)
        html = stamp_headings(html, p)
        html = xref.apply(html)
        bodies.append(f'<section class="{p["kind"]}">\n{html}\n</section>')

    overview = build_overview(parts, workspace, tree) if has_front else ""
    index = "" if (only or volume) else build_term_index(parts, tree)
    toc = build_toc(parts, tree_pos="", has_overview=bool(overview), has_index=bool(index))

    front = next((p for p in parts_all if p["kind"] == "front"), None)
    book_title = front["h1"] if front else course
    cover_vol = ""
    if volume and volume["kind"] == "vol":
        cover_vol = f"第{int_to_cn(volume['k'])}卷"
        cover_title, cover_sub = volume["title"], f"{book_title} · {course}"
    elif volume:
        cover_vol = "总纲"
        cover_title, cover_sub = parts[0]["h1"], f"{book_title} · {course}"
    elif only:
        ch = next(p for p in parts if p["kind"] == "chapter")
        cover_title, cover_sub = ch["h1"], f"样章预览 · {book_title}"
    else:
        cover_title, cover_sub = book_title, course
    files_meta = "|".join(p["path"].name for p in parts)
    meta = f"files={files_meta}; treefig={tree_r.count}; skelfig={skel_r.count}"
    if xref.dangling:
        print(f"⚠  交叉引用指向不存在的目标: {', '.join(sorted(set(xref.dangling)))}", file=sys.stderr)
    if skel_r.degraded:
        print("⚠  骨架图退化为卡片（matplotlib 不可用或绘制失败）", file=sys.stderr)
    out_note = f" · 册外引用降为文字 {xref.outside} 处" if volume else ""
    print(f"✓ 交叉引用 {xref.links} 处{out_note} · 原图 {fig_stats['slide']} · 自绘 {fig_stats['own']}"
          f" · 未标注图 {fig_stats['plain']} · 骨架图 {skel_r.count}", file=sys.stderr)

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8">
<title>{html_mod.escape(cover_title)}</title>
<meta name="keywords" content="{html_mod.escape(meta)}">
<meta name="generator" content="full-learn compile_story_pdf.py">
</head>
<body>
<header class="cover">
  {f'<p class="cover-vol">{html_mod.escape(cover_vol)}</p>' if cover_vol else ''}
  <h1 class="cover-title">{html_mod.escape(cover_title)}</h1>
  <p class="cover-sub">{html_mod.escape(cover_sub)}</p>
</header>
{toc}
{overview}
{chr(10).join(bodies)}
{index}
</body>
</html>"""
    return doc, fig_stats


# =====================================================================
# CSS
# =====================================================================

ROLE_STYLE = {
    "guide":    ("3px solid #5b8a8a", "#eef5f5", "#4a7373", "font-size: 9pt; padding: 0.3em 0.7em; color: #3d5c5c;"),
    "role":     ("5px solid #3949ab", "#e8eaf6", "#283593", ""),
    "aid":      ("4px solid #f0a020", "#fff6e5", "#a86b00", ""),
    "reality":  ("5px solid #2e8b57", "#eaf6ee", "#1f6b3f", ""),
    "think":    ("3px solid #0891b2", "#ecfeff", "#0e7490", "font-style: normal;"),
    "trap":     ("5px solid #e0521c", "#fdeee7", "#b53d0f", ""),
    "def":      ("5px solid #1a4a85", "#e7eef8", "#1a4a85", ""),
    "depth":    ("4px solid #607d8b", "#eceff1", "#455a64", ""),
    "clip":     ("3px solid #9e9e9e", "#f5f5f5", "#616161", "font-size: 9pt; color: #444;"),
    "breather": ("1.5px dashed #c9a227", "#fffbea", "#8a6d00", "color: #4a4030;"),
    "master":   ("6px solid #6a1b9a", "#f3e8f9", "#4a148c", "color: #2e1a3a;"),
    "diverge":  ("4px dotted #d4a017", "#fdf6dc", "#8a6d00", ""),
    "idea":     ("5px solid #b45309", "#fff8eb", "#92400e", "font-size: 10.5pt;"),
    "goal":     ("3px solid #00695c", "#eef5f4", "#00584c", "font-size: 8.8pt; padding: 0.2em 0.6em; margin-top: 0.4em; color: #1c3a36;"),
    "exam":     ("5px solid #c62828", "#fdecea", "#b71c1c", ""),
    # 出手块：这里只给底色与强调色，形状在 build_css「出手」一段
    "challenge": ("6px solid #c2410c", "#fff7ed", "#9a3412", ""),
    "route":    ("0 solid #fff", "#f1f5f9", "#475569", ""),
    "card":     ("0 solid #fff", "#faf7ff", "#4c1d95", ""),
    "blocksum": ("0 solid #fff", "#f0fdfa", "#115e59", ""),
}


def role_css() -> str:
    out, seen = [], set()
    for _mk, role, _name, label in BLOCK_ROLES:
        if role in seen:
            continue
        seen.add(role)
        border, bg, accent, extra = ROLE_STYLE[role]
        prop = "border" if "dashed" in border else "border-left"
        out.append(f".bq-{role} {{ {prop}: {border}; background: {bg}; {extra} }}")
        out.append(f".bq-{role} strong {{ color: {accent}; }}")
        out.append(f".bq-{role} blockquote {{ border-left-color: {accent}; }}")
        if label:
            out.append(f'.bq-{role}::before {{ content: "{label}"; color: {accent}; }}')
    return "\n".join(out)


def build_css(cjk_path, emoji_path) -> str:
    faces = ""
    if cjk_path:
        faces += f'@font-face {{ font-family: "CourseCJK"; src: url("file://{cjk_path}"); }}\n'
    if emoji_path:
        # unicode-range 限定: 不限范围的 emoji 字族会接管数字（CS1234 → CS 1 2 3 4）
        faces += (f'@font-face {{ font-family: "CourseEmoji"; src: url("file://{emoji_path}"); '
                  'unicode-range: U+1F000-1FAFF, U+2600-27BF, U+2B50-2B55, U+FE0F, U+200D; }\n')
    stack = ('"CourseCJK", ' if cjk_path else "") + '"Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", ' \
        + ('"CourseEmoji", ' if emoji_path else "") + "sans-serif"
    return f"""
{faces}
@page {{
  size: A5;
  margin: 16mm 12mm 16mm 12mm;
  @top-center {{
    content: string(crumb);
    font-size: 7.5pt; color: #8a97a8; font-family: {stack};
    padding-bottom: 1.5mm; border-bottom: 0.4pt solid #e3e8ee; width: 100%;
  }}
  @bottom-center {{
    content: counter(page) " / " counter(pages);
    font-size: 8pt; color: #888; font-family: {stack};
  }}
  @footnote {{ border-top: 0.5pt solid #c7ced6; padding-top: 1.2mm; margin-top: 2mm; }}
}}
@page :first {{ @top-center {{ content: none; border: none; }} @bottom-center {{ content: none; }} }}
@page tree-landscape {{
  size: A5 landscape; margin: 10mm 10mm 10mm 10mm;
  @top-center {{ content: none; border: none; }}
}}

html {{ font-family: {stack}; font-size: 10pt; line-height: 1.6; color: #222; }}
body {{ margin: 0; padding: 0; }}

/* 面包屑: 节标题前一行小字, 同时喂给页眉 */
.crumb {{ string-set: crumb content(); font-size: 7.5pt; color: #8794a5; margin: 1.1em 0 -0.5em 0; }}
h1.part-title {{ string-set: crumb attr(data-crumb); }}
.toc-title, .ov-title, .tree-title {{ string-set: crumb ""; }}

/* ---------- 封面 ---------- */
header.cover {{ page-break-after: always; text-align: center; margin-top: 30%; }}
.cover-title {{ font-size: 22pt; color: #1a4a85; border: none; margin-bottom: 0.6em; bookmark-level: none; }}
.cover-sub {{ color: #666; font-size: 12pt; text-align: center; }}

/* ---------- 目录 ---------- */
section.toc-page {{ page-break-after: always; }}
.toc-title {{ font-size: 17pt; text-align: center; border-bottom: 2px solid #333; padding-bottom: 0.3em; }}
.toc-page a {{ color: inherit; text-decoration: none; }}
.toc-page a::after {{ content: target-counter(attr(href), page); float: right; color: #6b7280; font-size: 9pt; }}
.toc-top {{ margin: 0.6em 0 0.2em; font-size: 11pt; color: #1a4a85; }}
.toc-ch  {{ margin: 0.8em 0 0.2em; font-size: 11.5pt; font-weight: bold; color: #1a4a85; }}
.toc-sec {{ margin: 0.12em 0 0.12em 1.4em; font-size: 9.5pt; color: #444; }}
.toc-part {{ margin: 0.8em 0 0.3em; font-size: 11pt; font-weight: bold; color: #6a1b9a; }}
.toc-en  {{ font-size: 7.5pt; color: #94a3b8; }}

/* ---------- 全书一览 / 科技树 / 索引 ---------- */
section.overview {{ page-break-after: always; }}
.ov-sum {{ color: #555; font-size: 9pt; }}
.ov-table td {{ font-size: 8.8pt; }}
section.tree-page, section.tree-page-list {{ page: tree-landscape; page-break-before: always; page-break-after: always; }}
.tree-title {{ font-size: 13pt; border: none; margin: 0 0 0.2em; text-align: center; }}
figure.tree-fig {{ margin: 0; text-align: center; }}
figure.tree-fig img {{ width: 100%; max-height: 100mm; }}
h2.tree-title {{ font-size: 12pt; margin: 0 0 0.3em; padding: 0.15em 0.5em; }}
figure.tree-fig figcaption {{ font-size: 7.5pt; color: #666; }}
.tree-inline img {{ width: 100%; }}
.tree-layer {{ margin: 0.3em 0; font-size: 9pt; }}
.tree-lk {{ display: inline-block; min-width: 3.5em; color: #1a4a85; font-weight: bold; }}
.tree-tag {{ font-size: 7pt; color: #b45309; border: 0.5pt solid #e5c07b; border-radius: 2px; padding: 0 0.2em; }}
.tree-note {{ font-size: 8pt; color: #666; }}
section.term-index {{ page-break-before: always; }}
.ix-item {{ font-size: 9pt; margin: 0.15em 0; }}
.ix-en {{ color: #6b7280; font-size: 8pt; }}
.ix-at {{ float: right; }}

/* ---------- 部分与章 ---------- */
section.front, section.chapter, section.back, section.synth, section.map {{ page-break-before: always; counter-reset: footnote; }}
section.synth > h1, section.map > h1 {{ color: #6a1b9a; border-bottom-color: #6a1b9a; }}
.xref-out {{ color: #6b7280; }}
/* 分卷册封面 */
.cover-vol {{ color: #6a1b9a; font-size: 13pt; letter-spacing: 0.1em; margin-bottom: 0.4em; text-align: center; }}
h1 {{ font-size: 18pt; color: #1a4a85; border-bottom: 3px double #1a4a85; padding-bottom: 0.3em;
      margin: 0.4em 0 0.8em; page-break-after: avoid; bookmark-level: 1; }}
h2 {{ font-size: 13pt; color: #1a4a85; margin: 1.3em 0 0.5em; padding: 0.3em 0.6em;
      border-left: 5px solid #1a4a85; background: #eef3f9; page-break-after: avoid; bookmark-level: 2; }}
h3 {{ font-size: 11pt; margin: 1em 0 0.4em; color: #444; border-left: 3px solid #888;
      padding-left: 0.5em; page-break-after: avoid; bookmark-level: none; }}
h4, h5, h6 {{ bookmark-level: none; page-break-after: avoid; }}

p {{ margin: 0.5em 0; text-align: justify; }}
strong {{ color: #111; }}

/* ---------- 脚注（出处） ---------- */
.fn {{ float: footnote; font-size: 7.5pt; line-height: 1.35; color: #4b5563; text-align: left;
      font-weight: normal; font-style: normal; }}
::footnote-call {{ content: counter(footnote); vertical-align: super; font-size: 65%; line-height: 0;
      color: #2a6fb5; padding-left: 0.1em; }}
::footnote-marker {{ content: counter(footnote) ". "; color: #2a6fb5; }}

/* ---------- 图 ---------- */
figure.fig {{ margin: 0.9em 0; padding: 0.45em 0.5em 0.4em; page-break-inside: avoid; text-align: center;
  border: 1px solid #dfe5ec; border-radius: 4px; background: #fff; }}
figure.fig img {{ max-width: 100%; max-height: 62vh; height: auto; }}
figure.fig figcaption {{ font-size: 8.4pt; color: #55636f; margin-top: 0.35em; text-align: left; line-height: 1.4; }}
.fig-chip {{ font-size: 7pt; font-weight: bold; border-radius: 3px; padding: 0.05em 0.4em; margin-right: 0.5em; }}
figure.fig-slide {{ border-color: #c9d8e8; }}
figure.fig-slide .fig-chip {{ color: #33526e; background: #fff; border: 0.6pt solid #5b7fa6; }}
figure.fig-own .fig-chip {{ color: #fff; background: #8a8f96; }}

/* ---------- 骨架图（章 / 卷 / 全书） ---------- */
figure.skel-fig {{ margin: 0.9em 0; text-align: center; page-break-inside: avoid; }}
figure.skel-fig img {{ width: 100%; max-height: 165mm; object-fit: contain; }}
figure.skel-fig figcaption {{ font-size: 8.4pt; color: #55636f; margin-top: 0.3em; text-align: left; line-height: 1.4; }}
.skel-cards {{ text-align: left; }}
.skel-card {{ border: 1px solid #1a4a85; border-radius: 5px; background: #f4f8fc; padding: 0.3em 0.6em; margin: 0.35em 0; }}
.skel-gt {{ font-weight: bold; color: #1a4a85; font-size: 9.5pt; }}
.skel-card ul {{ margin: 0.2em 0; padding-left: 1.2em; font-size: 8.6pt; }}
.skel-core {{ color: #b42318; font-weight: bold; }}
.skel-ref {{ color: #6b7a8c; margin-left: 0.6em; font-weight: normal; }}
.skel-rels {{ font-size: 8.6pt; color: #374151; }}

/* ---------- 章首地图（旧格式：§ 开头标签） ---------- */
.mmd {{ margin: 0.9em 0; page-break-inside: avoid; }}
.mmd-group {{ border: 1px solid #c9d8e8; border-radius: 5px; background: #f7fafd; padding: 0.3em 0.45em 0.45em; }}
.mmd-gt {{ font-size: 8.6pt; font-weight: bold; color: #33526e; margin-bottom: 0.35em; }}
.mmd-row {{ display: flex; flex-wrap: wrap; gap: 0.3em; }}
.mmd-row.mmd-loose {{ margin-top: 0.4em; }}
.mmd-node {{ display: inline-block; font-size: 8.2pt; line-height: 1.3; padding: 0.2em 0.45em;
  border-radius: 4px; border: 1px solid #cfd8e0; background: #fff; color: #24313d; }}
.mmd-node a.xref {{ color: inherit; border-bottom: none; }}
.mmd-core {{ border-color: #c62828; background: #fdecea; color: #8d2018; font-weight: bold; }}
.mmd-normal {{ border-color: #9fb6cc; background: #fff; }}
.mmd-bg {{ border-color: #d8dde2; background: #f3f5f7; color: #667180; font-size: 7.8pt; }}
.mmd-skip {{ border: 1px dashed #c3c8cd; background: #fafbfc; color: #939aa2; font-size: 7.8pt; }}
.mmd-arrow {{ text-align: center; font-size: 8pt; color: #5b7fa6; margin: 0.2em 0; }}

/* ---------- 引用块与块类型（角色表见 block_roles.py） ---------- */
blockquote {{ border-left: 3px solid #7aa5d2; background: #f2f6fb; margin: 0.8em 0; padding: 0.5em 0.8em;
  color: #333; page-break-inside: avoid; }}
blockquote h3 {{ font-size: 10.5pt; color: #1a4a85; border-left: none; background: rgba(255,255,255,0.55);
  padding: 0.2em 0.5em; margin: 0.6em 0 0.3em; border-radius: 2px; }}
blockquote.bq {{ border-radius: 4px; }}
blockquote.bq::before {{ display: block; font-size: 7.2pt; font-weight: bold; letter-spacing: 0.06em;
  margin: -0.05em 0 0.35em 0; }}
.bq blockquote {{ background: rgba(255,255,255,0.62); border-left-width: 3px; margin: 0.5em 0; }}
.bq-goal p {{ margin: 0.1em 0; }}
{role_css()}
.ext-mark {{ color: #c2410c; font-size: 85%; }}

/* ---------- 出手（chapter 理论 6）：挑战卡 / 揭晓页 / 路线条 / 先猜 / 心智卡 / 徽章 / 拼图进度 ---------- */
blockquote.bq-challenge {{ border: 1.2px solid #f0a46c; border-left: 6px solid #c2410c; border-radius: 6px;
  background: #fff7ed; padding: 0.75em 0.95em 0.6em; margin: 1.1em 0; }}
.bq-challenge > p:first-child {{ font-size: 10.3pt; line-height: 1.65; margin-top: 0; }}
.bq-challenge > p:first-child strong {{ display: inline-block; color: #fff; background: #c2410c; font-size: 8.6pt;
  padding: 0.05em 0.6em; border-radius: 3px; margin-right: 0.3em; letter-spacing: 0.05em; }}
.bq-challenge ul {{ list-style: none; padding-left: 0; margin: 0.6em 0; }}
.bq-challenge li {{ background: #fff; border: 0.8px solid #fdba74; border-radius: 4px; margin: 0.4em 0;
  padding: 0.3em 0.7em; }}
.bq-challenge > p:last-child {{ font-size: 8.6pt; color: #7c2d12; text-align: right; margin-bottom: 0; }}
.bq-challenge a {{ color: #c2410c; font-weight: bold; border-bottom: 1px dotted #c2410c; }}
.reveal-break {{ page-break-before: always; height: 0; margin: 0; }}
blockquote.bq-reveal {{ border-left: 5px solid #15803d; background: #f0fdf4; border-radius: 4px;
  padding: 0.7em 0.95em; margin-top: 0; }}
.bq-reveal > p:first-child strong {{ display: inline-block; color: #fff; background: #15803d; font-size: 8.6pt;
  padding: 0.05em 0.6em; border-radius: 3px; margin-right: 0.3em; letter-spacing: 0.05em; }}
.bq-reveal strong {{ color: #166534; }}
.bq-reveal ul {{ padding-left: 1.1em; }}
.bq-reveal li {{ margin: 0.35em 0; }}
blockquote.bq-route {{ border: none; border-radius: 3px; background: #f1f5f9; padding: 0.22em 0.65em;
  margin: 0.25em 0 0.85em; font-size: 8.2pt; line-height: 1.5; color: #475569; }}
.bq-route p {{ margin: 0; text-align: left; }}
.route-arrow {{ color: #94a3b8; padding: 0 0.3em; }}
blockquote.bq-guess {{ border: 1px solid #a5dbe6; border-left: 4px solid #0891b2; border-radius: 6px;
  padding: 0.35em 0.75em; margin: 0.9em 0 1.5em; font-size: 9.6pt; }}
blockquote.bq-guess::before {{ content: "先猜 · 押一个答案再往下读"; }}
blockquote.bq-card {{ border: 1.5px solid #6d28d9; border-radius: 6px; background: #faf7ff; padding: 0;
  margin: 1em 0 1.1em; }}
.bq-card > p {{ margin: 0.45em 0.85em; text-align: left; }}
.bq-card > p:first-child {{ background: #6d28d9; color: #fff; margin: 0; padding: 0.5em 0.85em;
  font-size: 10.3pt; font-weight: bold; border-radius: 4px 4px 0 0; }}
.bq-card > p:first-child strong {{ color: #fde68a; margin-right: 0.3em; }}
.bq-card ul {{ list-style: none; margin: 0.55em 0.85em 0.3em; padding: 0; }}
.bq-card li {{ padding-left: 1.55em; text-indent: -1.55em; margin: 0.4em 0; line-height: 1.55; }}
.card-mk {{ display: inline-block; width: 1.55em; text-indent: 0; }}
.bq-card > p:last-child {{ border-top: 1px dashed #c4b5fd; padding-top: 0.45em; margin-top: 0.5em;
  margin-bottom: 0.6em; }}
.bq-card > p:last-child strong {{ color: #5b21b6; }}
blockquote.bq-blocksum {{ border: 1.5px solid #0f766e; border-radius: 6px; background: #f0fdfa; padding: 0;
  margin: 1.2em 0 0.4em; page-break-inside: avoid; }}
.bq-blocksum > p {{ margin: 0.45em 0.85em; text-align: left; }}
.bq-blocksum > p:first-child {{ background: #0f766e; color: #fff; margin: 0; padding: 0.5em 0.85em;
  font-size: 10.3pt; border-radius: 4px 4px 0 0; }}
.bq-blocksum > p:first-child strong {{ color: #99f6e4; margin-right: 0.3em; }}
.bq-blocksum ul {{ margin: 0.55em 0.85em 0.3em; padding-left: 1.1em; }}
.bq-blocksum li {{ margin: 0.4em 0; line-height: 1.55; }}
.bq-blocksum li strong {{ color: #115e59; }}
.bq-blocksum > p:last-child {{ border-top: 1px dashed #5eead4; padding-top: 0.45em; margin-top: 0.5em;
  margin-bottom: 0.6em; }}
.bq-blocksum > p:last-child strong {{ color: #0f766e; }}
.badge-line {{ font-size: 9pt; color: #374151; text-align: left; margin: 0.55em 0; }}
.badge {{ display: inline-block; font-size: 7.8pt; color: #fff; background: #b91c1c; border-radius: 0.9em;
  padding: 0.02em 0.65em; margin-right: 0.5em; letter-spacing: 0.04em; }}
.badge-line.badge-world .badge {{ background: #2e7d32; }}
.badge-world strong:not(.badge) {{ color: #1b5e20; }}
ul.wm-list {{ margin-top: 0.2em; }}
ul.wm-list strong {{ font-weight: bold; color: #14532d; background: #dcfce7; padding: 0 0.15em; border-radius: 2px; }}
figure.progress-fig {{ margin: 0.8em 0 1em; }}
figure.progress-fig img {{ max-height: 110mm; }}

code {{ font-family: "DejaVu Sans Mono", "Consolas", monospace; font-size: 9pt; background: #f0f0f0;
  padding: 0 3px; border-radius: 2px; overflow-wrap: break-word; }}
pre {{ font-family: "DejaVu Sans Mono", "Consolas", monospace; font-size: 8pt; line-height: 1.35;
  background: #f7f7f7; border: 1px solid #ddd; border-radius: 3px; padding: 6px 8px;
  white-space: pre-wrap; overflow-wrap: break-word; word-break: break-word; page-break-inside: avoid; }}
pre code {{ background: transparent; padding: 0; font-size: inherit; }}

table {{ border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 9.5pt; page-break-inside: auto; }}
thead {{ display: table-header-group; }}
tr {{ page-break-inside: avoid; }}
th, td {{ border: 1px solid #ccc; padding: 4px 6px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
td code, th code {{ white-space: pre-wrap; word-break: break-all; overflow-wrap: anywhere; }}
th {{ background: #eef3f9; font-weight: bold; }}
hr {{ border: none; border-top: 1px dashed #bbb; margin: 1.2em 0; }}
ul, ol {{ padding-left: 1.4em; margin: 0.4em 0; }}
li {{ margin: 0.15em 0; }}
a {{ color: #2a6fb5; text-decoration: none; }}
a.xref {{ color: #c2410c; text-decoration: none; border-bottom: 1px dotted #c2410c; }}

{MATH_CSS}
"""


# =====================================================================
# main
# =====================================================================

def main():
    ap = argparse.ArgumentParser(description="full-learn: book/*.md → A5 PDF")
    ap.add_argument("book", help="output/<课>/full-learn 或其下的 book/")
    ap.add_argument("-o", "--output")
    ap.add_argument("--only", help="只编一章: 章号（3 / 03）或文件名（03-slug.md）")
    ap.add_argument("--with-front", action="store_true", help="--only 时带上书首（含科技树页）")
    ap.add_argument("--no-goals", action="store_true")
    ap.add_argument("--no-gate", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--volumes", action="store_true",
                    help="整本之外按 spine 卷划分各出 book-vol<K>.pdf，并出 book-map.pdf（总纲卷）")
    a = ap.parse_args()

    global NO_GOALS
    NO_GOALS = a.no_goals
    book_dir = resolve_book_dir(Path(a.book))
    workspace = book_dir.parent
    course = workspace.parent.name
    parts_all = collect(book_dir)

    if a.only:
        key = a.only
        if key.endswith(".md"):
            sel = [p for p in parts_all if p["path"].name == Path(key).name]
        else:
            sel = [p for p in parts_all if p["kind"] == "chapter" and p["nn"] == int(key)]
        if not sel or sel[0]["kind"] != "chapter":
            raise SystemExit(f"--only {key}: book/ 里找不到这一章")
        parts = ([p for p in parts_all if p["kind"] == "front"] if a.with_front else []) + sel
        default_out = workspace / f"book-ch{sel[0]['nn']:02d}.pdf"
    else:
        parts = parts_all
        default_out = workspace / "book.pdf"
    out_pdf = Path(a.output).resolve() if a.output else default_out

    print(f"组书 {len(parts)} 个文件（课程: {course}）:", file=sys.stderr)
    for p in parts:
        tag = {"front": "书首", "back": "书尾", "map": "总纲", "synth": p.get("short")}.get(
            p["kind"], f"第 {p.get('ch')} 章")
        print(f"  {p['path'].name}  [{tag}] {len(p['sections'])} 节", file=sys.stderr)

    jobs = [(parts, out_pdf, None)]
    if a.volumes:
        if a.only:
            raise SystemExit("--volumes 与 --only 不能同用")
        jobs += volume_jobs(parts_all, workspace, Path(a.output).resolve().parent if a.output else workspace)

    if a.no_gate:
        print("⚠⚠ --no-gate: 跳过编前门禁，这份 PDF 不能当成品交付", file=sys.stderr)
    elif not run_gate(parts, workspace):
        print(f"✗ 门禁未过，不生成 {out_pdf.name}（E-RENDER-01）。修完再编，或调试时加 --no-gate。",
              file=sys.stderr)
        sys.exit(1)

    _cjk_name, cjk_path = find_cjk_font()
    emoji_path = find_emoji_font()
    rc = 0
    for job_parts, job_out, volume in jobs:
        if volume:
            print(f"\n—— 分卷 {job_out.name}: {', '.join(p['path'].name for p in job_parts)}", file=sys.stderr)
        render_pdf(parts_all, job_parts, book_dir, workspace, course, bool(a.only), cjk_path, emoji_path,
                   job_out, volume)
        if not a.no_verify:
            import verify_pdf
            rc = max(rc, verify_pdf.run(job_out, book_dir))
    sys.exit(rc)


def render_pdf(parts_all, parts, book_dir, workspace, course, only, cjk_path, emoji_path, out_pdf, volume):
    with tempfile.TemporaryDirectory(prefix="fl-render-") as td:
        doc_html, _stats = build_document(parts_all, parts, book_dir, workspace, course,
                                          only=only, cjk_path=cjk_path, tmpdir=Path(td), volume=volume)
        font_config = FontConfiguration()
        document = HTML(string=doc_html, base_url=str(book_dir) + "/").render(
            stylesheets=[CSS(string=build_css(cjk_path, emoji_path), font_config=font_config)],
            font_config=font_config, presentational_hints=True)
        document.write_pdf(str(out_pdf))
        n_pages = len(document.pages)
    size_kb = out_pdf.stat().st_size // 1024
    print(f"✓ PDF: {out_pdf} · {n_pages} 页 · {size_kb} KB", file=sys.stderr)


def volume_jobs(parts_all, workspace: Path, out_dir: Path):
    """按 spine 的卷划分：每卷一册 book-vol<K>.pdf（该卷各章 + 卷串讲）+ book-map.pdf（总纲卷）。"""
    spine = workspace / "spine.md"
    vols = parse_volumes(spine.read_text(encoding="utf-8")) if spine.exists() else []
    if not vols:
        raise SystemExit("--volumes: spine.md 没有 `# 第 K 卷 <卷标题> — 解锁: …` 卷行，无从分卷")
    jobs = []
    for v in vols:
        chs = set(v["chs"])
        sel = [p for p in parts_all
               if (p["kind"] == "chapter" and p["ch"] in chs)
               or (p["kind"] == "synth" and (p["nn"] in chs or cn_to_int(str(p.get("vol", ""))) == v["k"]))]
        if not any(p["kind"] == "synth" for p in sel):
            print(f"⚠  第{int_to_cn(v['k'])}卷没有卷串讲 NNv-<slug>.md（应为 {max(chs):02d}v-*.md），本册只含各章",
                  file=sys.stderr)
        if not any(p["kind"] == "chapter" for p in sel):
            print(f"⚠  第{int_to_cn(v['k'])}卷在 book/ 里一章也没有，跳过", file=sys.stderr)
            continue
        jobs.append((sel, out_dir / f"book-vol{v['k']}.pdf", {"kind": "vol", "k": v["k"], "title": v["title"]}))
    mp = [p for p in parts_all if p["kind"] == "map"]
    if mp:
        jobs.append((mp, out_dir / "book-map.pdf", {"kind": "map", "k": 0, "title": mp[0]["h1"]}))
    else:
        print(f"⚠  没有 {MAP_FILE}：不出 book-map.pdf", file=sys.stderr)
    return jobs


if __name__ == "__main__":
    main()
