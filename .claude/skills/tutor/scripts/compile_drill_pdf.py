#!/usr/bin/env python3
"""
练习题逐题拆解：一份 MD → 一份 PDF（无封面、无目录），公式、图、提示框沿用 compile_story_pdf 的渲染。

用法:
    python3 compile_drill_pdf.py <file.md> [more.md ...]
图片路径按 MD 所在目录解析；PDF 写在 MD 旁边，同名。

和讲义渲染的三处差别（练习题里全是题目自己的东西）：
  - 行内 $...$ 一律当公式（讲义渲染器为了避开 "$5" 这类金额，会放过单个字母和纯数字）；
  - 标题末尾的 {…}（如条件集合 {Cancer, Bronchitis}）不当 attr_list 吞掉；
  - bmatrix / pmatrix 改写成带括号的 matrix；
  - 按标题自动套彩色面板（英文原题 / 中文解释 / 考点分析 / 易错点 / QA / 范式；每一小问的 图 / 中文拆解 / 思路 / 傻瓜拆解（完全版）/ English solution · 中文对照）；
  - 图注标签是"原题图"，不是"自绘"；题目来源行用普通引用框，不是"课件外延伸"框。
"""
import re
import sys
from pathlib import Path

from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

sys.path.insert(0, str(Path(__file__).parent))
from compile_story_pdf import build_css, find_cjk_font, md_to_html, tag_blockquote_roles  # noqa: E402

INLINE_DOLLAR = re.compile(r"(?<![\$\\])\$(?!\$)([^\$\n]+?)(?<!\\)\$(?!\$)")
ALT_RE = re.compile(r"!\[([^\]]*)\]")
TEX_PLAIN = {r"\to": "→", r"\rightarrow": "→", r"\leftarrow": "←", r"\mid": "|", r"\perp": "⊥", r"\ne": "≠",
             r"\le": "≤", r"\ge": "≥", r"\times": "×", r"\mu": "μ", r"\sigma": "σ", r"\pi": "π", r"\theta": "θ"}


def plain_math(alt: str) -> str:
    """图注不经过公式渲染（会露出 HTML 源码）：把 $...$ 里的常见命令换成 Unicode，去掉 $ 和花括号。"""
    def conv(m):
        t = m.group(1)
        for k, v in sorted(TEX_PLAIN.items(), key=lambda kv: -len(kv[0])):
            t = t.replace(k, v)
        return re.sub(r"\\[a-zA-Z]+|[{}]", "", t)
    return re.sub(r"\$+([^$]*)\$+", conv, alt).replace("\\(", "").replace("\\)", "")


EXTRA_CSS = """
figure.fig-own figcaption::before { content: "原题图"; }
figure figcaption:empty { display: none; }   /* 无图注的图（如范式例图）不显示"原题图"标签 */
figure.fig img, .pn img { width: auto !important; max-width: 92%; max-height: 34vh; height: auto; display: block; margin: 0 auto; }
.pn { border-radius: 6px; padding: 0.55em 0.85em 0.6em; margin: 0.9em 0; border-left: 4px solid; }
.pn > h2, .pn > h4 { margin-top: 0.1em; border: none; padding: 0; background: none; }
.pn > h2 { font-size: 13pt; }
.pn > h4 { font-size: 10.5pt; margin-bottom: 0.3em; }
.pn-q     { background: #f3f5f8; border-color: #7a8794; }
.pn-cn    { background: #eef5fc; border-color: #4a86c5; }
.pn-kp    { background: #fff8e8; border-color: #d9a227; }
.pn-trap  { background: #fdf0ef; border-color: #d0574b; }
.pn-fig   { background: #ffffff; border-color: #b8c2cc; border-left-width: 2px; }
.pn-break { background: #eef5fc; border-color: #4a86c5; }
.pn-idea  { background: #eef8f0; border-color: #3f9a5a; }
.pn-walk  { background: #fff8ee; border-color: #d9822b; }   /* 傻瓜拆解（完全版）：思路之后，把整题从零算一遍 */
.pn-sol   { background: #f6f4fa; border-color: #7b68a6; }
.pn-qa    { background: #eef7f7; border-color: #2f8f8f; }
.pn-pd    { background: #fbf6ec; border-color: #9a6b1f; border-left-width: 6px; }
.pn-pd table { width: 100%; font-size: 0.92em; }
.pn-pd td:first-child { white-space: nowrap; }
td .math-inline { white-space: normal; }   /* 表格里的长公式允许折行，否则冲出格子 */
/* 范式里的例子：另起一行、灰色小字，和步骤分开 */
.pn-pd .ex { display: block; margin: 0.2em 0 0.45em; padding: 0.15em 0.65em; border-left: 2px solid #d8c39a;
             background: #fffcf5; color: #5b6470; font-size: 0.9em; }
/* 规则下面紧跟的直觉：绿色，和灰色例子区分 */
.pn-pd .gist { display: block; color: #2f7a4a; font-size: 0.92em; margin: 0.05em 0 0.3em; }
.pn-sol p.zh { color: #4b5560; margin-top: -0.2em; }
h3 { margin-top: 1.4em; padding: 0.3em 0.6em; background: #2f4b66; color: #fff; border-radius: 4px; }
"""
# 标题 → 面板：二级标题按节名，四级标题（每一小问里的四段）按关键词
H2_PANEL = [("英文原题", "q"), ("中文解释", "cn"), ("考点分析", "kp"), ("通用思路", "idea"), ("易错", "trap"), ("QA", "qa"), ("范式", "pd")]
H4_PANEL = [("傻瓜", "walk"), ("图", "fig"), ("拆解", "break"), ("思路", "idea"), ("English", "sol"), ("解答", "sol")]
HEAD_RE = re.compile(r"(?=<h[1-6][\s>])")


def panelize(html: str) -> str:
    """按标题层级把正文包进彩色面板：h2 面板到下一个 h2 为止，h4 面板到下一个 h2/h3/h4 为止。"""
    out, open2, open4 = [], False, False
    for chunk in HEAD_RE.split(html):
        m = re.match(r"<h([1-6])[^>]*>(.*?)</h\1>", chunk, re.S)
        if m:
            lvl, title = int(m.group(1)), re.sub(r"<[^>]+>", "", m.group(2))
            if lvl <= 4 and open4:
                out.append("</div>"); open4 = False
            if lvl <= 2 and open2:
                out.append("</div>"); open2 = False
            if lvl == 2:
                key = next((k for w, k in H2_PANEL if w in title), None)
                if key:
                    out.append(f'<div class="pn pn-{key}">'); open2 = True
            elif lvl == 4:
                key = next((k for w, k in H4_PANEL if w in title), "fig")
                out.append(f'<div class="pn pn-{key}">'); open4 = True
        out.append(chunk)
    out += ["</div>"] * (open4 + open2)
    return "".join(out)


def prepare(md: str) -> str:
    out, fenced = [], False
    for line in md.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            line = ALT_RE.sub(lambda m: "![" + plain_math(m.group(1)) + "]", line)
            line = INLINE_DOLLAR.sub(lambda m: r"\(" + m.group(1) + r"\)", line)
            if line.startswith("#") and line.rstrip().endswith("}"):
                line = line.rstrip() + "​"
            line = line.replace("> 📍 来源", "> 🗂️ 来源")
        out.append(line)
    md = "\n".join(out)
    # bmatrix / pmatrix 渲染器不画括号：改写成 \left[ matrix \right]
    for env, l, r in (("bmatrix", "[", "]"), ("pmatrix", "(", ")")):
        md = md.replace(rf"\begin{{{env}}}", rf"\left{l}\begin{{matrix}}").replace(rf"\end{{{env}}}", rf"\end{{matrix}}\right{r}")
    return md


def compile_one(md_path: Path, css: str) -> Path:
    html = panelize(tag_blockquote_roles(md_to_html(prepare(md_path.read_text(encoding="utf-8")))))
    html = re.sub(r"<p>↳\s*", '<p class="zh">↳ ', html)   # 英文解答下一行的中文对照
    html = re.sub(r"例：(.*?)(?=</li>|</p>)", r'<span class="ex">例：\1</span>', html, flags=re.S)  # 只在范式面板里另起一行
    html = re.sub(r"直觉：(.*?)(?=</li>|</p>)", r'<span class="gist">直觉：\1</span>', html, flags=re.S)  # 和规则同一行并列
    doc = f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"></head><body><section class="first">{html}</section></body></html>'
    out = md_path.with_suffix(".pdf")
    fc = FontConfiguration()
    HTML(string=doc, base_url=str(md_path.parent)).write_pdf(
        str(out), stylesheets=[CSS(string=css + EXTRA_CSS, font_config=fc)], font_config=fc, presentational_hints=True)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    css = build_css(*find_cjk_font())
    for arg in sys.argv[1:]:
        out = compile_one(Path(arg).resolve(), css)
        print(f"✓ {out} ({out.stat().st_size // 1024} KB)")
