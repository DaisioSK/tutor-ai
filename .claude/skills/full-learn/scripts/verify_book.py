#!/usr/bin/env python3
"""
verify_book.py — 书稿 book/*.md 的脚本门禁（audit PARADIGM 方法 2「脚本注册表」verify_book 一行）。

用法:
    python3 verify_book.py <full-learn 工作区> [--chapter N] [--strip-blocks] [--baseline <旧书 book/ 目录>]

输入: <ws>/book/*.md · tree.json · spine.md · reader.md · raw/_manifest.json · raw/_figures.json · raw/*.txt
输出: 每个检查一行 `[PASS|FAIL|WARN|SKIP] verify_book.py#<检查名>  <信息>`，末行 `结果: PASS/FAIL (n fail, m warn)`；
      任一 FAIL 退出码 1。FAIL/WARN 信息带「怎么修 → 指向哪个模块 PARADIGM 的哪一段」。
副产物: 全书模式写 `<ws>/audit/coverage.md`（#coverage_table）；`--strip-blocks` 写 `<ws>/audit/strip-blocks/*.md`。

--chapter N  只查 book/NN-*.md；需要全书才能判的检查报 SKIP：
    prereq_no_forward · prereq_shape · prereq_backref（section 前置变体）
    files · front_first_page · apex_front_back · prereq_covers_external · front_mermaid · book_skeleton ·
    volume_synthesis · book_map ·
    generator_chapters ·
    toc_matches · front_elements · front_length · stats · case_thread · reverse_index · node_index ·
    keyword_index · exam_appendix · appendix_narrow · generators_in_book · nodes · apex · coverage_table ·
    exam_map · exercises（reading_guide_once 只查"章文件不含读法"那一半）。
    deps / term_first_use / xref_targets 在单章模式下以 spine 的节号代替未写出的章。

量法（audit 方法 2d 统一口径）:
    比例一律按字符；「字数」= CJK 字 + 拉丁词各计 1；节 = `## §` 到下一个 `## ` 之间；
    块按 block_roles.py（devices 词汇表的机读版）识别；材料外块 = ☕ 🎓 💡 📍，另加 ⚡ 标记的非引用行。
    出手块（⚔️ 押一注、其后 `<!-- reveal -->` 的「**揭晓**」块、🗺️ 路线、`🤔 先猜`、🧠 心智卡）与出手行（**本章 boss** /
    **现在去打** / **世界模型 vN** / **先回忆**）不算正课：不计节字数、阅读时长、分量占比，对硬核连续段透明，不当节首句；
    🗺️ 是箭头短语，不查顿号串。材料外节的顺序：节注释 → 🗺️ → 📍 → 正文。

出手检查（chapter 理论 6；按章跑，--chapter 也跑）:
    #challenge   E-CHAP-32 开章（首个 § 前）：**本章 boss** 行；⚔️ 块、题面 3–4 个 `> - A. …` 选项、跳关链接 #card-N；
                 ⚔️ 后 `<!-- reveal -->`，其后第一个引用块以 **揭晓** 开头、每个选项有「X 不对/对」、恰 1 个「对」且与「正解：X」一致
                 → 缺则 FAIL；揭晓没写「正解：X」WARN；非首章缺「先回忆」行 WARN
    #mind_card   E-CHAP-33 收章 h2 后第一块是 `> 🧠 **心智卡**　<问题>`；❌ 2–3 条且各含「不对，因为」；✅ 恰 1 条且含「因为」；
                 `**一句话**` 行；❌/✅ 用 bullet → 不符 FAIL；首行不是问句 WARN
    #world_model E-CHAP-34 收章 `**世界模型 vN**`（N = 章号，含本章新增加粗）缺/错 WARN；`**现在去打**` 行缺 FAIL
    #route_line  E-SEC-40 每个 `## §` 节注释后（可隔空行）紧跟 `> 🗺️ …`，≥3 个箭头 → 缺 FAIL；>7 步或多行 WARN
    分量档（核心/常规/背景）: 节级 🧭 写了就用它；否则 开章骨架里 :::core 叶子所挂的节 = 核心，
    spine 机读表分量为 0 且不是核心叶子 = 背景，其余 = 常规。负载档取 spine 机读表「负载」列。
    阅读时长: 节 = ⌈字数 ÷ 速率(轻 300/中 250/重 180)⌉ + 表格与 ASCII 图各 1 分钟；
    章 = Σ 节 + ⌈开章与收章字数 ÷ 300⌉。

启发式（只报 WARN，最终判断由 self / cold-read 承担）:
    ungrounded_tokens（数字与拉丁专名回 raw/ 搜，不认识推导式的上下文）· comparatives（比较句附近是否有原因词）·
    list_density · sentence_shape 的长句长段 · length_band · texture_run（25–40 行）· close 的"回到开章问题" ·
    stage_map 的完整度 · case_thread · head 的"能力与 spine 解锁一致" · depth_hint · reality_intro 的英文词 ·
    skeleton 的段长（<60 / >260 字）、≥6 节只有 2 个大概念、1 或 5 个子题、短名 >12 字、一节挂多叶、大概念没在骨架段出现、没写略写句 ·
    close 的"开章大概念在收章重现" · book_skeleton 的卷间关系词不在词表、总纲卷缺卷概念名 ·
    volume_synthesis 的字数（2000–5000 之外）· book_map 的根思想缺席、按问题找位置 <20 行。
文件: book/ 认 00-front · NN-<slug>（章）· NNv-<slug>（卷串讲，NN = 该卷最后一章）· 98-map（总纲卷）· 99-back；
    章级结构检查（structure / head / skeleton / close / questions 等）只对 NN-<slug> 跑；卷串讲与总纲只过
    core 的考务 / 元叙事、xref_format / xref_targets，与各自的 #volume_synthesis（E-BOOK-30）/ #book_map（E-BOOK-31）。
    #book_skeleton 另查全书任何文件不出现节点级科技树 mermaid（非 `%% skeleton`、非 § 开头标签的地图）→ FAIL。
脚本只定位、不判语义的部分（标在 EXPECT 的 self / cold-read 里）:
    比较级是否真正开盒、类比是否贴切、钩子是否剧透、补充块挂的是哪个材料结论、☕ 是否 link back、
    练习题子问粒度的覆盖清单（#exercises 只对到页）、"连续 3 个未解释术语"（#deps 只查早用）。
"""
import argparse
import glob
import json
import math
import os
import re
import statistics
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from block_roles import BLOCK_ROLES, MARKERS, GAME_MARKERS  # noqa: E402
import skeleton_figure  # noqa: E402  骨架 mermaid 解析（与编译器共用）

try:
    from latex_to_html import collect_unsupported, leftover_math  # noqa: E402
except Exception:  # 依赖缺失时公式检查静默跳过，不阻塞其余检查
    collect_unsupported = leftover_math = None
try:
    from verify_spine import parse_spine, parse_volumes, cn_to_int  # noqa: E402
except Exception:
    parse_spine = parse_volumes = cn_to_int = None

S = "verify_book.py"

# 注册表顺序（audit PARADIGM 方法 2 脚本注册表）
CHECKS = [
    # core
    "reader_md", "strip_external_coverage", "external_share", "self_sufficient", "term_first_use",
    "ungrounded_tokens", "supplement_history", "exam_logistics", "banned_words", "meta_narrative",
    "sentence_shape", "comparatives", "list_density",
    # section
    "section_header", "first_sentence_not_definition", "hook_terms", "formula_after_prose", "numbered_slots",
    "length_band", "goal_line", "route_line",
    # chapter
    "structure", "head", "reading_time", "skeleton", "weight_budget", "load_sequence",
    "heavy_junction", "breather", "texture_run", "mechanical_transition", "close", "stage_map", "questions",
    "no_catchall", "challenge", "mind_card", "world_model", "block_summary",
    # devices
    "slide_narration", "footnote_defs", "depth_hint", "aside_only_content", "reality_intro",
    "figure_candidates", "figures_per_section", "figure_format", "figure_context", "math_notation",
    "code_chunks", "heavy_device_ratio", "block_vocab", "guide_line", "guide_minutes", "texture_floor",
    "aside_budget", "breather_length", "master_length", "def_lines", "exam_block", "clip_lines",
    "external_marks",
    # section 变体 · 前置节（variants/prereq.md）
    "prereq_no_forward", "prereq_shape", "prereq_backref",
    # book
    "files", "front_first_page", "apex_front_back", "prereq_covers_external", "front_mermaid",
    "book_skeleton", "volume_synthesis", "book_map", "generator_chapters", "toc_matches", "reading_guide_once",
    "front_elements", "front_length", "stats",
    "case_thread", "xref_format", "xref_targets", "reverse_index", "node_index", "keyword_index",
    "exam_appendix", "appendix_narrow",
    # tree
    "generators_in_book",
    # audit
    "nodes", "apex", "spine_sync", "ids", "sources", "position", "coverage_table", "no_exempt_in_body",
    "exam_map", "exercises", "deps", "hollow", "baseline", "strip_blocks",
]

# 失败时指回的范式段落
FIX = {
    "reader_md": "core PARADIGM §方法 1", "strip_external_coverage": "core PARADIGM §理论 3（材料内容进正文）",
    "external_share": "core PARADIGM §判断准则（先查正文是否写薄）", "self_sufficient": "core PARADIGM §方法 7",
    "term_first_use": "core PARADIGM §方法 3", "ungrounded_tokens": "core PARADIGM §方法 5",
    "supplement_history": "core PARADIGM §方法 6", "exam_logistics": "core PARADIGM 禁止清单（考务）",
    "banned_words": "core PARADIGM 禁止清单", "meta_narrative": "core PARADIGM 禁止清单（元叙事）",
    "sentence_shape": "core PARADIGM §方法 2", "comparatives": "core PARADIGM §方法 4（三问）",
    "list_density": "core PARADIGM §方法 2",
    "section_header": "section PARADIGM §方法 2 入口 / CONTRACTS T4",
    "first_sentence_not_definition": "section PARADIGM §方法 2 入口", "hook_terms": "section PARADIGM §理论 3",
    "formula_after_prose": "section PARADIGM §理论 4", "numbered_slots": "section PARADIGM §理论 5",
    "length_band": "section PARADIGM §理论 6", "goal_line": "section PARADIGM §方法 4（目标行）",
    "structure": "chapter PARADIGM §方法 1、4", "head": "chapter PARADIGM §方法 1",
    "reading_time": "chapter PARADIGM §方法 1（时长由字数算）", "skeleton": "chapter PARADIGM §方法 1（本章骨架）、理论 5",
    "weight_budget": "chapter PARADIGM §方法 2（分量三档）",
    "load_sequence": "chapter PARADIGM §方法 2（编排规则）", "heavy_junction": "chapter PARADIGM §方法 2",
    "breather": "chapter PARADIGM §方法 2", "texture_run": "chapter PARADIGM §方法 2",
    "mechanical_transition": "chapter PARADIGM §方法 3", "close": "chapter PARADIGM §方法 4",
    "stage_map": "chapter PARADIGM §方法 4", "questions": "chapter PARADIGM §方法 4",
    "no_catchall": "chapter PARADIGM §方法 3",
    "challenge": "chapter PARADIGM 理论 6、§方法 1（先回忆 / 本章 boss / 开章挑战）· devices I ⚔️（E-CHAP-32）",
    "mind_card": "chapter PARADIGM §方法 4（心智卡）· devices I 🧠（E-CHAP-33）",
    "world_model": "chapter PARADIGM §方法 4（世界模型 vN / 现在去打）（E-CHAP-34）",
    "block_summary": "chapter PARADIGM §方法 4（🌳 块小结）· book PARADIGM 总结树（E-CHAP-36）",
    "route_line": "section PARADIGM §方法 1（🗺️ 路线）· devices I 🗺️（E-SEC-40）",
    "slide_narration": "devices PARADIGM 理论 5 / J 出处", "footnote_defs": "devices PARADIGM J 出处",
    "depth_hint": "devices PARADIGM J 深度提示", "aside_only_content": "devices PARADIGM 理论 3",
    "reality_intro": "devices PARADIGM C 🔍", "figure_candidates": "devices PARADIGM D 用哪张",
    "figures_per_section": "devices PARADIGM D 用哪张", "figure_format": "devices PARADIGM D 怎么用",
    "figure_context": "devices PARADIGM D 怎么用", "math_notation": "devices PARADIGM E 记法",
    "code_chunks": "devices PARADIGM F", "heavy_device_ratio": "devices PARADIGM F 何时不用",
    "block_vocab": "devices PARADIGM I 词汇表", "guide_line": "devices PARADIGM I 🧭",
    "guide_minutes": "devices PARADIGM I 🧭（时长口径）", "texture_floor": "devices PARADIGM I 质地下限",
    "aside_budget": "devices PARADIGM I 预算", "breather_length": "devices PARADIGM I ☕",
    "master_length": "devices PARADIGM I 🎓", "def_lines": "devices PARADIGM I 📌",
    "exam_block": "devices PARADIGM I 🎯", "clip_lines": "devices PARADIGM I 📎",
    "external_marks": "devices PARADIGM K",
    "prereq_no_forward": "section variants/prereq.md V-PRE-19（只能后引前）",
    "prereq_shape": "section variants/prereq.md「前置节长这样」· V-PRE-09/12/13/20",
    "prereq_backref": "section PARADIGM §方法 2 入口（前置回指）· E-SEC-41",
    "files": "book PARADIGM 方法 3 格式统一", "front_first_page": "book PARADIGM 方法 1 第一页",
    "apex_front_back": "book PARADIGM 方法 1 终极理解 / 方法 4", "prereq_covers_external": "book PARADIGM 方法 1 前置",
    "front_mermaid": "book PARADIGM 方法 1 大图", "book_skeleton": "book PARADIGM 方法 1（大图 = 全书骨架；节点级树不进书）",
    "volume_synthesis": "book PARADIGM 方法 5 volume", "book_map": "book PARADIGM 方法 6 map",
    "generator_chapters": "book PARADIGM 方法 1 生成元",
    "toc_matches": "book PARADIGM 方法 1 目录", "reading_guide_once": "book PARADIGM 方法 1 读法",
    "front_elements": "book PARADIGM 方法 1", "front_length": "book PARADIGM 方法 1 压缩",
    "stats": "book PARADIGM 方法 1 规模", "case_thread": "book PARADIGM 方法 2",
    "xref_format": "book PARADIGM 方法 3 格式统一", "xref_targets": "book PARADIGM 方法 3 终检",
    "reverse_index": "book PARADIGM 方法 4 附录", "node_index": "book PARADIGM 方法 4 附录",
    "keyword_index": "book PARADIGM 方法 4 附录", "exam_appendix": "book PARADIGM 方法 4 附录",
    "appendix_narrow": "book PARADIGM 理论 3", "generators_in_book": "tree PARADIGM §方法 3",
    "nodes": "spine / section PARADIGM", "apex": "spine PARADIGM", "spine_sync": "spine PARADIGM（cells）",
    "ids": "tree / spine PARADIGM", "sources": "devices PARADIGM J 出处", "position": "section PARADIGM",
    "coverage_table": "audit PARADIGM 方法 2a", "no_exempt_in_body": "chapter PARADIGM",
    "exam_map": "tree / spine PARADIGM", "exercises": "audit PARADIGM 方法 1（覆盖清单）",
    "deps": "spine PARADIGM（order）· core PARADIGM（读者模型）", "hollow": "section PARADIGM",
    "baseline": "audit PARADIGM 方法 2b", "strip_blocks": "audit PARADIGM 方法 3",
}

R = {c: {"fail": [], "warn": [], "info": [], "skip": None, "ran": False} for c in CHECKS}


def fail(c, m):
    R[c]["ran"] = True
    R[c]["fail"].append(m)


def warn(c, m):
    R[c]["ran"] = True
    R[c]["warn"].append(m)


def info(c, m):
    R[c]["ran"] = True
    R[c]["info"].append(m)


def skip(c, why):
    R[c]["skip"] = why


# ---------------------------------------------------------------- 文本工具
ID_RE = re.compile(r"\bN-\d+\b")
FENCE_RE = re.compile(r"^\s*```")
H_SEC_RE = re.compile(r"^## §(\d+)\.(\d+)\s+(.+?)\s*\(([^()]+)\)\s*$")
H_SEC_LOOSE = re.compile(r"^## §")
COMMENT_RE = re.compile(r"^<!--\s*nodes:\s*(.*?)\s*\|\s*sources:\s*(.*?)\s*-->\s*$")
FNDEF_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
FNREF_RE = re.compile(r"\[\^([^\]]+)\](?!:)")
IMG_RE = re.compile(r"!\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)\)")  # 图注里可含 E[n] 这类方括号
PAGE_RE = re.compile(r"(?:([A-Za-z][\w-]*)\s+)?\bp\.?\s*(\d+)(?:\s*[-–~]\s*p?\.?\s*(\d+))?")
CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.'+-]*")
SENT_SPLIT = re.compile(r"(?<=[。？！；?!;])")
EXTERNAL_BLOCKS = {"☕", "🎓", "💡", "📍"}
ASIDE_BLOCKS = {"☕", "🎓", "💡", "📍", "🔍"}
CALIB = {"📌", "📏", "🎯"}
ROLE_NAME = {m: name for m, _, name, _ in BLOCK_ROLES}
ACTION_RE = re.compile(r"[会能][^。；\n]{0,8}(?:算|判|写|推|说|认|选|验|估|读|画|拆|排|指|用|"
                       r"按|查|默|列|换|解|把|试|定位|重算)|算出|写出|推出|说出|认出|判断|重算")
VAGUE_RE = re.compile(r"理解|熟悉|掌握")
RATE = {"轻": 300, "中": 250, "重": 180}
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2705]")
GAME_LINE_RE = re.compile(r"^\*\*(?:\u672C\u7AE0 boss|\u73B0\u5728\u53BB\u6253|\u4E16\u754C\u6A21\u578B\s*v\d+|\u5148\u56DE\u5FC6)")
REVEAL_CMT_RE = re.compile(r"^\s*<!--\s*reveal\s*-->\s*$")


def zi(s):
    """字数：CJK 字 + 拉丁词各计 1。"""
    return len(CJK_RE.findall(s)) + len(WORD_RE.findall(CJK_RE.sub(" ", s)))


def plain(s):
    """去掉行内记号，留可读文字（用于句段、词表扫描）。"""
    s = re.sub(r"\\\((.*?)\\\)", " ", s)
    s = re.sub(r"(?<!\$)\$(?!\$)[^$\n]+\$", " ", s)
    s = re.sub(r"`[^`]*`", " ", s)
    s = IMG_RE.sub(" ", s)
    s = re.sub(r"\[([^\]^][^\]]*)\]\([^)]*\)", r"\1", s)
    s = FNREF_RE.sub("", s)
    s = re.sub(r"\*\*|__", "", s)
    s = re.sub(r"^\s*>\s?", "", s)
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)
    return s.strip()


def sentences(text):
    return [x.strip() for x in SENT_SPLIT.split(text) if x.strip()]


def parse_pages(text, default_short=None):
    """'L4 p27-29; T1-sol p1-2, p5' → {(short, page)}"""
    out, short = set(), default_short
    for m in PAGE_RE.finditer(text or ""):
        if m.group(1):
            short = m.group(1)
        if not short:
            continue
        a = int(m.group(2))
        b = int(m.group(3)) if m.group(3) else a
        if b < a:
            a, b = b, a
        if b - a > 400:
            continue
        out |= {(short, p) for p in range(a, b + 1)}
    return out


def bigrams(s):
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def overlap(a, b):
    A, B = bigrams(a), bigrams(b)
    return len(A & B) / max(1, min(len(A), len(B)))


def cut(items, n=8):
    items = list(items)
    s = "; ".join(str(x) for x in items[:n])
    return s + (f"; 另有 {len(items) - n} 处" if len(items) > n else "")


# ---------------------------------------------------------------- 文档模型
class Block:
    def __init__(self, marker, start, end, lines):
        self.marker, self.start, self.end, self.lines = marker, start, end, lines
        self.text = "\n".join(lines)
        self.body = "\n".join(plain(x) for x in lines)


class Doc:
    """一个 md 文件：逐行分类 + 块 + 脚注。"""

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.text = open(path, encoding="utf-8").read()
        self.lines = self.text.split("\n")
        self.kind = []
        infence, inmath, flang = False, False, ""
        for ln in self.lines:
            st = ln.strip()
            if FENCE_RE.match(ln):
                if not infence:
                    flang = st[3:].strip().lower()
                self.kind.append("mermaid" if flang == "mermaid" else "code")
                infence = not infence
                continue
            if infence:
                self.kind.append("mermaid" if flang == "mermaid" else "code")
                continue
            if st == "$$" or (st.startswith("$$") and not inmath and not st.endswith("$$")):
                self.kind.append("math")
                inmath = not inmath
                continue
            if inmath:
                self.kind.append("math")
                if st.endswith("$$"):
                    inmath = False
                continue
            if st.startswith("$$") and st.endswith("$$") and len(st) > 4:
                self.kind.append("math")
            elif not st:
                self.kind.append("blank")
            elif st.startswith(">"):
                self.kind.append("quote")
            elif st.startswith("#"):
                self.kind.append("heading")
            elif st.startswith("<!--"):
                self.kind.append("comment")
            elif FNDEF_RE.match(st):
                self.kind.append("fndef")
            elif st.startswith("|"):
                self.kind.append("table")
            elif IMG_RE.fullmatch(st):
                self.kind.append("image")
            elif re.match(r"^(?:[-*+]|\d+[.)])\s+", st):
                self.kind.append("list")
            else:
                self.kind.append("prose")
        self.blocks = []
        i = 0
        while i < len(self.lines):
            if self.kind[i] == "quote":
                j = i
                while j + 1 < len(self.lines) and self.kind[j + 1] == "quote":
                    j += 1
                first = self.lines[i].strip()[1:].strip()
                mk = next((m for m in MARKERS if first.startswith(m)), None)
                if mk is None and first and EMOJI_RE.match(first[0]):
                    mk = "?" + first[0]
                self.blocks.append(Block(mk, i, j + 1, self.lines[i:j + 1]))
                i = j + 1
            else:
                i += 1
        # 出手块与行（⚔️ / 揭晓 / 🗺️ / 🧠 / boss · 现在去打 · 世界模型 · 先回忆）：字数、时长、节首句类检查跳过
        self.game = set()
        for b in self.blocks:
            head = b.lines[0].lstrip(">").strip()
            if b.marker in GAME_MARKERS or head.startswith("**揭晓**") or re.match(r"^🤔\s*先猜", head):
                self.game |= set(range(b.start, b.end))
        self.route = {i for b in self.blocks if b.marker in ("🗺️", "🗺") for i in range(b.start, b.end)}
        for i, ln in enumerate(self.lines):
            if (self.kind[i] == "prose" and GAME_LINE_RE.match(ln.strip())) or REVEAL_CMT_RE.match(ln):
                self.game.add(i)
                if ln.strip().startswith("**世界模型"):      # 世界模型 vN 的拼图行（紧跟的列表）同样不算正课
                    j = i + 1
                    while j < len(self.lines) and self.kind[j] == "list":
                        self.game.add(j)
                        j += 1
        self.fndefs = {}
        for i, ln in enumerate(self.lines):
            m = FNDEF_RE.match(ln.strip())
            if m and self.kind[i] == "fndef":
                self.fndefs[m.group(1)] = (m.group(2), i)
        self.fnrefs = [(m.group(1), i) for i, ln in enumerate(self.lines)
                       if self.kind[i] not in ("fndef", "code", "mermaid") for m in FNREF_RE.finditer(ln)]

    def block_at(self, i):
        for b in self.blocks:
            if b.start <= i < b.end:
                return b
        return None

    def blocks_in(self, a, b):
        return [x for x in self.blocks if a <= x.start < b]

    def prose_in(self, a, b, kinds=("prose", "list")):
        return [(i, self.lines[i]) for i in range(a, b) if self.kind[i] in kinds]


class Section:
    pass


class Chapter(Doc):
    def __init__(self, path, num):
        super().__init__(path)
        self.num = num
        self.sections = []
        h2 = [i for i, ln in enumerate(self.lines) if ln.startswith("## ") and self.kind[i] == "heading"]
        fn_start = next((i for i in range(len(self.lines)) if self.kind[i] == "fndef"
                         and all(k in ("fndef", "blank") for k in self.kind[i:])), len(self.lines))
        self.body_end = fn_start
        for k, i in enumerate(h2):
            ln = self.lines[i]
            if not H_SEC_LOOSE.match(ln):
                continue
            s = Section()
            s.ch, s.line, s.raw = self, i, ln
            m = H_SEC_RE.match(ln)
            s.ok = bool(m)
            if m:
                s.a, s.b, s.title, s.en = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
            else:
                mm = re.match(r"^## §(\d+)\.(\d+)\s*(.*)$", ln)
                s.a, s.b = (int(mm.group(1)), int(mm.group(2))) if mm else (num, 0)
                s.title, s.en = (mm.group(3) if mm else ln[3:]), ""
            s.num = f"{s.a}.{s.b}"
            s.key = (s.a, s.b)
            s.end = min(next((x for x in h2 if x > i), len(self.lines)), fn_start)
            nxt = i + 1
            cm = COMMENT_RE.match(self.lines[nxt].strip()) if nxt < len(self.lines) else None
            s.comment_ok = bool(cm)
            s.nodes = ID_RE.findall(cm.group(1)) if cm else []
            s.sources_str = cm.group(2) if cm else ""
            s.pages = parse_pages(s.sources_str)
            s.start = i
            s.blocks = self.blocks_in(i, s.end)
            s.chars = sum(len(self.lines[x]) for x in range(i, s.end) if x not in self.game)
            body_lines = [self.lines[x] for x in range(i + 1, s.end)
                          if self.kind[x] not in ("comment", "fndef") and x not in self.game]
            s.zi = zi("\n".join(plain(x) for x in body_lines))
            s.guide = next((b for b in s.blocks if b.marker == "🧭"), None)
            self.sections.append(s)
        first = self.sections[0].line if self.sections else len(self.lines)
        last_end = self.sections[-1].end if self.sections else len(self.lines)
        self.open = (0, first)
        self.close = (last_end, fn_start)
        self.open_h2 = [i for i in h2 if i < first]
        self.close_h2 = [i for i in h2 if last_end <= i < fn_start]


# ---------------------------------------------------------------- 加载
class WS:
    def __init__(self, ws, only):
        self.ws, self.only = ws, only
        self.book = os.path.join(ws, "book")
        tp = os.path.join(ws, "tree.json")
        self.tree = json.load(open(tp, encoding="utf-8")) if os.path.exists(tp) else None
        self.nodes = {n["id"]: n for n in (self.tree or {}).get("nodes", [])}
        sp = os.path.join(ws, "spine.md")
        self.spine_header, self.spine_ch = "", []
        if os.path.exists(sp) and parse_spine:
            self.spine_header, self.spine_ch = parse_spine(open(sp, encoding="utf-8").read())
        self.spine_sec = {}
        for c in self.spine_ch:
            mach = {r[0]: r for r in c["machine"]}
            for r in c["main"]:
                if len(r) < 2:
                    continue
                mr = mach.get(r[0])
                # 分量格一节含多个节点时写成 "0/30"：取各节点分量的最大值（只取首个数会把重节误判成背景）
                ws_ = [int(x) for x in re.findall(r"\d+", mr[1])] if mr and len(mr) > 1 else []
                self.spine_sec[r[0]] = {
                    "ch": c["num"], "nodes": ID_RE.findall(r[1]), "unlock": r[4] if len(r) > 4 else "",
                    "weight": max(ws_) if ws_ else None,
                    "load": (mr[2].strip() if mr and len(mr) > 2 and mr[2].strip() in RATE else "中"),
                    "sources": mr[3] if mr and len(mr) > 3 else "",
                    "figs": [x.strip() for x in re.split(r"[,，（(]", mr[4]) if x.strip().endswith(".png")], "figs_note": mr[4]
                    if mr and len(mr) > 4 else [],
                }
        self.volumes = parse_volumes(open(sp, encoding="utf-8").read()) \
            if os.path.exists(sp) and parse_volumes else []
        self.spine_order = {}
        for k, sec in enumerate(self.spine_sec):
            a, b = sec.split(".")
            self.spine_order[sec] = (int(a), int(b))
        rp = os.path.join(ws, "reader.md")
        self.reader = open(rp, encoding="utf-8").read() if os.path.exists(rp) else None
        m = re.search(r"^考试信息[:：]\s*(.*)$", self.reader or "", re.M)
        self.exam = bool(m and m.group(1).strip() and not m.group(1).strip().startswith("无"))
        self.exam_text = m.group(1).strip() if m else ""
        mp = os.path.join(ws, "raw", "_manifest.json")
        self.manifest = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else None
        self.mats = {x["short"]: x for x in (self.manifest or {}).get("materials", [])}
        fp = os.path.join(ws, "raw", "_figures.json")
        self.figs = json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else None
        self._raw = None
        # 书稿
        self.front = self.back = self.map = None
        self.chapters, self.extra = [], []
        self.synths = {}          # 卷串讲 NNv-<slug>.md：{NN: Doc}（不是章，章级结构检查不跑）
        if os.path.isdir(self.book):
            for f in sorted(os.listdir(self.book)):
                if not f.endswith(".md"):
                    continue
                p = os.path.join(self.book, f)
                sm = re.match(r"^(\d{2})v-([a-z0-9][a-z0-9-]*)\.md$", f)
                if f == "00-front.md":
                    self.front = Doc(p)
                elif f == "99-back.md":
                    self.back = Doc(p)
                elif f == "98-map.md":
                    self.map = Doc(p)
                elif sm:
                    if only is None:
                        self.synths[int(sm.group(1))] = Doc(p)
                else:
                    m = re.match(r"^(\d{2})-([a-z0-9][a-z0-9-]*)\.md$", f)
                    if m and 1 <= int(m.group(1)) <= 97:
                        if only is None or int(m.group(1)) == only:
                            self.chapters.append(Chapter(p, int(m.group(1))))
                    else:
                        self.extra.append(f)
        self.secs = [s for c in self.chapters for s in c.sections]
        self.sec_by = {s.num: s for s in self.secs}
        # 节点落点：书中节注释优先，否则 spine
        self.land = {}
        for s in self.secs:
            for n in s.nodes:
                self.land.setdefault(n, s.key)
        self.plan = {}
        for sec, d in self.spine_sec.items():
            for n in d["nodes"]:
                self.plan.setdefault(n, self.spine_order[sec])

    @property
    def raw(self):
        if self._raw is None:
            txt = []
            for p in glob.glob(os.path.join(self.ws, "raw", "*.txt")):
                txt.append(open(p, encoding="utf-8", errors="ignore").read())
            vn = os.path.join(self.ws, "raw", "_visual_notes.md")
            if os.path.exists(vn):
                txt.append(open(vn, encoding="utf-8").read())
            self._raw = "\n".join(txt).lower()
        return self._raw


def tier(ws, ch, s):
    if s.guide:
        m = re.search(r"本节[:：]\s*(核心|常规|背景)", s.guide.text)
        if m:
            return m.group(1)
    if s.num in ch.core_secs:
        return "核心"
    d = ws.spine_sec.get(s.num)
    if d and d["weight"] == 0:
        return "背景"
    return "常规"


def load_of(ws, s):
    d = ws.spine_sec.get(s.num)
    return d["load"] if d else "中"


def section_minutes(ch, s, load):
    a, b = s.start + 1, s.end
    body = "\n".join(plain(ch.lines[i]) for i in range(a, b)
                     if ch.kind[i] not in ("comment", "fndef", "mermaid", "image") and i not in ch.game and not
                     (ch.kind[i] == "quote" and ch.lines[i].lstrip(">").strip().startswith("🧭")))
    tables = sum(1 for i in range(a, b) if ch.kind[i] == "table" and (i == a or ch.kind[i - 1] != "table"))
    ascii_figs = 0
    i = a
    while i < b:
        if ch.kind[i] == "code" and FENCE_RE.match(ch.lines[i]):
            j = i + 1
            while j < b and not FENCE_RE.match(ch.lines[j]):
                j += 1
            if any(re.search(r"[│┌└┐┘─├┤┬┴┼+|]-{2,}|[│┌└┐┘─├┤]", ch.lines[x]) for x in range(i + 1, j)):
                ascii_figs += 1
            i = j + 1
        else:
            i += 1
    return math.ceil(zi(body) / RATE[load]) + tables + ascii_figs


def region_zi(ch, a, b):
    return zi("\n".join(plain(ch.lines[i]) for i in range(a, b)
                        if ch.kind[i] in ("prose", "list", "quote", "heading", "table") and i not in ch.game
                        and not ch.lines[i].lstrip(">").strip().startswith("🧭")))


# ---------------------------------------------------------------- core
BANNED = ["总之", "值得注意", "总结一下", "接下来我们将", "让我们", "非常", "大家都知道", "众所周知", "实际上",
          "我们", "开发者", "同学们", "不难看出", "显而易见"]
META = ["对照式发散", "痛点-方案-效果", "raise + reject", "插件式补充", "结构化叙事",
        "入口问题", "凭什么现在能懂", "留下的新问题", "生成元", "脊柱", "四格"]
PUSH_RE = re.compile(r"看一眼|去看|参见|详见|打开|这里不重复|此处不重复|不再重复|推导见|自己打印|请参考|参考课件")
SAME_RE = re.compile(r"[与同和]\s*§\s*\d+(?:\.\d+)?\s*(?:相同|一样|类似).{0,8}(?:不重复|不再|略)")
COMPARE_RE = re.compile(r"更(?:高级|好|快|强|省事|优|高效|先进|合理|准确|稳定)")
REASON_RE = re.compile(r"因为|由于|在于|原因|所以|于是|之所以|因此|——|：|:")
YEAR_RE = re.compile(r"(?<!\d)(1[89]\d\d|20\d\d)\s*年?(?!\d)")
EXAM_RE = re.compile(r"必考|高频|押题|常考|分值|满分|卷面|题型构成|考场|考试时长|开卷|闭卷|"
                     r"\d+\s*分(?![钟布位析配量母子类支段别解成之歧组担摊块散离派享工流区辨叉开清裂])|"
                     r"\d{4}-\d{2}-\d{2}|\d{1,2}\s*月\s*\d{1,2}\s*日")


def text_units(ch, a, b, with_blocks=True, kinds=("prose", "list")):
    """(行号, 纯文本) — 正文与块，跳过代码、公式、注释、脚注定义。"""
    ks = set(kinds) | ({"quote"} if with_blocks else set())
    return [(i, plain(ch.lines[i])) for i in range(a, b) if ch.kind[i] in ks]


def check_core(ws, docs):
    # reader_md
    if ws.reader is None:
        fail("reader_md", "reader.md 不存在 —— tree 开跑前就要有，先跑 core 方法 1 推断读者")
    else:
        errs = []
        for k in ("起点", "目的", "范围", "发散", "考试信息"):
            if not re.search(rf"^{k}[:：]\s*\S", ws.reader, re.M):
                errs.append(f"缺「{k}:」行")
        m = re.search(r"divergence_layers\s*=\s*(\d+)", ws.reader)
        if not m or not 0 <= int(m.group(1)) <= 3:
            errs.append("divergence_layers 缺失或不在 0–3")
        m = re.search(r"divergence_breadth\s*=\s*(\d+)", ws.reader)
        if not m or not 1 <= int(m.group(1)) <= 8:
            errs.append("divergence_breadth 缺失或不在 1–8")
        m = re.search(r"relevance_threshold\s*=\s*(\S+)", ws.reader)
        if not m or m.group(1).strip("·") not in ("严格", "中等", "宽松"):
            errs.append("relevance_threshold 缺失或不在 {严格,中等,宽松}")
        for e in errs:
            fail("reader_md", e)
        if not errs:
            info("reader_md", f"字段齐全；考试信息{'已声明' if ws.exam else '无'}")

    for ch in ws.chapters:
        tag = f"第 {ch.num} 章"
        total = len(ch.text) or 1
        # external_share
        ext = sum(len(b.text) for b in ch.blocks if b.marker in EXTERNAL_BLOCKS)
        ext += sum(len(ch.lines[i]) for i in range(len(ch.lines)) if "⚡" in ch.lines[i] and ch.kind[i] != "quote")
        share = ext / total
        (warn if share > 0.25 else info)("external_share", f"{tag} 材料外补充 {share:.1%}" +
                                         (" > 25%，先查正文是否写薄" if share > 0.25 else ""))
        # strip_external_coverage
        for s in ch.sections:
            prose_refs, ext_refs = set(), set()
            for i in range(s.start, s.end):
                b = ch.block_at(i)
                refs = set(FNREF_RE.findall(ch.lines[i]))
                if b and b.marker in EXTERNAL_BLOCKS:
                    ext_refs |= refs
                else:
                    prose_refs |= refs
            only = ext_refs - prose_refs
            if only:
                fail("strip_external_coverage", f"§{s.num} 出处 {', '.join(sorted(only))} 只出现在材料外块里 —— "
                                                f"材料内容要写进正文")
            rest = zi("\n".join(t for _, t in text_units(ch, s.start + 2, s.end, with_blocks=False)
                                if "⚡" not in t))
            if s.nodes and rest < 40:
                fail("strip_external_coverage", f"§{s.num} 删掉材料外块与 ⚡ 句后正文只剩 {rest} 字")
        info("strip_external_coverage", f"{tag} {len(ch.sections)} 节已做删块对账")

        units = text_units(ch, 0, ch.body_end) + [(i, plain(ch.lines[i])) for i in range(ch.body_end)
                                                  if ch.kind[i] == "heading"]
        shorts = set(ws.mats)
        for i, t in units:
            loc = f"{ch.name}:L{i + 1}"
            # self_sufficient
            if SAME_RE.search(t) or (PUSH_RE.search(t) and (
                    re.search(r"课件|幻灯片|讲义|courses/|\.pdf|\.ipynb|\.pptx|文件", t) or
                    any(re.search(rf"(?<![\w-]){re.escape(sh)}(?![\w-])", t) for sh in shorts))):
                fail("self_sufficient", f"{loc} 推诿句「{t[:40]}」—— 把要的内容就地写出")
            # supplement_history（⚡ 行）
            if "⚡" in t and YEAR_RE.search(t):
                fail("supplement_history", f"{loc} 材料外句含年份「{YEAR_RE.search(t).group(0)}」")
            # banned_words
            for w in BANNED:
                if w in t:
                    fail("banned_words", f"{loc} 「{w}」: {t[:36]}")
                    break
            # meta_narrative
            for w in META:
                if w in t:
                    fail("meta_narrative", f"{loc} 内部代号/技法名「{w}」")
            if "🧠" in ch.lines[i] and i not in ch.game:      # 🧠 心智卡（收章第一块）不算旧版残留
                fail("meta_narrative", f"{loc} 旧版残留 🧠")
            # exam_logistics
            m = EXAM_RE.search(t)
            if m:
                fail("exam_logistics", f"{loc} 考务/重要度字样「{m.group(0)}」")
            # comparatives
            for m in COMPARE_RE.finditer(t):
                tail = t[m.end():m.end() + 60]
                nxt = ch.lines[i + 1] if i + 1 < len(ch.lines) else ""
                if not REASON_RE.search(tail) and not REASON_RE.search(plain(nxt)[:60]):
                    warn("comparatives", f"{loc} 「{t[max(0, m.start() - 8):m.end() + 8]}」附近没见原因 —— 自查三问")
        for b in ch.blocks:
            if b.marker in EXTERNAL_BLOCKS:
                if YEAR_RE.search(b.body):
                    fail("supplement_history", f"{ch.name}:L{b.start + 1} {b.marker} 块含年份「{YEAR_RE.search(b.body).group(0)}」")
                if re.search(r"[“\"「][^”\"」]{4,}[”\"」]\s*[—-]{1,2}\s*\S", b.body) or re.search(r"\S{2,8}(?:曾说|说过|回忆)", b.body):
                    warn("supplement_history", f"{ch.name}:L{b.start + 1} {b.marker} 块疑似人名引语")
        # sentence_shape
        long_s, long_p = [], []
        para, para_start = [], None
        for i in range(ch.body_end + 1):
            k = ch.kind[i] if i < ch.body_end else "blank"
            if k == "prose":
                if not para:
                    para_start = i
                para.append(plain(ch.lines[i]))
                continue
            if para:
                ptxt = "".join(para)
                if zi(ptxt) > 140:
                    long_p.append(f"L{para_start + 1}({zi(ptxt)}字)")
                for sn in sentences(ptxt):
                    if zi(sn) > 30:
                        long_s.append(f"L{para_start + 1}")
                para = []
        for i, t in units:
            if i in ch.route:          # 🗺️ 路线是箭头短语，不是句子
                continue
            for m in re.finditer(r"(?:[^、，。；：\s]{1,14}、){2,}[^、，。；：\s]{1,14}", t):
                items = m.group(0).split("、")
                termish = sum(1 for x in items if re.search(r"[A-Za-z]", x) or
                              any(n.get("name", "\0") in x for n in ws.nodes.values()))
                (fail if termish >= 2 else warn)(
                    "sentence_shape", f"{ch.name}:L{i + 1} 顿号串 {len(items)} 项「{m.group(0)[:30]}」"
                                      + ("（术语串，拆成有关系的句子）" if termish >= 2 else ""))
        if long_p:
            warn("sentence_shape", f"{ch.name} 段 >140 字 {len(long_p)} 处: {cut(long_p, 6)}")
        if long_s:
            warn("sentence_shape", f"{ch.name} 句 >30 字 {len(long_s)} 句（复核是否该拆）")
        # list_density
        for s in ch.sections:
            tot = sum(len(ch.lines[i]) for i in range(s.start + 2, s.end) if ch.kind[i] in ("prose", "list", "table"))
            lt = sum(len(ch.lines[i]) for i in range(s.start + 2, s.end) if ch.kind[i] in ("list", "table"))
            if tot and lt / tot > 0.5:
                warn("list_density", f"§{s.num} 列表/表格占正文 {lt / tot:.0%} —— 讲解主体应是推理散文")
        info("list_density", f"{tag} 已量")

    # front/back 也查禁词、考务、元叙事
    for d in docs:
        for i, ln in enumerate(d.lines):
            if d.kind[i] in ("code", "fndef", "comment"):
                continue
            t = plain(ln)
            m = EXAM_RE.search(t)
            if m and not (d is ws.back and re.search(r"往年题|题号", t)):
                fail("exam_logistics", f"{d.name}:L{i + 1} 考务/重要度字样「{m.group(0)}」")
            for w in META:
                if w in t:
                    fail("meta_narrative", f"{d.name}:L{i + 1} 内部代号「{w}」")
            if d.kind[i] == "mermaid" and re.search(r'"[^"]*(?:external|生成元)[^"]*"', ln):
                fail("meta_narrative", f"{d.name}:L{i + 1} 图标签用了内部代号")
    for c in ("banned_words", "self_sufficient", "supplement_history", "comparatives", "sentence_shape",
              "meta_narrative", "exam_logistics"):
        if ws.chapters or docs:
            R[c]["ran"] = True

    # term_first_use：节点首次出现处中英并列
    hits = 0
    for nid, key in ws.land.items():
        n = ws.nodes.get(nid)
        if not n or not n.get("name") or not n.get("en"):
            continue
        name, en = n["name"], n["en"]
        if len(name) < 3 and not re.search(r"[A-Za-z]", name):
            continue
        s = ws.sec_by.get(f"{key[0]}.{key[1]}")
        if not s:
            continue
        found = None
        for t in ws.secs:
            if t.key > key:
                break
            pos = t.ch.text.find(name, sum(len(x) + 1 for x in t.ch.lines[:t.start + 2]))
            endpos = sum(len(x) + 1 for x in t.ch.lines[:t.end])
            if 0 <= pos < endpos:
                found = (t, pos)
                break
        if not found:
            continue
        hits += 1
        t, pos = found
        win = t.ch.text[max(0, pos - 150):pos + len(name) + 150].lower()
        if en.lower() not in win:
            fail("term_first_use", f"{nid}「{name}」首次出现在 §{t.num}，附近没有英文原名「{en}」")
    info("term_first_use", f"核对 {hits} 个节点名的首次出现")


def check_tokens(ws):
    if not glob.glob(os.path.join(ws.ws, "raw", "*.txt")):
        skip("ungrounded_tokens", "raw/*.txt 不存在，无法回查")
        return
    raw = ws.raw
    raw_nums = set(re.findall(r"\d+(?:\.\d+)?", raw))
    bad = []
    for ch in ws.chapters:
        for i in range(ch.body_end):
            if ch.kind[i] not in ("prose", "list", "quote", "table"):
                continue
            b = ch.block_at(i)
            if b and b.marker in EXTERNAL_BLOCKS | {"✅", "🧭"}:
                continue
            ln = ch.lines[i]
            if "⚡" in ln or "编个数" in ln or re.search(r"[=×÷≈]|\\times|\\approx", ln):
                continue
            t = plain(ln)
            t = re.sub(r"§\s*\d+(?:\.\d+)?|第\s*\d+\s*章|N-\d+|[A-Za-z][\w-]*\s+p\d+(?:-\d+)?", " ", t)
            for num in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", t):
                if len(num.replace(".", "")) < 2 or num in raw_nums:
                    continue
                if num.startswith("0.") and num[1:] in raw:
                    continue
                bad.append(f"{ch.name}:L{i + 1} {num}")
            for w in re.findall(r"(?<![A-Za-z])[A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]+)*", t):
                if w.lower() not in raw and not any(w.lower() in (n.get("en") or "").lower() for n in ws.nodes.values()):
                    bad.append(f"{ch.name}:L{i + 1} {w}")
    if bad:
        warn("ungrounded_tokens", f"{len(bad)} 个数字/拉丁专名在 raw/ 搜不到且句边无 ⚡/算式/编个数: {cut(bad, 10)}"
                                  " —— 逐个核：删、改定性、补算式或加 ⚡")
    else:
        info("ungrounded_tokens", "正文数字与专名都能回 raw/ 搜到或有豁免")


# ---------------------------------------------------------------- section
GOAL_PREFIX = re.compile(r"^>\s*✅\s*(?:\*\*)?[^：:*]*?(?:\*\*)?[：:]\s*")


def first_sentences(ch, s, n=2):
    out = []
    for i in range(s.start + 1, s.end):
        k = ch.kind[i]
        if k in ("comment", "blank", "fndef") or i in ch.game:      # 🗺️ 路线行不是节首句
            continue
        if k == "quote" and ch.lines[i].lstrip(">").strip().startswith("🧭"):
            continue
        if k in ("prose", "list", "quote"):
            for sn in sentences(plain(ch.lines[i]).lstrip("🤔").strip()):
                out.append((i, sn))
                if len(out) >= n:
                    return out
        else:
            break
    return out


def check_section(ws):
    succ = {}
    for nid, n in ws.nodes.items():
        for r in n.get("requires", []):
            succ.setdefault(r, []).append(nid)
    for ch in ws.chapters:
        # numbered_slots（按文件）
        slots = [i for i, ln in enumerate(ch.lines)
                 if re.match(r"^\s*(?:#{2,6}\s*|\*\*|>\s*\*\*)?\s*[①②③④⑤⑥⑦⑧⑨⑩]", ln)]
        if len(slots) >= 3:
            fail("numbered_slots", f"{ch.name} 有 {len(slots)} 个 ①②③ 式编号小标题: L{', L'.join(str(x + 1) for x in slots[:6])}")
        elif slots:
            warn("numbered_slots", f"{ch.name} 有 ①② 式编号行: L{', L'.join(str(x + 1) for x in slots)}")
        else:
            info("numbered_slots", f"{ch.name} 无编号小标题")
        exp = 1
        for s in ch.sections:
            tag = f"§{s.num}"
            # section_header
            if not s.ok:
                fail("section_header", f"{ch.name}:L{s.line + 1} 节标题不合 `## §N.M 中文 (English)`: {s.raw[:50]}")
            if s.a != ch.num:
                fail("section_header", f"{tag} 节号的章号与文件 {ch.name} 不符")
            if s.b != exp:
                fail("section_header", f"{tag} 节号不连续（应为 §{ch.num}.{exp}）")
            exp = s.b + 1
            if not s.comment_ok:
                fail("section_header", f"{tag} 标题下一行不是 `<!-- nodes: … | sources: … -->`")
            elif not s.nodes or not s.pages:
                fail("section_header", f"{tag} 节注释的 nodes 或 sources 为空/无法解析")
            for n in s.nodes:
                if ws.nodes and n not in ws.nodes:
                    fail("section_header", f"{tag} 节注释里的 {n} 不在 tree.json")
            if re.search(r"[A-Za-z][\w-]*\s+p\d+|课件", s.raw):
                fail("section_header", f"{tag} 节标题里有页码/课件字样")
            # first_sentence_not_definition / hook_terms
            fs = first_sentences(ch, s, 2)
            names = []
            for n in s.nodes:
                nd = ws.nodes.get(n, {})
                names += [x for x in (nd.get("name"), nd.get("en")) if x and len(x) >= 2]
            if fs:
                first = fs[0][1]
                if re.search(r"定义为|是指|指的是|^所谓|^让我们|^下面|^接下来|^本节", first) or \
                        any(first.startswith(x) for x in names):
                    fail("first_sentence_not_definition", f"{tag} 首句是定义/过渡: 「{first[:40]}」—— 换成画面或具体问题")
                hook = " ".join(x[1] for x in fs)
                later = []
                for n in s.nodes:
                    later += [ws.nodes.get(x, {}).get("name") for x in succ.get(n, [])]
                for x in names + [y for y in later if y and len(y) >= 3]:
                    if x and x.lower() in hook.lower():
                        fail("hook_terms", f"{tag} 钩子前两句已出现本节/后继术语「{x}」")
                        break
            else:
                fail("first_sentence_not_definition", f"{tag} 找不到节首句")
            # formula_after_prose
            fm = next((i for i in range(s.start, s.end) if ch.kind[i] == "math"), None)
            if fm is not None:
                before = sum(len(sentences(plain(ch.lines[i]))) for i in range(s.start + 2, fm)
                             if ch.kind[i] in ("prose", "list"))
                if before < 2:
                    fail("formula_after_prose", f"{tag} 首个公式块（L{fm + 1}）前只有 {before} 句叙事 —— 先给思路与画面")
            # length_band
            load = load_of(ws, s)
            lo, hi = {"轻": (150, 300), "中": (300, 500), "重": (500, 800)}[load]
            if len(s.nodes) > 1:
                hi = max(hi, 1000)
            body_zi = zi("\n".join(t for i, t in text_units(ch, s.start + 2, s.end) if i not in ch.game))
            if not lo <= body_zi <= hi:
                warn("length_band", f"{tag}（{load}）{body_zi} 字，参考 {lo}-{hi} —— 越界须有差距上的理由")
            # goal_line
            gb = [b for b in s.blocks if b.marker == "✅"]
            if not gb:
                fail("goal_line", f"{tag} 缺 ✅ 目标行")
            else:
                g = gb[-1]
                if s.blocks[-1] is not g:
                    fail("goal_line", f"{tag} ✅ 不是本节最后一块（其后还有 {s.blocks[-1].marker}）")
                if len(g.lines) > 1:
                    fail("goal_line", f"{tag} ✅ 目标行写了 {len(g.lines)} 行，应一行")
                gt = plain(GOAL_PREFIX.sub("", g.lines[0]))
                L = len(gt)
                if L > 60:
                    fail("goal_line", f"{tag} ✅ {L} 字 > 60")
                elif L > 40:
                    warn("goal_line", f"{tag} ✅ {L} 字（≤40）")
                if not ACTION_RE.search(gt):
                    fail("goal_line", f"{tag} ✅ 不是可检验动作: 「{gt[:30]}」")
                if VAGUE_RE.search(gt):
                    fail("goal_line", f"{tag} ✅ 含 理解/熟悉/掌握")
        info("section_header", f"{ch.name} {len(ch.sections)} 节")
    for c in ("first_sentence_not_definition", "hook_terms", "formula_after_prose", "length_band", "goal_line"):
        if ws.secs:
            R[c]["ran"] = True


# ---------------------------------------------------------------- chapter
def mermaid_blocks(doc, a, b):
    """[(起行, 止行, 源码)]：区间 [a, b) 内的 mermaid 围栏（源码不含围栏行）。"""
    out, i = [], a
    while i < b:
        if doc.kind[i] == "mermaid" and FENCE_RE.match(doc.lines[i]):
            j = i + 1
            while j < len(doc.lines) and not FENCE_RE.match(doc.lines[j]):
                j += 1
            out.append((i, j, "\n".join(doc.lines[i + 1:j])))
            i = j + 1
        else:
            i += 1
    return out


def skel_graph_issues(sk):
    """骨架图共有的结构问题: (fail 列表, warn 列表)。只看大概念之间的边与连通性。"""
    fails, warns = [], []
    gids = [g["id"] for g in sk["groups"]]
    adj = {g: set() for g in gids}
    for e in sk["edges"]:
        a, b = e.get("ga"), e.get("gb")
        if a not in adj or b not in adj:
            fails.append(f"边 {e['a']}→{e['b']} 的端点不在任何大概念里")
            continue
        if a == b:
            continue
        adj[a].add(b)
        adj[b].add(a)
    if gids:
        seen, stack = {gids[0]}, [gids[0]]
        while stack:
            for n in adj[stack.pop()]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        lone = [g["label"] for g in sk["groups"] if g["id"] not in seen]
        if lone:
            fails.append(f"图不连通：「{'」「'.join(lone)}」与其余大概念之间没有边")
    return fails, warns


def check_skeleton(ws, ch, oa, ob, firstp):
    """E-CHAP-04 + E-CHAP-07：开章的本章骨架（段 + `%% skeleton` 图）。算出 ch.core_secs 与 ch.skel_concepts。"""
    C = "skeleton"
    ch.core_secs, ch.skel_concepts = set(), []
    nums = [s.num for s in ch.sections]
    # 旧格式残留（带走清单 / 节路线图 / 索引表）
    ci = next((i for i in range(oa, ob) if "带走" in ch.lines[i] and ch.kind[i] in ("prose", "list")), None)
    if ci is not None and any(ch.kind[j] == "list" for j in range(ci + 1, min(ob, ci + 4))):
        fail(C, f"{ch.name}:L{ci + 1} 开章还留着平铺的「带走」清单（旧格式，骨架即带走清单）")
    blocks = mermaid_blocks(ch, oa, ob)
    for a, _b, src in blocks:
        if not skeleton_figure.is_skeleton(src) and re.search(r'[\[\(\{]\s*"?\s*§\s*\d', src):
            fail(C, f"{ch.name}:L{a + 1} 开章还留着「§ 开头标签」的节路线图（旧格式，换成骨架图）")
    for i in range(oa, ob):
        if ch.kind[i] == "table" and re.match(r"^\|\s*§\s*\|", ch.lines[i].strip()):
            fail(C, f"{ch.name}:L{i + 1} 开章还留着「| § |」索引表（旧格式）")
            break
    # 骨架段
    li = next((i for i in range(oa, ob) if "本章骨架" in ch.lines[i] and ch.kind[i] in ("prose", "list", "quote")), None)
    para = ""
    if li is None:
        fail(C, f"{ch.name} 开章缺「本章骨架」引导段（`**本章骨架**　<连词成句的一段话>`）")
    else:
        j, buf = li, []
        while j < ob and ch.kind[j] in ("prose", "list", "quote") and not (j > li and "%% skeleton" in ch.lines[j]):
            buf.append(plain(ch.lines[j]))
            j += 1
        para = re.sub(r"^\s*本章骨架\s*[:：]?\s*", "", "\n".join(buf))
        n = zi(para)
        if n < 60 or n > 260:
            warn(C, f"{ch.name} 骨架段 {n} 字（约 80–160 字为宜）")
        if "🎯" in para:
            fail(C, f"{ch.name} 骨架段用了 🎯（🎯 只留给考点块）")
    # 骨架图
    sks = [(a, b, src) for a, b, src in blocks if skeleton_figure.is_skeleton(src)]
    if not sks:
        fail(C, f"{ch.name} 开章缺骨架图（首行 `%% skeleton` 的 mermaid）")
        return
    a, _b, src = sks[0]
    if len(sks) > 1:
        warn(C, f"{ch.name} 开章有 {len(sks)} 张骨架图，只认第一张")
    if firstp is not None and a <= firstp + 1:
        fail(C, f"{ch.name} 骨架图应在开章场景之后（读者先有困惑，再给外框）")
    if ID_RE.search(src) or ID_RE.search(para):
        fail(C, f"{ch.name} 骨架段/图里出现节点 id（{ID_RE.search(src + para).group(0)}）")
    if "分量" in src or "分量" in para:
        fail(C, f"{ch.name} 骨架段/图里出现「分量」字样")
    sk = skeleton_figure.parse_skeleton(src)
    gs = sk["groups"]
    ch.skel_concepts = [g["label"] for g in gs]
    if len(gs) == 2 and len(nums) < 6:
        pass                                    # 节数 < 6 的短章允许 2 个大概念
    elif len(gs) == 2:
        warn(C, f"{ch.name} 骨架图只有 2 个大概念，本章 {len(nums)} 节（≥6 节应 3–6 个）")
    elif not 3 <= len(gs) <= 6:
        fail(C, f"{ch.name} 骨架图有 {len(gs)} 个大概念（subgraph），应 3–6 个（<6 节的章可 2 个）")
    if sk["loose"]:
        fail(C, f"{ch.name} 骨架图有不在任何大概念里的节点: {', '.join(l['id'] for l in sk['loose'])}")
    where = {}
    for g in gs:
        k = len(g["leaves"])
        if k == 0 or k > 5:
            fail(C, f"{ch.name} 大概念「{g['label']}」下 {k} 个子题（应 1–4 个）")
        elif k == 1:
            warn(C, f"{ch.name} 大概念「{g['label']}」下只有 1 个子题（自查它是否该并进别的大概念）")
        elif k == 5:
            warn(C, f"{ch.name} 大概念「{g['label']}」下 5 个子题（应 2–4 个）")
        for l in g["leaves"]:
            if not l["ref"] or not l["secs"]:
                fail(C, f"{ch.name} 子题「{l['label']}」没写成 `短名 · §N.M`")
                continue
            if not l["short"]:
                fail(C, f"{ch.name} 子题「{l['label']}」只有 § 没有短名")
            elif zi(l["short"]) > 12:
                warn(C, f"{ch.name} 子题短名「{l['short']}」{zi(l['short'])} 字（≤12 字）")
            for x in l["secs"]:
                if x not in nums:
                    fail(C, f"{ch.name} 子题「{l['short']}」标的 §{x} 不在本章")
                where.setdefault(x, []).append(l["short"])
                if l["core"]:
                    ch.core_secs.add(x)
    miss = [x for x in nums if x not in where]
    dup = [f"§{x}（{'、'.join(v)}）" for x, v in where.items() if len(v) > 1 and x in nums]
    if miss:
        fail(C, f"{ch.name} 骨架没挂上 §{', §'.join(miss)}（每节恰挂一片叶子；挂不上就该压成背景或挪章）")
    if dup:
        warn(C, f"{ch.name} 一节挂在多片叶子上: {'; '.join(dup)}")
    if not ch.core_secs and not miss:
        warn(C, f"{ch.name} 骨架里没有标 :::core 的叶子（承重的叶子即核心档）")
    gid = {g["id"] for g in gs}
    for e in sk["edges"]:
        if e.get("ga") not in gid or e.get("gb") not in gid or e["ga"] == e["gb"]:
            continue
        if not e["label"]:
            fail(C, f"{ch.name} 边 {e['a']}→{e['b']} 没写 `|关系词：短语|`")
        elif e["rel"] not in skeleton_figure.REL_WORDS:
            fail(C, f"{ch.name} 边 {e['a']}→{e['b']} 的关系词「{e['rel']}」不在词表（{'/'.join(skeleton_figure.REL_WORDS)}）")
        elif not e["phrase"]:
            fail(C, f"{ch.name} 边 {e['a']}→{e['b']} 只有关系词「{e['rel']}」，缺短语")
    fs, ws_ = skel_graph_issues(sk)
    for m in fs:
        fail(C, f"{ch.name} {m}")
    for m in ws_:
        warn(C, f"{ch.name} {m}")
    if para:
        flat = re.sub(r"\s+", "", para)
        absent = [c for c in ch.skel_concepts if re.sub(r"\s+", "", c) not in flat]
        if absent:
            warn(C, f"{ch.name} 骨架段没出现大概念「{'」「'.join(absent)}」（每个大概念在段中加粗出现一次，遮住图能画回来）")
    if not re.search(r"略写|不展开|只略", "\n".join(ch.lines[oa:ob])):
        warn(C, f"{ch.name} 开章没写哪些内容只略写不展开（没有就写一句「本章没有只略写的内容。」）")
    info(C, f"{ch.name} {len(gs)} 个大概念: {' / '.join(ch.skel_concepts)}；核心 §{', §'.join(sorted(ch.core_secs, key=lambda x: int(x.split('.')[1])))}")


def check_chapter(ws):
    total_ch = len(ws.spine_ch)
    for ch in ws.chapters:
        tag = f"第 {ch.num} 章"
        sp = next((c for c in ws.spine_ch if c["num"] == ch.num), None)
        # structure
        if not re.match(rf"^# 第\s*{ch.num}\s*章\s+\S", ch.lines[0]):
            fail("structure", f"{ch.name} 首行不是 `# 第 {ch.num} 章 <标题>`")
        if len(ch.open_h2) != 1:
            fail("structure", f"{ch.name} 开章不编号 h2 应恰 1 个，实为 {len(ch.open_h2)}")
        if len(ch.close_h2) != 1:
            fail("structure", f"{ch.name} 收章不编号 h2 应恰 1 个，实为 {len(ch.close_h2)}")
        if any(re.search(r"课件页|材料页|课件对照", ch.lines[i]) for i in range(len(ch.lines)) if ch.kind[i] == "table"):
            fail("structure", f"{ch.name} 含课件逐页对照表（属 audit/书尾）")
        if not ch.sections:
            fail("structure", f"{ch.name} 没有任何 `## §` 节")
        if sp and [s.num for s in ch.sections] != [r[0] for r in sp["main"]]:
            fail("structure", f"{ch.name} 节序 {[s.num for s in ch.sections]} 与 spine {[r[0] for r in sp['main']]} 不一致")
        info("structure", f"{ch.name} 已查")
        # head
        oa, ob = ch.open
        firstp = next((i for i in range(1, ob) if ch.kind[i] != "blank"), None)
        if firstp is None or ch.kind[firstp] != "prose" or not re.search(r"[？?]\s*$", plain(ch.lines[firstp])):
            fail("head", f"{ch.name} 标题后首行不是一句问句（开章先立问题）")
        gl = [b for b in ch.blocks_in(oa, ob) if b.marker == "🧭"]
        if not gl:
            fail("head", f"{ch.name} 首个 § 之前没有章首 🧭 导读条")
        else:
            g = gl[0]
            if sum(len(x) for x in ch.lines[:g.start]) > 1500:
                fail("head", f"{ch.name} 章首 🧭 不在前 1500 字内")
            if re.search(r"课件|\bp\d+|[A-Za-z][\w-]*\s+p\d+", g.text):
                fail("head", f"{ch.name} 章首 🧭 写了出处")
            if sp and overlap(g.body, sp["unlock"]) < 0.25:
                warn("head", f"{ch.name} 章首 🧭 与 spine 解锁「{sp['unlock'][:30]}」字面重合低，自查能力表述是否一致")
        # skeleton（E-CHAP-04 / E-CHAP-07）：算出 ch.core_secs（骨架里 :::core 叶子的节 = 核心档）
        check_skeleton(ws, ch, oa, ob, firstp)
        # tiers / loads
        tiers = {s.num: tier(ws, ch, s) for s in ch.sections}
        loads = [load_of(ws, s) for s in ch.sections]
        # weight_budget
        total = sum(s.chars for s in ch.sections) or 1
        core = [s.chars for s in ch.sections if tiers[s.num] == "核心"]
        bg = [s for s in ch.sections if tiers[s.num] == "背景"]
        cs = sum(core) / total
        if not core:
            fail("weight_budget", f"{tag} 没有核心节（骨架里标 :::core 的叶子所在的节即核心）")
        elif cs < 0.45:
            fail("weight_budget", f"{tag} 核心节合计 {cs:.0%} < 45%")
        elif cs < 0.55:
            warn("weight_budget", f"{tag} 核心节合计 {cs:.0%}（45–55%）")
        bgs = sum(s.chars for s in bg) / total
        if bgs > 0.15:
            fail("weight_budget", f"{tag} 背景节合计 {bgs:.0%} > 15%")
        med = statistics.median(core) if core else None
        for s in bg:
            if s.zi > 800:
                fail("weight_budget", f"§{s.num} 背景节 {s.zi} 字 > 800")
            if med and s.chars > med:
                fail("weight_budget", f"§{s.num} 背景节比核心节中位数还长")
        if ch.sections:
            longest = max(ch.sections, key=lambda s: s.chars)
            ws_w = [ws.spine_sec.get(s.num, {}).get("weight") or 0 for s in ch.sections]
            top = sorted(ws_w, reverse=True)[:max(1, len(ws_w) // 3)]
            if (ws.spine_sec.get(longest.num, {}).get("weight") or 0) < min(top) and tiers[longest.num] != "核心":
                warn("weight_budget", f"{tag} 最长节 §{longest.num} 不是高分量节")
        info("weight_budget", f"{tag} 分量档 " + " ".join(f"§{k}:{v}" for k, v in tiers.items()))
        # load_sequence
        run, prev = 0, None
        for s, ld in zip(ch.sections, loads):
            run = run + 1 if ld == prev else 1
            prev = ld
            if ld == "重" and run >= 3:
                fail("load_sequence", f"{tag} 连续 3 个重节（止于 §{s.num}）")
            if ld == "轻" and run >= 4:
                fail("load_sequence", f"{tag} 连续 4 个以上轻节（止于 §{s.num}）")
        info("load_sequence", f"{tag} 负载序列 {''.join(loads)}")
        # heavy_junction / breather
        for k, (s, ld) in enumerate(zip(ch.sections, loads)):
            br = [b for b in s.blocks if b.marker == "☕"]
            if ld == "重" and not br:
                fail("breather", f"§{s.num} 重节内没有 ☕")
            if ld == "轻" and br:
                fail("breather", f"§{s.num} 轻节不放 ☕")
            fm = next((i for i in range(s.start, s.end) if ch.kind[i] in ("math", "code")), None)
            if ld == "重" and br and fm is not None and br[-1].start < fm:
                warn("breather", f"§{s.num} ☕ 在第一个公式/代码之前，应在最重一步之后")
            if k and ld == "重" and loads[k - 1] == "重":
                p = ch.sections[k - 1]
                mid = (p.start + p.end) // 2
                if not any(b.marker == "☕" and b.start >= mid for b in p.blocks):
                    fail("heavy_junction", f"§{p.num}→§{s.num} 重-重交界处（前节后半）没有 ☕")
        R["heavy_junction"]["ran"] = R["breather"]["ran"] = True
        # texture_run
        run, start = 0, None
        for i in range(ch.body_end + 1):
            k = ch.kind[i] if i < ch.body_end else "end"
            hard = k in ("math", "code", "table") or (k in ("prose", "list") and re.search(r"\\\(|\$|=", ch.lines[i]))
            if hard:
                if not run:
                    start = i
                run += 1
            elif k in ("blank",) or i in ch.game:      # 出手块/行对硬核连续段透明：不算正课，也不算换质地
                continue
            else:
                if run > 40:
                    fail("texture_run", f"{ch.name}:L{start + 1} 硬核连续 {run} 行未换质地")
                elif run > 25:
                    warn("texture_run", f"{ch.name}:L{start + 1} 硬核连续 {run} 行（约 25 行换一次质地）")
                run = 0
        R["texture_run"]["ran"] = True
        # mechanical_transition
        for i, t in text_units(ch, 0, ch.body_end):
            m = re.search(r"接下来我们|下面介绍|下一节我们|下面我们来|接下来讲|接下来介绍|下面来看|接下来看", t)
            if m:
                fail("mechanical_transition", f"{ch.name}:L{i + 1}「{m.group(0)}」")
        R["mechanical_transition"]["ran"] = True
        # close
        ca, cb = ch.close
        ctext = "\n".join(plain(ch.lines[i]) for i in range(ca, cb))
        if not ch.close_h2:
            fail("close", f"{ch.name} 没有收章 h2")
        else:
            if not re.search(r"现在能|你能做到|现在可以", ctext):
                fail("close", f"{ch.name} 收章缺「你现在能做到」")
            q = plain(ch.lines[firstp]) if firstp is not None else ""
            if q and overlap(q, ctext) < 0.3:
                warn("close", f"{ch.name} 收章与开章问题「{q[:24]}」字面重合低，自查是否回答了它")
            if ch.num < total_ch and not re.search(r"[？?]", ctext.strip().split("\n")[-1] if ctext.strip() else ""):
                warn("close", f"{ch.name} 收章最后一句不是抛给下一章的问题")
            flat = re.sub(r"\s+", "", ctext)
            gone = [c for c in ch.skel_concepts if re.sub(r"\s+", "", c) not in flat]
            if gone:
                warn("close", f"{ch.name} 收章没回到骨架：大概念「{'」「'.join(gone)}」没再出现（回到骨架段逐个填上本章结论）")
        # stage_map
        cm = [i for i in range(ca, cb) if ch.kind[i] == "mermaid"]
        if not cm:
            fail("stage_map", f"{ch.name} 收章缺阶段地图（mermaid）")
        else:
            src = "\n".join(ch.lines[i] for i in cm)
            miss = [s.num for s in ch.sections if s.num not in src and not set(s.nodes) & set(ID_RE.findall(src))]
            prevs = [k for k in range(1, ch.num) if not re.search(rf"第\s*{k}\s*章|§{k}\.|\bch{k}\b|\bC{k}\b", src)]
            if miss:
                warn("stage_map", f"{ch.name} 阶段地图没标本章 §{', §'.join(miss)}")
            if prevs:
                warn("stage_map", f"{ch.name} 阶段地图没体现前面第 {cut(prevs, 10)} 章")
        # questions
        qi = next((i for i in range(ca, cb) if "思考题" in ch.lines[i]), None)
        if qi is None:
            fail("questions", f"{ch.name} 收章缺章末思考题")
        else:
            qs, j = [], qi + 1
            while j < cb and ch.kind[j] in ("list", "blank", "prose") and not ch.lines[j].startswith("#"):
                if ch.kind[j] == "list" and re.match(r"^\s*\d+[.)]", ch.lines[j]):
                    qs.append(j)
                j += 1
            if not 3 <= len(qs) <= 5:
                fail("questions", f"{ch.name} 思考题 {len(qs)} 道（应 3–5）")
            for j in qs:
                for x in re.findall(r"§\s*(\d+)\.\d+", ch.lines[j]):
                    if int(x) > ch.num:
                        fail("questions", f"{ch.name}:L{j + 1} 思考题用到后面章 §{x}.x")
                if re.search(r"答案[:：]|答[:：]", ch.lines[j]):
                    fail("questions", f"{ch.name}:L{j + 1} 答案紧跟题目（应在书尾）")
        # no_catchall
        for i, ln in enumerate(ch.lines):
            if ch.kind[i] == "heading" and re.search(r"卡住了怎么办|验算清单|练习题|习题|综合练习|错误汇总|常见错误", ln):
                fail("no_catchall", f"{ch.name}:L{i + 1} 综合节「{ln.strip()[:30]}」")
        R["no_catchall"]["ran"] = True
        # reading_time（章首时长 = Σ节 + 开收章）
        secmin = {s.num: section_minutes(ch, s, ld) for s, ld in zip(ch.sections, loads)}
        oc = region_zi(ch, oa, ob) + region_zi(ch, ca, cb)
        calc = sum(secmin.values()) + math.ceil(oc / 300)
        ch.calc_minutes, ch.sec_minutes = calc, secmin
        if gl:
            m = re.search(r"约\s*(\d+)\s*分钟", gl[0].text)
            if not m:
                fail("reading_time", f"{ch.name} 章首 🧭 缺「约 N 分钟」")
            else:
                given = int(m.group(1))
                sg = [b for s in ch.sections for b in s.blocks if b.marker == "🧭"]
                if sg:
                    ssum = sum(int(x) for b in sg for x in re.findall(r"约\s*(\d+)\s*分钟", b.text))
                    if ssum != given:
                        fail("reading_time", f"{ch.name} 章首 {given} 分钟 ≠ 各节导读条之和 {ssum}")
                if abs(given - calc) > 1:
                    fail("reading_time", f"{ch.name} 章首写 {given} 分钟，按字数算应为 {calc}（节 {sum(secmin.values())} + 开收章 {math.ceil(oc / 300)}）")
                else:
                    info("reading_time", f"{ch.name} 约 {given} 分钟（算得 {calc}）")
        for i, t in text_units(ch, 0, ch.body_end, with_blocks=False):
            # 只抓"阅读时长"口径的分钟数；算例里的"等 4 分钟"是内容，不算
            if re.search(r"(?:读|阅读|看完|读完|学完)[^。]{0,8}\d+\s*分钟|\d+\s*分钟[^。]{0,4}(?:读完|看完|读)", t):
                fail("reading_time", f"{ch.name}:L{i + 1} 正文里手写阅读分钟数")
        R["reading_time"]["ran"] = True


# ---------------------------------------------------------------- 出手（chapter 理论 6）
OPTION_RE = re.compile(r"^>\s*[-*]\s*([A-D])\s*[.、．)）:：]")
CARD_ITEM_RE = re.compile(r"^>\s*[-*+]\s*(❌|✅)")


def check_game(ws):
    """E-CHAP-32 challenge · E-CHAP-33 mind_card · E-CHAP-34 world_model · E-SEC-40 route_line。"""
    first_ch = min([c["num"] for c in ws.spine_ch] + [c.num for c in ws.chapters] + [1])
    for ch in ws.chapters:
        oa, ob = ch.open
        ca, cb = ch.close
        L = lambda i: f"{ch.name}:L{i + 1}"  # noqa: E731
        # ---- challenge（E-CHAP-32）
        C = "challenge"
        if not any(ch.lines[i].strip().startswith("**本章 boss**") for i in range(oa, ob) if ch.kind[i] == "prose"):
            fail(C, f"{ch.name} 开章（首个 § 之前）缺「**本章 boss**」一行")
        if ch.num > first_ch and not any(re.match(r"^\*\*先回忆", ch.lines[i].strip()) or
                                         ("先回忆" in ch.lines[i] and ch.kind[i] in ("prose", "quote"))
                                         for i in range(oa, ob)):
            warn(C, f"{ch.name} 非首章开章缺「先回忆 v{ch.num - 1}」一行")
        cb_ = [b for b in ch.blocks_in(oa, ob) if b.marker in ("⚔️", "⚔")]
        if not cb_:
            fail(C, f"{ch.name} 开章缺 ⚔️ 押一注块")
        else:
            b = cb_[0]
            if len(cb_) > 1:
                warn(C, f"{ch.name} 开章有 {len(cb_)} 个 ⚔️，只认第一个")
            opts = [OPTION_RE.match(x).group(1) for x in b.lines if OPTION_RE.match(x)]
            if not 3 <= len(opts) <= 4:
                fail(C, f"{L(b.start)} ⚔️ 题面 {len(opts)} 个选项（应 3–4 个，写成 `> - A. …`）")
            links = re.findall(r"\]\(#card-(\d+)\)", "\n".join(ch.lines[oa:ob]))
            if not links:
                fail(C, f"{L(b.start)} ⚔️ 缺跳关链接 `[直接跳到本章心智卡](#card-{ch.num})`")
            elif any(int(x) != ch.num for x in links):
                fail(C, f"{L(b.start)} 跳关链接指向 #card-{links[0]}，应为 #card-{ch.num}")
            rv = next((i for i in range(b.end, ob) if REVEAL_CMT_RE.match(ch.lines[i])), None)
            if rv is None:
                fail(C, f"{L(b.start)} ⚔️ 之后缺 `<!-- reveal -->`（揭晓要另起一页）")
            else:
                rb = next((x for x in ch.blocks_in(rv, ob)), None)
                if rb is None or not rb.lines[0].lstrip(">").strip().startswith("**揭晓**"):
                    fail(C, f"{L(rv)} `<!-- reveal -->` 之后第一个引用块不是「> **揭晓**」块")
                else:
                    judged = {}
                    for x in rb.lines:
                        m = re.match(r"^>\s*[-*]\s*([A-D])\s*[.、．)）]?\s*(?:选项)?\s*(不对|错|对)", x)
                        if m:
                            judged[m.group(1)] = m.group(2)
                    miss = [o for o in opts if o not in judged]
                    if miss:
                        fail(C, f"{L(rb.start)} 揭晓没对选项 {'、'.join(miss)} 下判断（每项写「- X 不对：…」/「- X 对：…」）")
                    right = [o for o, v in judged.items() if v == "对"]
                    if opts and len(right) != 1:
                        fail(C, f"{L(rb.start)} 揭晓里判「对」的选项 {len(right)} 个（应恰 1 个）")
                    m = re.search(r"正解[:：]\s*([A-D])", rb.text)
                    if not m:
                        warn(C, f"{L(rb.start)} 揭晓首行没写「正解：X」")
                    elif right and m.group(1) != right[0]:
                        fail(C, f"{L(rb.start)} 正解写 {m.group(1)}，判「对」的却是 {right[0]}")
                    if not miss and len(right) == 1:
                        info(C, f"{ch.name} {len(opts)} 选项，正解 {right[0]}")
        R[C]["ran"] = True
        # ---- mind_card（E-CHAP-33）
        C = "mind_card"
        if ch.close_h2:
            h = ch.close_h2[0]
            fb = next((i for i in range(h + 1, cb) if ch.kind[i] != "blank"), None)
            cards = [b for b in ch.blocks_in(ca, cb) if b.marker == "🧠"]
            if not cards:
                fail(C, f"{ch.name} 收章缺 🧠 心智卡")
            else:
                b = cards[0]
                if fb != b.start:
                    fail(C, f"{L(b.start)} 🧠 心智卡不是收章第一块（应紧跟收章 h2 标题）")
                head = re.sub(r"^>\s*🧠\s*(?:\*\*心智卡\*\*)?\s*", "", b.lines[0]).strip()
                if not re.match(r"^>\s*🧠\s*\*\*心智卡\*\*", b.lines[0]):
                    fail(C, f"{L(b.start)} 心智卡首行应为 `> 🧠 **心智卡**　<问题>`")
                if not head:
                    fail(C, f"{L(b.start)} 心智卡首行没写问题")
                elif not re.search(r"[？?]\s*$", head):
                    warn(C, f"{L(b.start)} 心智卡首行「{head[:24]}」不是问句")
                items = [(CARD_ITEM_RE.match(x).group(1), x) for x in b.lines if CARD_ITEM_RE.match(x)]
                loose = [x for x in b.lines if ("❌" in x or "✅" in x) and not CARD_ITEM_RE.match(x)]
                if loose:
                    fail(C, f"{L(b.start)} 心智卡的 ❌/✅ 要写成 bullet（`> - ❌ …`），有 {len(loose)} 行不是")
                wrong = [x for k, x in items if k == "❌"]
                right = [x for k, x in items if k == "✅"]
                if not 2 <= len(wrong) <= 3:
                    fail(C, f"{L(b.start)} 心智卡 ❌ {len(wrong)} 条（应 2–3 条）")
                bad = [x for x in wrong if not re.search(r"不对\s*[，,。]?\s*因为", x)]
                if bad:
                    fail(C, f"{L(b.start)} 心智卡有 {len(bad)} 条 ❌ 没写「不对，因为 …」")
                if len(right) != 1:
                    fail(C, f"{L(b.start)} 心智卡 ✅ {len(right)} 条（应恰 1 条）")
                elif "因为" not in right[0]:
                    fail(C, f"{L(b.start)} 心智卡 ✅ 没写「因为 …」（理由讲机制）")
                if not any(re.match(r"^>\s*\*\*一句话\*\*", x) for x in b.lines):
                    fail(C, f"{L(b.start)} 心智卡缺「**一句话**：…」一行")
                info(C, f"{ch.name} ❌×{len(wrong)} ✅×{len(right)}")
        R[C]["ran"] = True
        # ---- world_model（E-CHAP-34）
        C = "world_model"
        wl = [i for i in range(ca, cb) if ch.kind[i] == "prose" and re.match(r"^\*\*世界模型\s*v(\d+)", ch.lines[i].strip())]
        if not wl:
            warn(C, f"{ch.name} 收章缺「**世界模型 v{ch.num}**」段（按章序由同一作者补）")
        else:
            n = int(re.match(r"^\*\*世界模型\s*v(\d+)", ch.lines[wl[0]].strip()).group(1))
            if n != ch.num:
                warn(C, f"{L(wl[0])} 世界模型写 v{n}，应为 v{ch.num}")
            elif sum(ch.lines[j].count("**") for j in range(wl[0], cb)
                     if j == wl[0] or (ch.kind[j] == "list" and j in ch.game)) < 4:
                warn(C, f"{L(wl[0])} 世界模型 v{n} 没把本章新增的部分加粗")
        if not any(ch.kind[i] == "prose" and ch.lines[i].strip().startswith("**现在去打**") for i in range(ca, cb)):
            fail(C, f"{ch.name} 收章缺「**现在去打**　<题号>…」一行")
        R[C]["ran"] = True
        # ---- route_line（E-SEC-40）
        C = "route_line"
        for s in ch.sections:
            i = s.start + 1
            if i < s.end and ch.kind[i] == "comment":
                i += 1
            while i < s.end and ch.kind[i] == "blank":
                i += 1
            b = ch.block_at(i)
            if not b or b.marker not in ("🗺️", "🗺") or b.start != i:
                fail(C, f"§{s.num} 节注释后没有紧跟 `> 🗺️ …` 路线行")
                continue
            arrows = len(re.findall(r"→|->|⟶", b.text))
            if arrows < 3:
                fail(C, f"§{s.num} 🗺️ 只有 {arrows} 个箭头（≥3，4–6 步）")
            elif arrows > 6:
                warn(C, f"§{s.num} 🗺️ {arrows + 1} 步（4–6 步为宜）")
            if len(b.lines) > 1:
                warn(C, f"§{s.num} 🗺️ 写了 {len(b.lines)} 行，应一行")
        R[C]["ran"] = True


BLOCKSUM_ITEMS = ("这块在问", "合起来的答案", "往上挂", "往下接")


def check_block_summary(ws):
    """E-CHAP-36：两章及以上的块，块末章收章有 🌳 块小结（🧠 之后、世界模型 vN 之前），后接该块的小树图
    （L3：框 = 块内各章，框内一行「留下：…」）。块取自各卷串讲的 L2 卷内图（框标题「块名 · 第a–b章」）。"""
    C = "block_summary"
    blocks = []
    synths = ws.synths or {   # 单章模式不载卷串讲（章级检查不跑它），这里只为认块读一下
        int(f[:2]): Doc(os.path.join(ws.book, f)) for f in sorted(os.listdir(ws.book))
        if re.match(r"^\d{2}v-[a-z0-9][a-z0-9-]*\.md$", f)} if os.path.isdir(ws.book) else {}
    for _nn, d in sorted(synths.items()):
        for _a, _b, src in mermaid_blocks(d, 0, len(d.lines)):
            sk = skeleton_figure.parse_skeleton(src) if skeleton_figure.is_skeleton(src) else None
            if sk and skeleton_figure.level(sk) == "L2":
                blocks += [(g["label"].split("·")[0].strip(), sorted(g["chs"])) for g in sk["groups"]]
                break
    if not blocks:
        skip(C, "没有卷串讲的 L2 卷内图，认不出块")
        return
    end_of = {chs[-1]: (name, chs) for name, chs in blocks if len(chs) >= 2}
    for ch in ws.chapters:
        ca, cb = ch.close
        L = lambda i: f"{ch.name}:L{i + 1}"  # noqa: E731
        sums = [b for b in ch.blocks_in(ca, cb) if b.marker == "🌳"]
        if ch.num not in end_of:
            for b in sums:
                fail(C, f"{L(b.start)} 第 {ch.num} 章不是多章块的块末章，不该有 🌳 块小结")
            continue
        name, chs = end_of[ch.num]
        if not sums:
            fail(C, f"{ch.name} 是「{name}」（第 {chs[0]}–{chs[-1]} 章）的块末章，收章缺 🌳 块小结")
            continue
        b = sums[0]
        if not re.match(r"^>\s*🌳\s*\*\*块小结\*\*", b.lines[0]):
            fail(C, f"{L(b.start)} 块小结首行应为 `> 🌳 **块小结**　<块名>（第 a–b 章 · …）`")
        elif name not in b.lines[0]:
            warn(C, f"{L(b.start)} 块小结首行没写块名「{name}」")
        miss = [k for k in BLOCKSUM_ITEMS if not any(re.match(rf"^>\s*[-*]\s*\*\*{k}\*\*", x) for x in b.lines)]
        if miss:
            fail(C, f"{L(b.start)} 块小结缺 bullet：{'、'.join(miss)}（`> - **这块在问**：…`）")
        if not any(re.match(r"^>\s*\*\*一句话\*\*", x) for x in b.lines):
            fail(C, f"{L(b.start)} 块小结缺「**一句话**：…」一行")
        card = next((x for x in ch.blocks_in(ca, cb) if x.marker == "🧠"), None)
        if card and b.start < card.start:
            fail(C, f"{L(b.start)} 块小结应在 🧠 心智卡之后（叶 → 块 → 全书）")
        wl = next((i for i in range(ca, cb) if re.match(r"^\*\*世界模型\s*v\d+", ch.lines[i].strip())), None)
        if wl is not None and b.start > wl:
            fail(C, f"{L(b.start)} 块小结应在「世界模型 v{ch.num}」之前")
        # 小树图：块小结之后、下一个引用块 / 世界模型之前的第一张 `%% skeleton`
        stop = wl if wl is not None and wl > b.end else cb
        trees = [skeleton_figure.parse_skeleton(src) for _a, _b, src in mermaid_blocks(ch, b.end, stop)
                 if skeleton_figure.is_skeleton(src)]
        if not trees:
            fail(C, f"{L(b.start)} 块小结后缺小树图（`%% skeleton`，框 = 第{chs[0]}–{chs[-1]}章，框内「留下：…」）")
            continue
        sk = trees[0]
        got = sorted(c for g in sk["groups"] for c in g["chs"])
        if got != chs:
            fail(C, f"{L(b.start)} 小树图的框是第 {got} 章，块是第 {chs} 章")
        if not skeleton_figure.is_blocksum(sk):
            fail(C, f"{L(b.start)} 小树图每框应只有「留下：…」行（该章心智卡一句话的压缩版）")
        long_ = [l["text"] for g in sk["groups"] for l in g["leaves"] if len(l["text"]) > 28]
        if long_:
            warn(C, f"{L(b.start)} 小树图有 {len(long_)} 行「留下」超过 24 字（如「{long_[0][:16]}…」）")
        linked = {e["ga"] for e in sk["edges"]} | {e["gb"] for e in sk["edges"]}
        lone = [g["label"] for g in sk["groups"] if g["id"] not in linked]
        if lone:
            fail(C, f"{L(b.start)} 小树图里 {'、'.join(lone)} 没连任何边")
        info(C, f"{ch.name} 「{name}」第 {chs[0]}–{chs[-1]} 章")
    R[C]["ran"] = True


# ---------------------------------------------------------------- devices
SLIDE_RE =re.compile(r"课件|幻灯片|[Ss]lides?\b|这页|这一页|本页|红框|左上角|右上角|左下角|右下角|上图左|PPT")


def check_devices(ws):
    pref_full = bool(ws.reader and re.search(r"偏好[:：].*原图.*全", ws.reader))
    for ch in ws.chapters:
        tag = f"第 {ch.num} 章"
        total = len(ch.text) or 1
        # slide_narration
        for i in range(ch.body_end):
            k = ch.kind[i]
            if k in ("prose", "list", "quote", "heading", "table"):
                t = plain(ch.lines[i])
                m = SLIDE_RE.search(t)
                if m:
                    fail("slide_narration", f"{ch.name}:L{i + 1} 描述载体「{m.group(0)}」: {t[:36]}")
                if re.search(r"(?<![\w\[^])[A-Za-z][\w-]*\s+p\d+", t) and k != "table":
                    fail("slide_narration", f"{ch.name}:L{i + 1} 正文里出现页码（只放节注释与脚注）")
        R["slide_narration"]["ran"] = True
        # footnote_defs
        refs = {r for r, _ in ch.fnrefs}
        for r, i in ch.fnrefs:
            if r not in ch.fndefs:
                fail("footnote_defs", f"{ch.name}:L{i + 1} 脚注 [^{r}] 没有定义")
        for d, (content, i) in ch.fndefs.items():
            if d not in refs:
                warn("footnote_defs", f"{ch.name}:L{i + 1} 脚注定义 [^{d}] 未被引用")
            pg = parse_pages(content)
            if pg and ws.mats:
                for sh, _ in pg:
                    if sh not in ws.mats:
                        fail("footnote_defs", f"{ch.name}:L{i + 1} 脚注 [^{d}] 的材料短名 {sh} 未在 manifest 登记")
            m = re.match(r"^([A-Za-z][\w-]*?)p(\d+)", d)
            norm = {(re.sub(r"[^A-Za-z0-9]", "", a).lower(), b) for a, b in pg}
            if m and pg and (re.sub(r"[^A-Za-z0-9]", "", m.group(1)).lower(), int(m.group(2))) not in norm:
                warn("footnote_defs", f"{ch.name}:L{i + 1} 脚注标签 [^{d}] 与内容「{content}」不一致")
        info("footnote_defs", f"{ch.name} 脚注 {len(ch.fndefs)} 条")
        tiers = {s.num: tier(ws, ch, s) for s in ch.sections}
        figs_in_ch = set()
        for s in ch.sections:
            ttag = f"§{s.num}"
            # depth_hint
            if tiers[s.num] == "核心":
                own = {r for r, i in ch.fnrefs if s.start <= i < s.end}
                if not any(o in ch.fndefs and not parse_pages(ch.fndefs[o][0]) for o in own):
                    warn("depth_hint", f"{ttag} 核心节没有指向延伸材料的深度提示脚注")
            # aside_only_content
            pro_refs, aside_refs = set(), set()
            for i in range(s.start + 2, s.end):
                b = ch.block_at(i)
                refs = set(FNREF_RE.findall(ch.lines[i]))
                if b and b.marker in ASIDE_BLOCKS - {"📍"}:
                    aside_refs |= refs
                else:
                    pro_refs |= refs
            only = aside_refs - pro_refs
            if only:
                fail("aside_only_content", f"{ttag} 出处 {', '.join(sorted(only))} 只在 💡/☕/🎓/🔍 里出现")
            for b in s.blocks:
                if b.marker in {"💡", "☕", "🎓"} and re.search(r"\$\$|!\[", b.text):
                    fail("aside_only_content", f"{ttag} {b.marker} 块里放了公式块/原图（材料内容进正课）")
            # figures
            n_fig = 0
            for i in range(s.start, s.end):
                for m in IMG_RE.finditer(ch.lines[i]):
                    n_fig += 1
                    alt, src = m.group(1), m.group(2)
                    figs_in_ch.add(os.path.basename(src))
                    if ch.kind[i] != "image":
                        fail("figure_format", f"{ch.name}:L{i + 1} 图没有独占一行")
                    if not os.path.exists(os.path.normpath(os.path.join(ws.book, src))):
                        fail("figure_format", f"{ch.name}:L{i + 1} 图文件不存在: {src}")
                    fm = re.search(r"·\s*课件\s+([A-Za-z][\w-]*)\s+p(\d+)\s*$", alt)
                    if fm:
                        if "raw/figures/" not in src:
                            fail("figure_format", f"{ch.name}:L{i + 1} 课件原图应引 ../raw/figures/")
                        if ws.mats and fm.group(1) not in ws.mats:
                            fail("figure_format", f"{ch.name}:L{i + 1} 图注短名 {fm.group(1)} 未登记")
                        if s.pages and (fm.group(1), int(fm.group(2))) not in s.pages:
                            warn("sources", f"{ttag} 图注页 {fm.group(1)} p{fm.group(2)} 不在本节 sources")
                    elif not alt.startswith("自绘 · "):
                        fail("figure_format", f"{ch.name}:L{i + 1} 图注应为 `<图意> · 课件 <短名> p<N>` 或以 `自绘 · ` 开头: {alt[:30]}")

                    def nb(step):
                        j = i + step
                        while 0 <= j < s.end and j >= s.start and ch.kind[j] == "blank":
                            j += step
                        return ch.kind[j] if s.start <= j < s.end else "end"
                    bk, ak = nb(-1), nb(1)
                    if bk in ("heading", "comment", "image") or ak in ("heading", "image", "end"):
                        fail("figure_context", f"{ch.name}:L{i + 1} 图前后须各一段讲解（前:{bk} 后:{ak}）")
            if n_fig > 3:
                fail("figures_per_section", f"{ttag} 嵌图 {n_fig} 张 > 3")
            # reality_intro
            for b in s.blocks:
                if b.marker != "🔍":
                    continue
                ii = next((k for k, x in enumerate(b.lines) if re.match(r"^>\s*#{1,6}\s*入门", x)), None)
                if ii is None:
                    warn("reality_intro", f"{ch.name}:L{b.start + 1} 🔍 没有 `### 入门：…` 段")
                    continue
                if EMOJI_RE.search(b.lines[ii]):
                    fail("reality_intro", f"{ch.name}:L{b.start + ii + 1} 入门小标题带 emoji")
                if not re.match(r"^>\s*###\s*入门[:：]", b.lines[ii]):
                    fail("reality_intro", f"{ch.name}:L{b.start + ii + 1} 入门子标题应为 `### 入门：…`")
                jj = next((k for k in range(ii + 1, len(b.lines)) if re.match(r"^>\s*#{1,6}\s", b.lines[k])), len(b.lines))
                part = [x for x in b.lines[ii + 1:jj] if plain(x)]
                if len(part) > 12:
                    fail("reality_intro", f"{ch.name}:L{b.start + 1} 入门段 {len(part)} 行 > 12")
                if part and not re.search(r"对应到", part[-1]):
                    fail("reality_intro", f"{ch.name}:L{b.start + 1} 入门段末行缺「对应到…世界」映射")
                if any(re.match(r"^>\s*[-*]\s", x) for x in part):
                    fail("reality_intro", f"{ch.name}:L{b.start + 1} 入门段用了子弹")
                en = [w for x in part for w in re.findall(r"[A-Za-z]{3,}", plain(x))]
                if en:
                    warn("reality_intro", f"{ch.name}:L{b.start + 1} 入门段有英文词 {cut(sorted(set(en)), 5)}")
        R["figures_per_section"]["ran"] = R["figure_format"]["ran"] = R["figure_context"]["ran"] = True
        R["aside_only_content"]["ran"] = R["depth_hint"]["ran"] = R["reality_intro"]["ran"] = True
        # figure_candidates（含 spine 预选原图）
        if ws.figs is not None:
            pages = set().union(*[s.pages for s in ch.sections]) if ch.sections else set()
            cand = [f for f in ws.figs if (f.get("short"), f.get("page")) in pages and not f.get("looks_like_table")]
            if cand and not figs_in_ch:
                warn("figure_candidates", f"{tag} sources 页有 {len(cand)} 张非表格候选原图，本章零嵌图 —— 写明理由")
            info("figure_candidates", f"{tag} 嵌图 {len(figs_in_ch)} 张，候选 {len(cand)} 张")
        else:
            info("figure_candidates", "raw/_figures.json 不存在，候选核对跳过")
        pre = [(s.num, f) for s in ch.sections for f in ws.spine_sec.get(s.num, {}).get("figs", [])]
        elsewhere = set()
        for other in sorted(glob.glob(os.path.join(ws.book, "[0-9][0-9]-*.md"))):
            if os.path.basename(other) != ch.name:
                elsewhere |= set(re.findall(r"raw/figures/([^)\s]+\.png)", open(other, encoding="utf-8").read()))
        dup_ok = {f for f in elsewhere}  # 已在别章嵌过：本章回指即可（devices D 同图只嵌一次）
        miss = [f"§{n} {f}" for n, f in pre if f not in figs_in_ch and f not in dup_ok
                and not re.search(re.escape(f) + r"[^|]*重复", ws.spine_sec.get(n, {}).get("figs_note", ""))]
        if miss:
            (fail if pref_full else warn)("figure_candidates", f"{tag} spine 预选原图未进书 {len(miss)} 张: {cut(miss, 6)}"
                                          + ("（reader.md 偏好原图要全）" if pref_full else ""))
        # math_notation
        for i, ln in enumerate(ch.lines):
            k = ch.kind[i]
            if k in ("code",) and re.search(r"\\frac|\$\$|\\\(", ln):
                fail("math_notation", f"{ch.name}:L{i + 1} 代码块内有 LaTeX")
            if k in ("code", "mermaid"):
                continue
            if "\\[" in ln and k != "math" or re.search(r"^\s*\\\[\s*$", ln):
                fail("math_notation", f"{ch.name}:L{i + 1} 用了 `\\[…\\]`，display 用 `$$`")
            if k != "math" and "$$" in ln:
                fail("math_notation", f"{ch.name}:L{i + 1} `$$` 没有独占一行")
            if k == "math" and ln.strip() == "$$" and (i == 0 or ch.kind[i - 1] != "math"):
                if i > 0 and ch.kind[i - 1] != "blank":
                    warn("math_notation", f"{ch.name}:L{i + 1} display 公式前缺空行")
            if k != "math" and re.search(r"(?<![\$\\])\$(?!\$)[^$\n]*[\\^_{][^$\n]*\$(?!\$)", ln):
                fail("math_notation", f"{ch.name}:L{i + 1} 行内用了 `$…$`，改 `\\(…\\)`")
            if k == "table":
                for mm in re.finditer(r"\\\((.*?)\\\)", ln):
                    if "|" in mm.group(1):
                        fail("math_notation", f"{ch.name}:L{i + 1} 表格里的数学含 `|`，用 `\\mid`")
        if leftover_math is not None:
            try:
                for ln_no, txt in leftover_math(ch.text):
                    fail("math_notation", f"{ch.name}:L{ln_no} 残留数学界符: {str(txt)[:40]}")
                unk = collect_unsupported(ch.text)
                if unk:
                    fail("math_notation", f"{ch.name} 渲染器不认识的 LaTeX 命令: {', '.join(sorted(unk))}")
            except Exception as e:  # noqa: BLE001
                info("math_notation", f"公式转换模块出错，跳过渲染检查: {e}")
        else:
            info("math_notation", "latex_to_html 导入失败，渲染检查跳过")
        R["math_notation"]["ran"] = True
        # code_chunks（代码块与 display 推导块 ≤14 行，前有引出后有讲解）
        i = 0
        while i < ch.body_end:
            k = ch.kind[i]
            if k in ("code", "math"):
                j = i
                while j + 1 < len(ch.lines) and ch.kind[j + 1] == k and not (k == "code" and FENCE_RE.match(ch.lines[j])
                                                                              and j > i):
                    j += 1
                n = j - i + 1 - 2
                if n > 14:
                    fail("code_chunks", f"{ch.name}:L{i + 1} {'代码' if k == 'code' else '推导'}块 {n} 行 > 14，分块")
                if k == "code":
                    pb = next((ch.kind[x] for x in range(i - 1, -1, -1) if ch.kind[x] != "blank"), "")
                    na = next((ch.kind[x] for x in range(j + 1, len(ch.lines)) if ch.kind[x] != "blank"), "")
                    if pb not in ("prose", "list") or na not in ("prose", "list", "quote"):
                        fail("code_chunks", f"{ch.name}:L{i + 1} 代码块前须有引出、后须有讲解")
                i = j + 1
            else:
                i += 1
        R["code_chunks"]["ran"] = True
        # heavy_device_ratio
        heavy = sum(len(ch.lines[x]) for x in range(len(ch.lines)) if ch.kind[x] in ("code", "table"))
        r = heavy / total
        if r > 0.2:
            warn("heavy_device_ratio", f"{tag} 代码块+表格 {r:.0%} > 20%" + ("（>30%）" if r > 0.3 else ""))
        else:
            info("heavy_device_ratio", f"{tag} 代码块+表格 {r:.0%}")
        # block_vocab
        cnt = {}
        for b in ch.blocks:
            cnt[b.marker or "(无标记)"] = cnt.get(b.marker or "(无标记)", 0) + 1
            if b.marker and b.marker.startswith("?"):
                fail("block_vocab", f"{ch.name}:L{b.start + 1} 未知块标记 {b.marker[1:]}")
            first = b.lines[0].lstrip(">").strip()
            if re.match(r"^\*\*(?:tip|note|Tip|Note|NOTE|TIP|重要|注意|提示)\*\*", first):
                fail("block_vocab", f"{ch.name}:L{b.start + 1} 空标签块「{first[:12]}」")
            if b.marker == "🎯" and not ws.exam:
                fail("block_vocab", f"{ch.name}:L{b.start + 1} reader.md 未声明考试却有 🎯")
            if b.marker in ROLE_NAME and b.marker not in ("🎓", "🧭", "✅", "🧩", "🤔"):
                bm = re.match(r"^\S+\s*\*\*([^*]+)\*\*", first)
                if bm and bm.group(1).strip() != ROLE_NAME[b.marker]:
                    warn("block_vocab", f"{ch.name}:L{b.start + 1} {b.marker} 的名字「{bm.group(1)}」≠ 词汇表「{ROLE_NAME[b.marker]}」")
            for x in b.lines[1:]:
                if any(x.lstrip(">").strip().startswith(m) for m in MARKERS):
                    fail("block_vocab", f"{ch.name}:L{b.start + 1} 一个引用块里出现第二个块标记（块之间要空行）")
                    break
        for i, ln in enumerate(ch.lines):
            if ch.kind[i] == "heading" and EMOJI_RE.search(ln):
                fail("block_vocab", f"{ch.name}:L{i + 1} 标题含 emoji")
            if ch.kind[i] in ("prose", "list") and any(m in ln for m in MARKERS):
                fail("block_vocab", f"{ch.name}:L{i + 1} 块 emoji 不在引用块首字")
        info("block_vocab", f"{ch.name} " + " ".join(f"{k}×{v}" for k, v in sorted(cnt.items(), key=lambda x: -x[1])))
        # guide_line / guide_minutes
        gl = [b for b in ch.blocks_in(*ch.open) if b.marker == "🧭"]
        for g in gl:
            if not re.match(r"^>\s*🧭\s*本章[:：]\s*\S.*\s·\s*约\s*\d+\s*分钟\s*$", g.lines[0]) or len(g.lines) > 1:
                fail("guide_line", f"{ch.name}:L{g.start + 1} 章首 🧭 格式应为 `> 🧭 本章: {{念头}} · 约 N 分钟`（一行）")
        sg = [(s, b) for s in ch.sections for b in s.blocks if b.marker == "🧭"]
        if sg and len({s.num for s, _ in sg}) != len(ch.sections):
            fail("guide_line", f"{ch.name} 节级 🧭 有的节有、有的节没有（全书统一）")
        for s, b in sg:
            if not re.match(r"^>\s*🧭\s*本节[:：]\s*(核心|常规|背景)\s*·\s*约\s*\d+\s*分钟\s*·\s*\S", b.lines[0]):
                fail("guide_line", f"§{s.num} 节级 🧭 格式应为 `本节: 核心|常规|背景 · 约 N 分钟 · 读法`")
            if re.search(r"轻度|中度|重度|负载|课件|\bp\d+", b.text):
                fail("guide_line", f"§{s.num} 节级 🧭 含负载评级或出处")
            m = re.search(r"约\s*(\d+)\s*分钟", b.text)
            if m and abs(int(m.group(1)) - ch.sec_minutes.get(s.num, 0)) > 1:
                fail("guide_minutes", f"§{s.num} 导读条 {m.group(1)} 分钟，按字数应为 {ch.sec_minutes.get(s.num)}")
        if gl:
            m = re.search(r"约\s*(\d+)\s*分钟", gl[0].text)
            if m and abs(int(m.group(1)) - ch.calc_minutes) > 1:
                fail("guide_minutes", f"{ch.name} 章首 {m.group(1)} 分钟，按口径应为 {ch.calc_minutes}")
        R["guide_line"]["ran"] = R["guide_minutes"]["ran"] = True
        # texture_floor
        for s in ch.sections:
            mk = [b.marker for b in s.blocks]
            t = tiers[s.num]
            cal = CALIB if ws.exam else CALIB - {"🎯"}
            if t == "核心":
                if not set(mk) & {"💡", "☕", "🔍"}:
                    fail("texture_floor", f"§{s.num} 核心节缺辅助/例子块（💡/☕/🔍）")
                if not set(mk) & cal:
                    fail("texture_floor", f"§{s.num} 核心节缺校准块（📌/📏{'/🎯' if ws.exam else ''}）")
            elif t == "常规":
                if not set(mk) & (cal | {"⚠️", "⚠", "📎"}):
                    fail("texture_floor", f"§{s.num} 常规节缺校准块")
            else:
                if sum(1 for x in mk if x in cal | {"⚠️", "⚠", "📎"}) > 1:
                    fail("texture_floor", f"§{s.num} 背景节校准块 >1")
                if set(mk) & {"💡", "☕"}:
                    warn("texture_floor", f"§{s.num} 背景节配了 💡/☕，自查是否硬配")
            if "📏" in mk and t != "核心":
                fail("texture_floor", f"§{s.num} 📏 只在核心节开（本节为{t}）")
        R["texture_floor"]["ran"] = True
        # aside_budget
        cof = sum(len(b.text) for b in ch.blocks if b.marker == "☕") / total
        mas = [b for b in ch.blocks if b.marker == "🎓"]
        msh = sum(len(b.text) for b in mas) / total
        if cof > 0.08:
            fail("aside_budget", f"{tag} ☕ {cof:.1%} > 8%")
        if msh > 0.15:
            fail("aside_budget", f"{tag} 🎓 {msh:.1%} > 15%")
        if len(mas) > 1:
            fail("aside_budget", f"{tag} 🎓 {len(mas)} 个（每章至多 1）")
        info("aside_budget", f"{tag} ☕ {cof:.1%} · 🎓 {msh:.1%}")
        for b in ch.blocks:
            z = zi(b.body)
            loc = f"{ch.name}:L{b.start + 1}"
            if b.marker == "☕" and not 80 <= z <= 200:
                fail("breather_length", f"{loc} ☕ {z} 字（80–200）")
            if b.marker == "☕" and YEAR_RE.search(b.body):
                fail("breather_length", f"{loc} ☕ 含年份（编造的行业细节）")
            if b.marker == "🎓":
                if not 150 <= z <= 400:
                    fail("master_length", f"{loc} 🎓 {z} 字（150–400）")
                if YEAR_RE.search(b.body):
                    fail("master_length", f"{loc} 🎓 含年份")
            if b.marker == "📌":
                if len(b.lines) > 2:
                    fail("def_lines", f"{loc} 📌 {len(b.lines)} 行 > 2")
                elif zi(b.body) > 80:
                    warn("def_lines", f"{loc} 📌 {zi(b.body)} 字，A5 上会超过 2 行")
            if b.marker == "🎯":
                if z > 80:
                    fail("exam_block", f"{loc} 🎯 {z} 字 > 80")
                m = re.search(r"分值|频次|必考|高频|常考|每年|\d+\s*分(?!钟|布|位|析)|%", b.body)
                if m:
                    fail("exam_block", f"{loc} 🎯 含「{m.group(0)}」")
            if b.marker == "📎":
                if not 1 <= len(b.lines) <= 3:
                    fail("clip_lines", f"{loc} 📎 {len(b.lines)} 行（1–3）")
                if not re.search(r"深入查|知道存在即可|知道有|想深入", b.body):
                    warn("clip_lines", f"{loc} 📎 没留「深入查 X / 知道存在即可」")
        for c in ("breather_length", "master_length", "def_lines", "exam_block", "clip_lines"):
            R[c]["ran"] = True
        # external_marks
        for s in ch.sections:
            ext = [n for n in s.nodes if ws.nodes.get(n, {}).get("kind") == "external"]
            marked = "（材料外）" in s.raw
            if s.nodes and len(ext) == len(s.nodes):
                if not marked:
                    fail("external_marks", f"§{s.num} 全是材料外节点，标题缺「（材料外）」后缀")
                first = next((b for b in s.blocks if b.marker not in ("🧭", "🗺️", "🗺")), None)
                if not first or first.marker != "📍":
                    fail("external_marks", f"§{s.num} 材料外节首缺 📍")
                elif not re.search(r"§\s*\d+\.\d+", first.text):
                    warn("external_marks", f"§{s.num} 📍 没写来源节（§N.M）")
            elif marked:
                fail("external_marks", f"§{s.num} 标了（材料外）但含材料内节点")
            if marked and EMOJI_RE.search(s.raw):
                fail("external_marks", f"§{s.num} 材料外标题带 emoji")
        R["external_marks"]["ran"] = True


# ---------------------------------------------------------------- book
def h2_sections(doc):
    out, cur = {}, None
    for i, ln in enumerate(doc.lines):
        if ln.startswith("## "):
            cur = ln[3:].strip()
            out[cur] = []
        elif cur:
            out[cur].append(i)
    return out


def tables(doc):
    """[(起行, 表头 cells, 行 list)]"""
    out, i = [], 0
    while i < len(doc.lines):
        if doc.kind[i] == "table":
            j = i
            while j + 1 < len(doc.lines) and doc.kind[j + 1] == "table":
                j += 1
            rows = [[c.strip() for c in doc.lines[x].strip().strip("|").split("|")] for x in range(i, j + 1)]
            rows = [r for r in rows if not set("".join(r)) <= set("-: ")]
            out.append((i, rows[0] if rows else [], rows[1:]))
            i = j + 1
        else:
            i += 1
    return out


VOL_RE = re.compile(r"^#\s+第\s*\S+\s*卷", re.M)
VOL_PREFIX_RE = re.compile(r"^(?:卷\s*[一二三四五六七八九十\d]+|第\s*\S+\s*卷)\s*[·:：]?\s*")


def skel_chapters(sk):
    """骨架图里各叶子标的章号 → {章: [叶子短名]}。"""
    out = {}
    for g in sk["groups"]:
        for l in g["leaves"]:
            for c in l["chs"]:
                out.setdefault(c, []).append(l["short"])
    return out


def is_position_map(sk):
    """卷串讲开头的 L1 位置图（带 class … here / dim）：同一张全书图的复制品，不算"另一张全书图"。"""
    return bool(sk.get("here") or sk.get("dim"))


def check_map_l1(C, M, nvol, nch):
    """98-map 的全书图 = L1（框标题「卷…」，框内一行「第a–b章」；合起来恰好覆盖 1..nch）。"""
    sks = [(a, skeleton_figure.parse_skeleton(src)) for a, _b, src in mermaid_blocks(M, 0, len(M.lines))
           if skeleton_figure.is_skeleton(src)]
    book = [(a, sk) for a, sk in sks if skeleton_figure.figure_kind(sk) == "book" and not is_position_map(sk)]
    if not book:
        fail(C, "98-map.md 没有 L1 全书图（框 = 卷、框标题以「卷」开头、框内一行「第a–b章」）")
        return
    if len(book) > 1:
        warn(C, f"98-map.md 有 {len(book)} 张全书图，只认第一张（L1 全书图只放一张）")
    a0, bk = book[0]
    where = f"98-map.md:L{a0 + 1}"
    if skeleton_figure.level(bk) != "L1":
        fail(C, f"{where} 全书图还是旧式（框里列块），应换成 L1：框内 2–3 行说明 + 一行「第a–b章」，不列块")
    if nvol and len(bk["groups"]) != nvol:
        fail(C, f"{where} 全书图有 {len(bk['groups'])} 卷，spine 有 {nvol} 卷")
    cov = {}
    for g in bk["groups"]:
        chs = [c for l in g["leaves"] for c in l["chs"]]
        if not chs:
            fail(C, f"{where}「{g['label']}」框内没有「第a–b章」行")
        for c in chs:
            cov.setdefault(c, []).append(g["label"])
    miss = [c for c in range(1, nch + 1) if c not in cov]
    dup = [f"第{c}章" for c, v in sorted(cov.items()) if len(v) > 1]
    extra = sorted(c for c in cov if c > nch or c < 1)
    if miss:
        fail(C, f"{where} 全书图的章范围没覆盖第 {cut(miss, 12)} 章")
    if dup:
        fail(C, f"{where} 全书图里一章落在多卷: {cut(dup, 6)}")
    if extra:
        fail(C, f"{where} 全书图标了不存在的第 {extra} 章")
    gid = {g["id"] for g in bk["groups"]}
    for e in bk["edges"]:
        if e.get("ga") not in gid or e.get("gb") not in gid or e["ga"] == e["gb"]:
            continue
        if not e["label"] or not e["phrase"]:
            fail(C, f"{where} 全书图的边 {e['a']}→{e['b']} 没写 `|关系词：短语|`")
        elif e["rel"] not in skeleton_figure.REL_WORDS:
            warn(C, f"{where} 全书图的边 {e['a']}→{e['b']} 关系词「{e['rel']}」不在词表")
    for m in skel_graph_issues(bk)[0]:
        fail(C, f"{where} 全书图: {m}")


def check_book_skeleton(ws, F, B):
    """E-BOOK-07：书首全书骨架（每卷一个 subgraph、块标章范围、卷间边带关系词）+ 每卷一张卷骨架；书尾回到骨架。"""
    C = "book_skeleton"
    sks = [(a, skeleton_figure.parse_skeleton(src)) for a, _b, src in mermaid_blocks(F, 0, len(F.lines))
           if skeleton_figure.is_skeleton(src)]
    book = [(a, sk) for a, sk in sks if skeleton_figure.figure_kind(sk) == "book" and not is_position_map(sk)]
    vols = [(a, sk) for a, sk in sks if skeleton_figure.figure_kind(sk) != "book"]
    if not book:
        fail(C, "书首没有全书骨架图（`%% skeleton`，每卷一个 subgraph、标签以「卷」开头）")
        return
    if len(book) > 1:
        warn(C, f"书首有 {len(book)} 张全书骨架图，只认第一张")
    a0, bk = book[0]
    spine_txt = open(os.path.join(ws.ws, "spine.md"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(ws.ws, "spine.md")) else ""
    nvol = len(VOL_RE.findall(spine_txt))
    nch = len(ws.spine_ch) or max([c.num for c in ws.chapters] + [0])
    if nvol and len(bk["groups"]) != nvol:
        fail(C, f"00-front.md:L{a0 + 1} 全书骨架有 {len(bk['groups'])} 卷，spine 有 {nvol} 卷")
    cov = skel_chapters(bk)
    miss = [c for c in range(1, nch + 1) if c not in cov]
    dup = [f"第{c}章（{'、'.join(v)}）" for c, v in sorted(cov.items()) if len(v) > 1]
    extra = sorted(c for c in cov if c > nch or c < 1)
    if miss:
        fail(C, f"全书骨架没覆盖第 {cut(miss, 12)} 章（每章恰在一块）")
    if dup:
        fail(C, f"全书骨架里一章落在多块: {cut(dup, 6)}")
    if extra:
        fail(C, f"全书骨架标了不存在的第 {extra} 章")
    for g in bk["groups"]:
        for l in g["leaves"]:
            if not l["chs"]:
                fail(C, f"全书骨架的块「{l['label']}」没标章范围（`块名 · 第a–b章`）")
    gid = {g["id"] for g in bk["groups"]}
    for e in bk["edges"]:
        if e.get("ga") not in gid or e.get("gb") not in gid or e["ga"] == e["gb"]:
            continue
        if not e["label"] or not e["phrase"]:
            fail(C, f"全书骨架的边 {e['a']}→{e['b']} 没写 `|关系词：短语|`")
        elif e["rel"] not in skeleton_figure.REL_WORDS:
            warn(C, f"全书骨架的边 {e['a']}→{e['b']} 关系词「{e['rel']}」不在词表（{'/'.join(skeleton_figure.REL_WORDS)}）")
    for m in skel_graph_issues(bk)[0]:
        fail(C, f"全书骨架: {m}")
    # 卷骨架：每卷一张，覆盖该卷的章（不漏不重）
    vcov = [(a, sk, skel_chapters(sk)) for a, sk in vols]
    for g in bk["groups"]:
        want = {c for l in g["leaves"] for c in l["chs"]}
        if not want:
            continue
        best = max(vcov, key=lambda t: len(want & set(t[2])), default=None)
        if not best or not want & set(best[2]):
            fail(C, f"「{g['label']}」缺卷骨架图（块为 subgraph、章为子题，覆盖第 {min(want)}–{max(want)} 章）")
            continue
        a, sk, vc = best
        vm = sorted(want - set(vc))
        vx = sorted(set(vc) - want)
        vd = [f"第{c}章" for c, v in sorted(vc.items()) if len(v) > 1]
        if vm:
            fail(C, f"00-front.md:L{a + 1}「{g['label']}」的卷骨架漏了第 {cut(vm, 10)} 章")
        if vx:
            fail(C, f"00-front.md:L{a + 1}「{g['label']}」的卷骨架多出不属于本卷的第 {cut(vx, 10)} 章")
        if vd:
            fail(C, f"00-front.md:L{a + 1}「{g['label']}」的卷骨架里一章出现多次: {'、'.join(vd)}")
        for m in skel_graph_issues(sk)[0]:
            fail(C, f"00-front.md:L{a + 1} 卷骨架: {m}")
    # 总纲卷回到骨架（原"书尾回到骨架"：book PARADIGM 方法 6 起由 98-map 承担）
    M = ws.map
    if M:
        check_map_l1(C, M, nvol, nch)
        flat = re.sub(r"\s+", "", M.text)
        gone = [g["label"] for g in bk["groups"]
                if re.sub(r"\s+", "", VOL_PREFIX_RE.sub("", g["label"])) not in flat]
        if gone:
            warn(C, f"总纲卷没回到全书骨架：卷概念「{'」「'.join(gone)}」没在 98-map.md 出现")
    else:
        warn(C, "没有 98-map.md，全书骨架没有填满版的回收处（见 #book_map）")
    info(C, f"全书骨架 {len(bk['groups'])} 卷 · 覆盖 {len(cov)} 章 · 卷骨架 {len(vols)} 张")


def node_trees(ws):
    """全书任何文件里的节点级科技树 mermaid → [位置]。不算：`%% skeleton` 骨架图、标签以 §N.M 或
    「第N章」开头的章首/章末进度图（粒度到节或章；与 compile_story_pdf.is_section_map / is_stage_map 同口径）。"""
    out = []
    for d in list(ws.chapters) + book_docs(ws):
        for a, _b, src in mermaid_blocks(d, 0, len(d.lines)):
            if skeleton_figure.is_skeleton(src) or re.search(r'[\[\(\{]\s*"?\s*(?:§|第)\s*\d', src):
                continue
            first = next((x.strip() for x in src.split("\n") if x.strip()), "")
            out.append(f"{d.name}:L{a + 1}（{first[:24]}）")
    return out


def book_docs(ws):
    """书首、各卷串讲、总纲、书尾（不含章）。"""
    return [d for d in [ws.front] + [ws.synths[k] for k in sorted(ws.synths)] + [ws.map, ws.back] if d]


SEC_REF_RE = re.compile(r"§\s*(\d+)\.(\d+)")


def body_text(doc):
    """正文行（去代码 / mermaid / 注释），用于字数与引用扫描。"""
    return "\n".join(ln for i, ln in enumerate(doc.lines) if doc.kind[i] not in ("code", "mermaid", "comment"))


def chapter_skeleton_leaves(ch):
    """章开章骨架图（首个 `%% skeleton`）→ 叶子挂的 § 列表（'12.3'）。"""
    for _a, _b, src in mermaid_blocks(ch, ch.open[0], ch.open[1]):
        if skeleton_figure.is_skeleton(src):
            sk = skeleton_figure.parse_skeleton(src)
            return [x for g in sk["groups"] for l in g["leaves"] for x in l["secs"]]
    return []


def h2_block(doc, key):
    """标题含 key 的 `## ` 小节 → (起行, 止行)；没有返回 None。"""
    h2 = [i for i, ln in enumerate(doc.lines) if ln.startswith("## ") and doc.kind[i] == "heading"]
    for k, i in enumerate(h2):
        if key in doc.lines[i]:
            return i, (h2[k + 1] if k + 1 < len(h2) else len(doc.lines))
    return None


def check_volume_synthesis(ws):
    """E-BOOK-30：每卷最后一章之后一份卷串讲 NNv-<slug>.md。"""
    C = "volume_synthesis"
    if not ws.volumes:
        skip(C, "spine.md 没有卷行（`# 第 K 卷 … — 解锁: …`）")
        return
    last = {max(v["chs"]): v for v in ws.volumes}
    for nn in sorted(ws.synths):
        if nn not in last:
            fail(C, f"{ws.synths[nn].name}: 第 {nn} 章不是任何一卷的最后一章（卷末章: {sorted(last)}）")
    for v in ws.volumes:
        nn = max(v["chs"])
        d = ws.synths.get(nn)
        tag = f"第 {v['k']} 卷"
        if not d:
            fail(C, f"{tag}（第 {min(v['chs'])}–{nn} 章）缺卷串讲 book/{nn:02d}v-<slug>.md")
            continue
        n = d.name
        h1 = next((ln for ln in d.lines if ln.startswith("# ")), "")
        m = re.match(r"^#\s+第\s*([一二三四五六七八九十\d]+)\s*卷串讲\s*[:：]\s*\S", h1)
        if not m:
            fail(C, f"{n} 首行应为「# 第 K 卷串讲：<卷标题>」，实为「{h1[:30]}」")
        elif cn_to_int and cn_to_int(m.group(1)) != v["k"]:
            fail(C, f"{n} 标题写的是第 {m.group(1)} 卷，按文件号应为 {tag}")
        for i, ln in enumerate(d.lines):
            if d.kind[i] == "heading" and re.match(r"^##\s+§", ln):
                fail(C, f"{n}:L{i + 1} 卷串讲用了 § 节标题（小节用不编号的 `## `，CONTRACTS T4）")
            if d.kind[i] == "comment" and "nodes:" in ln:
                fail(C, f"{n}:L{i + 1} 卷串讲带了节注释 `<!-- nodes -->`")
            if d.kind[i] not in ("code", "mermaid") and "![" in ln:
                fail(C, f"{n}:L{i + 1} 卷串讲放了原图（只讲关系，不放图）")
        # 卷骨架 = L2 卷内图（框标题「块名 · 第a–b章」，覆盖本卷全部章、不重）；L1 位置图与 L3 块内图不计
        sks = [skeleton_figure.parse_skeleton(src) for _a, _b, src in mermaid_blocks(d, 0, len(d.lines))
               if skeleton_figure.is_skeleton(src)]
        l2 = [sk for sk in sks if skeleton_figure.level(sk) == "L2"]
        legacy = [sk for sk in sks if skeleton_figure.figure_kind(sk) == "volume"]
        if l2:
            got = {}
            for g in l2[0]["groups"]:
                for c in g["chs"]:
                    got.setdefault(c, []).append(g["label"])
            if len(l2) > 1:
                warn(C, f"{n} 有 {len(l2)} 张卷内图（框标题「块名 · 第a–b章」），只认第一张")
            miss = sorted(set(v["chs"]) - set(got))
            extra = sorted(set(got) - set(v["chs"]))
            dup = [f"第{c}章" for c, ls in sorted(got.items()) if len(ls) > 1]
            if miss:
                fail(C, f"{n} 的卷内图没覆盖本卷第 {cut(miss, 10)} 章（框标题「块名 · 第a–b章」）")
            if extra:
                fail(C, f"{n} 的卷内图标了不属于本卷的第 {cut(extra, 10)} 章")
            if dup:
                fail(C, f"{n} 的卷内图里一章落在多块: {'、'.join(dup)}")
            for m in skel_graph_issues(l2[0])[0]:
                fail(C, f"{n} 卷内图: {m}")
        elif legacy:
            got = set()
            for sk in legacy:
                got |= set(skel_chapters(sk))
            miss = sorted(set(v["chs"]) - got)
            warn(C, f"{n} 还是旧式卷骨架（块里列章），应换成 L2 卷内图（框 = 块，框标题「块名 · 第a–b章」，框内 补：/交出：）")
            if miss:
                fail(C, f"{n} 的骨架图没覆盖本卷第 {cut(miss, 10)} 章")
        else:
            fail(C, f"{n} 没有卷内图（`%% skeleton`，框 = 块，框标题「块名 · 第a–b章」，覆盖本卷全部章）")
        # 概念位置表 / 跨章易混
        if not any("大概念" in "".join(head) for _i0, head, _rows in tables(d)):
            fail(C, f"{n} 缺概念位置表（表头含「大概念」：| 章 | 大概念 | 用到前面的什么 | 交给后面什么 |）")
        if not h2_block(d, "跨章易混"):
            fail(C, f"{n} 缺「## 跨章易混」小节")
        # 引用的 § 都存在
        body = body_text(d)
        bad = sorted({f"§{a}.{b}" for a, b in SEC_REF_RE.findall(body) if f"{a}.{b}" not in ws.sec_by},
                     key=lambda x: tuple(int(y) for y in x[1:].split(".")))
        if bad:
            fail(C, f"{n} 引用了不存在的节: {cut(bad, 10)}")
        nz = zi(plain(body))
        if not 2000 <= nz <= 5000:
            warn(C, f"{n} {nz} 字（约 2500–4000 字为宜，2000–5000 之外报）")
        info(C, f"{n} {nz} 字 · 引 § {len(set(SEC_REF_RE.findall(body)))} 个")


def check_book_map(ws):
    """E-BOOK-31：总纲卷 98-map.md + 全书不出现节点级科技树。"""
    C = "book_map"
    M = ws.map
    if not M:
        fail(C, "缺总纲卷 book/98-map.md（book PARADIGM 方法 6）")
        return
    h1 = next((ln for ln in M.lines if ln.startswith("# ")), "")
    if not re.match(r"^#\s+总纲", h1):
        fail(C, f"98-map.md 首行应为「# 总纲：全书归位」，实为「{h1[:30]}」")
    sks = [skeleton_figure.parse_skeleton(src) for _a, _b, src in mermaid_blocks(M, 0, len(M.lines))
           if skeleton_figure.is_skeleton(src)]
    if not any(skeleton_figure.figure_kind(sk) == "book" for sk in sks):
        fail(C, "98-map.md 没有全书骨架图（`%% skeleton`，每卷一个 subgraph）")
    # 层级总目录：全部章号 + 全部章骨架叶子上的 §
    blk = h2_block(M, "层级总目录")
    if not blk:
        fail(C, "98-map.md 缺「## 层级总目录」")
    else:
        t = "\n".join(M.lines[blk[0]:blk[1]])
        chs = {int(x) for x in re.findall(r"第\s*(\d+)\s*章", t)}
        want = sorted(c["num"] for c in ws.spine_ch) or sorted(c.num for c in ws.chapters)
        miss = [c for c in want if c not in chs]
        if miss:
            fail(C, f"层级总目录漏了第 {cut(miss, 12)} 章")
        secs = {f"{a}.{b}" for a, b in SEC_REF_RE.findall(t)}
        leaf = [x for ch in ws.chapters for x in chapter_skeleton_leaves(ch)]
        lmiss = [f"§{x}" for x in dict.fromkeys(leaf) if x not in secs]
        if lmiss:
            fail(C, f"层级总目录漏了 {len(lmiss)} 个章骨架叶子上的节: {cut(lmiss, 12)}")
        info(C, f"层级总目录 {len(chs)} 章 · {len(secs)} 节")
    # 跨卷主线：每个 generator 出现（00-front 的读者说法 / 名称分段）
    blk = h2_block(M, "跨卷主线")
    if not blk:
        fail(C, "98-map.md 缺「## 跨卷主线」")
    else:
        t = re.sub(r"\s+", "", "\n".join(M.lines[blk[0]:blk[1]]))
        for g in (ws.tree or {}).get("generators", []):
            name = ws.nodes.get(g, {}).get("name", "")
            keys = [name] + [x for x in re.split(r"[：:（(，,]", name) if len(x) >= 3]
            if not any(re.sub(r"\s+", "", k) in t for k in keys if k) and g not in t:
                warn(C, f"跨卷主线没写根思想 {g}「{name}」")
    # 按问题找位置
    blk = h2_block(M, "按问题找位置")
    if not blk:
        fail(C, "98-map.md 缺「## 按问题找位置」")
    else:
        rows = sum(len(r) for i0, _h, r in tables(M) if blk[0] <= i0 < blk[1])
        if rows < 20:
            warn(C, f"按问题找位置只有 {rows} 行（约 25–40 行为宜，<20 报）")
        else:
            info(C, f"按问题找位置 {rows} 行")
    bad = sorted({f"§{a}.{b}" for a, b in SEC_REF_RE.findall(body_text(M)) if f"{a}.{b}" not in ws.sec_by},
                 key=lambda x: tuple(int(y) for y in x[1:].split(".")))
    if bad:
        fail(C, f"98-map.md 引用了不存在的节: {cut(bad, 10)}")


def check_book(ws, chapter_mode):
    whole = ["files", "front_first_page", "apex_front_back", "prereq_covers_external", "front_mermaid", "book_skeleton",
             "volume_synthesis", "book_map", "generator_chapters", "toc_matches", "front_elements", "front_length", "stats", "case_thread",
             "reverse_index", "node_index", "keyword_index", "exam_appendix", "appendix_narrow"]
    # xref_format / xref_targets（按章也能判）
    all_secs = set(ws.spine_sec) | {s.num for s in ws.secs}
    nch = max([c["num"] for c in ws.spine_ch] + [c.num for c in ws.chapters] + [0])
    docs = list(ws.chapters) + ([] if chapter_mode else book_docs(ws))
    for d in docs:
        for i, ln in enumerate(d.lines):
            if d.kind[i] in ("code", "fndef", "comment"):
                continue
            t = ln
            m = re.search(r"第\s*\d+\s*弧|前面第.{1,3}节|后面第.{1,3}节|\bKP-?\d|第[一二三四五六七八九十]+节|§\s*\d+(?![\d.])", t)
            if m:
                fail("xref_format", f"{d.name}:L{i + 1} 引用写法「{m.group(0)}」（只用 §N.M / 第 N 章 / N-xx）")
            for x in re.findall(r"§\s*(\d+\.\d+)", t):
                if all_secs and x not in all_secs:
                    fail("xref_targets", f"{d.name}:L{i + 1} §{x} 既不在书里也不在 spine")
            for x in re.findall(r"第\s*(\d+)\s*章", t):
                if nch and int(x) > nch:
                    fail("xref_targets", f"{d.name}:L{i + 1} 第 {x} 章不存在")
            if d.kind[i] != "mermaid":
                for x in ID_RE.findall(t):
                    if ws.nodes and x not in ws.nodes:
                        fail("xref_targets", f"{d.name}:L{i + 1} {x} 不在 tree.json")
    R["xref_format"]["ran"] = R["xref_targets"]["ran"] = True
    # reading_guide_once —— 章文件部分
    for ch in ws.chapters:
        t = ch.text
        if re.search(r"^#+\s*读法|满电精读|快速路径|复习路径|考前路径", t, re.M):
            fail("reading_guide_once", f"{ch.name} 章文件含读法指南（只在书首一次）")
        if re.search(r"发散参数|divergence_|relevance_threshold", t):
            fail("reading_guide_once", f"{ch.name} 章文件含全书配置（发散参数）")
    R["reading_guide_once"]["ran"] = True
    if chapter_mode:
        for c in whole:
            skip(c, "需要全书（--chapter 模式）")
        return
    # files
    if not os.path.isdir(ws.book):
        for c in whole:
            fail(c, "book/ 不存在") if c == "files" else skip(c, "book/ 不存在")
        return
    if not ws.front:
        fail("files", "缺 00-front.md")
    if not ws.back:
        fail("files", "缺 99-back.md")
    for f in ws.extra:
        fail("files", f"多余或命名不合规的文件 {f}（应为 NN-<英文 slug>.md / NNv-<slug>.md 卷串讲 / 98-map.md 总纲）")
    got = sorted(c.num for c in ws.chapters)
    want = sorted(c["num"] for c in ws.spine_ch)
    if want and got != want:
        miss = sorted(set(want) - set(got))
        extra = sorted(set(got) - set(want))
        fail("files", f"章文件与 spine 不一一对应：缺 {cut(miss, 12)}" + (f"；多 {extra}" if extra else ""))
    info("files", f"{len(got)} 章 + 卷串讲 {len(ws.synths)} + {'总纲 ' if ws.map else ''}"
                  f"{'书首' if ws.front else ''}{'书尾' if ws.back else ''}")
    tree = ws.tree or {}
    F, B = ws.front, ws.back
    if not F:
        for c in ("front_first_page", "apex_front_back", "prereq_covers_external", "front_mermaid", "generator_chapters",
                  "toc_matches", "front_elements", "front_length", "case_thread"):
            fail(c, "缺 00-front.md")
        skip("book_skeleton", "没有书首（00-front.md 存在时才查）")
    else:
        ftext = F.text
        fh = h2_sections(F)
        first_h2 = next((i for i, ln in enumerate(F.lines) if ln.startswith("## ")), len(F.lines))
        # front_first_page
        for i0, head, rows in tables(F):
            if i0 < first_h2 and len(head) >= 4:
                fail("front_first_page", f"00-front.md:L{i0 + 1} 第一页有 {len(head)} 列表格")
        fp = next((i for i in range(1, first_h2) if F.kind[i] == "prose"), None)
        if fp is None:
            fail("front_first_page", "第一个 ## 之前没有回答「这个范围在说什么」的段落")
        else:
            info("front_first_page", f"首段: {plain(F.lines[fp])[:30]}")
        # apex_front_back
        st = (tree.get("apex") or {}).get("statement", "")
        if not re.search(r"终极理解", ftext):
            fail("apex_front_back", "书首没有终极理解专属块/节")
        if st and overlap(st, ftext) < 0.6:
            fail("apex_front_back", "书首终极理解与 tree.apex.statement 不一致")
        if B and st and overlap(st, B.text) < 0.4:
            fail("apex_front_back", "书尾没有回收终极理解")
        R["apex_front_back"]["ran"] = True
        # prereq_covers_external
        pk = next((k for k in fh if "前置" in k), None)
        if not pk:
            fail("prereq_covers_external", "书首没有「前置」节")
        else:
            ptxt = "\n".join(F.lines[i] for i in fh[pk])
            for nid, n in ws.nodes.items():
                if n.get("kind") == "external" and n.get("role") != "extension" and nid not in ptxt \
                        and n.get("name", "\0") not in ptxt:
                    fail("prereq_covers_external", f"前置清单缺 {nid}「{n.get('name')}」")
            for w in ("必备", "加分", "自检"):
                if w not in ptxt:
                    fail("prereq_covers_external", f"前置清单缺「{w}」")
        R["prereq_covers_external"]["ran"] = True
        # front_mermaid
        # 大图 = 全书骨架（节点级科技树不进书，见 #book_skeleton / #book_map）
        if "```mermaid" not in ftext:
            fail("front_mermaid", "书首没有 mermaid 骨架图")
        elif "根思想" not in ftext:
            fail("front_mermaid", "书首大图说明缺「根思想」")
        R["front_mermaid"]["ran"] = True
        # book_skeleton
        check_book_skeleton(ws, F, B)
    trees = node_trees(ws)
    if trees:
        fail("book_skeleton", f"书里出现节点级科技树 mermaid（不进书，职能由 98-map 层级总目录接手）: {cut(trees, 6)}")
    check_volume_synthesis(ws)
    check_book_map(ws)
    if F:
        # generator_chapters
        for g in tree.get("generators", []):
            n = ws.nodes.get(g, {})
            lines = [ln for ln in F.lines if n.get("name", "\0") in ln or g in ln]
            if not lines:
                fail("generator_chapters", f"书首没列出根思想 {g}「{n.get('name')}」")
                continue
            chs = {int(x) for ln in lines for x in re.findall(r"第\s*(\d+)", ln)}
            chs |= {int(x) for ln in lines for x in re.findall(r"第[^章]*?(\d+)[、，,和与及 ]", ln)}
            if not chs:
                fail("generator_chapters", f"根思想 {g} 没标展开章节")
            for c in sorted(chs):
                ids = {x for s in ws.secs if s.a == c for x in s.nodes}
                if not any(g in ws.nodes.get(x, {}).get("derives_from", []) or x == g for x in ids):
                    fail("generator_chapters", f"根思想 {g} 标了第 {c} 章，但该章没有 derives_from 它的节点")
        R["generator_chapters"]["ran"] = True
        # toc_matches
        tk = next((k for k in fh if "目录" in k), None)
        if not tk:
            fail("toc_matches", "书首没有「目录」节")
        else:
            tl = [F.lines[i] for i in fh[tk]]
            for c in ws.spine_ch:
                rows = [x for x in tl if re.search(rf"第\s*{c['num']}\s*章(?!\d)", x)]
                if len(rows) != 1:
                    fail("toc_matches", f"目录里第 {c['num']} 章 {len(rows)} 行（应恰 1）")
                elif not parse_pages(rows[0]) and not any(sh in rows[0] for sh in ws.mats):
                    warn("toc_matches", f"目录第 {c['num']} 章行没写覆盖材料")
        R["toc_matches"]["ran"] = True
        # reading_guide_once（书首部分）
        for w in ("满电", "快速", "复习"):
            if w not in ftext:
                fail("reading_guide_once", f"书首读法缺「{w}」路径")
        if len(re.findall(r"^#+\s*读法", ftext, re.M)) > 1:
            fail("reading_guide_once", "书首读法出现不止一次")
        # front_elements
        el = {"定位": fp is not None, "前置": bool(pk), "大图": "```mermaid" in ftext,
              "生成元": bool(re.search(r"根思想", ftext))}
        for k, v in el.items():
            if not v:
                fail("front_elements", f"书首缺要素「{k}」")
        R["front_elements"]["ran"] = True
        # front_length
        if ws.chapters:
            med = statistics.median(len(c.text) for c in ws.chapters)
            if len(ftext) >= med:
                fail("front_length", f"书首 {len(ftext)} 字符 ≥ 章中位数 {int(med)}")
            else:
                info("front_length", f"书首 {len(ftext)} < 章中位数 {int(med)}")
        # case_thread（启发式）
        if "案例" not in ftext:
            warn("case_thread", "书首没有运行案例登场")
        else:
            rows = [ln for ln in F.lines if re.search(r"第\s*\d+\s*章", ln) and "案例" not in ln]
            info("case_thread", "书首有运行案例")
        if B and "案例" not in B.text:
            warn("case_thread", "书尾没有运行案例的完整解答")
        R["case_thread"]["ran"] = True
    # stats
    both = (F.text if F else "") + "\n" + (B.text if B else "")
    nsec = len(ws.secs)
    for pat, want_n, lab in ((r"(\d+)\s*章", len(ws.chapters), "章数"), (r"(\d+)\s*节(?!点)", nsec, "节数"),
                             (r"(\d+)\s*个?节点", len(ws.nodes), "节点数")):
        vals = {int(x) for x in re.findall(pat, both)}
        if want_n not in vals:
            fail("stats", f"书首/书尾没给出与实际一致的{lab}（实际 {want_n}）")
    if re.search(r"高频节点|高频", both):
        fail("stats", "给了高频类重要度统计")
    R["stats"]["ran"] = True
    if not B:
        for c in ("reverse_index", "node_index", "keyword_index", "exam_appendix", "appendix_narrow"):
            fail(c, "缺 99-back.md")
        return
    bh = h2_sections(B)
    bt = tables(B)
    # reverse_index
    rk = next((k for k in bh if "反查" in k), None)
    if not rk:
        fail("reverse_index", "书尾没有「材料 → 本书反查表」")
    else:
        lines = bh[rk]
        mapped = set()
        for i0, head, rows in bt:
            if i0 in lines:
                for r in rows:
                    if r and len(r) > 1 and re.search(r"§", " ".join(r[1:])):
                        mapped |= parse_pages(r[0])
                    for x in r[1:]:
                        if any(m in x for m in EXTERNAL_BLOCKS):
                            fail("position", f"反查表落点列是补充块: {r[0]} → {x}")
        want_p = set()
        for n in ws.nodes.values():
            want_p |= parse_pages("; ".join(n.get("sources", [])))
        ex = {p for e in (tree.get("coverage") or {}).get("exempt", []) for p in parse_pages(e.get("source", ""))}
        miss = sorted(want_p - mapped - ex)
        if miss:
            fail("reverse_index", f"反查表缺 {len(miss)} 页: {cut([f'{a} p{b}' for a, b in miss], 10)}")
        if not any(B.kind[i] == "prose" for i in lines[:6]):
            warn("reverse_index", "反查表前缺一句用途说明")
        info("reverse_index", f"映射 {len(mapped)} 页")
    # node_index
    nk = next((k for k in bh if "节点索引" in k), None)
    if not nk:
        fail("node_index", "书尾没有节点索引")
    else:
        txt = "\n".join(B.lines[i] for i in bh[nk])
        miss = [n for n in ws.nodes if n not in txt]
        if miss:
            fail("node_index", f"节点索引缺 {len(miss)} 个: {cut(miss, 10)}")
        for i0, head, rows in bt:
            if i0 in bh[nk] and len(head) != 4:
                fail("node_index", f"节点索引应 4 列（id / 名称 / 所在节 / 出处），实为 {len(head)}")
    # keyword_index
    kk = [k for k in bh if "关键词" in k]
    if not kk:
        fail("keyword_index", "书尾没有英文关键词索引")
    else:
        kl = {i for k in kk for i in bh[k]}
        kt = [t for t in bt if t[0] in kl]
        if not kt:
            fail("keyword_index", "关键词索引没有表")
        for i0, head, rows in kt:
            bad = [r[0] for r in rows if len(r) > 1 and "§" not in r[1]]
            if bad:
                fail("keyword_index", f"L{i0 + 1} 关键词位置不是 §: {cut(bad, 5)}")
        R["keyword_index"]["ran"] = True
    # exam_appendix
    ek = [k for k in bh if re.search(r"考试|往年题|考察", k)]
    if ws.exam and not ek:
        fail("exam_appendix", "reader.md 声明了考试，书尾缺考试附录")
    if not ws.exam and ek:
        fail("exam_appendix", "reader.md 未声明考试，书尾却有考试附录")
    for k in ek:
        t = "\n".join(B.lines[i] for i in bh[k])
        m = re.search(r"占比|频次|高频|必考|\d+\s*%", t)
        if m:
            fail("exam_appendix", f"考试附录含「{m.group(0)}」")
    R["exam_appendix"]["ran"] = True
    # appendix_narrow
    for i0, head, rows in bt:
        if len(head) > 4:
            fail("appendix_narrow", f"99-back.md:L{i0 + 1} 表 {len(head)} 列 > 4")
    R["appendix_narrow"]["ran"] = True


# ---------------------------------------------------------------- audit
def check_audit(ws, chapter_mode, args):
    tree = ws.tree or {}
    # spine_sync / ids（按章也能判）
    for s in ws.secs:
        sp = ws.spine_sec.get(s.num)
        if not sp:
            fail("spine_sync", f"§{s.num} 不在 spine")
            continue
        miss = [n for n in sp["nodes"] if n not in s.nodes]
        extra = [n for n in s.nodes if n not in sp["nodes"]]
        if miss:
            fail("spine_sync", f"§{s.num} spine 安排的 {', '.join(miss)} 不在节注释里")
        if extra:
            warn("spine_sync", f"§{s.num} 节注释多出 spine 未安排的 {', '.join(extra)}")
    for ch in ws.chapters:
        for sec, d in ws.spine_sec.items():
            if d["ch"] == ch.num and sec not in ws.sec_by:
                fail("spine_sync", f"spine 的 §{sec} 在 {ch.name} 里没有")
    R["spine_sync"]["ran"] = True
    for s in ws.secs:
        for n in s.nodes:
            if ws.nodes and n not in ws.nodes:
                fail("ids", f"§{s.num} 注释 id {n} 不在 tree.json")
    for ch in ws.chapters:
        for i, ln in enumerate(ch.lines):
            if ch.kind[i] in ("comment", "code"):
                continue
            for n in ID_RE.findall(ln):
                if n in ws.nodes and n not in ws.land and n not in ws.plan:
                    warn("ids", f"{ch.name}:L{i + 1} 引用 {n} 但它没有落点节（悬空）")
    R["ids"]["ran"] = True
    # sources
    for ch in ws.chapters:
        for s in ch.sections:
            for sh, p in s.pages:
                m = ws.mats.get(sh)
                if ws.mats and not m:
                    warn("sources", f"§{s.num} sources 短名 {sh} 未登记")
                elif m and p > m.get("pages", 10 ** 6):
                    warn("sources", f"§{s.num} {sh} p{p} 超出材料页数 {m['pages']}")
            for r, i in ch.fnrefs:
                if s.start <= i < s.end and r in ch.fndefs:
                    pg = parse_pages(ch.fndefs[r][0])
                    out = [f"{a} p{b}" for a, b in pg if (a, b) not in s.pages]
                    if out and s.pages:
                        warn("sources", f"§{s.num} 脚注 [^{r}] 的 {', '.join(out)} 不在本节 sources")
    if not ws.mats:
        info("sources", "raw/_manifest.json 不存在，页数上限核对跳过")
    R["sources"]["ran"] = True
    # position
    for s in ws.secs:
        ch = s.ch
        for n in s.nodes:
            nd = ws.nodes.get(n, {})
            pats = [x for x in (nd.get("name"), nd.get("en")) if x and len(x) >= 3]
            inprose = inaside = False
            for i in range(s.start + 2, s.end):
                if not any(p.lower() in ch.lines[i].lower() for p in pats):
                    continue
                b = ch.block_at(i)
                if b and b.marker in EXTERNAL_BLOCKS:
                    inaside = True
                else:
                    inprose = True
            if inaside and not inprose:
                fail("position", f"§{s.num} 节点 {n}「{nd.get('name')}」只出现在补充块里")
    R["position"]["ran"] = True
    # no_exempt_in_body
    for ch in ws.chapters:
        for i, ln in enumerate(ch.lines):
            if ch.kind[i] in ("comment", "fndef", "code"):
                continue
            if "豁免" in ln or re.search(r"(?:不展开|不讲|跳过).{0,20}[A-Za-z][\w-]*\s+p\d+|[A-Za-z][\w-]*\s+p\d+.{0,20}(?:不展开|不讲|跳过)", ln):
                fail("no_exempt_in_body", f"{ch.name}:L{i + 1} 正文列了豁免页/不展开页")
    R["no_exempt_in_body"]["ran"] = True
    # deps（早用即 FAIL；落点用书中注释，缺时用 spine）
    order = {**ws.plan, **ws.land}
    reported = set()
    for s in ws.secs:
        ch = s.ch
        req = {r for n in s.nodes for r in ws.nodes.get(n, {}).get("requires", [])}
        txt = "\n".join(ch.lines[i] for i in range(s.start + 2, s.end) if ch.kind[i] not in ("comment", "mermaid", "fndef"))
        low = txt.lower()
        for nid, key in order.items():
            if key <= s.key or nid in req or nid in reported:
                continue
            n = ws.nodes.get(nid, {})
            name, en = n.get("name", ""), n.get("en", "")
            hit = None
            if len(name) >= 3 and name in txt:
                hit = name
            elif len(en) >= 6 and re.search(rf"(?<![A-Za-z]){re.escape(en.lower())}(?![A-Za-z])", low):
                hit = en
            if hit:
                reported.add(nid)
                # 同章先用后讲：读者按整章读、作者应就地白话解释一句 → WARN；跨章提前 → FAIL
                ptr = rf"§\s*{key[0]}\.{key[1]}(?!\d)|第\s*{key[0]}\s*章"
                foreshadow = bool(re.search(ptr, txt))  # 预告式首现：就地一句白话 + 指明落点节
                (warn if key[0] == s.key[0] or foreshadow else fail)(
                    "deps", f"§{s.num} 提前用了「{hit}」（{nid}，落点 §{key[0]}.{key[1]}）—— "
                    + ("确认用到处已就地白话解释" if key[0] == s.key[0] or foreshadow else "改用通用说法、调序，或就地一句白话并指明落点节"))
    R["deps"]["ran"] = True
    # hollow
    for s in ws.secs:
        ch = s.ch
        rest = [t for _, t in text_units(ch, s.start + 2, s.end, with_blocks=False)]
        has = any(ch.kind[i] in ("math", "table", "code", "image") for i in range(s.start + 2, s.end))
        z = zi("\n".join(rest))
        t = tier(ws, ch, s) if hasattr(ch, "core_secs") else "常规"
        floor = {"核心": 300, "常规": 150, "背景": 60}[t]
        if z < floor and not (has and z >= floor // 2):
            fail("hollow", f"§{s.num}（{t}）盖住所有块后正文只剩 {z} 字（下限 {floor}）")
        if re.search(r"(?:原则|要点|步骤)是\s*[A-Za-z]\s*[。]|有以下几[点条]\s*[。：:]\s*$", "\n".join(rest)):
            warn("hollow", f"§{s.num} 疑似空壳句（只说'原则是 X'不列 X）")
    R["hollow"]["ran"] = True
    # --strip-blocks
    if args.strip_blocks:
        od = os.path.join(ws.ws, "audit", "strip-blocks")
        os.makedirs(od, exist_ok=True)
        for ch in ws.chapters:
            keep = [ln for i, ln in enumerate(ch.lines) if ch.kind[i] != "quote" and "⚡" not in ln]
            open(os.path.join(od, ch.name), "w", encoding="utf-8").write("\n".join(keep))
        info("strip_blocks", f"纯正文已导出到 {od}（逐节对照 sources 页打勾，E-AUDIT-27）")
    else:
        skip("strip_blocks", "未给 --strip-blocks")
    # --baseline
    if args.baseline:
        old_pages, old_nodes = set(), set()
        for p in glob.glob(os.path.join(args.baseline, "*.md")):
            for ln in open(p, encoding="utf-8").read().split("\n"):
                cm = COMMENT_RE.match(ln.strip())
                if cm:
                    old_nodes |= set(ID_RE.findall(cm.group(1)))
                    old_pages |= parse_pages(cm.group(2))
        new_nodes = {n for s in ws.secs for n in s.nodes}
        new_pages = set().union(*[s.pages for s in ws.secs]) if ws.secs else set()
        ln_ = sorted(old_nodes - new_nodes)
        lp = sorted(old_pages - new_pages)
        if ln_:
            fail("baseline", f"只增不减: 旧版认领的节点新版缺 {cut(ln_, 10)}")
        if lp:
            fail("baseline", f"只增不减: 旧版认领的页新版缺 {cut([f'{a} p{b}' for a, b in lp], 10)}")
        info("baseline", f"旧版 {len(old_nodes)} 节点 / {len(old_pages)} 页")
    else:
        skip("baseline", "未给 --baseline")

    whole = ["generators_in_book", "nodes", "apex", "coverage_table", "exam_map", "exercises"]
    if chapter_mode:
        for c in whole:
            skip(c, "需要全书（--chapter 模式）")
        return
    landed = {n for s in ws.secs for n in s.nodes}
    # generators_in_book
    miss = [g for g in tree.get("generators", []) if g not in landed]
    if miss:
        fail("generators_in_book", f"生成元没进任何节注释: {', '.join(miss)}")
    else:
        info("generators_in_book", f"{len(tree.get('generators', []))} 个生成元都有落点")
    # nodes
    miss = [n for n, d in ws.nodes.items() if d.get("kind") != "external" and n not in landed]
    if miss:
        fail("nodes", f"{len(miss)} 个非 external 节点没有落点节: {cut(miss, 12)}")
    if ws.back:
        bm = [n for n in ws.nodes if n not in ws.back.text]
        if bm:
            fail("nodes", f"{len(bm)} 个节点不在书尾反查/索引附录: {cut(bm, 10)}")
    R["nodes"]["ran"] = True
    # apex
    miss = [n for n in (tree.get("apex") or {}).get("unfolds", []) if n not in landed]
    if miss:
        fail("apex", f"apex.unfolds 没有落点节: {', '.join(miss)}")
    else:
        info("apex", "apex.unfolds 都有落点")
    # coverage_table / exam_map / exercises 需要 manifest
    if not ws.mats:
        for c in ("coverage_table", "exam_map", "exercises"):
            skip(c, "raw/_manifest.json 不存在，无法按材料对账")
        return
    node_sec = {}
    for s in ws.secs:
        for n in s.nodes:
            node_sec.setdefault(n, []).append(s)
    page_nodes = {}
    for nid, n in ws.nodes.items():
        for pg in parse_pages("; ".join(n.get("sources", []))):
            page_nodes.setdefault(pg, set()).add(nid)
    ex = {}
    for e in (tree.get("coverage") or {}).get("exempt", []):
        for pg in parse_pages(e.get("source", "")):
            ex[pg] = e.get("reason", "")
    for m in ws.mats.values():
        for e in m.get("exempt_pages", []):
            ex[(m["short"], e["page"])] = e.get("reason", "")
    figs = {}
    for s in ws.secs:
        for i in range(s.start, s.end):
            for mm in IMG_RE.finditer(s.ch.lines[i]):
                fm = re.search(r"课件\s+([A-Za-z][\w-]*)\s+p(\d+)", mm.group(1))
                if fm:
                    figs.setdefault((fm.group(1), int(fm.group(2))), set()).add(s.num)
    summ, detail, uncovered = [], [], []
    for sh, m in ws.mats.items():
        tot = m.get("pages", 0)
        cov = exm = 0
        for p in range(1, tot + 1):
            ns = page_nodes.get((sh, p), set())
            secs = {x.num for n in ns for x in node_sec.get(n, [])} | {x.num for x in ws.secs if (sh, p) in x.pages}
            secs = sorted(secs, key=lambda v: tuple(map(int, v.split("."))))
            if secs:
                cov += 1
                fig = " 🖼" if (sh, p) in figs else ""
                detail.append(f"| {sh} p{p} | {', '.join(sorted(ns))} | " + ", ".join(f"§{x}" for x in secs) + f"{fig} |")
            elif (sh, p) in ex:
                exm += 1
                detail.append(f"| {sh} p{p} | 豁免: {ex[(sh, p)]} | — |")
            else:
                uncovered.append(f"{sh} p{p}")
                detail.append(f"| {sh} p{p} | {', '.join(sorted(ns)) or '—'} | **未覆盖** |")
        rate = (cov + exm) / tot if tot else 1
        summ.append(f"| {sh} | {tot} | {cov} | {exm} | {tot - cov - exm} | {rate:.0%} |")
    od = os.path.join(ws.ws, "audit")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "coverage.md"), "w", encoding="utf-8") as f:
        f.write("# coverage — 由 verify_book.py#coverage_table 生成，勿手改\n\n"
                "| 材料 | 总页 | 已覆盖 | 豁免 | 未覆盖 | 覆盖率 |\n|---|---|---|---|---|---|\n" + "\n".join(summ) +
                "\n\n## 明细\n\n| 材料页 | 节点 id | 落点 |\n|---|---|---|\n" + "\n".join(detail) + "\n")
    if uncovered:
        fail("coverage_table", f"{len(uncovered)} 页既未落到书中节、也未豁免: {cut(uncovered, 12)}")
    else:
        info("coverage_table", f"audit/coverage.md 已生成，全部材料页有归宿")
    # exam_map / exercises
    for sh, m in ws.mats.items():
        role = m.get("role")
        if role not in ("exam", "practice", "solution"):
            continue
        for p in range(1, m.get("pages", 0) + 1):
            if (sh, p) in ex:
                continue
            ns = page_nodes.get((sh, p), set())
            cited = any((sh, p) in s.pages for s in ws.secs)
            if not cited and not any(n in node_sec for n in ns):
                fail("exercises", f"{sh} p{p}（{role}）在书里没有归宿")
            if role == "exam":
                lost = [n for n in ns if n not in node_sec]
                if lost:
                    fail("exam_map", f"{sh} p{p} 考到的 {', '.join(sorted(lost))} 没有落点节")
    R["exam_map"]["ran"] = R["exercises"]["ran"] = True


# ---------------------------------------------------------------- 输出
# ---------------------------------------------------------------- section 变体 · 前置节
# 覆盖表在 modules/compose/section/variants/prereq.md：「检查」列里不带 + 的检查对前置节关闭（下面
# apply_prereq_variant 把命中前置节的 FAIL/WARN 摘掉），带 + 的是变体新增的检查（check_prereq）。
VARIANT_PREREQ = os.path.join(HERE, "..", "modules", "compose", "section", "variants", "prereq.md")
GREEK_RE = re.compile(r"[α-ωΑ-Ωϱϑϕ]")
GREEK_GENERIC = set("ΣΔδεπθαβ")              # 纯数学里通用的记号，前置节可用
SRC_FN_RE = re.compile(r"\bp\.?\s?\d+")      # 脚注定义里带页码 = 指向材料页
BANNED_IN_PREREQ = ("☕", "🎓", "🤔", "🔍", "⚔️", "⚔")


def variant_prereq_checks():
    off, add = set(), set()
    if not os.path.exists(VARIANT_PREREQ):
        return off, add
    for ln in open(VARIANT_PREREQ, encoding="utf-8"):
        if not re.match(r"^\|\s*V-PRE-\d+\s*\|", ln):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", ln.strip())[1:-1]]
        for x in re.split(r"[,，]\s*", cells[5] if len(cells) > 5 else ""):
            x = x.strip()
            if x and x not in ("—", "-"):
                (add if x.startswith("+") else off).add(x.lstrip("+"))
    return off, add


def is_prereq(ws, s):
    return bool(s.nodes) and all(ws.nodes.get(n, {}).get("role") == "prerequisite" for n in s.nodes)


def sec_lines(s):
    """节正文的行号（不含标题与节注释、脚注定义）。"""
    ch = s.ch
    return [i for i in range(s.start + 1, s.end) if ch.kind[i] not in ("comment", "fndef")]


def name_keys(n):
    """材料节点名里可拿来查"后文术语"的片段：中文名截掉括号/冒号后的主干（≥3 字），英文名（≥6 字母）。"""
    keys = []
    head = re.split(r"[（(：:]", n.get("name", ""))[0].strip()
    if len(head) >= 3:
        keys.append(head)
    en = re.split(r"[(:]", n.get("en", ""))[0].strip()
    if len(en) >= 6:
        keys.append(en)
    return keys


def check_prereq(ws):
    """E-SEC-41 prereq_backref · E-SEC-42 prereq_no_forward · E-SEC-43 prereq_shape。"""
    pre = [s for s in ws.secs if is_prereq(ws, s)]
    if not pre:
        for c in ("prereq_no_forward", "prereq_shape", "prereq_backref"):
            skip(c, "无前置节")
        return
    # 每个节点第一次出场的节（按 spine，全书口径，不受 --chapter 影响）
    first_key = {}
    for sec, row in ws.spine_sec.items():
        m = re.match(r"(\d+)\.(\d+)", sec)
        if m:
            for n in row["nodes"]:
                k = (int(m.group(1)), int(m.group(2)))
                first_key[n] = min(first_key.get(n, k), k)
    material = [s for s in ws.secs if not is_prereq(ws, s)]
    greek_first = {}
    for s in material:
        for g in set(GREEK_RE.findall("\n".join(s.ch.lines[i] for i in sec_lines(s)))):
            greek_first[g] = min(greek_first.get(g, s.key), s.key)
    for s in pre:
        ch, idx = s.ch, sec_lines(s)
        text = "\n".join(ch.lines[i] for i in idx)
        tag = f"§{s.num}"
        # ---- prereq_no_forward（E-SEC-42）
        C = "prereq_no_forward"
        for m in re.finditer(r"§(\d+)\.(\d+)", text):
            if (int(m.group(1)), int(m.group(2))) > s.key:
                fail(C, f"{tag} 引用了后文 §{m.group(1)}.{m.group(2)}")
        for m in re.finditer(r"第\s*(\d+)\s*章", text):
            if int(m.group(1)) > ch.num:
                fail(C, f"{tag} 提到后文第 {m.group(1)} 章")
        for nid, n in ws.nodes.items():
            if n.get("kind") == "external" or first_key.get(nid, (0, 0)) <= s.key:
                continue
            for k in name_keys(n):
                if (k in text) if re.search(r"[一-鿿]", k) else re.search(rf"\b{re.escape(k)}\b", text, re.I):
                    fail(C, f"{tag} 出现后文材料节点「{k}」（{nid}，§{'.'.join(map(str, first_key[nid]))} 才出场）")
                    break
        for g in sorted(set(GREEK_RE.findall(text)) - GREEK_GENERIC):
            if g in greek_first and greek_first[g] > s.key:
                fail(C, f"{tag} 用了后文材料的符号「{g}」（§{'.'.join(map(str, greek_first[g]))} 才出现）")
        for key, i in ch.fnrefs:
            if s.start < i < s.end and key in ch.fndefs and SRC_FN_RE.search(ch.fndefs[key][0]):
                fail(C, f"{tag} 挂了材料页脚注 [^{key}]")
        R[C]["ran"] = True
        # ---- prereq_shape（E-SEC-43）
        C = "prereq_shape"
        blocks = ch.blocks_in(s.start, s.end)
        pin = next((b for b in blocks if b.marker == "📍"), None)
        if pin is None or "前置" not in pin.text or "够用线" not in pin.text:
            fail(C, f"{tag} 节首缺「📍 前置 · 约 N 分钟 · 够用线：…」")
        if not any(b.marker == "🔑" for b in blocks):
            fail(C, f"{tag} 缺 🔑 一句念头")
        rest = [i for i in idx if not (pin and pin.start <= i < pin.end)]
        if not any("够用线" in ch.lines[i] for i in rest):
            fail(C, f"{tag} 台阶里没有一处「够用线」")
        body = [i for i in idx if ch.kind[i] != "blank"]
        if len(body) > 40:
            fail(C, f"{tag} 正文 {len(body)} 行 > 40")
        bad = sorted({b.marker for b in blocks if b.marker in BANNED_IN_PREREQ})
        if bad:
            fail(C, f"{tag} 前置节不开 {' '.join(bad)}")
        R[C]["ran"] = True
    # ---- prereq_backref（E-SEC-41）：后文第一次用到前置的那一节要回指它
    C = "prereq_backref"
    sec_of = {}
    for s in ws.secs:
        for n in s.nodes:
            sec_of.setdefault(n, s)
    for s in pre:
        for p in s.nodes:
            users = [u for u, n in ws.nodes.items() if p in n.get("requires", []) and n.get("kind") != "external"]
            us = sorted((sec_of[u] for u in users if u in sec_of), key=lambda x: x.key)
            if not us:
                continue
            u = us[0]
            utext = "\n".join(u.ch.lines[i] for i in sec_lines(u))
            if not re.search(rf"§{s.a}\.{s.b}(?!\d)", utext):
                fail(C, f"§{u.num} 第一次用到前置 {p}（§{s.num}）却没回指 §{s.num}")
    R[C]["ran"] = True


def apply_prereq_variant(ws, off):
    """覆盖表关掉的检查：摘掉落在前置节（或全是前置节的补给站章）上的 FAIL/WARN。"""
    pre = [s for s in ws.secs if is_prereq(ws, s)]
    if not pre:
        return
    nums = {s.num for s in pre}
    spans = {}
    for s in pre:
        spans.setdefault(s.ch.name, []).append((s.start, s.end))
    supply = {ch.name for ch in ws.chapters if ch.sections and all(is_prereq(ws, s) for s in ch.sections)}

    def hits(m):
        if any(x in nums for x in re.findall(r"§(\d+\.\d+)(?!\d)", m)):
            return True
        mm = re.match(r"^(\S+\.md):L(\d+)", m)
        if mm and any(a <= int(mm.group(2)) - 1 < b for a, b in spans.get(mm.group(1), [])):
            return True
        return any(m.startswith(name) for name in supply)

    for c in off:
        if c in R:
            R[c]["fail"] = [m for m in R[c]["fail"] if not hits(m)]
            R[c]["warn"] = [m for m in R[c]["warn"] if not hits(m)]



def finish(quiet=False):
    nf = nw = 0
    for c in CHECKS:
        r = R[c]
        if r["skip"] and not r["ran"]:
            if quiet:
                continue
            print(f"[SKIP] {S}#{c}  {r['skip']}")
            continue
        if r["fail"]:
            nf += 1
            items = r["fail"]
            print(f"[FAIL] {S}#{c}  {cut(items, 20 if len(items) <= 20 else 12)}  → 修法见 {FIX.get(c, '')}")
            if r["warn"]:
                print(f"       (另有 WARN: {cut(r['warn'], 4)})")
        elif r["warn"]:
            nw += 1
            print(f"[WARN] {S}#{c}  {cut(r['warn'], 8)}  → {FIX.get(c, '')}")
        elif quiet:
            continue
        elif r["ran"]:
            print(f"[PASS] {S}#{c}  {cut(r['info'], 3)}")
        else:
            print(f"[SKIP] {S}#{c}  无可检对象")
    print(f"结果: {'FAIL' if nf else 'PASS'} ({nf} fail, {nw} warn)")
    sys.exit(1 if nf else 0)


def main():
    ap = argparse.ArgumentParser(description="full-learn 书稿门禁")
    ap.add_argument("ws")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--strip-blocks", action="store_true")
    ap.add_argument("--baseline")
    ap.add_argument("--quiet", action="store_true", help="只印 FAIL / WARN 与结果行（agent 自查用，省上下文）")
    args = ap.parse_args()
    ws = WS(args.ws, args.chapter)
    if ws.tree is None:
        print(f"[FAIL] {S}#files  tree.json 不存在 —— 先跑 tree")
        print("结果: FAIL (1 fail, 0 warn)")
        sys.exit(1)
    if args.chapter is not None and not ws.chapters:
        print(f"[FAIL] {S}#files  book/{args.chapter:02d}-*.md 不存在")
        print("结果: FAIL (1 fail, 0 warn)")
        sys.exit(1)
    chapter_mode = args.chapter is not None
    for ch in ws.chapters:
        ch.core_secs, ch.skel_concepts = set(), []
    check_chapter(ws)          # 先跑：算出骨架核心叶子（分量档）与时长
    check_game(ws)             # 出手：challenge / mind_card / world_model / route_line
    check_block_summary(ws)    # 🌳 块小结（块末章）
    docs = [] if chapter_mode else book_docs(ws)
    check_core(ws, docs)
    check_tokens(ws)
    check_section(ws)
    check_devices(ws)
    check_book(ws, chapter_mode)
    check_audit(ws, chapter_mode, args)
    check_prereq(ws)
    apply_prereq_variant(ws, variant_prereq_checks()[0])
    for c in CHECKS:  # 只在失败时记录的检查：有书稿且没被 SKIP 就算跑过
        if ws.chapters and not R[c]["skip"]:
            R[c]["ran"] = True
    finish(args.quiet)


if __name__ == "__main__":
    main()
