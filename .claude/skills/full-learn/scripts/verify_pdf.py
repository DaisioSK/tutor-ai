#!/usr/bin/env python3
"""
verify_pdf.py — 成品 PDF 门禁（render 理论 5「源码门禁看不见成品」的第二层）。

用法:
    python3 verify_pdf.py output/<课>/full-learn/book.pdf [--book output/<课>/full-learn/book]

book/ 默认取 PDF 同级的 book/；PDF 实际包含哪些 MD 从 PDF 元数据 keywords 读
（compile_story_pdf.py 写入 files=…; treefig=…; skelfig=…），所以单章预览 book-chNN.pdf、
分卷册 book-vol<K>.pdf / book-map.pdf 也能单独验（死链检查同样适用：册外引用应已降为纯文本）。
卷串讲 NNv-*.md（锚点 syn-NN）与总纲 98-map.md（锚点 map）各要一个一级书签、一个目录条目、一个命名目标。

检查（audit 脚本注册表 verify_pdf.py#…）:
  text_layer       每页都有文本层；整页只剩一个标题 → WARN
  page_size        全部 A5 竖版；横版只允许科技树页
  bookmarks        PDF 书签含每章（h1）与每节（§N.M）
  links            内链全部落到存在的目标；ch-N / sec-N-M / front / back 都是命名目标；
                   MD 里章号、节号无重复；目录页链接数 ≥ 章 + 节数
  text_residue     文本层无 `[^`、`<!--`、机读注释、mermaid 占位；LaTeX 源码残留 WARN
  figure_chips     PDF 中大图数 = MD 引用的图数 + 科技树图数；"课件原图" chip 数 = alt 含
                   「课件 <短名> p<N>」的引用数；"自绘" chip 同理
  overflow         任何文字 span 的 x1 > 页宽 − 8pt
  font_assignment  中文字符都落在 CJK 字体；数字与拉丁字母不落在 emoji 字体
  fresh            PDF 修改时间 ≥ 所含 book/*.md 的最新修改时间

输出 INFO / WARN / FAIL，末行 `结果: PASS/FAIL (n fail, m warn)`，任一 FAIL 退出码 1。
依赖: pymupdf（pip install --user --break-system-packages pymupdf）
"""
import argparse
import re
import sys
from pathlib import Path

A5 = (419.53, 595.28)
TOL = 1.5
CJK_FONT_HINTS = ("coursecjk", "yahei", "simhei", "simsun", "notosanscjk", "notoserifcjk", "sourcehan",
                  "wenquanyi", "wqy", "uming", "ukai", "pingfang", "hiragino", "heiti", "songti")
SLIDE_ALT_RE = re.compile(r"课件\s*[A-Za-z][\w.\-]*\s*p\s*\d")
IMG_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
CH_H1_RE = re.compile(r"^#\s+第\s*(\d+)\s*章", re.M)
SEC_RE = re.compile(r"^##\s+§\s*(\d+)\.(\d+)", re.M)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ALNUM_RE = re.compile(r"[0-9A-Za-z]")


class Report:
    def __init__(self):
        self.rows = []

    def info(self, check, msg):
        self.rows.append(("INFO", check, msg, []))

    def warn(self, check, msg, detail=None):
        self.rows.append(("WARN", check, msg, detail or []))

    def fail(self, check, msg, detail=None):
        self.rows.append(("FAIL", check, msg, detail or []))

    def emit(self, name) -> int:
        print(f"# verify_pdf — {name}\n")
        icon = {"INFO": "ℹ️ ", "WARN": "⚠️  WARN", "FAIL": "❌ FAIL"}
        for lvl in ("INFO", "WARN", "FAIL"):
            for l, check, msg, detail in self.rows:
                if l != lvl:
                    continue
                print(f"{icon[l]} [{check}] {msg}")
                for d in detail[:20]:
                    print(f"      {d}")
                if len(detail) > 20:
                    print(f"      …… 另有 {len(detail) - 20} 行")
        nf = sum(1 for r in self.rows if r[0] == "FAIL")
        nw = sum(1 for r in self.rows if r[0] == "WARN")
        print(f"\n结果: {'PASS' if not nf else 'FAIL'} ({nf} fail, {nw} warn)")
        return 1 if nf else 0


def _strip_fences(md: str) -> str:
    out, inf = [], False
    for ln in md.split("\n"):
        if re.match(r"^\s*(```|~~~)", ln):
            inf = not inf
            out.append("")
            continue
        out.append("" if inf else ln)
    return "\n".join(out)


SYN_FILE_RE = re.compile(r"^(\d{2})v-.+\.md$")


def expected_from_md(md_files):
    """parts: 卷串讲 / 总纲卷 [(锚点, 书签前缀正则, 文件名)] —— 各占一个一级书签、一个目录条目、一个命名目标。"""
    exp = {"chapters": [], "sections": [], "slide": 0, "own": 0, "images": 0,
           "dup": [], "files": md_files, "parts": []}
    seen_ch, seen_sec = set(), set()
    for f in md_files:
        md = _strip_fences(f.read_text(encoding="utf-8"))
        sm = SYN_FILE_RE.match(f.name)
        if sm:
            exp["parts"].append((f"syn-{int(sm.group(1))}", r"\s*第\s*\S+?\s*卷串讲", f.name))
        elif f.name == "98-map.md":
            exp["parts"].append(("map", r"\s*总纲", f.name))
        for m in CH_H1_RE.finditer(md):
            n = int(m.group(1))
            if n in seen_ch:
                exp["dup"].append(f"ch-{n}（{f.name}）")
            seen_ch.add(n)
            exp["chapters"].append(n)
        for m in SEC_RE.finditer(md):
            k = (int(m.group(1)), int(m.group(2)))
            if k in seen_sec:
                exp["dup"].append(f"sec-{k[0]}-{k[1]}（{f.name}）")
            seen_sec.add(k)
            exp["sections"].append(k)
        for alt, _src in IMG_MD_RE.findall(md):
            exp["images"] += 1
            if SLIDE_ALT_RE.search(alt):
                exp["slide"] += 1
            elif alt.strip().startswith("自绘"):
                exp["own"] += 1
    return exp


def page_body_lines(text: str):
    """去掉页眉面包屑和页脚 'N / M' 后的正文行。"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    lines = [l for l in lines if not re.fullmatch(r"\d+\s*/\s*\d+", l)]
    return lines


def run(pdf_path, book_dir=None) -> int:
    try:
        import fitz
    except ImportError:
        print("✗ 缺依赖 pymupdf: pip install --user --break-system-packages pymupdf")
        return 2
    pdf_path = Path(pdf_path).resolve()
    book_dir = Path(book_dir).resolve() if book_dir else pdf_path.parent / "book"
    rep = Report()
    doc = fitz.open(str(pdf_path))

    # ---------- 所含文件 ----------
    kw = (doc.metadata or {}).get("keywords", "") or ""
    m = re.search(r"files=([^;]*)", kw)
    names = [n for n in (m.group(1).split("|") if m else []) if n]
    treefig = int((re.search(r"treefig=(\d+)", kw) or [0, 0])[1])
    skelfig = int((re.search(r"skelfig=(\d+)", kw) or [0, 0])[1])   # 骨架图同样不是课件原图
    if names:
        md_files = [book_dir / n for n in names if (book_dir / n).exists()]
        missing = [n for n in names if not (book_dir / n).exists()]
        if missing:
            rep.warn("fresh", f"PDF 元数据列出的 MD 在 {book_dir} 找不到: {', '.join(missing)}")
    else:
        md_files = sorted(book_dir.glob("[0-9][0-9]-*.md"))
        rep.warn("links", "PDF 元数据没有 files=…（不是 compile_story_pdf.py 编的？），按 book/ 全部 MD 核对")
    exp = expected_from_md(md_files)
    rep.info("text_layer", f"{doc.page_count} 页 · 所含 MD {len(md_files)} 个 · "
             f"{len(exp['chapters'])} 章 {len(exp['sections'])} 节")

    texts = [doc[i].get_text() for i in range(doc.page_count)]
    full = "\n".join(texts)

    # ---------- page_size ----------
    bad = []
    for i, pg in enumerate(doc):
        w, h = pg.rect.width, pg.rect.height
        portrait = abs(w - A5[0]) < TOL and abs(h - A5[1]) < TOL
        landscape = abs(w - A5[1]) < TOL and abs(h - A5[0]) < TOL
        if portrait:
            continue
        if landscape and "科技树" in texts[i]:
            continue
        bad.append(f"p{i + 1}: {w:.1f} × {h:.1f} pt")
    if bad:
        rep.fail("page_size", f"{len(bad)} 页不是 A5 竖版（横版只允许科技树页）", bad)
    else:
        rep.info("page_size", "全部 A5（科技树页横版）")

    # ---------- text_layer ----------
    empty = [f"p{i + 1}" for i, t in enumerate(texts) if not t.strip()]
    if empty:
        rep.fail("text_layer", f"{len(empty)} 页没有文本层（空白页或整页成图）", empty)
    lonely = []
    for i, t in enumerate(texts):
        body = page_body_lines(t)
        if doc[i].get_image_info():
            continue
        if 0 < len(body) <= 2 and i not in (0, doc.page_count - 1) and len("".join(body)) < 40:
            lonely.append(f"p{i + 1}: {' / '.join(body)[:60]}")
    if lonely:
        rep.warn("text_layer", f"{len(lonely)} 页几乎只剩一行（整页只剩标题？打开看一眼）", lonely)

    # ---------- bookmarks ----------
    toc = doc.get_toc(simple=True)
    titles = [t for _lvl, t, _p in toc]
    miss = []
    for n in exp["chapters"]:
        if not any(re.match(rf"\s*第\s*{n}\s*章", t) for _l, t, _p in toc if _l == 1):
            miss.append(f"第 {n} 章（level 1）")
    for n, mm in exp["sections"]:
        if not any(re.match(rf"\s*§\s*{n}\.{mm}\b", t) for t in titles):
            miss.append(f"§{n}.{mm}")
    for _anchor, pat, fname in exp["parts"]:
        if not any(re.match(pat, t) for _l, t, _p in toc if _l == 1):
            miss.append(f"{fname} 的标题（level 1）")
    if not toc:
        rep.fail("bookmarks", "PDF 没有书签")
    elif miss:
        rep.fail("bookmarks", f"书签缺 {len(miss)} 项", miss)
    else:
        rep.info("bookmarks", f"书签 {len(toc)} 条，章节齐全")

    # ---------- links ----------
    try:
        named = doc.resolve_names()
    except Exception:  # noqa: BLE001
        named = None
    if exp["dup"]:
        rep.fail("links", "MD 里章号/节号重复，锚点会撞", exp["dup"])
    if named is not None:
        need = [f"ch-{n}" for n in exp["chapters"]] + [f"sec-{n}-{m}" for n, m in exp["sections"]]
        need += [a for a, pfx in (("front", "00-"), ("back", "99-"))
                 if any(f.name.startswith(pfx) for f in md_files)]
        need += [a for a, _pat, _f in exp["parts"]]
        lost = [a for a in need if a not in named]
        if lost:
            rep.fail("links", f"{len(lost)} 个锚点不是 PDF 命名目标", lost)
    broken, n_int, toc_links = [], 0, 0
    # 目录跨多页时只有首页带"目录"字样；续页以页码列开头（抽出的文本先是一串数字）
    in_toc = [False] * doc.page_count
    for i in range(doc.page_count):
        head = texts[i][:200]
        in_toc[i] = "目录" in head or (i > 0 and in_toc[i - 1] and head.lstrip()[:1].isdigit())
    for i, pg in enumerate(doc):
        for ln in pg.get_links():
            k = ln.get("kind")
            if k == fitz.LINK_GOTO:
                n_int += 1
                if not (0 <= ln.get("page", -1) < doc.page_count):
                    broken.append(f"p{i + 1}: → page {ln.get('page')}")
            elif k == fitz.LINK_NAMED:
                n_int += 1
                dest = ln.get("nameddest") or ln.get("name")
                if named is not None and dest not in named:
                    broken.append(f"p{i + 1}: → #{dest}")
            elif k == fitz.LINK_URI and (ln.get("uri") or "").endswith("#"):
                broken.append(f"p{i + 1}: 空链接（MD 链接没解析到书内目标）")
            if in_toc[i] and k in (fitz.LINK_GOTO, fitz.LINK_NAMED):
                toc_links += 1
    if broken:
        rep.fail("links", f"{len(broken)} 条内链落空", broken)
    # 目录条目：每章、每节各一条，卷串讲 / 总纲各一条（其不编号小节只进书签、不进目录）
    need_toc = len(exp["chapters"]) + len(exp["sections"]) + len(exp["parts"])
    if toc_links < need_toc:
        rep.fail("links", f"目录页可点条目 {toc_links} < 章 + 节 + 卷串讲/总纲 {need_toc}")
    rep.info("links", f"内链 {n_int} 条（目录页 {toc_links} 条），全部有目标" if not broken else
             f"内链 {n_int} 条")

    # ---------- text_residue ----------
    res = []
    for pat, why in ((r"\[\^", "脚注源码 [^…]"), (r"<!--", "HTML 注释"), (r"nodes:\s*N-\d", "机读注释"),
                     (r"MERMAIDBLOCK", "mermaid 占位"), (r"\$\$", "数学界符 $$")):
        for i, t in enumerate(texts):
            for mm in re.finditer(pat, t):
                res.append(f"p{i + 1} {why}: …{t[max(0, mm.start() - 15):mm.end() + 25]!r}")
    if res:
        rep.fail("text_residue", f"文本层有 {len(res)} 处源码残留", res)
    latex = []
    for i, t in enumerate(texts):
        for mm in re.finditer(r"\\(frac|sum|mathrm|text|left|right|begin|end|sqrt|cdot|lambda|rho|mu)\b", t):
            latex.append(f"p{i + 1}: …{t[max(0, mm.start() - 15):mm.end() + 20]!r}")
    if latex:
        rep.warn("text_residue", f"{len(latex)} 处像 LaTeX 源码（若在代码块里可忽略）", latex)
    if not res and not latex:
        rep.info("text_residue", "无 [^ / <!-- / 机读注释 / LaTeX 残留")

    # ---------- figure_chips ----------
    big = 0
    for pg in doc:
        for info in pg.get_image_info():
            x0, y0, x1, y1 = info["bbox"]
            if (x1 - x0) * (y1 - y0) > 1600 and max(x1 - x0, y1 - y0) > 40:  # 按面积排除 emoji 之类的小位图；扁长截图（如 uptime 一行）也算大图
                big += 1
    want = exp["images"] + treefig + skelfig
    if big < want:
        rep.fail("figure_chips", f"PDF 里大图 {big} 张 < MD 引用 {exp['images']} + 科技树 {treefig} + 骨架图 {skelfig} = {want}"
                 "（有图静默丢了：路径错或文件不存在）")
    elif big > want:
        rep.warn("figure_chips", f"PDF 里大图 {big} 张 > 预期 {want}")
    chips_slide = len(re.findall(r"课件原图", full))
    chips_own = len(re.findall(r"(?m)^\s*自绘", full))
    if chips_slide < exp["slide"]:
        rep.fail("figure_chips", f"\"课件原图\" chip {chips_slide} 个 < 原图引用 {exp['slide']} 个"
                 "（原图被当成自绘或未包成 figure）")
    elif chips_slide > exp["slide"]:
        rep.warn("figure_chips", f"\"课件原图\" 出现 {chips_slide} 次 > 原图引用 {exp['slide']}（正文也提到了这个词？）")
    if chips_own < exp["own"]:
        rep.fail("figure_chips", f"\"自绘\" chip {chips_own} 个 < 自绘引用 {exp['own']} 个")
    if big >= want and chips_slide >= exp["slide"] and chips_own >= exp["own"]:
        rep.info("figure_chips", f"大图 {big} 张（原图 {exp['slide']} · 自绘 {exp['own']} · 科技树 {treefig} · 骨架图 {skelfig}），chip 齐全")

    # ---------- overflow / font_assignment ----------
    over, cjk_bad, emoji_bad, fonts = [], [], [], set()
    for i, pg in enumerate(doc):
        limit = pg.rect.width - 8
        for b in pg.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for sp in line.get("spans", []):
                    t = sp["text"]
                    if not t.strip():
                        continue
                    font = sp["font"]
                    fonts.add(font.split("+")[-1])
                    if sp["bbox"][2] > limit:
                        over.append(f"p{i + 1} x1={sp['bbox'][2]:.0f} > {limit:.0f}: {t[:40]!r}")
                    fl = font.lower().replace(" ", "").replace("-", "")
                    if CJK_RE.search(t) and not any(h in fl for h in CJK_FONT_HINTS):
                        cjk_bad.append(f"p{i + 1} [{font}] {t[:30]!r}")
                    if ALNUM_RE.search(t) and "emoji" in fl:
                        emoji_bad.append(f"p{i + 1} [{font}] {t[:30]!r}")
    if over:
        rep.fail("overflow", f"{len(over)} 个文字 span 伸出页边（拆长行或缩表列）", over)
    else:
        rep.info("overflow", "无文字伸出页边")
    if cjk_bad:
        rep.fail("font_assignment", f"{len(cjk_bad)} 处中文没落在 CJK 字体（会成方块）", cjk_bad)
    if emoji_bad:
        rep.fail("font_assignment", f"{len(emoji_bad)} 处数字/字母落在 emoji 字体（CS1234 → CS 1 2 3 4）", emoji_bad)
    if not cjk_bad and not emoji_bad:
        rep.info("font_assignment", "字体: " + ", ".join(sorted(fonts)))

    # ---------- fresh ----------
    if md_files:
        newest = max(md_files, key=lambda f: f.stat().st_mtime)
        if pdf_path.stat().st_mtime < newest.stat().st_mtime:
            rep.fail("fresh", f"PDF 比 {newest.name} 旧：MD 改过后没重编")
        else:
            rep.info("fresh", "PDF 不落后于 MD")

    return rep.emit(pdf_path.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--book", help="book/ 目录（默认 PDF 同级的 book/）")
    a = ap.parse_args()
    sys.exit(run(a.pdf, a.book))


if __name__ == "__main__":
    main()
