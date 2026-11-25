#!/usr/bin/env python3
"""
Compile cheatsheet/*.md into a single print-friendly PDF.

Usage:
    python3 compile_cheatsheet_pdf.py <course_cheatsheet_dir> [output_pdf_path] [--flow]

Collects every `NN-*.md` / `NNx-*.md` (e.g. 03a-, 03b-) in order; other .md files are ignored.

Differences from compile_story_pdf.py:
- A4 portrait (not A5), tight margins for max space efficiency
- No cover page, no separate TOC (00-index.md already serves as navigation)
- Each file starts on a new page by default; --flow lets files run on, separated by a large title and spacing
- No cross-reference linking (cheatsheet is for print, no clicks expected)
- Smaller font sizes, denser line spacing
- Tables with explicit grid borders for readability under stress

Dependencies:
    pip install --user --break-system-packages markdown weasyprint pymdown-extensions
"""

import sys
import re
import base64
from io import BytesIO
from pathlib import Path

import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


# ---------- Font detection (CJK + Emoji) ----------

def find_fonts():
    """Find CJK + emoji fonts. Returns (primary_cjk_path, emoji_path, font_family_name)."""
    cjk_candidates = [
        ("/mnt/c/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
        ("/mnt/c/Windows/Fonts/simhei.ttf", "SimHei"),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK SC"),
    ]
    emoji_candidates = [
        "/mnt/c/Windows/Fonts/seguiemj.ttf",  # Segoe UI Emoji (Windows)
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",  # Linux
    ]

    cjk_path, cjk_name = None, "Microsoft YaHei"
    for p, name in cjk_candidates:
        if Path(p).exists():
            cjk_path, cjk_name = p, name
            print(f"✓ CJK font: {name} ({p})", file=sys.stderr)
            break

    emoji_path = next((p for p in emoji_candidates if Path(p).exists()), None)
    if emoji_path:
        print(f"✓ Emoji font: {emoji_path}", file=sys.stderr)

    return cjk_path, emoji_path, cjk_name


# ---------- File collection ----------

def collect_md_files(cheatsheet_dir: Path):
    """Return [(file_index, path)] sorted; index.md (00-index.md) goes first."""
    files = []
    for f in cheatsheet_dir.glob("*.md"):
        # 分册允许带字母后缀（03a-、03b-），按 (数字, 后缀) 排序
        m = re.match(r"^(\d+)([a-z]?)-", f.name)
        if m:
            files.append(((int(m.group(1)), m.group(2)), f))
    files.sort(key=lambda x: x[0])
    return [(n, f) for (n, _), f in files]


# ---------- MD → HTML ----------

def md_to_html(md_text: str) -> str:
    extensions = [
        "fenced_code",
        "tables",
        "attr_list",
        "sane_lists",
        "pymdownx.superfences",
        "pymdownx.arithmatex",  # Wrap $...$ / $$...$$ in <span class="arithmatex">\(...\)</span>
    ]
    extension_configs = {
        "pymdownx.arithmatex": {"generic": True},
    }
    md = markdown.Markdown(
        extensions=extensions,
        extension_configs=extension_configs,
        output_format="html5",
    )
    return md.convert(md_text)


# ---------- LaTeX math rendering (matplotlib.mathtext → SVG → inline base64) ----------

_MATH_INLINE_RE = re.compile(r'<span class="arithmatex">\\\((.+?)\\\)</span>', re.DOTALL)
_MATH_BLOCK_RE = re.compile(r'<div class="arithmatex">\\\[(.+?)\\\]</div>', re.DOTALL)

_MATPLOTLIB_READY = False

def _ensure_matplotlib():
    global _MATPLOTLIB_READY
    if _MATPLOTLIB_READY:
        return
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["mathtext.fontset"] = "cm"  # Computer Modern, LaTeX-like
    _MATPLOTLIB_READY = True


def _render_latex_to_svg_data_url(latex: str) -> str | None:
    """Render LaTeX expression to a base64-encoded SVG data URL. Returns None on failure."""
    _ensure_matplotlib()
    from matplotlib import mathtext
    buf = BytesIO()
    expr = f"${latex.strip()}$"
    try:
        mathtext.math_to_image(expr, buf, format="svg", dpi=150)
    except Exception as e:
        print(f"⚠  math render failed: {latex[:60]!r} ({e})", file=sys.stderr)
        return None
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_math_in_html(html: str) -> str:
    """Replace arithmatex spans/divs with rendered math images (inline / block)."""

    def inline_repl(m):
        latex = m.group(1)
        url = _render_latex_to_svg_data_url(latex)
        if url is None:
            return f'<code>{_html_escape(latex)}</code>'
        return f'<img src="{url}" class="math-inline" alt="{_html_escape(latex)}" />'

    def block_repl(m):
        latex = m.group(1)
        url = _render_latex_to_svg_data_url(latex)
        if url is None:
            return f'<pre class="math-fallback">{_html_escape(latex)}</pre>'
        return f'<div class="math-block"><img src="{url}" alt="{_html_escape(latex)}" /></div>'

    html = _MATH_INLINE_RE.sub(inline_repl, html)
    html = _MATH_BLOCK_RE.sub(block_repl, html)
    return html


# ---------- Strip cross-file MD links (they don't work in print) ----------

MDLINK_RE = re.compile(r'<a\s+href="\d+-[^"]*\.md(?:#[^"]*)?"[^>]*>([^<]+)</a>')

def strip_md_links(html: str) -> str:
    """Convert <a href="01-foo.md">text</a> → text (links break in print PDFs)."""
    return MDLINK_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", html)


# ---------- Build document ----------

def build_full_html(files, course_title: str) -> str:
    sections = []
    for idx, path in files:
        html = md_to_html(path.read_text(encoding="utf-8"))
        html = strip_md_links(html)
        html = render_math_in_html(html)
        # First file (00-index) gets no page break before
        cls = "ch-index" if idx == 0 and path.name.startswith("00") else "ch"
        sections.append(f'<section class="{cls}">\n{html}\n</section>')

    body = "\n".join(sections)
    safe_title = course_title.replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
</head>
<body>
{body}
</body>
</html>"""


# ---------- CSS ----------

FLOW_CSS = """
/* --flow：分册不换页，用大标题和留白隔开（省纸） */
section.ch, section.ch-index { page-break-before: auto !important; page-break-after: auto !important; }
section.ch { margin-top: 1.6em; padding-top: 0.5em; border-top: 3px double #1a4a85; }
section.ch h1 { font-size: 15pt; margin-top: 0.2em; }
"""


def build_css(cjk_path: str, emoji_path: str | None) -> str:
    font_face = ""
    if cjk_path:
        font_face += f"""
@font-face {{
  font-family: "CourseCJK";
  src: url("file://{cjk_path}");
  font-weight: normal;
}}
"""
    if emoji_path:
        font_face += f"""
@font-face {{
  font-family: "CourseEmoji";
  src: url("file://{emoji_path}");
  unicode-range: U+2300-23FF, U+1F300-1F9FF, U+2600-26FF, U+2700-27BF, U+1F000-1F2FF;
}}
"""

    # 不要把 "Segoe UI Emoji" / "Noto Color Emoji" 这类**系统 emoji 字族名**写进 stack。
    # 它们覆盖 keycap 底座字符 U+0030-0039，Pango 会把正文里的**数字**整段判给 emoji 字体，
    # 渲染成全角宽度 —— "CS1234" 会排成 "CS 1 2 3 4"。CourseEmoji 有 unicode-range 限制，安全；
    # 其余 emoji 交给 fontconfig 自动回退（仍然落到 Noto Color Emoji，彩色正常）。
    primary_stack = '"CourseCJK", "CourseEmoji", "Microsoft YaHei", sans-serif'

    return f"""
{font_face}

@page {{
  size: A4;
  /* 打印密度优先: 左右 9mm 仍在几乎所有家用/办公打印机的可打印区内,
     上下 8mm / 下 7mm 给页码留位。想再省纸就调这里, 不要动字号以外的内容。 */
  margin: 8mm 9mm 7mm 9mm;
  @bottom-center {{
    content: counter(page) " / " counter(pages);
    font-size: 6.5pt;
    color: #888;
    font-family: {primary_stack};
  }}
}}

html {{
  font-family: {primary_stack};
  font-size: 8.4pt;
  line-height: 1.26;
  color: #1a1a1a;
}}

body {{ margin: 0; padding: 0; }}

/* Each chapter starts on a new page (except the index, which leads) */
section.ch {{ page-break-before: always; }}
section.ch-index {{ page-break-after: always; }}

/* ---------- Headings ---------- */
/* h1 = chapter title */
h1 {{
  font-size: 12pt;
  color: #1a4a85;
  border-bottom: 1.5px solid #1a4a85;
  padding-bottom: 0.12em;
  margin: 0 0 0.3em 0;
  page-break-after: avoid;
}}
/* h2 = knowledge point (bold blue side bar) */
h2 {{
  font-size: 9.8pt;
  color: #1a4a85;
  margin: 0.5em 0 0.18em 0;
  padding: 0.1em 0.4em;
  border-left: 3px solid #1a4a85;
  background: #eef3f9;
  page-break-after: avoid;
  page-break-inside: avoid;
}}
/* h3 = section (核心认知/判断/计算/简答) — slim grey side bar */
h3 {{
  font-size: 9pt;
  font-weight: bold;
  color: #444;
  margin: 0.35em 0 0.18em 0;
  padding-left: 0.35em;
  border-left: 2px solid #888;
  page-break-after: avoid;
}}
/* h4 = sub-section (✅ True / ❌ False) — inline-style */
h4 {{
  font-size: 8.6pt;
  font-weight: bold;
  margin: 0.28em 0 0.12em 0;
  color: #555;
  page-break-after: avoid;
}}

p {{ margin: 0.14em 0; }}
strong {{ color: #111; }}

/* ---------- Blockquotes (used in 简答 English fragments / answer panels) ---------- */
blockquote {{
  border-left: 2px solid #7aa5d2;
  background: #f7faff;
  margin: 0.22em 0;
  padding: 0.16em 0.45em;
  color: #333;
  font-size: 8pt;
  line-height: 1.22;
  page-break-inside: avoid;
}}
blockquote p {{ margin: 0.06em 0; }}

/* ---------- Code ---------- */
code {{
  font-family: "DejaVu Sans Mono", "Consolas", monospace;
  font-size: 8pt;
  background: #f0f0f0;
  padding: 0 2px;
  border-radius: 2px;
}}
pre {{
  font-family: "DejaVu Sans Mono", "Consolas", monospace;
  font-size: 7pt;
  line-height: 1.18;
  background: #f7f7f7;
  border: 1px solid #ddd;
  border-radius: 2px;
  padding: 3px 5px;
  /* 兜底: 绝不允许代码块横向溢出页面被裁掉 (见 verify_teach.py 的 pre 行宽门禁)。
     门禁保证源码行 <= 70 等宽单位, 正常不会触发换行; 触发了也只是折行, 不丢字。 */
  white-space: pre-wrap;
  overflow-wrap: break-word;
  word-break: break-word;
  page-break-inside: avoid;
  margin: 0.28em 0;
}}
pre code {{ background: transparent; padding: 0; font-size: inherit; }}

/* ---------- Tables (critical for cheatsheet density) ---------- */
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 0.28em 0;
  font-size: 7.9pt;
  line-height: 1.2;
  /* 不再整表 page-break-inside: avoid —— 一张 25 行的公式表放不下就整块跳页,
     会在上一页留大半页空白。改成允许断开, 但保证 (1) 单行不被劈开,
     (2) 表头在续页重复打印。 */
  page-break-inside: auto;
}}
thead {{ display: table-header-group; }}
tr {{ page-break-inside: avoid; }}
th, td {{
  border: 1px solid #999;
  padding: 1.5px 4px;
  text-align: left;
  vertical-align: top;
}}
th {{
  background: #eef3f9;
  font-weight: bold;
  color: #1a4a85;
}}

/* Italic English fragments inside bullets — visually subordinate */
em {{
  color: #555;
  font-style: italic;
}}

/* Horizontal rule */
hr {{
  border: none;
  border-top: 1px dashed #aaa;
  margin: 0.4em 0;
}}

/* Lists */
ul, ol {{ padding-left: 1.05em; margin: 0.18em 0; }}
li {{ margin: 0.02em 0; }}

a {{ color: #2a6fb5; text-decoration: none; }}

/* ---------- LaTeX math (rendered SVG via matplotlib.mathtext) ---------- */
img.math-inline {{
  vertical-align: -0.25em;
  height: 1.15em;
}}
.math-block {{
  text-align: center;
  margin: 0.32em 0;
  page-break-inside: avoid;
}}
.math-block img {{
  max-width: 95%;
  height: auto;
}}
pre.math-fallback {{
  background: #fff8dc;
  border: 1px dashed #c98;
  font-size: 8pt;
  padding: 4px 6px;
}}
"""


# ---------- Main ----------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    flow = "--flow" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--flow"]
    cs_dir = Path(args[0]).resolve()
    output_pdf = Path(args[1]).resolve() if len(args) >= 2 else cs_dir / "full-cheatsheet.pdf"

    if not cs_dir.is_dir():
        raise SystemExit(f"Not a directory: {cs_dir}")

    files = collect_md_files(cs_dir)
    if not files:
        raise SystemExit(f"No numbered MD files in {cs_dir}")

    print(f"Found {len(files)} files:", file=sys.stderr)
    for n, f in files:
        print(f"  {f.name}", file=sys.stderr)

    course_name = cs_dir.parent.name
    title = course_name.replace("-", " ").title() + " · 速查"

    cjk_path, emoji_path, _ = find_fonts()
    html_doc = build_full_html(files, title)
    css = build_css(cjk_path, emoji_path) + (FLOW_CSS if flow else "")

    font_config = FontConfiguration()
    HTML(string=html_doc, base_url=str(cs_dir)).write_pdf(
        str(output_pdf),
        stylesheets=[CSS(string=css, font_config=font_config)],
        font_config=font_config,
        presentational_hints=True,
    )

    size_kb = output_pdf.stat().st_size // 1024
    print(f"✓ PDF generated: {output_pdf} ({size_kb} KB)", file=sys.stderr)

    check_font_assignment(output_pdf)
    check_sections_self_contained(files)
    check_worked_examples(files)


# ---------- Gate: 每节必须自带本体，不许推给别处 ----------

_DEFER_RE = re.compile(
    r"(详见|见课件|翻课件|不重复|展开在|对比在|推导在|完整.{0,4}在 L\d"
    r"|(?:在|见) \*\*?L\d-\d+|Detail in|see slide)"
)
_ROUTE_RE = re.compile(r"^>\s*(🧭|🗺|⏱)")
_TIP_RE = re.compile(r"^>\s*(⚠️|🎯|💡|✍️|🔑|☕)")


def check_sections_self_contained(files) -> None:
    """默认 PDF 是考场上唯一的纸质参考, 所以每一节都必须自带本体。

    两类失败:
      1. 推诿 —— 用 "详见课件 pXX" / "对比在 L4-17" 代替内容
      2. 空壳 —— 去掉 route 三行与提示块之后, 正文既短又没有表格/公式块
    """
    defer, hollow = [], []
    for _idx, path in files:
        if not re.match(r"^\d+-L", path.name):
            continue  # 路由页不检查
        text = path.read_text(encoding="utf-8")
        for block in re.split(r"^## ", text, flags=re.M)[1:]:
            head = block.split("\n")[0].strip()
            body = block.split("\n", 1)[1] if "\n" in block else ""
            core = "\n".join(l for l in body.split("\n") if not _ROUTE_RE.match(l))
            if _DEFER_RE.search(core):
                defer.append((path.name, head))
            substantive = "".join(
                l for l in core.split("\n") if l.strip() and not _TIP_RE.match(l)
            )
            has_struct = ("|---" in core) or ("```" in core)
            if len(substantive) < 150 and not has_struct:
                hollow.append((path.name, head, len(substantive)))

    if not defer and not hollow:
        print("✓ 自足门禁: 每节均自带本体, 无推诿指向", file=sys.stderr)
        return

    print("✗ 自足门禁 FAIL", file=sys.stderr)
    for name, head in defer:
        print(f"    推诿: [{name}] {head}", file=sys.stderr)
        print("           用「详见课件/见 §X」代替了本体。考场上用户只有这一份 PDF，"
              "把内容写进来。", file=sys.stderr)
    for name, head, n in hollow:
        print(f"    空壳: [{name}] {head} — 正文仅 {n} 字且无表格/公式块", file=sys.stderr)
    sys.exit(1)


# ---------- Gate: worked example 必须是可照抄的三块 ----------

_EX_HEAD_RE = re.compile(r"^### .*\U0001f9ee")


def check_worked_examples(files) -> None:
    """例题是用户考场上照着替换数字的模板, 缺一块就抄不下去。

    三块缺一不可:
      1. **题目** —— 英文原题照抄, 用户要能认出考卷上哪道题对应它
      2. | 符号 | 表 —— 每个已知量配一句中文"这是什么"
      3. | 步  | 表 —— 逐步求解, 不许合并步骤

    另外: 标题里带「练习题」的(来自 tutorial / practice questions),
    还必须有一行「一句话思路」, 否则用户换个数字就不会做了。
    """
    bad = []
    for _idx, path in files:
        if not re.match(r"^\d+-L", path.name):
            continue
        text = path.read_text(encoding="utf-8")
        blocks = re.split(r"(?m)^### ", text)[1:]
        for blk in blocks:
            head = blk.split("\n", 1)[0].strip()
            if not _EX_HEAD_RE.match("### " + head):
                continue
            miss = []
            if "**题目" not in blk:
                miss.append("题目原文")
            if not re.search(r"(?m)^\| 符号 ", blk):
                miss.append("符号表(已知量+中文解释)")
            if not re.search(r"(?m)^\| 步 ", blk):
                miss.append("逐步求解表")
            if "练习题" in head and "一句话思路" not in blk:
                miss.append("一句话思路")
            if miss:
                bad.append((path.name, head, miss))

    if not bad:
        print("\u2713 例题门禁: 题面/符号表/步骤表齐全", file=sys.stderr)
        return

    print("\u2717 例题门禁 FAIL", file=sys.stderr)
    for name, head, miss in bad:
        print(f"    [{name}] {head}", file=sys.stderr)
        print(f"           缺: {', '.join(miss)}", file=sys.stderr)
    print("    例题是照抄模板: 题面让用户认出题型, 符号表让他知道每个数是什么, "
          "步骤表让他逐行替换。", file=sys.stderr)
    sys.exit(1)


# ---------- Gate: emoji 字体不得吃掉正文字符 ----------

def check_font_assignment(pdf_path: Path) -> None:
    """正文的数字/字母若被 emoji 字体渲染, 会排成全角宽度 (CS1234 → CS 1 2 3 4)。

    这是 font stack 里混入系统 emoji 字族名时的典型症状, 肉眼在 PDF 里很难第一时间
    发现, 所以编译完直接扫一遍 span。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ℹ  跳过字体门禁 (未装 PyMuPDF)", file=sys.stderr)
        return

    doc = fitz.open(str(pdf_path))
    offenders = {}
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if "emoji" not in span["font"].lower():
                        continue
                    body = [c for c in span["text"] if c.isascii() and c.isalnum()]
                    if body:
                        offenders.setdefault(span["font"], []).append(span["text"][:40])
    doc.close()

    if not offenders:
        print("✓ 字体门禁: 正文字符未被 emoji 字体接管", file=sys.stderr)
        return

    print("✗ 字体门禁 FAIL: emoji 字体渲染了正文的字母/数字，会排成全角宽度", file=sys.stderr)
    for font, samples in offenders.items():
        print(f"    {font}: {len(samples)} 处，例 {samples[:3]}", file=sys.stderr)
    print("    修法: 从 primary_stack 里去掉系统 emoji 字族名"
          " (Segoe UI Emoji / Noto Color Emoji)，只保留带 unicode-range 的 CourseEmoji",
          file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
