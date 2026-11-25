#!/usr/bin/env python3
"""
Compile the teaching story chain (teach/*.md) into a single mobile-friendly PDF
with clickable internal cross-references (Arc N, Arc N §M, §M, KP-X.Y).

Usage:
    python3 compile_story_pdf.py <course_teach_dir> [output_pdf_path]
    python3 compile_story_pdf.py <course_teach_dir> [output_pdf_path] --only <N-slug.md>   # 单讲模式
    ... --no-goals                                                                     # 不打印 ✅ 教学目标块
    python3 compile_story_pdf.py <assignment_prep_dir> --prep                              # 作业预备模式

Merges:
    teach/index.md + teach/1-*.md + teach/2-*.md + ... (in filename order)

Output:
    Single PDF with:
    - Page breaks between arcs
    - CJK fonts (auto-detected)
    - Clickable cross-references: "Arc 1 §3" → jumps to that section,
      "KP-5.7" → jumps to the section defining that knowledge point.

Dependencies:
    pip install --user --break-system-packages markdown weasyprint pymdown-extensions
"""

import sys
import re
import html as html_mod
from pathlib import Path

import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

sys.path.insert(0, str(Path(__file__).resolve().parent))
from latex_to_html import convert_math_blocks, MATH_CSS   # noqa: E402


# ---------- Font detection ----------

def find_cjk_font():
    """Find a CJK-capable font on the system. Returns (font_family_name, font_file_paths)."""
    candidates = [
        ("/mnt/c/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
        ("/mnt/c/Windows/Fonts/msyhbd.ttc", "Microsoft YaHei"),
        ("/mnt/c/Windows/Fonts/simhei.ttf", "SimHei"),
        ("/mnt/c/Windows/Fonts/simsun.ttc", "SimSun"),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK SC"),
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "WenQuanYi Micro Hei"),
        ("/usr/share/fonts/truetype/arphic/uming.ttc", "AR PL UMing CN"),
    ]
    available = [(p, name) for p, name in candidates if Path(p).exists()]
    if not available:
        print("⚠  No CJK font found. PDF may render Chinese as boxes.", file=sys.stderr)
        return None, []
    primary = available[0]
    print(f"✓ Using CJK font: {primary[1]} ({primary[0]})", file=sys.stderr)
    return primary[1], [p for p, _ in available]


# ---------- MD collection ----------

def collect_md_files(teach_dir: Path):
    """Return (index_file, [(arc_number, path), ...], appendix_files) sorted by arc number.

    Recognizes:
      - index.md → index page
      - N-slug.md → arc N (sorted by N)
      - extra-N-slug.md → "extra arc" with offset (placed after regular arcs)
      - exam-keyword-index.md → appendix
    """
    teach_dir = Path(teach_dir)
    if not teach_dir.is_dir():
        raise SystemExit(f"Not a directory: {teach_dir}")

    index = teach_dir / "index.md"
    arc_files = []
    extra_files = []
    for f in teach_dir.glob("*.md"):
        if f.name in ("index.md", "exam-keyword-index.md"):
            continue
        # extra-N-slug.md
        m_extra = re.match(r"^extra-(\d+)-", f.name)
        if m_extra:
            extra_files.append((int(m_extra.group(1)), f))
            continue
        # N-slug.md
        m = re.match(r"^(\d+)-", f.name)
        if m:
            arc_files.append((int(m.group(1)), f))
    arc_files.sort(key=lambda x: x[0])
    extra_files.sort(key=lambda x: x[0])

    # Append extras after regular arcs, with high arc numbers (offset 100 + N)
    if extra_files:
        max_arc = max((n for n, _ in arc_files), default=0)
        for n, f in extra_files:
            arc_files.append((max_arc + 100 + n, f))

    # Appendix files (placed after arcs)
    appendix_files = []
    exam_index = teach_dir / "exam-keyword-index.md"
    if exam_index.exists():
        appendix_files.append(exam_index)

    return (index if index.exists() else None), arc_files, appendix_files


# ---------- Knowledge-point → (arc, sec) map from index.md ----------

KP_ROW_RE = re.compile(
    r"\|\s*(KP-[0-9G]+\.\d+)\s*\|[^|]+\|\s*Arc\s*(\d+)\s*§\s*(\d+)\s*\|"
)

def build_kp_map(index_path: Path) -> dict[str, str]:
    """Parse the knowledge-point index table in index.md; return {KP-X.Y: 'arc-N-sec-M'}."""
    if not index_path or not index_path.exists():
        return {}
    kp_map = {}
    for m in KP_ROW_RE.finditer(index_path.read_text(encoding="utf-8")):
        kp_id, arc_n, sec_m = m.group(1), int(m.group(2)), int(m.group(3))
        kp_map[kp_id] = f"arc-{arc_n}-sec-{sec_m}"
    return kp_map


# ---------- MD → HTML ----------

# LLM/NLP token notations like <s>, <eos>, <bos> get interpreted as HTML by the
# markdown processor. <s> in particular silently turns on strikethrough that
# leaks across the rest of the document. Wrap any such bare tag in backticks
# (turning it into inline code) before parsing — but only outside fenced
# code/inline code, where the author's escaping is already correct.
TOKEN_TAG_RE = re.compile(r'<(/?(?:s|eos|bos|pad|cls|sep|unk|mask))>', re.IGNORECASE)
_CODE_SPLIT_RE = re.compile(r'(```[\s\S]*?```|`[^`\n]+`)')

def escape_token_tags(text: str) -> str:
    parts = _CODE_SPLIT_RE.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = TOKEN_TAG_RE.sub(lambda m: f'`<{m.group(1)}>`', parts[i])
    return "".join(parts)


# ---------- 本讲大纲: mermaid flowchart 的受限子集 → HTML ----------
# WeasyPrint 里没有 JS, mermaid 渲不了; 又不想在编 PDF 时依赖 mermaid.ink 之类的外部服务
# (离线要能出片)。大纲图的形状是固定的 —— 「认知段落 (subgraph) 里排着若干 § (node)」——
# 所以这里只解析这一个子集, 渲成分栏卡片。MD 里仍是标准 mermaid, IDE / GitHub 照常渲染。
MERMAID_FENCE_RE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
_MMD_SUBGRAPH = re.compile(r'^\s*subgraph\s+(\w+)\s*\[\s*"?(.*?)"?\s*\]\s*$')
_MMD_NODE = re.compile(r'^\s*(\w+)\s*[\[\(\{]+\s*"?(.*?)"?\s*[\]\)\}]+\s*(?::::(\w+))?\s*$')
_MMD_EDGE = re.compile(r'^\s*(\w+)\s*-{2,3}>?\s*(?:\|\s*(.*?)\s*\|)?\s*(\w+)\s*$')
_MMD_CLASS = re.compile(r'^\s*class\s+([\w,\s]+?)\s+(\w+)\s*$')
# 分量 → 配色。类名沿用大纲里写的三档, 没标类的按"常规"。
MMD_TIER = {
    "core": ("mmd-core", "🎯"), "key": ("mmd-core", "🎯"),
    "normal": ("mmd-normal", ""), "mid": ("mmd-normal", ""),
    "bg": ("mmd-bg", ""), "background": ("mmd-bg", ""),
    "skip": ("mmd-skip", "—"), "out": ("mmd-skip", "—"),
}


def render_mermaid(src: str) -> str:
    """把大纲用的 mermaid flowchart 渲成 HTML 卡片。不认识的语法行直接忽略。"""
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
            if cur:
                groups[cur]["nodes"].append(nid)
            else:
                seq.append(nid)
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

def split_adjacent_blockquotes(md_text: str) -> str:
    """Python-Markdown merges two '>' blocks separated only by a blank line into ONE blockquote.
    Authors mean them as separate callouts (📌 定义 then 🎯 考试提醒), and Layer B styling needs
    them separate. Insert an empty HTML comment between them to force a block boundary.
    Continuation inside one box is written with bare '>' lines, which are not blank, so untouched."""
    lines = md_text.split("\n")
    out = []
    in_fence = False
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
    """Inside a blockquote, a '- item' line right after a text line does not start a list in
    Python-Markdown (it needs a blank '>' line first), so '📏 要懂多深? / - 考试够用 ...' collapses
    into one paragraph. Insert the missing '>' line automatically."""
    lines = md_text.split("\n")
    out = []
    for line in lines:
        st = line.lstrip()
        if (st.startswith(">") and out):
            body = st[1:].lstrip()
            prev = out[-1].lstrip()
            prev_body = prev[1:].lstrip() if prev.startswith(">") else None
            is_item = body.startswith(("- ", "* ", "+ ")) or (body[:1].isdigit() and body[1:3] in (". ", ".\t"))
            prev_is_item = prev_body is not None and (prev_body.startswith(("- ", "* ", "+ ")) or (prev_body[:1].isdigit() and prev_body[1:3] in (". ", ".\t")))
            if is_item and prev_body not in (None, "") and not prev_is_item:
                out.append(">")
        out.append(line)
    return "\n".join(out)


# ---------- 课件原图 (content-coverage.md §1.4 / presentation.md 图块) ----------
# Markdown `![课件 p20 · 说明](../raw/figures/xxx.png)` 独占一段 → <figure> + 图注。
# 图注保留 alt 原文; 带 "课件 p" 的判为课件原图并加 chip, 其余 (自绘) 用中性样式。
IMG_PARA_RE = re.compile(r'<p>\s*(<img\b[^>]*\balt="([^"]*)"[^>]*>)\s*</p>')


def wrap_figures(html: str) -> str:
    def repl(m):
        img, alt = m.group(1), m.group(2)
        cls = "fig fig-slide" if re.search(r"课件\s*p\d", alt) else "fig fig-own"
        return f'<figure class="{cls}">{img}<figcaption>{alt}</figcaption></figure>'
    return IMG_PARA_RE.sub(repl, html)


NO_GOALS = False
GOAL_BQ_RE = re.compile(r"^>\s*✅.*(?:\n>.*)*\n?", re.M)


def strip_goal_blocks(md_text: str) -> str:
    """--no-goals: 把 ✅ 教学目标块从成品里摘掉。

    目标块是写作期的加权依据和门禁凭据 (content-coverage.md §2.0), 留在 MD 里;
    读者手上的 PDF 不一定要印 —— 一讲十几节, 每节一块也是版面。
    """
    return GOAL_BQ_RE.sub("", md_text)


def md_to_html(md_text: str) -> str:
    mermaid_blocks = []

    def _stash_mermaid(m):
        mermaid_blocks.append(render_mermaid(m.group(1)))
        return f"\n\nMERMAIDBLOCK{len(mermaid_blocks) - 1}ENDMERMAID\n\n"

    md_text = MERMAID_FENCE_RE.sub(_stash_mermaid, md_text)
    md_text = escape_token_tags(md_text)
    md_text, _math_unknown = convert_math_blocks(md_text)
    if _math_unknown:
        print('  ⚠  未识别的 LaTeX 命令: ' + ', '.join(sorted(_math_unknown)),
              file=sys.stderr)
    md_text = split_adjacent_blockquotes(md_text)
    md_text = fix_blockquote_lists(md_text)
    extensions = [
        "fenced_code",
        "tables",
        "toc",
        "attr_list",
        "sane_lists",
        "pymdownx.superfences",
    ]
    md = markdown.Markdown(extensions=extensions, output_format="html5")
    html = wrap_figures(md.convert(md_text))
    for i, block in enumerate(mermaid_blocks):
        html = re.sub(rf"<p>\s*MERMAIDBLOCK{i}ENDMERMAID\s*</p>", block, html)
        html = html.replace(f"MERMAIDBLOCK{i}ENDMERMAID", block)
    return html


# ---------- Blockquote role tagging (writing-craft.md Layer B block types) ----------
# Every callout starts with a marker emoji (or a legacy **定义** / **要懂多深?** bold head).
# We map it to a CSS class so each block type gets its own colour + label chip in the PDF,
# letting the reader tell "hardcore / breather / lookup / advanced" apart at a glance.

BQ_ROLE_MARKERS = [
    ("🧭", "guide"), ("🧩", "role"), ("💡", "aid"), ("☕", "breather"),
    ("🔍", "reality"), ("⚠️", "trap"), ("⚠", "trap"), ("🎓", "master"),
    ("📌", "def"), ("📏", "depth"), ("🎯", "exam"), ("📎", "clip"), ("📍", "diverge"),
    ("✅", "goal"),
]
BQ_LEGACY_HEADS = [
    ("<strong>定义", "def"), ("<strong>要懂多深", "depth"), ("<strong>典型陷阱", "trap"),
    ("<strong>考试选型决策树", "exam"),
]
# Nested blockquotes inside a 🔍 box (the mandatory "对应到 X 世界" link-back line) are NOT
# their own callout type — labelling them "打个比方" mislabels a mapping as an analogy.
# They inherit the parent box styling instead.
BQ_OPEN_RE = re.compile(r'<blockquote>(\s*<p>\s*)', re.DOTALL)


def tag_blockquote_roles(html: str) -> str:
    """Add class="bq bq-<role>" to blockquotes whose first paragraph starts with a Layer B marker."""
    def repl(m):
        head = html[m.end():m.end() + 48]
        role = next((r for mk, r in BQ_ROLE_MARKERS if head.startswith(mk)), None)
        # 大纲的「必须带走的 N 条」也以 🎯 开头, 但它不是考试提醒 —— 顶着"考前必看"
        # 的标签会让读者以为这是一张考点清单, 而它是全讲的认知锚点。单独成一类。
        if role == "exam" and "必须带走" in head:
            role = "takeaway"
        if role is None:
            role = next((r for mk, r in BQ_LEGACY_HEADS if head.startswith(mk)), None)
        cls = f' class="bq bq-{role}"' if role else ''
        return f'<blockquote{cls}>{m.group(1)}'
    return BQ_OPEN_RE.sub(repl, html)


# ---------- Heading → stable section IDs ----------

H2_SECTION_RE = re.compile(r'<h2\b([^>]*)>(\s*§\s*(\d+)[^<]*)</h2>', re.DOTALL)
H2_TITLE_EXTRACT_RE = re.compile(r'<h2\s[^>]*id="arc-\d+-sec-(\d+)"[^>]*>(.*?)</h2>', re.DOTALL)
# 标题里常有行内代码 (`§1 \`factor_product\``)，渲染后是 <code>…</code>。
# 旧正则要求标题内部不含任何标签，于是这类小节整节从目录里消失。
TAG_RE = re.compile(r'<[^>]+>')

def stamp_section_ids(html: str, arc_num: int) -> str:
    """Replace generated h2 IDs with stable ones like id='arc-1-sec-3'."""
    def repl(m):
        attrs = m.group(1)
        inner = m.group(2)
        sec_num = int(m.group(3))
        # Strip existing id attribute if present
        attrs = re.sub(r'\s+id="[^"]*"', '', attrs)
        return f'<h2{attrs} id="arc-{arc_num}-sec-{sec_num}">{inner}</h2>'
    return H2_SECTION_RE.sub(repl, html)


# ---------- 阅读位置面包屑 (content-coverage.md §2.3) ----------
# 大纲只在讲首出现一次, 读到第 12 节时读者早忘了自己在哪一段。所以从大纲的 mermaid 里
# 取出「§N 属于哪一段」, 在每个 § 标题前盖一行面包屑, 并把它设成 running header 的字符串 ——
# 之后每一页的页眉都显示当前所在的段与节, 翻到哪儿都知道自己在哪。
# 面包屑由大纲派生, 不用作者另写, 所以不会和大纲对不上。
def outline_segment_map(md_text: str) -> dict:
    """从讲首大纲的 mermaid 里解析出 {§号: (段名, 节短名)}。没有大纲就返回空。"""
    m = MERMAID_FENCE_RE.search(md_text)
    if not m:
        return {}
    out, cur = {}, ""
    for raw in m.group(1).split("\n"):
        line = raw.strip()
        sg = _MMD_SUBGRAPH.match(line)
        if sg:
            cur = re.sub(r"\s*·.*$", "", sg.group(2)).strip()   # "① 把话说准 · §1-§4" → "① 把话说准"
            continue
        if line == "end":
            cur = ""
            continue
        nd = _MMD_NODE.match(line)
        if nd and cur:
            label = nd.group(2)
            sec = re.match(r"§\s*(\d+)\s*(.*)$", label)
            if sec:
                out[int(sec.group(1))] = (cur, sec.group(2).strip())
    return out


CRUMB_H2_RE = re.compile(r'(<h2\s[^>]*id="arc-(\d+)-sec-(\d+)"[^>]*>)')


def stamp_crumbs(html: str, seg_map: dict, total: int) -> str:
    """在每个 § 标题前插入一行面包屑; 它同时是 running header 的取值来源。"""
    if not seg_map:
        return html

    def repl(m):
        sec = int(m.group(3))
        seg, short = seg_map.get(sec, ("", ""))
        if not seg:
            return m.group(1)
        label = f"{seg} · §{sec}/{total} {short}".strip()
        return (f'<p class="crumb">{html_mod.escape(label)}</p>' + m.group(1))
    return CRUMB_H2_RE.sub(repl, html)


def extract_section_titles(html: str) -> list[tuple[int, str]]:
    """Extract (sec_num, title) for each §-section in this arc's HTML."""
    out = []
    for m in H2_TITLE_EXTRACT_RE.finditer(html):
        sec_num = int(m.group(1))
        title = html_mod.unescape(TAG_RE.sub('', m.group(2))).strip()
        out.append((sec_num, title))
    return out


# ---------- MD-file links → in-PDF anchors ----------

# After md_to_html, links to other arc files like [Arc 2](2-cloud-models.md)
# become <a href="2-cloud-models.md">Arc 2</a>. In a single PDF these are broken.
# Rewrite them to anchors like <a href="#arc-2">Arc 2</a>.

MDLINK_ARC_RE = re.compile(r'href="(\d+)-[^"]*\.md(?:#[^"]*)?"')
MDLINK_INDEX_RE = re.compile(r'href="index\.md(?:#[^"]*)?"')

def rewrite_md_links(html: str) -> str:
    """Convert <a href="N-slug.md"> → <a href="#arc-N">, index.md → #index."""
    html = MDLINK_ARC_RE.sub(lambda m: f'href="#arc-{m.group(1)}"', html)
    html = MDLINK_INDEX_RE.sub('href="#index"', html)
    return html


# ---------- Cross-reference linking (the fun part) ----------

# We want to turn plain text like "Arc 3 §2"、"Arc 1"、"KP-5.7"、"§4" into <a href="...">.
# But we must NOT touch text inside <pre>, <code>, or existing <a>.
# Strategy: split the HTML into protected and unprotected chunks, substitute only in the latter.

PROTECT_RE = re.compile(
    r'(<pre[\s\S]*?</pre>'           # code blocks
    r'|<code[\s\S]*?</code>'         # inline code
    r'|<a\s[\s\S]*?</a>'             # existing links
    r'|<h[1-6][\s\S]*?</h[1-6]>'     # headings (don't link the § in titles)
    r'|<[^>]+>)',                    # any tag opening (so we only match text content)
    re.IGNORECASE,
)

# In text nodes, find references. Order matters: most-specific first.
# Pattern allows optional space between "Arc N" and "§M".
REF_ARC_SEC_RE = re.compile(r'Arc\s*(\d+)\s*§\s*(\d+)')
REF_ARC_RE = re.compile(r'Arc\s*(\d+)')
REF_KP_RE = re.compile(r'KP-([0-9G]+\.\d+)')
REF_SEC_LOCAL_RE = re.compile(r'§\s*(\d+)')  # only applied when we know current arc


def link_references_in_text(text: str, current_arc: int | None, kp_map: dict[str, str]) -> str:
    """Convert reference patterns to <a href="#..."> anchors in a plain-text snippet.

    Each substitution is stashed behind a placeholder token so later passes
    don't re-match inside already-linked text (which would produce nested <a>).
    """
    placeholders: dict[str, str] = {}

    def stash(html_fragment: str) -> str:
        key = f"\x00XREF{len(placeholders)}\x01"
        placeholders[key] = html_fragment
        return key

    # 1) Most specific: "Arc N §M"
    text = REF_ARC_SEC_RE.sub(
        lambda m: stash(f'<a class="xref" href="#arc-{m.group(1)}-sec-{m.group(2)}">Arc {m.group(1)} §{m.group(2)}</a>'),
        text,
    )

    # 2) "Arc N" alone
    text = REF_ARC_RE.sub(
        lambda m: stash(f'<a class="xref" href="#arc-{m.group(1)}">Arc {m.group(1)}</a>'),
        text,
    )

    # 3) "KP-X.Y"
    def kp_sub(m):
        kp_id = f"KP-{m.group(1)}"
        target = kp_map.get(kp_id)
        if target:
            return stash(f'<a class="xref" href="#{target}">{kp_id}</a>')
        return kp_id
    text = REF_KP_RE.sub(kp_sub, text)

    # 4) "§M" (local ref, only within an arc)
    if current_arc is not None:
        text = REF_SEC_LOCAL_RE.sub(
            lambda m: stash(f'<a class="xref" href="#arc-{current_arc}-sec-{m.group(1)}">§{m.group(1)}</a>'),
            text,
        )

    # Restore placeholders
    for key, val in placeholders.items():
        text = text.replace(key, val)
    return text


def add_crossref_links(html: str, current_arc: int | None, kp_map: dict[str, str]) -> str:
    """Walk the HTML, only substituting in text nodes (not inside pre/code/a/headings)."""
    parts = PROTECT_RE.split(html)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Text node — safe to substitute references
            out.append(link_references_in_text(part, current_arc, kp_map))
        else:
            # Protected chunk — keep as is
            out.append(part)
    return "".join(out)


# ---------- Build full HTML document ----------

ARC_TITLE_EXTRACT_RE = re.compile(r'<h1\b[^>]*>([^<]+)</h1>', re.DOTALL)

def build_full_html(index_path, arc_files, course_title: str, kp_map: dict[str, str],
                    appendix_files: list = None, teach_dir: Path = None, prep: bool = False) -> str:
    cover_sub = "跟着熟手想一遍 · Assignment Prep" if prep else "教学故事链 · Story Chain"
    cover_hint = ("按顺序读; 遇到 ▶ 就停下来自己写" if prep
                  else "点击\u201cArc N\u201d、\u201c§N\u201d、\u201cKP-X.Y\u201d可跳转")
    sections = []
    toc_data = []  # [(arc_num, arc_title, [(sec_num, sec_title), ...])]

    # Index first (no arc number for local §M resolution)
    if index_path:
        html = md_to_html(index_path.read_text(encoding="utf-8"))
        html = tag_blockquote_roles(html)
        html = rewrite_md_links(html)
        html = add_crossref_links(html, current_arc=None, kp_map=kp_map)
        sections.append(f'<section class="first" id="index">\n{html}\n</section>')

    # Then each arc
    for arc_num, path in arc_files:
        md_src = path.read_text(encoding="utf-8")
        if NO_GOALS:
            md_src = strip_goal_blocks(md_src)
        seg_map = outline_segment_map(md_src)
        html = md_to_html(md_src)
        html = tag_blockquote_roles(html)
        html = stamp_section_ids(html, arc_num)
        html = stamp_crumbs(html, seg_map, len(re.findall(r"^## §\d+", md_src, re.M)))
        html = rewrite_md_links(html)
        html = add_crossref_links(html, current_arc=arc_num, kp_map=kp_map)

        # Extract Arc title from h1 for TOC
        arc_title_match = ARC_TITLE_EXTRACT_RE.search(html)
        arc_title = arc_title_match.group(1).strip() if arc_title_match else f"Arc {arc_num}"
        sec_titles = extract_section_titles(html)
        toc_data.append((arc_num, arc_title, sec_titles))

        sections.append(f'<section class="arc" id="arc-{arc_num}">\n{html}\n</section>')

    # Appendix files (e.g. exam keyword index) — placed after all arcs
    for apath in (appendix_files or []):
        html = md_to_html(apath.read_text(encoding="utf-8"))
        html = tag_blockquote_roles(html)
        html = rewrite_md_links(html)
        html = add_crossref_links(html, current_arc=None, kp_map=kp_map)
        slug = apath.stem
        sections.append(f'<section class="arc" id="{slug}">\n{html}\n</section>')

    body = "\n".join(sections)
    safe_title = course_title.replace("<", "&lt;").replace(">", "&gt;")

    # Build clickable TOC page
    toc_html = build_toc_html(toc_data, has_index=index_path is not None)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
</head>
<body>
<header class="cover">
  <h1 class="cover-title">{safe_title}</h1>
  <p class="cover-sub">{cover_sub}</p>
  <p class="cover-hint">{cover_hint}</p>
</header>
{toc_html}
{build_graph_page(teach_dir)}
{body}
</body>
</html>"""


def build_graph_page(teach_dir: Path) -> str:
    """If knowledge-graph.png exists in parent dir, embed it as a full page."""
    # Graph lives in output/{course}/, one level up from teach/
    graph_png = teach_dir.parent / "knowledge-graph.png"
    if not graph_png.exists():
        return ""
    return f"""<section class="graph-page">
  <h1 class="graph-title">全课程知识图谱</h1>
  <p class="graph-hint">实线=依赖递进 | 粗线=实现支撑 | 虚线=对比并列 | 点线=组成使用</p>
  <img src="file://{graph_png}" class="graph-img" />
</section>"""


def build_toc_html(toc_data, has_index: bool) -> str:
    """Build a clickable TOC page after cover."""
    lines = ['<section class="toc-page">']
    lines.append('<h1 class="toc-title">📑 目录</h1>')
    if has_index:
        lines.append('<div class="toc-entry toc-entry-index"><a href="#index">📋 知识点索引</a></div>')
    for arc_num, arc_title, sec_titles in toc_data:
        lines.append(f'<div class="toc-arc"><a href="#arc-{arc_num}"><strong>{arc_title}</strong></a></div>')
        for sec_num, sec_title in sec_titles:
            lines.append(f'<div class="toc-sec"><a href="#arc-{arc_num}-sec-{sec_num}">{sec_title}</a></div>')
    lines.append('</section>')
    return "\n".join(lines)


# ---------- CSS ----------

def build_css(cjk_font: str | None, cjk_paths: list[str]) -> str:
    font_face_rules = ""
    if cjk_font and cjk_paths:
        font_face_rules = f"""
@font-face {{
  font-family: "CourseCJK";
  src: url("file://{cjk_paths[0]}");
  font-weight: normal;
}}
"""

    primary = '"CourseCJK", ' if font_face_rules else ""
    math_css = MATH_CSS

    return f"""
{font_face_rules}

@page {{
  size: A5;
  margin: 16mm 12mm 16mm 12mm;
  @bottom-center {{
    content: counter(page) " / " counter(pages);
    font-size: 8pt;
    color: #888;
    font-family: {primary}"Microsoft YaHei", sans-serif;
  }}
  @top-center {{
    /* 默认取 first: 本页第一个面包屑; 本页没有新节时沿用上一页的值。
       (试过 string(crumb, start) —— WeasyPrint 下解析为空, 整条页眉消失。) */
    content: string(crumb);
    font-size: 7.5pt;
    color: #93a0b0;
    font-family: {primary}"Microsoft YaHei", sans-serif;
    padding-bottom: 1.5mm;
    border-bottom: 0.4pt solid #e3e8ee;
    width: 100%;
  }}
}}

/* 阅读位置面包屑: 正文里每节标题前一行, 同时喂给页眉 (见 stamp_crumbs) */
.crumb {{
  string-set: crumb content();
  font-size: 7.5pt; color: #8794a5; margin: 1.1em 0 -0.5em 0;
  letter-spacing: 0.02em;
}}

html {{
  font-family: {primary}"Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif;
  font-size: 10pt;
  line-height: 1.6;
  color: #222;
}}

body {{ margin: 0; padding: 0; }}

header.cover {{
  page-break-after: always;
  text-align: center;
  margin-top: 28%;
}}
.cover-title {{
  font-size: 22pt;
  margin-bottom: 0.5em;
  border: none;
}}
.cover-sub {{ color: #666; font-size: 13pt; }}
.cover-hint {{ color: #2a6fb5; font-size: 9pt; margin-top: 2em; }}

section.arc {{ page-break-before: always; }}
section.toc-page {{ page-break-after: always; }}
section.graph-page {{ page: graph-landscape; page-break-before: always; page-break-after: always; }}
@page graph-landscape {{ size: A5 landscape; margin: 8mm; }}
.graph-title {{ font-size: 14pt; text-align: center; margin-bottom: 0.2em; border: none; }}
.graph-hint {{ font-size: 7pt; color: #666; text-align: center; margin-bottom: 0.3em; }}
.graph-img {{ width: 100%; max-height: 90%; }}

/* ---------- TOC page ---------- */
.toc-title {{
  font-size: 18pt;
  border-bottom: 2px solid #333;
  padding-bottom: 0.3em;
  margin-bottom: 1em;
  text-align: center;
}}
.toc-entry-index {{
  margin: 0.4em 0;
  font-size: 11pt;
  color: #2a6fb5;
}}
.toc-arc {{
  margin: 0.8em 0 0.2em 0;
  font-size: 11.5pt;
  color: #1a4a85;
}}
.toc-arc a {{ color: #1a4a85; }}
.toc-sec {{
  margin: 0.15em 0 0.15em 1.5em;
  font-size: 9.5pt;
  color: #444;
}}
.toc-sec a {{ color: #444; }}

/* ---------- Headings (visual hierarchy: Arc > § > sub) ---------- */
/* h1 = Arc title (big, bold, top of arc) */
h1 {{
  font-size: 18pt;
  color: #1a4a85;
  border-bottom: 3px solid #1a4a85;
  padding-bottom: 0.3em;
  margin-top: 0.5em;
  margin-bottom: 0.8em;
  page-break-after: avoid;
}}
/* h2 = § section (CONCEPT — blue side bar, prominent) */
h2 {{
  font-size: 13.5pt;
  color: #1a4a85;
  margin-top: 1.4em;
  margin-bottom: 0.5em;
  padding: 0.3em 0.6em;
  border-left: 5px solid #1a4a85;
  background: #eef3f9;
  page-break-after: avoid;
}}
/* h3 = sub-heading inside a section or example (TEACHING SUB-TOPIC) */
h3 {{
  font-size: 11pt;
  margin-top: 1em;
  margin-bottom: 0.4em;
  color: #444;
  border-left: 3px solid #888;
  padding-left: 0.5em;
  page-break-after: avoid;
}}

p {{ margin: 0.5em 0; text-align: justify; }}
strong {{ color: #111; }}

/* ---------- 课件原图 / 自绘图 ---------- */
figure.fig {{ margin: 0.9em 0; padding: 0.45em 0.5em 0.4em; page-break-inside: avoid; text-align: center;
  border: 1px solid #dfe5ec; border-radius: 4px; background: #fff; }}
figure.fig img {{ max-width: 100%; max-height: 62vh; height: auto; }}
figure.fig figcaption {{ font-size: 8.4pt; color: #55636f; margin-top: 0.35em; text-align: left; line-height: 1.4; }}
figure.fig-slide {{ border-color: #c9d8e8; }}
figure.fig-slide figcaption::before {{ content: "课件原图"; font-size: 7pt; font-weight: bold; color: #fff; background: #5b7fa6;
  border-radius: 3px; padding: 0.05em 0.4em; margin-right: 0.5em; }}
figure.fig-own figcaption::before {{ content: "自绘"; font-size: 7pt; font-weight: bold; color: #fff; background: #8a8f96;
  border-radius: 3px; padding: 0.05em 0.4em; margin-right: 0.5em; }}

/* ---------- 本讲大纲 (mermaid flowchart 子集, 见 render_mermaid) ---------- */
.mmd {{ margin: 0.9em 0; page-break-inside: avoid; }}
.mmd-group {{ border: 1px solid #c9d8e8; border-radius: 5px; background: #f7fafd; padding: 0.3em 0.45em 0.45em; }}
.mmd-gt {{ font-size: 8.6pt; font-weight: bold; color: #33526e; margin-bottom: 0.35em; }}
.mmd-row {{ display: flex; flex-wrap: wrap; gap: 0.3em; }}
.mmd-row.mmd-loose {{ margin-top: 0.4em; }}
.mmd-node {{ display: inline-block; font-size: 8.2pt; line-height: 1.3; padding: 0.2em 0.45em;
  border-radius: 4px; border: 1px solid #cfd8e0; background: #fff; color: #24313d; }}
.mmd-core {{ border-color: #c62828; background: #fdecea; color: #8d2018; font-weight: bold; }}
.mmd-normal {{ border-color: #9fb6cc; background: #fff; }}
.mmd-bg {{ border-color: #d8dde2; background: #f3f5f7; color: #667180; font-size: 7.8pt; }}
.mmd-skip {{ border: 1px dashed #c3c8cd; background: #fafbfc; color: #939aa2; font-size: 7.8pt; }}
.mmd-arrow {{ text-align: center; font-size: 8pt; color: #5b7fa6; margin: 0.2em 0; }}

/* ---------- Blockquotes — different roles by emoji prefix ---------- */
blockquote {{
  border-left: 3px solid #7aa5d2;
  background: #f2f6fb;
  margin: 0.8em 0;
  padding: 0.5em 0.8em;
  color: #333;
  page-break-inside: avoid;
}}
blockquote strong {{ color: #2a4a6b; }}
/* h3 INSIDE blockquote (e.g. "入门" / "真实场景") — distinguish from regular h3 */
blockquote h3 {{
  font-size: 10.5pt;
  color: #1a4a85;
  border-left: none;
  background: rgba(255,255,255,0.5);
  padding: 0.2em 0.5em;
  margin-top: 0.6em;
  margin-bottom: 0.3em;
  border-radius: 2px;
}}

/* ---------- Layer B block types: one colour + label chip per role ---------- */
blockquote.bq {{ border-radius: 4px; }}
blockquote.bq::before {{
  display: block;
  font-size: 7.2pt;
  font-weight: bold;
  letter-spacing: 0.06em;
  margin: -0.05em 0 0.35em 0;
  opacity: 0.9;
}}
/* 🧭 导读条 / 读法指南 — slim strip, low-key */
.bq-guide {{ border-left: 3px solid #5b8a8a; background: #eef5f5; color: #3d5c5c; font-size: 9pt; padding: 0.3em 0.7em; }}
.bq-guide::before {{ content: "导读 · 先看这行再决定怎么读"; color: #4a7373; }}
.bq-guide strong {{ color: #2f5555; }}
/* 🧩 核心角色 — indigo anchor */
.bq-role {{ border-left: 5px solid #3949ab; background: #e8eaf6; }}
.bq-role::before {{ content: "核心角色 · 忘了公式靠这句重建"; color: #283593; }}
.bq-role strong {{ color: #283593; }}
/* 💡 打个比方 — amber aid */
.bq-aid {{ border-left: 4px solid #f0a020; background: #fff6e5; }}
.bq-aid::before {{ content: "打个比方 · 辅助消化"; color: #a86b00; }}
.bq-aid strong {{ color: #8a5a00; }}
/* ☕ 换气 — cream, dashed: visibly "not the main line" */
.bq-breather {{ border: 1.5px dashed #c9a227; background: #fffbea; color: #4a4030; }}
.bq-breather::before {{ content: "换气 · 轻松读 · 跳过不影响主线"; color: #8a6d00; }}
.bq-breather strong {{ color: #6b5300; }}
/* 🔍 真实场景 — green, with its own sub-heading tint */
.bq-reality {{ border-left: 5px solid #2e8b57; background: #eaf6ee; }}
.bq-reality::before {{ content: "真实场景 · 概念落地"; color: #1f6b3f; }}
.bq-reality strong {{ color: #1f6b3f; }}
.bq-reality h3 {{ color: #1f6b3f; background: rgba(255,255,255,0.6); }}
/* ⚠️ 陷阱 — orange-red */
.bq-trap {{ border-left: 5px solid #e0521c; background: #fdeee7; }}
.bq-trap::before {{ content: "陷阱 · 考前扫一遍"; color: #b53d0f; }}
.bq-trap strong {{ color: #b53d0f; }}
/* 🎓 师门心法 — deep purple, thick edge: advanced & optional */
.bq-master {{ border-left: 6px solid #6a1b9a; background: #f3e8f9; color: #2e1a3a; }}
.bq-master::before {{ content: "师门心法 · 进阶 · 考试不考 · 想真正懂再读"; color: #4a148c; }}
.bq-master strong {{ color: #4a148c; }}
.bq-master em {{ color: #7b4fa0; }}
/* 📌 定义 — the classic blue lookup box */
.bq-def {{ border-left: 5px solid #1a4a85; background: #e7eef8; }}
.bq-def::before {{ content: "定义 · 速查"; color: #1a4a85; }}
/* 📏 要懂多深 — slate */
.bq-depth {{ border-left: 4px solid #607d8b; background: #eceff1; }}
.bq-depth::before {{ content: "要懂多深 · 投入校准"; color: #455a64; }}
.bq-depth strong {{ color: #37474f; }}
/* 🎯 考试提醒 — red */
.bq-exam {{ border-left: 5px solid #c62828; background: #fdecea; }}
.bq-exam::before {{ content: "考试提醒 · 考前必看"; color: #b71c1c; }}
.bq-exam strong {{ color: #b71c1c; }}

/* ✅ 学完这节 — 教学目标。它的主要作用是给作者定篇幅 (content-coverage.md §2.0),
   对读者只是一行自查; 所以不挂标签 chip、小字、细边, 一节只占一行 */
.bq-goal {{ border-left: 3px solid #00695c; background: #eef5f4; color: #1c3a36;
  font-size: 8.8pt; padding: 0.25em 0.6em; margin-top: 0.5em; }}
.bq-goal strong {{ color: #00584c; }}

.bq-takeaway {{ border-left: 6px solid #1b5e20; background: #edf7ee; color: #1f3d24; }}
.bq-takeaway::before {{ content: "本讲要点 · 读完能自己说出来"; color: #1b5e20; }}
.bq-takeaway strong {{ color: #14401a; }}
/* Nested blockquote inside a callout (the mandatory "对应到 X 世界" link-back inside a 🔍 box,
   or a quoted formula inside 🎓) — inherit the parent's accent instead of the default blue,
   so it reads as part of the parent box rather than a foreign block dropped into it. */
.bq blockquote {{
  background: rgba(255,255,255,0.62);
  border-left-width: 3px;
  margin: 0.5em 0;
}}
.bq-reality blockquote {{ border-left-color: #2e8b57; }}
.bq-master blockquote  {{ border-left-color: #6a1b9a; }}
.bq-breather blockquote{{ border-left-color: #c9a227; }}
.bq-aid blockquote     {{ border-left-color: #f0a020; }}
.bq-trap blockquote    {{ border-left-color: #e0521c; }}
.bq-role blockquote    {{ border-left-color: #3949ab; }}

/* 📎 小补充 — grey, smaller */
.bq-clip {{ border-left: 3px solid #9e9e9e; background: #f5f5f5; font-size: 9pt; color: #444; }}
.bq-clip::before {{ content: "小补充 · 知道存在即可"; color: #616161; }}
/* 📍 发散说明 — pale yellow */
.bq-diverge {{ border-left: 4px solid #d4a017; background: #fdf6dc; }}
.bq-diverge::before {{ content: "发散 · 课件外延伸"; color: #8a6d00; }}

code {{
  font-family: "DejaVu Sans Mono", "Consolas", monospace;
  font-size: 9pt;
  background: #f0f0f0;
  padding: 0 3px;
  border-radius: 2px;
  overflow-wrap: break-word;
}}
pre {{
  font-family: "DejaVu Sans Mono", "Consolas", monospace;
  font-size: 8pt;
  line-height: 1.35;
  background: #f7f7f7;
  border: 1px solid #ddd;
  border-radius: 3px;
  padding: 6px 8px;
  /* 兜底: 绝不允许代码块横向溢出页面被裁掉 (见 verify_teach.py 的 pre 行宽门禁)。
     门禁保证源码行 <= 70 等宽单位, 正常不会触发换行; 触发了也只是折行, 不丢字。 */
  white-space: pre-wrap;
  overflow-wrap: break-word;
  word-break: break-word;
  page-break-inside: avoid;
}}
pre code {{ background: transparent; padding: 0; font-size: inherit; }}

table {{
  border-collapse: collapse;
  width: 100%;
  margin: 0.8em 0;
  font-size: 9.5pt;
  /* 整表 avoid 会把前面的标题孤零零留在上一页; 超过一页时反正也要断。
     改成: 表可跨页, 但单行不许劈开, 表头每页重复。 */
  page-break-inside: auto;
}}
thead {{ display: table-header-group; }}
tr {{ page-break-inside: avoid; }}
th, td {{ border: 1px solid #ccc; padding: 4px 6px; text-align: left; vertical-align: top;
          overflow-wrap: anywhere; }}
/* 单元格里的行内代码常是没有空格的长 token (函数调用 / dict 字面量)。
   不允许在 token 内部断行时, 那一列会把表撑得比 A5 还宽, 其余列被挤成一字一行。
   break-all 让它在任意字符处折行 —— 代码难看一点, 但表格保住了。 */
td code, th code {{ white-space: pre-wrap; word-break: break-all; overflow-wrap: anywhere; }}
th {{ background: #eef3f9; font-weight: bold; }}

hr {{ border: none; border-top: 1px dashed #bbb; margin: 1.2em 0; }}

ul, ol {{ padding-left: 1.4em; margin: 0.4em 0; }}
li {{ margin: 0.15em 0; }}

a {{ color: #2a6fb5; text-decoration: none; }}

/* Internal cross-reference links: subtle distinct style */
a.xref {{
  color: #c2410c;
  text-decoration: none;
  border-bottom: 1px dotted #c2410c;
}}

{math_css}
"""


# ---------- Main ----------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    argv = list(sys.argv[1:])
    prep = "--prep" in argv                   # 作业预备模式: 换掉讲义封面文案
    if prep:
        argv.remove("--prep")
    global NO_GOALS
    NO_GOALS = "--no-goals" in argv           # 不把 ✅ 教学目标块印进 PDF (MD 里仍保留)
    if NO_GOALS:
        argv.remove("--no-goals")
    only = None
    if "--only" in argv:                      # 单讲模式: 只编这一份 MD, 不带 index, 图片相对路径按 teach/ 解析
        i = argv.index("--only")
        only = argv[i + 1]
        del argv[i:i + 2]
    teach_dir = Path(argv[0]).resolve()
    if only:
        only_path = (teach_dir / only).resolve()
        output_pdf = Path(argv[1]).resolve() if len(argv) >= 2 else only_path.with_suffix(".pdf")
        m = re.match(r"^(\d+)-", only_path.name)
        index_path, appendix_files = None, []
        arc_files = [(int(m.group(1)) if m else 1, only_path)]
    else:
        output_pdf = Path(argv[1]).resolve() if len(argv) >= 2 else teach_dir / "full-story.pdf"
        index_path, arc_files, appendix_files = collect_md_files(teach_dir)
    if not arc_files and not index_path:
        raise SystemExit(f"No MD files found in {teach_dir}")

    total = len(arc_files) + (1 if index_path else 0) + len(appendix_files)
    print(f"Found {total} files:", file=sys.stderr)
    if index_path:
        print(f"  {index_path.name}", file=sys.stderr)
    for n, f in arc_files:
        print(f"  {f.name} (arc {n})", file=sys.stderr)
    for f in appendix_files:
        print(f"  {f.name} (appendix)", file=sys.stderr)

    kp_map = build_kp_map(index_path) if index_path else {}
    if kp_map:
        print(f"✓ Indexed {len(kp_map)} knowledge points for cross-linking", file=sys.stderr)

    course_name = teach_dir.parent.name
    title = course_name.replace("-", " ").title() + (" · 作业预备" if prep else " · 教学故事链")
    if only:
        first_h1 = re.search(r"^#\s+(.+)$", arc_files[0][1].read_text(encoding="utf-8"), re.M)
        title = first_h1.group(1).strip() if first_h1 else arc_files[0][1].stem

    cjk_font, cjk_paths = find_cjk_font()
    html_doc = build_full_html(index_path, arc_files, title, kp_map, appendix_files, teach_dir, prep)
    css = build_css(cjk_font, cjk_paths)

    font_config = FontConfiguration()
    HTML(string=html_doc, base_url=str(teach_dir)).write_pdf(
        str(output_pdf),
        stylesheets=[CSS(string=css, font_config=font_config)],
        font_config=font_config,
        presentational_hints=True,
    )

    size_kb = output_pdf.stat().st_size // 1024
    print(f"✓ PDF generated: {output_pdf} ({size_kb} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
