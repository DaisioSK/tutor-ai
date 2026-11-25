#!/usr/bin/env python3
"""
verify_teach.py — teach MD 的内容覆盖与结构验证 (content-coverage.md Layer 0 门禁)

用法:
    python3 verify_teach.py <course_output_dir> <teach_md> [--baseline old.md]
    python3 verify_teach.py <course_output_dir> <teach_md> --layout-only   # 只查 PDF 排版, Arc 模式也适用

检查 (FAIL 任一项 → 退出码 1):
  KP 覆盖 / 页覆盖 (含豁免) / 对照表位置合法 / 每 § 导读条含分量·课件页·分钟 /
  本讲大纲 (必带 N 条 + mermaid + 每 § 一行 + N 条逐条标落点 §) / 每 § 的 ✅ 教学目标块 /
  权重 (背景 § 不长于核心 § 中位数, 核心 ≥ 45%) /
  分钟之和 = 文件头 / ☕ 🎓 预算 / 外部补充占比 (WARN) / 🧠 与元叙事残留 /
  课件原图 (文件存在 / 图注带 课件 pN 或 自绘 / 页码在对照表 / 图前后有讲解段) /
  围栏配对 / 代码块行宽 (A5 页宽) / ASCII 图右边框对齐 / LaTeX 命令可渲染 / --baseline 只增不减
"""
import argparse, glob, json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from latex_to_html import (collect_unsupported, count_math, leftover_math,
                                convert_math_blocks)
except Exception:            # 没装依赖时不阻塞其他检查
    collect_unsupported = count_math = leftover_math = None
    convert_math_blocks = None

BLOCK_MARKERS = ["🧭", "🧩", "💡", "☕", "🔍", "⚠️", "⚠", "🎓", "📌", "📏", "🎯", "📎", "📍"]
EXTERNAL_BLOCKS = ["☕", "🎓", "💡", "📍"]
FORBIDDEN_POSITIONS = ["☕", "🎓", "💡", "📍"]
META_NARRATIVE = ["对照式发散", "痛点-方案-效果", "raise + reject", "插件式补充", "结构化叙事"]
EXEMPT_REASONS = ["封面", "目录", "分节", "路标", "学习目标", "总结", "致谢", "参考文献", "logo", "重复", "动画帧"]

fails, warns, infos = [], [], []
def FAIL(m): fails.append(m)
def WARN(m): warns.append(m)
def INFO(m): infos.append(m)


# ---------- PDF 排版门禁: 代码块行宽 ----------
# compile_story_pdf.py 用 A5 (148mm) + 12mm 左右边距 → 正文 124mm = 351.5pt。
# pre 再扣 padding 8px×2 + border 1px×2 = 13.5pt → 可用 338pt。
# 字体 DejaVu Sans Mono 8pt, advance 0.602em = 4.816pt/字符 → 70.1 个等宽字符。
# CJK 不在该字体里, 回落到中文字体, 1em = 8pt, 折合 8/4.816 = 1.661 个等宽单位。
PRE_MAX_W = 70.0
CJK_UNIT = 1.661


def render_width(s):
    """代码块内一行在 PDF 里占的宽度, 以等宽字符为单位。"""
    return sum(CJK_UNIT if unicodedata.east_asian_width(c) in ("W", "F") else 1.0 for c in s)


def wide_pre_lines(md_lines):
    """返回 [(行号, 宽度, 行内容)] — 围栏代码块内超过 PRE_MAX_W 的行。"""
    bad, infence = [], False
    for i, ln in enumerate(md_lines, 1):
        if re.match(r"^\s*```", ln):
            infence = not infence
            continue
        if infence:
            w = render_width(ln.rstrip())
            if w > PRE_MAX_W:
                bad.append((i, round(w, 1), ln.rstrip()))
    return bad


RIGHT_BORDER = "│┃║┆┇┊┋┤┥┦┧┨┩┪┫"                "┐┑┒┓┘┙┚┛╡╢╣╕╖╗"                "╛╜╝╬╪┼"


def has_cjk(s):
    return any(unicodedata.east_asian_width(c) in ("W", "F") for c in s)


def ragged_borders(md_lines):
    """ASCII 图右边框错位。

    代码块里 CJK 宽 1.661 个等宽单位 (非整数), 所以只要一行的右边框前面有中文,
    它的落点就和别的行对不齐, 框会画歪 (见 0-prologue 的三层栈图)。
    判据: 连续若干行都以边框字符收尾时, 它们的渲染宽度必须一致;
    只在其中至少一行的边框前含 CJK 时才判失败 —— 纯 ASCII 行长短不一是正常图形。
    返回 [(起行, 止行, 最小宽, 最大宽)]。
    """
    groups, cur, infence = [], [], False
    for i, ln in enumerate(md_lines, 1):
        if re.match(r"^\s*```", ln):
            infence = not infence
            if cur: groups.append(cur); cur = []
            continue
        s = ln.rstrip()
        if infence and s and s[-1] in RIGHT_BORDER:
            cur.append((i, render_width(s), s))
        elif cur:
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    out = []
    for g in groups:
        ws = {round(x[1], 1) for x in g}
        # 容差 0.5 个等宽单位 (≈2.4pt): CJK 宽 1.661 是无理配比, 含中文的行和纯 ASCII 行
        # 永远不可能精确等宽; 0.5 以内肉眼看不出, 超过就是明显的歪框。
        if len(g) >= 2 and max(ws) - min(ws) > 0.5 and any(has_cjk(x[2][:-1]) for x in g):
            out.append((g[0][0], g[-1][0], min(ws), max(ws)))
    return out


def parse_pages(text):
    """'p3-5, p20' / 'p14–16' / 'p.7' → {3,4,5,20,...}"""
    pages = set()
    for m in re.finditer(r"p\.?\s*(\d+)(?:\s*[-–~]\s*p?\.?\s*(\d+))?", text):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        if b < a: a, b = b, a
        if b - a > 400: continue  # not a page range
        pages.update(range(a, b + 1))
    return pages


def parse_kp_decl(text):
    """'KP-7.1 ~ KP-7.22, KP-8.1 ~ KP-8.3, KP-9.5' → set of ids (ranges expanded)."""
    ids = set()
    for m in re.finditer(r"KP-(\d+)\.(\d+)\s*[~\-–至到]+\s*KP-(\d+)\.(\d+)", text):
        if m.group(1) == m.group(3):
            ids.update(f"KP-{m.group(1)}.{i}" for i in range(int(m.group(2)), int(m.group(4)) + 1))
    ids.update(f"KP-{a}.{b}" for a, b in re.findall(r"KP-(\d+)\.(\d+)", text))
    return ids


def blocks(md_lines):
    """Yield (marker, text) for each blockquote group (consecutive '>' lines)."""
    cur = []
    for ln in md_lines + [""]:
        if ln.lstrip().startswith(">"):
            cur.append(ln)
        elif cur:
            body = "\n".join(cur)
            first = cur[0].lstrip()[1:].strip()
            marker = next((mk for mk in BLOCK_MARKERS if first.startswith(mk)), None)
            yield marker, body
            cur = []


NL_JOIN = chr(10)


def broken_tables(md_lines):
    """表格行里的数学一旦渲染出真竖线, Markdown 会多切一列, 整张表退化成一行纯文本。

    这是**静默**故障: 编译不报错, 只有翻 PDF 才看得见。数学转换跑在 Markdown 解析之前,
    所以这里按同样的顺序模拟一次 —— 转完数学再数竖线, 变多了就是要出事。
    """
    if convert_math_blocks is None:
        return []
    out, in_fence = [], False
    for i, ln in enumerate(md_lines, 1):
        if re.match(r"^\s*```", ln):
            in_fence = not in_fence
            continue
        if in_fence or not ln.lstrip().startswith("|"):
            continue
        if "$" not in ln and "\\(" not in ln:
            continue
        rendered, _ = convert_math_blocks(ln)
        if rendered.count("|") > ln.count("|"):
            out.append((i, ln.strip()[:90]))
    return out


def check_pdf_layout(lines):
    """PDF 排版四检: 围栏配对 / 表格未被竖线切坏 / 代码块行宽 / ASCII 图右边框对齐。

    与讲义结构无关, Arc 模式和单讲模式都适用 (见 --layout-only)。
    """
    fences = [i for i, l in enumerate(lines, 1) if re.match(r"^\s*```", l)]
    if len(fences) % 2:
        FAIL(f"``` 围栏数为奇数 ({len(fences)} 个, 最后一个在 L{fences[-1]}) — "
             f"未闭合的围栏会把后面整段正文当成代码块渲染进 PDF")

    bad_tab = broken_tables(lines)
    if bad_tab:
        FAIL("表格行里的公式渲染出了真竖线, Markdown 会多切一列 —— "
             f"整张表在 PDF 里退化成一行纯文本, 共 {len(bad_tab)} 行。"
             "条件竖线请用 \\mid (输出 U+2223, 不是分隔符):")
        for _i, _ln in bad_tab[:20]:
            fails.append(f"    L{_i}: {_ln}")

    # 表格单元格里没有空格的长 token (长函数调用 / dict 字面量) 会把整张表撑过页宽,
    # 其余列被挤成一字一行。编译器已给 td code 加了 break-all 兜底, 这里只 WARN 提醒
    # 作者: 能在源码里加空格或拆行的, 比让 PDF 在字符中间硬折好看。
    TOKEN_MAX = 36
    in_f, long_tok = False, []
    for i, l in enumerate(lines, 1):
        if re.match(r"^\s*```", l):
            in_f = not in_f
            continue
        if in_f or not l.lstrip().startswith("|") or re.match(r"^\s*\|[\s:|-]+\|\s*$", l):
            continue
        for cell in l.strip().strip("|").split("|"):
            # 链接渲染后只剩链接文字; CJK 串本来就能在任意字间折行 —— 都不算
            cell = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)
            for tok in re.findall(r"[\x21-\x7e]+", cell):
                if len(tok) > TOKEN_MAX:
                    long_tok.append((i, tok[:50]))
    if long_tok:
        WARN(f"表格单元格里有 {len(long_tok)} 个超过 {TOKEN_MAX} 字符且无空格的 token, "
             f"PDF 会在字符中间硬折 (td code 已 break-all 兜底); 能拆就在源码里加空格: "
             + "; ".join(f"L{i} {t}" for i, t in long_tok[:5]))

    wide = wide_pre_lines(lines)
    if wide:
        FAIL(f"代码块行宽超出 A5 页宽 (上限 {PRE_MAX_W:.0f} 等宽单位, CJK 按 {CJK_UNIT} 折算), "
             f"共 {len(wide)} 行 — PDF 里会折行或被裁掉, 请在源码里断行/缩短注释:")
        for i, wd, ln in wide[:20]:
            fails.append(f"    L{i} (宽 {wd}): {ln[:80]}")
        if len(wide) > 20:
            fails.append(f"    …… 另有 {len(wide) - 20} 行")

    if collect_unsupported is not None:
        md_src = NL_JOIN.join(lines)
        unk = collect_unsupported(md_src)
        if unk:
            FAIL("LaTeX 命令 compile_story_pdf 不认识, PDF 里会原样印出源码: "
                 + ", ".join(sorted(unk))
                 + " — 要么改写成已支持的写法, 要么在 latex_to_html.py 里补上")
        for ln_no, txt in leftover_math(md_src):
            FAIL(f"L{ln_no} 还残留数学界符, 转换器没接住 —— PDF 里会印出 LaTeX 源码: {txt}")
        nb, ni = count_math(md_src)
        if nb or ni:
            INFO(f"数学: display {nb} 块 · 行内 {ni} 处 (全部可渲染)")

    for ra, rb, lo, hi in ragged_borders(lines):
        FAIL(f"ASCII 图右边框错位 L{ra}-L{rb}: 各行渲染宽度 {lo}-{hi} 等宽单位 "
             f"(差 {round(hi-lo,1)}) — 边框前有中文, PDF 里画不齐; "
             f"改成左锚定 (只保留左边框) 或去掉中文")


def report_and_exit(name):
    print("# verify_teach — " + name)
    print("")
    for m in infos: print("ℹ️  " + m)
    for m in warns: print("⚠️  WARN " + m)
    for m in fails: print("❌ FAIL " + m)
    print("")
    print("结果: " + ("PASS" if not fails else "FAIL")
          + f" ({len(fails)} fail, {len(warns)} warn)")
    sys.exit(1 if fails else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("course_dir")
    ap.add_argument("teach_md")
    ap.add_argument("--baseline")
    ap.add_argument("--layout-only", action="store_true",
                    help="只跑 PDF 排版三检 (围栏/行宽/边框), 跳过单讲模式的覆盖与结构检查")
    a = ap.parse_args()

    md = open(a.teach_md, encoding="utf-8").read()
    lines = md.split("\n")
    n_chars = len(md)

    # ---------- scan 产物是否过期 (版本漂移检测) ----------
    # extract_figures.py 是后加进流水线的; 在它之前做完的课程没有 raw/figures/,
    # 于是 teach 一张课件原图都没有 —— 而「有 _figures.json 却零嵌图」的旧检查
    # 在这种情况下条件不成立, 永远不会触发。缺席比错误更难发现, 所以显式查一次。
    _figjson = os.path.join(a.course_dir, "raw", "_figures.json")
    # teach/ 用 ../raw/figures/, assignment{N}/prep/ 深一层用 ../../raw/figures/ —— 都算嵌图
    _nfig = len(re.findall(r"\]\((?:\.\./)+raw/figures/", md))
    if not os.path.exists(_figjson):
        FAIL("scan 产物过期: 缺 raw/_figures.json —— extract_figures.py 没跑过, "
             "本课程不可能有任何课件原图。先跑 "
             f"extract_figures.py courses/<课程> {a.course_dir}/raw")
    else:
        try:
            _cand = len(json.load(open(_figjson, encoding="utf-8")))
        except Exception:
            _cand = 0
        _is_prep = f"{os.sep}prep{os.sep}" in os.path.abspath(a.teach_md)
        if _cand and _nfig == 0 and not _is_prep:
            # 作业预备材料不是讲义, 嵌课件原图是可选项, 不为此告警
            WARN(f"课件裁出 {_cand} 张原图, 本篇一张都没嵌 (content-coverage.md §1.4: 原图优先于自绘)")
        elif _nfig:
            INFO(f"课件原图: 嵌入 {_nfig} 张 (候选 {_cand} 张)")

    if a.layout_only:
        check_pdf_layout(lines)
        report_and_exit(os.path.basename(a.teach_md))

    # ---------- header: KP declaration ----------
    decl_line = next((l for l in lines[:40] if "覆盖知识点" in l), "")
    declared = parse_kp_decl(decl_line)
    if not declared:
        FAIL("文件头缺 `覆盖知识点: KP-x.y ~ KP-x.z` 声明 (前 40 行内)")

    # ---------- concepts.json: expected KPs + lecture code ----------
    concepts = json.load(open(os.path.join(a.course_dir, "concepts.json"), encoding="utf-8"))
    kp_source = {}
    for arc in concepts.get("arcs", []):
        for c in arc.get("concepts", []):
            kp_source[c["id"]] = c.get("source", "")
    unknown = sorted(k for k in declared if k not in kp_source)
    if unknown:
        FAIL(f"文件头声明的 KP 在 concepts.json 里不存在: {unknown}")
    expected = declared & set(kp_source)

    codes = [re.match(r"\s*(L\w+?)\s+p", kp_source[k]).group(1)
             for k in expected if re.match(r"\s*(L\w+?)\s+p", kp_source[k])]
    lecture = max(set(codes), key=codes.count) if codes else None
    total_pages = None
    if lecture:
        cands = glob.glob(os.path.join(a.course_dir, "raw", f"*{lecture}-*.txt")) + \
                glob.glob(os.path.join(a.course_dir, "raw", f"{lecture}*.txt"))
        if cands:
            raw = open(cands[0], encoding="utf-8").read()
            total_pages = len(re.findall(r"^--- Page \d+ ---$", raw, re.M))
            INFO(f"课件 {lecture}: {os.path.basename(cands[0])}, {total_pages} 页")
        else:
            WARN(f"找不到 {lecture} 的 raw txt, 跳过页覆盖检查")
    else:
        WARN("无法从 KP source 推断讲次代号, 跳过页覆盖检查")

    # ---------- sections + 导读条 ----------
    sec_idx = [(i, re.match(r"^## §(\d+)", l).group(1)) for i, l in enumerate(lines) if re.match(r"^## §\d+", l)]
    minutes_sum, guide_pages = 0, set()
    tier_of, body_len = {}, {}          # §号 → 分量 / 正文字符数 (content-coverage.md §2)
    sec_text = {}                       # §号 → 该节正文, 供教学目标块检查 (§2.0)
    sec_bounds = [(i, num) for i, num in sec_idx]
    for k, (i, num) in enumerate(sec_bounds):
        end = sec_bounds[k + 1][0] if k + 1 < len(sec_bounds) else len(lines)
        nxt = next((x for x, l in enumerate(lines[i:end], i) if re.match(r"^## ", l) and x > i), end)
        body_len[num] = sum(len(l) for l in lines[i:nxt])
        sec_text[num] = "\n".join(lines[i:nxt])
    for i, num in sec_idx:
        j = i + 1
        while j < len(lines) and lines[j].strip() == "": j += 1
        first = lines[j] if j < len(lines) else ""
        if not first.lstrip().startswith("> 🧭"):
            FAIL(f"§{num}: 标题下第一行不是 🧭 导读条"); continue
        m = re.search(r"约\s*(\d+)\s*分钟", first)
        if m: minutes_sum += int(m.group(1))
        else: FAIL(f"§{num}: 导读条缺 `约 N 分钟`")
        pm = re.search(r"课件[^·\n]*", first)
        if pm and parse_pages(pm.group(0)):
            guide_pages |= parse_pages(pm.group(0))
        else:
            FAIL(f"§{num}: 导读条缺 `课件 pN-M`")
        if not re.search(r"轻度|中度|重度", first):
            FAIL(f"§{num}: 导读条缺负载评级 (轻度/中度/重度)")
        tm = re.search(r"🎯?核心|常规|背景", first)
        if tm:
            tier_of[num] = tm.group(0).lstrip("🎯")
        else:
            FAIL(f"§{num}: 导读条缺分量 (🎯核心 / 常规 / 背景) —— content-coverage.md §2.2")
    INFO(f"§ 数: {len(sec_idx)}, 导读条分钟之和: {minutes_sum}")

    # ---------- 每 § 的教学目标 post status (content-coverage.md §2.0) ----------
    # 目标是分量的依据: 没写目标, "这节该多长"就只能凭手感, 于是课件一页图和必考公式一样长。
    # 脚本只能验目标块在不在、写得可不可检验; 读者到不到得了, 靠 §2.0.1 的顺读自足测试。
    ACTION_RE = re.compile(r"[会能][^。；\n]{0,4}(?:算|判|写|推|说|认|选|验|估|读|画|拆|排|指|用|"
                           r"按|查|默|列|换|解|把|试|定位|重算)|算出|写出|推出|说出|认出|判断|重算")
    VAGUE_RE = re.compile(r"理解了|熟悉|掌握|了解一下|有个印象|有所了解")
    for num in tier_of:
        body = sec_text.get(num, "").split("\n")
        gi = next((k for k, l in enumerate(body) if l.lstrip().startswith("> ✅")), None)
        if gi is None:
            FAIL(f"§{num}: 缺 `> ✅ **学完这节你应该**: …` 教学目标块 (content-coverage.md §2.0) —— "
                 f"没有目标就没有加权依据")
            continue
        gj = gi
        while gj + 1 < len(body) and body[gj + 1].lstrip().startswith(">"): gj += 1
        goal = " ".join(body[gi:gj + 1])
        if not ACTION_RE.search(goal):
            FAIL(f"§{num}: ✅ 目标没写成可检验动作 (会算 / 能判断 / 能写出 / 能推出 / 能说出为什么) "
                 f"—— 验不了的目标等于没有 (§2.0)")
        if VAGUE_RE.search(goal):
            WARN(f"§{num}: ✅ 目标里有「理解 / 熟悉 / 掌握」这类没法验的词, 换成动作 (§2.0)")
        # 目标是加权尺, 不是第二份小结: 写长了就成复述, 版面也吃不消 (§2.0)
        gtext = re.sub(r"^>\s*✅\s*\**[^*:：]*\**[:：]?\s*", "", goal.replace("> ", " ")).strip()
        if len(gtext) > 100:
            FAIL(f"§{num}: ✅ 目标写了 {len(gtext)} 字 —— 规格是一行, 现在是在复述本节 (§2.0)")
        elif len(gtext) > 50:
            WARN(f"§{num}: ✅ 目标 {len(gtext)} 字, 偏长 (一行, 公式除外约 40 字) —— 砍到只剩动作和输入输出")
        if any(l.lstrip().startswith("> ") and not l.lstrip().startswith("> ✅")
               for l in body[gj + 1:]):
            WARN(f"§{num}: ✅ 目标块后面还有别的块 —— 它该是这一节的最后一块, 读者读完立刻自查 (§2.0)")

    # ---------- 本讲大纲 + 权重 (content-coverage.md §2) ----------
    if sec_idx:
        outline = ""
        om = re.search(r"^## 本讲大纲\s*$(.*?)(?=^## )", md, re.M | re.S)
        if not om:
            FAIL("缺 `## 本讲大纲` 一节 (content-coverage.md §2.3): "
                 "读者需要一张地图才知道哪几节是重点")
        else:
            outline = om.group(1)
            if "```mermaid" not in outline:
                FAIL("本讲大纲里没有 ```mermaid 流程图 (content-coverage.md §2.3)")
            if not re.search(r"必须带走", outline):
                FAIL("本讲大纲缺「必须带走的 N 条」块 (content-coverage.md §2.1)")
            else:
                # 总目标必须被各节的教学目标之和覆盖: 每一条都要能指到承担它的 § (§2.0)。
                ol = outline.split("\n")
                ti = next(k for k, l in enumerate(ol) if "必须带走" in l)
                tj = ti
                while tj + 1 < len(ol) and ol[tj + 1].lstrip().startswith(">"): tj += 1
                items = [l for l in ol[ti:tj + 1] if re.match(r"^>\s*(\d+\.|-)\s+", l.lstrip())]
                if not items:
                    FAIL("「必须带走的 N 条」块里一条都没有 (格式: `> 1. {…} (§7, §9)`)")
                naked = [l.strip()[:28] for l in items if not re.search(r"§\s*\d", l)]
                if naked:
                    FAIL(f"「必须带走」这几条没标落点 §: {naked} —— 指不到 § 说明没人负责教它 "
                         f"(content-coverage.md §2.0)")
            missing = [n for n in tier_of if not re.search(rf"§{n}(?!\d)", outline)]
            if missing:
                FAIL(f"本讲大纲没列到这些 §: {', '.join('§' + n for n in missing)} —— 一个 § 一个节点, 不漏不并")

            # 面包屑由大纲派生 (content-coverage.md §2.4): 标签写不对, 页眉就是空的或被截断
            mm = re.search(r"```mermaid\s*\n(.*?)```", outline, re.S)
            if mm:
                src = mm.group(1)
                for sg in re.finditer(r'^\s*subgraph\s+\w+\s*\[\s*"?(.*?)"?\s*\]\s*$', src, re.M):
                    lab = sg.group(1)
                    if "·" not in lab:
                        FAIL(f"大纲的 subgraph 标签 “{lab}” 缺 `·` —— 面包屑取不到段名 "
                             f"(格式: `段名 · §范围`)")
                    elif len(lab.split("·")[0].strip()) > 10:
                        WARN(f"大纲段名 “{lab.split('·')[0].strip()}” 偏长, 页眉会挤 (≤ 8 字)")
                seen_nodes = 0
                for nd in re.finditer(r'^\s*\w+\s*\[\s*"?(.*?)"?\s*\](?::::\w+)?\s*$', src, re.M):
                    lab = nd.group(1)
                    if lab.startswith("§"):
                        seen_nodes += 1
                        short = re.sub(r"^§\s*\d+\s*", "", lab)
                        if not short:
                            FAIL(f"大纲节点 “{lab}” 只有 §号没有短名 —— 页眉会只剩一个编号")
                        elif len(short) > 14:
                            WARN(f"大纲节点短名 “{short}” 有 {len(short)} 字 (≤ 12 字), 页眉会挤")
                if seen_nodes and seen_nodes < len(tier_of):
                    FAIL(f"大纲里只有 {seen_nodes} 个 `§N 短名` 节点, 本讲有 {len(tier_of)} 个 § —— "
                         f"缺的那几节没有面包屑")

        core = [body_len[n] for n, t in tier_of.items() if t == "核心"]
        bg = [(n, body_len[n]) for n, t in tier_of.items() if t == "背景"]
        total = sum(body_len.values()) or 1
        if core:
            core_med = sorted(core)[len(core) // 2]
            over = [n for n, ln in bg if ln > core_med]
            if over:
                FAIL(f"背景 § 比核心 § 的中位数还长: {', '.join('§' + n for n in over)} "
                     f"(核心中位 {core_med} 字符) —— 权重反了, 砍背景而不是给核心加字")
            share = sum(core) / total
            INFO(f"分量: 核心 {len(core)} 节占 {share:.0%} · 常规 {sum(1 for t in tier_of.values() if t=='常规')} 节 "
                 f"· 背景 {len(bg)} 节占 {sum(l for _, l in bg)/total:.0%}")
            if share < 0.45:
                FAIL(f"🎯核心 § 篇幅合计只有 {share:.0%} < 45% —— 重点被支撑材料挤掉了 (content-coverage.md §2.2)")
        else:
            FAIL("一个 🎯核心 § 都没有 —— 先回答「读者只该记住哪 3-5 件事」(content-coverage.md §2.1)")
        for n, ln in bg:
            if ln > 1600:
                WARN(f"§{n} 标了背景却有 {ln} 字符 (规格 ≤800 字) —— 压成表或砍掉")

    hm = re.search(r"预计阅读:\s*(\d+)\s*分钟", md)
    if hm:
        if int(hm.group(1)) != minutes_sum:
            FAIL(f"文件头预计阅读 {hm.group(1)} ≠ 各 § 导读条之和 {minutes_sum}")
    else:
        FAIL("文件头缺 `预计阅读: N 分钟`")

    # ---------- 课件对照表 ----------
    tbl_pages, tbl_exempt, tbl_kps, bad_pos = set(), set(), set(), []
    t_start = next((i for i, l in enumerate(lines) if re.match(r"^##\s*课件对照表", l)), None)
    if t_start is None:
        FAIL("缺 `## 课件对照表` 一节 (content-coverage.md §1.2)")
    else:
        for l in lines[t_start + 1:]:
            if l.startswith("## "): break
            if not l.startswith("|") or set(l.replace("|", "").strip()) <= set("-: "): continue
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if len(cells) < 4 or cells[0] in ("课件页",): continue
            pages = parse_pages(cells[0])
            if not pages: continue
            pos = cells[3]
            if "豁免" in pos:
                tbl_exempt |= pages
                if not any(w in pos or w in cells[1] for w in EXEMPT_REASONS):
                    FAIL(f"对照表 {cells[0]}: 豁免无合法理由 ({pos})")
            else:
                tbl_pages |= pages
                if any(f in pos for f in FORBIDDEN_POSITIONS):
                    bad_pos.append(f"{cells[0]} → {pos}")
            tbl_kps |= set(re.findall(r"KP-\d+\.\d+", cells[2]))
        if bad_pos:
            FAIL(f"对照表位置列出现 ☕/🎓/💡/📍 (它们不能承载课件内容): {bad_pos}")
        if total_pages:
            all_pages = set(range(1, total_pages + 1))
            uncovered = sorted(all_pages - tbl_pages - tbl_exempt)
            if uncovered:
                FAIL(f"课件页未覆盖 ({len(uncovered)}/{total_pages}): {uncovered}")
            over = sorted((tbl_pages | tbl_exempt) - all_pages)
            if over: WARN(f"对照表页码超出课件页数: {over}")
            INFO(f"对照表: 讲到 {len(tbl_pages)} 页, 豁免 {len(tbl_exempt)} 页, 课件共 {total_pages} 页")
        # KP coverage
        if expected:
            missing = sorted(expected - tbl_kps, key=lambda k: [int(x) for x in k[3:].split(".")])
            if missing: FAIL(f"KP 未出现在对照表 ({len(missing)}/{len(expected)}): {missing}")
            extra = sorted(tbl_kps - expected)
            if extra: WARN(f"对照表出现文件头未声明的 KP: {extra}")
            INFO(f"KP: 声明 {len(expected)}, 对照表命中 {len(expected & tbl_kps)}")
        if guide_pages and tbl_pages:
            only_guide = sorted(guide_pages - tbl_pages - tbl_exempt)
            if only_guide: WARN(f"导读条提到但对照表没有的页: {only_guide}")

    # ---------- blocks: budgets, external share, marker sanity ----------
    counts, chars = {}, {}
    for marker, body in blocks(lines):
        key = marker or "(plain)"
        counts[key] = counts.get(key, 0) + 1
        chars[key] = chars.get(key, 0) + len(body)
    def share(k): return chars.get(k, 0) / max(n_chars, 1)
    if share("☕") > 0.08: FAIL(f"☕ 占比 {share('☕'):.1%} > 8%")
    if share("🎓") > 0.15: FAIL(f"🎓 占比 {share('🎓'):.1%} > 15%")
    ext = sum(chars.get(k, 0) for k in EXTERNAL_BLOCKS) + sum(len(l) for l in lines if "⚡" in l and not l.lstrip().startswith(">"))
    if ext / max(n_chars, 1) > 0.25: WARN(f"外部补充总量 {ext/n_chars:.1%} > 25% — 检查正课是否写薄")
    INFO("块统计: " + ", ".join(f"{k}×{v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])))
    INFO(f"占比: ☕ {share('☕'):.1%} · 🎓 {share('🎓'):.1%} · 外部补充合计 {ext/max(n_chars,1):.1%}")

    # ---------- 课件原图 (content-coverage.md §1.4) ----------
    fig_pages, n_figs = set(), 0
    md_dir = os.path.dirname(os.path.abspath(a.teach_md))
    for i, l in enumerate(lines):
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", l.strip())
        if not m: continue
        n_figs += 1
        alt, src = m.group(1), m.group(2)
        if not os.path.exists(os.path.join(md_dir, src)):
            FAIL(f"图文件不存在: {src}")
        pm = re.search(r"课件\s*p(\d+)", alt)
        if pm: fig_pages.add(int(pm.group(1)))
        elif not alt.startswith("自绘"):
            FAIL(f"图注须以 `课件 pN ·` 或 `自绘 ·` 开头: {alt[:40]}")
        def neighbour(step):
            j = i + step
            while 0 <= j < len(lines) and lines[j].strip() == "": j += step
            return lines[j].strip() if 0 <= j < len(lines) else ""
        before, after = neighbour(-1), neighbour(1)
        if before.startswith("#") or before.startswith("![") or after.startswith("#") or after.startswith("![") or not after:
            FAIL(f"图 {src.split('/')[-1]} 前后须各有一段讲解 (不许图贴标题 / 图贴图)")
    if fig_pages and (tbl_pages or tbl_exempt):
        stray = sorted(fig_pages - tbl_pages - tbl_exempt)
        if stray: FAIL(f"图注页码不在对照表内: {stray}")
    fj = os.path.join(a.course_dir, "raw", "_figures.json")
    if os.path.exists(fj) and lecture:
        avail = [f for f in json.load(open(fj, encoding="utf-8")) if lecture in f["source"] and not f.get("looks_like_table")]
        if avail and n_figs == 0:
            WARN(f"_figures.json 有 {len(avail)} 张 {lecture} 候选原图, 正文零嵌图 — 原图优先于自绘 (content-coverage.md §1.4)")
        INFO(f"课件原图: 嵌入 {n_figs} 张 (页 {sorted(fig_pages)}), 候选 {len(avail)} 张")

    check_pdf_layout(lines)

    # ---------- residue ----------
    if "🧠" in md: FAIL(f"🧠 残留 {md.count('🧠')} 处 (负载评级应写 轻度/中度/重度)")
    for w in META_NARRATIVE:
        if w in md: FAIL(f"元叙事禁词: {w}")

    # ---------- baseline: 只增不减 ----------
    if a.baseline:
        b = open(a.baseline, encoding="utf-8").read()
        b_kps = set(re.findall(r"KP-\d+\.\d+", b))
        b_pages = set()
        bt = b.find("## 课件对照表")
        b_pages = parse_pages(b[bt:]) if bt >= 0 else parse_pages(b)
        new_pages = tbl_pages | tbl_exempt | guide_pages
        lost_p = sorted(b_pages - new_pages) if total_pages else []
        lost_k = sorted(b_kps - tbl_kps - declared)
        if lost_p: FAIL(f"只增不减: 旧版涉及的课件页新版未认领: {lost_p}")
        if lost_k: FAIL(f"只增不减: 旧版提到的 KP 新版缺失: {lost_k}")
        INFO(f"baseline 对账: 旧版页 {len(b_pages)} / KP {len(b_kps)}")

    # ---------- report ----------
    report_and_exit(os.path.basename(a.teach_md))


if __name__ == "__main__":
    main()
