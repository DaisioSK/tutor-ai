"""故事表 md → HTML 卡片：每个表格行一张卡（标签 / 故事 / 技术要点 | 和故事的联系 | 计算样例），左侧幕与集目录。
桌面正文居中加宽，三栏并排（无计算样例的卡两栏；窄屏计算样例落到下一行）；手机版 PDF 三块上下排。
格内写法：`• 项` 并列、`1. 项` 顺序、`∵ / ∴` 递进、`• 名称：解释` 概念、`⚠️ …` 陷阱，其余为段落。
用法：python3 to_html.py <story-table.md> [out.html] [--book <book_dir>] [--pdf]
  --book  从书里取章名（`# 第 N 章 …`）与节名（`## §N.M …`），写进卡片标签；章变时插章名分隔条
  --pdf   另出手机版 PDF（同名 .pdf，110×195mm 单栏；开头可点的幕 / 集目录带页码，侧栏书签分两级）"""
import html
import json
import re
import sys
from pathlib import Path

argv = sys.argv[1:]
book = Path(argv[argv.index("--book") + 1]) if "--book" in argv else None
want_pdf = "--pdf" in argv
pos = [a for k, a in enumerate(argv) if not a.startswith("--") and (k == 0 or argv[k - 1] != "--book")]
src = Path(pos[0])
out = Path(pos[1]) if len(pos) > 1 else src.with_suffix(".html")

CH_NAME, SEC_NAME, SEC_EN = {}, {}, {}
# 名字只用书里有的：章 `# 第 N 章 中文 (English)`、节 `## §N.M 中文 (English)`；有英文原题就并列，不自造、不另译
bi = lambda zh, en: f"{zh} · {en}" if zh and en else zh or en  # noqa: E731
if book:
    for f in sorted(book.glob("[0-9][0-9]-*.md")):
        txt = f.read_text(encoding="utf-8")
        m = re.search(r"^#\s*第\s*(\d+)\s*章\s*(.+?)\s*(?:\(([^)]*)\))?\s*$", txt, re.M)
        if m:
            CH_NAME[int(m.group(1))] = bi(m.group(2).strip(), (m.group(3) or "").strip())
        for a, b, name, en in re.findall(r"^## §(\d+)\.(\d+)\s+(.+?)\s*(?:\(([^)]*)\))?\s*$", txt, re.M):
            SEC_NAME[f"{a}.{b}"] = bi(name.strip(), en.strip())
            SEC_EN[f"{a}.{b}"] = en.strip()


# 课件定位（可选）：<book_dir>/../source-map.json，§N.M → {lecture, scribe, scribe_page, slides:[起,止]}
SRC = {}
if book and (book.parent / "source-map.json").exists():
    SRC = json.loads((book.parent / "source-map.json").read_text(encoding="utf-8"))


def secs_of(where: str) -> list:
    """`在哪` 列里出现的全部 §N.M（含 §1.3–1.5 这种区间）。"""
    out = []
    for a, b, e in re.findall(r"§(\d+)\.(\d+)(?:\s*[–-]\s*(?:\d+\.)?(\d+))?", where):
        out += [f"{a}.{k}" for k in range(int(b), int(e or b) + 1)]
    return out


def pages(rs: list) -> str:
    lo, hi = min(r[0] for r in rs), max(r[1] for r in rs)
    return f"p.{lo}" if lo == hi else f"p.{lo}–{hi}"


def src_card(secs: list) -> str:
    """单张卡，跟在节名后的括号里：L2 Slides p.19–21；无 slides 的讲退到 Scribe 页。"""
    rs = [SRC[s] for s in secs if s in SRC]
    if not rs:
        return ""
    sl = [r["slides"] for r in rs if r.get("slides")]
    return f"L{rs[0]['lecture']} " + (f"Slides {pages(sl)}" if sl
                                      else f"Scribe {pages([[r['scribe_page']] * 2 for r in rs])}，本讲无 slides")


def src_span(secs: list) -> str:
    """集 / 幕标题：L4 Slides p.5–49（同一幕跨讲时列出每讲）。"""
    by = {}
    for s in secs:
        if s in SRC:
            by.setdefault(SRC[s]["lecture"], []).append(SRC[s])
    parts = []
    for lec, rs in by.items():
        sl = [r["slides"] for r in rs if r.get("slides")]
        parts.append(f"L{lec} " + (f"Slides {pages(sl)}" if sl else f"Scribe {pages([[r['scribe_page']] * 2 for r in rs])}"))
    return " · ".join(parts)


def label(where: str) -> str:
    """`**第2章** 卷一 §2.6 · 🧠🎯` → 两行标签：卷 · 第N章 章名 ｜ §N.M 节名 · 记号。"""
    m = re.match(r"^\*\*第(\d+)章\*\*\s*(\S*)\s*(.*?)\s*·\s*(.*)$", where)
    if not m or not book:
        return inline(where)
    ch, vol, secs, marks = int(m.group(1)), m.group(2), m.group(3), m.group(4)
    own = re.search(r"「([^」]+)」", secs)                    # 节名覆盖：§N.M「标准名」替换书里的中文标题，英文原题保留
    names = []
    for a, b, e in re.findall(r"§(\d+)\.(\d+)(?:\s*[–-]\s*(?:\d+\.)?(\d+))?", secs):
        for k in range(int(b), int(e or b) + 1):
            nm = SEC_NAME.get(f"{a}.{k}", "")
            if own:
                nm = bi(own.group(1), SEC_EN.get(f"{a}.{k}", ""))
            names.append(f"§{a}.{k} {nm}".strip())
    part = re.search(r"[（(](\d+/\d+)[）)]", secs)          # 一节拆成几行时的「（1/3）」
    sec_txt = "　".join(names) or secs
    if part:
        sec_txt += f"（{part.group(1)}）"
    loc = src_card(secs_of(secs))
    return (f'<span class=chn>{html.escape(vol)} · 第{ch}章 {html.escape(CH_NAME.get(ch, ""))}</span>'
            f'<span class=secn>{html.escape(sec_txt)}'
            + (f'<span class=loc>（{html.escape(loc)}）</span>' if loc else "")
            + f'</span><span class=mk>{html.escape(marks)}</span>')


def inline(s: str) -> str:
    s = html.escape(s.strip(), quote=False)
    s = s.replace("&lt;br&gt;", "<br>").replace("&lt;br/&gt;", "<br>")
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def bullets(cell: str) -> str:
    """并列 `• x` → <ul>；顺序 `1. x` → <ol>；递进 `∵ x` / `∴ x` → 推理块；其余行 → 段落。
    `• 名称：解释` 的名称加粗。"""
    parts = [p.strip() for p in re.split(r"<br\s*/?>", cell) if p.strip()]
    blocks = []                                   # [(kind, [text])]，kind ∈ p / ul / ol / why
    for p in parts:
        mo = re.match(r"^(\d+)[.、)]\s+(.*)$", p)
        if blocks and blocks[-1][0] == "drv" and mo:  # 推导：后面连着的 1. 2. … 归进推导方块
            blocks[-1][1].append(mo.group(2))
            continue
        if re.match(r"^推导[：:]", p):                # 推导 → 可折叠的小方块（选看）
            kind, txt = "drv", re.sub(r"^推导[：:]\s*", "", p)
            blocks.append((kind, [txt] if txt else []))
            continue
        if "↔" in p and len(p) < 120:                # 映射：意象 ↔ 概念 → 对照表
            kind, txt = "map", p.lstrip("•-· ").strip()
        elif p.startswith(("•", "- ", "· ")):
            kind, txt = "ul", p.lstrip("•-· ").strip()
        elif mo:
            kind, txt = "ol", mo.group(2)
        elif p.startswith(("∵", "∴")):
            kind, txt = "why", p
        else:
            kind, txt = "p", p
        if kind != "p" and blocks and blocks[-1][0] == kind:
            blocks[-1][1].append(txt)
        else:
            blocks.append((kind, [txt]))

    def li(it):
        m = re.match(r"^([^：:]{1,14})[：:]\s*(.*)$", it)
        if m and not re.search(r"[=＝]", m.group(1)):
            return f"<li><span class=k>{inline(m.group(1))}</span>：{inline(m.group(2))}</li>"
        return f"<li>{inline(it)}</li>"
    h = ""
    for kind, xs in blocks:
        if kind == "p":
            cls = lambda x: ("warn" if x.startswith("⚠") else "exam" if x.startswith("🎯") else  # noqa: E731
                             "lead" if x.startswith("💡") else "link" if x.startswith("↩") else "")
            h += "".join(f"<p class={cls(x)}>{inline(x)}</p>" if cls(x) else f"<p>{inline(x)}</p>" for x in xs)
        elif kind == "map":
            trs = []
            for x in xs:
                a, _, b = x.partition("↔")
                trs.append(f"<tr><td>{inline(a)}</td><td class=arr>↔</td><td>{inline(b)}</td></tr>")
            h += "<table class=map>" + "".join(trs) + "</table>"
        elif kind == "drv":
            h += ("<details class=drv><summary>推导</summary><ol>"
                  + "".join(f"<li>{inline(x)}</li>" for x in xs) + "</ol></details>")
        elif kind == "why":
            h += "<div class=chain>" + "".join(
                f'<div class="{"so" if x.startswith("∴") else "be"}"><b>{x[0]}</b>{inline(x[1:])}</div>'
                for x in xs) + "</div>"
        else:
            h += f"<{kind}>" + "".join(li(x) for x in xs) + f"</{kind}>"
    return h


def cells(row: str):
    return [c.strip() for c in re.split(r"(?<!\\)\|", row.strip())[1:-1]]


lines = src.read_text(encoding="utf-8").split("\n")


def span_below(k: int, stop: tuple) -> str:
    """第 k 行标题之下、到下一个同级或更高级标题之前，所有卡片的课件页段。"""
    secs = []
    for ln in lines[k + 1:]:
        if ln.startswith(stop):
            break
        if ln.startswith("| **第"):
            secs += secs_of(cells(ln)[0])
    return src_span(secs) if SRC else ""


def heading(tag: str, k: int, text: str, stop: tuple) -> tuple:
    """目录与书签只放标题本身；课件页段只出现在正文标题下。"""
    loc = span_below(k, stop)
    return (f'<{tag} id="s{eid}" data-bm="{html.escape(text)}">{inline(text)}'
            + (f'<span class=hloc>📍 {html.escape(loc)}</span>' if loc else "") + f"</{tag}>"), text


body, toc, title = [], [], "课程故事"
i, eid, last_ch = 0, 0, None
while i < len(lines):
    ln = lines[i]
    if ln.startswith("# "):
        title = ln[2:].strip()
        body.append(f"<h1>{inline(title)}</h1>")
    elif ln.strip() == "<!-- md -->":            # 前瞻章节等普通 Markdown 块：列表、表格、引用照常渲染
        j = lines.index("<!-- /md -->", i)
        import markdown
        block = markdown.markdown("\n".join(lines[i + 1:j]), extensions=["tables"])

        def _hid(m):
            global eid
            eid += 1
            text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            text = re.sub(r"（L[^）]*）$", "", text).strip()   # 目录与书签不放课件页
            toc.append(("act" if m.group(1) == "2" else "ep", eid, html.unescape(text)))
            return f'<h{m.group(1)} id="s{eid}" data-bm="{text}">{m.group(2)}</h{m.group(1)}>'
        body.append('<div class=md>' + re.sub(r"<h([23])>(.*?)</h\1>", _hid, block) + '</div>')
        i = j + 1
        continue
    elif ln.startswith("## "):
        eid += 1
        h, full = heading("h2", i, ln[3:].strip(), ("# ", "## "))
        body.append(h)
        toc.append(("act", eid, full))
    elif ln.startswith("### "):
        eid += 1
        h, full = heading("h3", i, ln[4:].strip(), ("# ", "## ", "### "))
        body.append(h)
        toc.append(("ep", eid, full))
    elif ln.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            rows.append(lines[i])
            i += 1
        head = cells(rows[0])
        for r in rows[2:]:
            c = cells(r) + [""] * 5
            where, story, tech, why, calc = c[0], c[1], c[2], c[3], c[4]
            n = len(head)
            calc = "" if calc in ("", "—", "-") else calc
            mc = re.match(r"^\*\*第(\d+)章\*\*", where)
            if book and mc and int(mc.group(1)) != last_ch:
                last_ch = int(mc.group(1))
                body.append(f'<div class=chap>第 {last_ch} 章　{html.escape(CH_NAME.get(last_ch, ""))}</div>')
            body.append(
                '<article class=card>'
                f'<div class=where>{label(where)}</div>'
                f'<div class=story>{bullets(story)}</div>'
                f'<div class="cols{" c3" if calc else ""}">'
                f'<section class=tech><h4>{inline(head[2]) if n > 2 else "技术要点"}</h4>{bullets(tech)}</section>'
                + (f'<section class=why><h4>{inline(head[3])}</h4>{bullets(why)}</section>' if n > 3 and why else "")
                + (f'<section class=calc><h4>{inline(head[4]) if n > 4 else "计算样例"}</h4>{bullets(calc)}</section>' if calc else "")
                + '</div></article>')
        continue
    elif ln.strip():
        para = [ln.strip()]
        while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith(("#", "|")):
            i += 1
            para.append(lines[i].strip())
        body.append(f"<p class=narr>{inline(' '.join(para))}</p>")
    i += 1

nav = "".join(
    f'<a class="{k}" href="#s{n}">{html.escape(re.sub(r"[（(].*?[）)]", "", t) if k == "act" else t)}</a>'
    for k, n, t in toc)

CSS = """
:root{--bg:#fbfaf7;--fg:#1f2328;--mut:#5d6470;--card:#fff;--line:#e4e1d8;--acc:#b45309;--tag:#f3efe6;
--tech:#eef5ff;--why:#f2f8ef;--calc:#fdf6e9;--k:#1d4ed8;--k2:#15803d}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15171a;--fg:#e6e6e6;--mut:#9aa1ab;
--card:#1d2024;--line:#30343a;--acc:#f59e0b;--tag:#2a2d31;--tech:#1a2432;--why:#1b2a1e;--calc:#2a2418;--k:#93c5fd;--k2:#86efac}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15.5px/1.7 "PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif}
nav{position:fixed;top:0;left:0;bottom:0;width:250px;overflow:auto;padding:18px 14px;border-right:1px solid var(--line);font-size:13px}
nav a{display:block;color:var(--mut);text-decoration:none;padding:3px 6px;border-radius:4px}
nav a.act{color:var(--fg);font-weight:700;margin-top:10px}
nav a:hover{background:var(--tag)}
main{margin-left:250px;padding:24px 32px 80px}
main>.in{max-width:1640px;margin:0 auto}
h1{font-size:26px;margin:4px 0 12px}
h2{font-size:21px;margin:40px 0 6px;padding-bottom:6px;border-bottom:2px solid var(--acc)}
h3{font-size:17px;margin:28px 0 4px;color:var(--acc)}
p.narr{margin:8px 0 12px;color:var(--fg)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:12px 0 16px;overflow:hidden}
.where{background:var(--tag);color:var(--mut);font-size:12.5px;padding:5px 14px;font-weight:600;letter-spacing:.02em}
.story{padding:10px 16px 6px;font-size:16px}
.story p{margin:0 0 4px}
.story ul{margin:2px 0 4px;padding-left:1.2em}
.story p{max-width:68em}
.cols{display:grid;grid-template-columns:1.25fr 1fr;gap:0;border-top:1px solid var(--line)}
.cols.c3{grid-template-columns:1.2fr 1fr .9fr}
.cols section{padding:8px 14px 10px;font-size:14px}
.tech{background:var(--tech)}.why{background:var(--why);border-left:1px solid var(--line)}
.calc{background:var(--calc);border-left:1px solid var(--line)}.calc .k{color:var(--acc);font-weight:700}
@media (max-width:1280px){.cols.c3{grid-template-columns:1.25fr 1fr}.cols.c3 .calc{grid-column:1/-1;border-left:0;border-top:1px solid var(--line)}}
h4{margin:0 0 4px;font-size:12px;color:var(--mut);font-weight:700;letter-spacing:.04em}
.cols ul,.cols ol{margin:0 0 4px;padding-left:1.25em}.cols li{margin:2px 0}.story ol{margin:2px 0 4px;padding-left:1.4em}
.cols p{margin:0 0 4px}
.tech .k{color:var(--k);font-weight:700}.why .k{color:var(--k2);font-weight:700}
code{font-family:Consolas,monospace;font-size:.92em}
table.map{border-collapse:collapse;width:100%;margin:2px 0 6px;font-size:.95em}table.map td{padding:1px 4px;vertical-align:top;border-bottom:1px dotted var(--line)}table.map td:first-child{color:var(--acc);width:44%}table.map td.arr{color:var(--mut);width:1.4em;text-align:center}
.cols p.warn{background:rgba(220,38,38,.08);border-left:3px solid #dc2626;padding:2px 6px;border-radius:3px;margin:4px 0}
.cols p.lead{font-weight:700;margin:0 0 4px}
.cols p.link{color:var(--mut);font-size:.95em;border-bottom:1px dashed var(--line);padding-bottom:4px;margin:0 0 6px}
.cols details.drv{background:rgba(29,78,216,.06);border-left:3px solid var(--k);padding:2px 6px;border-radius:3px;margin:4px 0}
.cols details.drv summary{cursor:pointer;color:var(--k);font-weight:700;font-size:.95em}
.cols details.drv ol{margin:2px 0 2px;padding-left:1.4em}
.cols p.exam{background:rgba(124,58,237,.08);border-left:3px solid #7c3aed;padding:2px 6px;border-radius:3px;margin:4px 0}
.chain{margin:2px 0 6px;padding-left:2px}.chain div{padding-left:1.35em;text-indent:-1.35em;margin:1px 0}
.chain b{display:inline-block;width:1.35em;text-indent:0;color:var(--acc)}.chain .so{padding-left:2.1em}.chain .so b{color:var(--k2)}
@media (max-width:860px){nav{display:none}main{margin-left:0;padding:16px}.cols,.cols.c3{grid-template-columns:1fr}.why{border-left:0;border-top:1px solid var(--line)}}
.where .chn{display:block;color:var(--fg);font-size:13px}.where .secn{margin-right:.6em}.where .mk{white-space:nowrap}
.where .loc{color:var(--acc);font-weight:700}
h2 .hloc,h3 .hloc{display:block;font-size:12.5px;font-weight:500;color:var(--mut);margin-top:2px}
.md p{margin:6px 0 9px}.md ul,.md ol{margin:4px 0 8px;padding-left:1.3em}.md li{margin:3px 0}
.md blockquote{margin:8px 0;padding:6px 12px;background:var(--tag);border-left:3px solid var(--acc);border-radius:4px}.md blockquote p{margin:2px 0}
.md table{border-collapse:collapse;width:100%;margin:8px 0;font-size:.92em}.md td,.md th{border:1px solid var(--line);padding:4px 6px;vertical-align:top}.md th{background:var(--tag)}
.md hr{border:0;border-top:1px dashed var(--line);margin:16px 0}
.md h4{margin:18px 0 6px;padding-top:8px;border-top:1px solid var(--line);font-size:1.08em;color:var(--acc);letter-spacing:0}
.chap{margin:22px 0 4px;font-size:14px;font-weight:700;color:var(--mut);border-bottom:1px dashed var(--line);padding-bottom:3px}
@media print{nav{display:none}main{margin:0;max-width:none}.card{break-inside:avoid}}
"""
# 手机版 PDF：窄页单栏、字号放大、两栏改上下、浅色
PDF_CSS = """
@page{size:110mm 195mm;margin:6mm 5mm 8mm;@bottom-center{content:counter(page);font-size:8pt;color:#999}}
:root{--bg:#fff;--fg:#1f2328;--mut:#5d6470;--card:#fff;--line:#e4e1d8;--acc:#b45309;--tag:#f3efe6;
--tech:#eef5ff;--why:#f2f8ef;--calc:#fdf6e9;--k:#1d4ed8;--k2:#15803d}
body{font-size:10.5pt;line-height:1.6;background:#fff}nav{display:none}main{margin:0;padding:0;max-width:none}main>.in{max-width:none}
h1{font-size:15pt}h2{font-size:13pt;break-before:page}h3{font-size:11.5pt;break-after:avoid}
.chap{break-after:avoid}.card{break-inside:auto;margin:8px 0 10px}.where{break-after:avoid}
p{orphans:2;widows:2}.story{break-inside:auto}
.story{font-size:10.5pt;padding:7px 10px 4px}.cols{display:block}.cols section{padding:6px 10px 7px;font-size:9.8pt}
.why,.calc{border-left:0;border-top:1px solid var(--line)}.cols li,.chain div{break-inside:avoid}
"""
# PDF 开头的跳转目录：幕 / 集，可点，带页码（weasyprint target-counter）；侧栏书签由 h2/h3 自动生成
PDF_TOC = ('<section class=ptoc><h1>目录</h1>' + "".join(
    f'<a class="{k}" href="#s{n}">{html.escape(t)}</a>' for k, n, t in toc) + '</section>')
PDF_CSS += """
.ptoc{break-after:page}.ptoc h1{font-size:15pt;margin:0 0 8px}
.ptoc a{display:block;color:#1f2328;text-decoration:none;font-size:9.6pt;padding:1.5px 0 1.5px 1.2em}
.ptoc a.act{font-weight:700;font-size:10.5pt;padding:7px 0 2px 0}
.ptoc a::after{content:leader('.') target-counter(attr(href), page);color:#888}
h2{bookmark-level:1;bookmark-label:attr(data-bm)}h3{bookmark-level:2;bookmark-label:attr(data-bm)}h1,h4,.ptoc h1{bookmark-level:none}
"""
doc = lambda extra="", pre="": f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}{extra}</style></head><body><nav>{nav}</nav><main><div class=in>{pre}{''.join(body)}</div></main></body></html>"""  # noqa: E731
out.write_text(doc(), encoding="utf-8")
print(out, sum(1 for b in body if b.startswith("<article")), "cards")
if want_pdf:
    import weasyprint
    pdf = out.with_suffix(".pdf")
    weasyprint.HTML(string=doc(PDF_CSS, PDF_TOC), base_url=str(out.parent)).write_pdf(pdf)
    print(pdf)
