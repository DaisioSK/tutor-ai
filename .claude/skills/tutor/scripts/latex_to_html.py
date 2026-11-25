#!/usr/bin/env python3
"""
latex_to_html.py — 把 teach MD 里的 LaTeX 数学转成 WeasyPrint 能排的 HTML。

为什么不用现成方案:
  - MathJax / KaTeX 要跑 JS, WeasyPrint 没有 JS 引擎
  - MathML WeasyPrint 不支持
  - matplotlib mathtext 不支持 \\text{} 里的中文, 而本仓公式大量出现 \\text{（§5 用途二）}
  - texlive 太重, 且 CJK 要 xelatex + 额外宏包
所以自带一个转换器: Unicode 符号 + <sub>/<sup> + CSS 分数线/求和限/花括号。
零依赖, 确定性, 中文照常出。

支持范围见 SUPPORTED；不认识的命令会原样保留并被 collect_unsupported() 报出来,
由 verify_teach.py 转成门禁失败 —— 宁可显式失败, 不要静默降级成一坨源码。

用法:
    from latex_to_html import convert_math_blocks, collect_unsupported, MATH_CSS
    html_ready_md = convert_math_blocks(md_text)
"""
import re

# ---------------------------------------------------------------- 符号表

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "pi": "π", "varpi": "ϖ", "rho": "ρ", "varrho": "ϱ", "sigma": "σ",
    "varsigma": "ς", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

SYMBOLS = {
    # 关系
    # \mid 用 U+2223 DIVIDES 而不是 ASCII 竖线: 数学转换发生在 Markdown 解析之前,
    # 吐出真竖线会给表格行凭空加一列, 整张表退化成一行纯文本 (静默, 不报错)。
    # U+2223 长得一样但不是 Markdown 的列分隔符。同理 ert / \Vert。
    "mid": " ∣ ", "vert": "∣", "Vert": "∥",
    "perp": " ⊥ ", "parallel": "∥",
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
    "approx": "≈", "sim": "∼", "simeq": "≃", "cong": "≅", "equiv": "≡",
    "propto": "∝", "asymp": "≍", "ll": "≪", "gg": "≫", "doteq": "≐",
    # 集合
    "in": "∈", "notin": "∉", "ni": "∋", "subset": "⊂", "supset": "⊃",
    "subseteq": "⊆", "supseteq": "⊇", "cup": "∪", "cap": "∩",
    "setminus": "\u2216", "emptyset": "∅", "varnothing": "∅",
    "bigcup": "⋃", "bigcap": "⋂",
    # 箭头
    "to": "→", "rightarrow": "→", "leftarrow": "←", "leftrightarrow": "↔",
    "longrightarrow": "⟶", "longleftarrow": "⟵",
    "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔",
    "Longrightarrow": " ⟹ ", "Longleftarrow": "⟸",
    "Longleftrightarrow": "⟺", "mapsto": "↦", "implies": "⟹", "iff": "⟺",
    # 运算
    "times": "×", "div": "÷", "pm": "±", "mp": "∓", "cdot": "·",
    "ast": "∗", "star": "⋆", "circ": "∘", "bullet": "∙", "oplus": "⊕",
    "otimes": "⊗", "wedge": "∧", "vee": "∨", "neg": "¬", "lnot": "¬",
    # 大算符 / 杂项
    "partial": "∂", "nabla": "∇", "infty": "∞", "forall": "∀", "exists": "∃",
    "dots": "…", "ldots": "…", "cdots": "⋯", "vdots": "⋮", "ddots": "⋱",
    "prime": "′", "angle": "∠", "triangle": "△", "square": "□",
    "top": "⊤", "bot": "⊥", "vdash": "⊢", "models": "⊨",
    "aleph": "ℵ", "hbar": "ℏ", "ell": "ℓ", "Re": "ℜ", "Im": "ℑ",
    "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉",
    "langle": "⟨", "rangle": "⟩", "backslash": "\\",
}

# 组合用变音符 (跟在基字符后面)
ACCENTS = {
    "bar": "̄", "overline": "̄", "tilde": "̃", "hat": "̂",
    "widehat": "̂", "widetilde": "̃", "breve": "̆",
    "dot": "̇", "ddot": "̈", "vec": "⃗", "check": "̌",
    "acute": "́", "grave": "̀", "mathring": "̊",
}

# 直立体的算符名
OPNAMES = {
    "exp", "ln", "log", "lg", "sin", "cos", "tan", "cot", "sec", "csc",
    "sinh", "cosh", "tanh", "min", "max", "sup", "inf", "lim", "det", "dim",
    "gcd", "deg", "arg", "ker", "Pr", "mod", "argmax", "argmin",
}

# 大算符: 是否把上下标摆成上下 (display 模式下)
BIGOPS = {
    "sum": ("∑", True), "prod": ("∏", True), "coprod": ("∐", True),
    "int": ("∫", False), "iint": ("∬", False), "iiint": ("∭", False),
    "oint": ("∮", False), "bigcup": ("⋃", True), "bigcap": ("⋂", True),
    "bigoplus": ("⨁", True), "bigotimes": ("⨂", True), "bigvee": ("⋁", True),
    "bigwedge": ("⋀", True), "lim": ("lim", True),
}

# 空白
SPACES = {
    "quad": " ", "qquad": "  ", ",": " ", ";": " ",
    ":": " ", "!": "", " ": " ", "thinspace": " ",
    "enspace": " ", "hspace": None,   # hspace 吞一个参数
}

# 字体族: 命令 -> (css class, 是否直立)
FONTS = {
    "text": "m-text", "textrm": "m-text", "textnormal": "m-text",
    "textbf": "m-textbf", "textit": "m-textit", "textsc": "m-textsc",
    "mathrm": "m-text", "mathbf": "m-bf", "boldsymbol": "m-bf",
    "mathit": "m-it", "mathcal": "m-cal", "mathbb": "m-bb",
    "mathsf": "m-sf", "mathtt": "m-tt", "mathfrak": "m-cal",
}

# 无副作用、直接丢弃的命令 (只影响 TeX 排版尺寸)
DROP = {
    "displaystyle", "textstyle", "scriptstyle", "scriptscriptstyle",
    "limits", "nolimits", "left", "right", "big", "Big", "bigg", "Bigg",
    "bigl", "Bigl", "biggl", "Biggl", "bigr", "Bigr", "biggr", "Biggr",
    "middle", "mathstrut", "strut", "nonumber", "notag",
}

DELIMS = {"(": "(", ")": ")", "[": "[", "]": "]", "|": "|", ".": "",
          "\\{": "{", "\\}": "}", "{": "{", "}": "}", "/": "/"}

SUPPORTED = (set(GREEK) | set(SYMBOLS) | set(ACCENTS) | OPNAMES | set(BIGOPS)
             | set(SPACES) | set(FONTS) | DROP
             | {"frac", "dfrac", "tfrac", "cfrac", "sqrt", "underbrace",
                "overbrace", "underset", "overset", "stackrel", "boxed",
                "cancel", "begin", "end", "not", "operatorname", "substack",
                "binom", "choose", "atop", "over", "pmod", "bmod", "i", "j"})

ENVIRONMENTS = {"aligned", "align", "align*", "alignedat", "gathered",
                "gather", "gather*", "cases", "matrix", "pmatrix", "bmatrix",
                "vmatrix", "Vmatrix", "array", "split", "equation", "equation*"}


# ---------------------------------------------------------------- 词法

TOKEN_RE = re.compile(r"""
    (?P<cmd>\\[A-Za-z]+\*?)      # \frac \begin \align*
  | (?P<esc>\\[^A-Za-z])         # \{ \} \, \; \\ \%
  | (?P<open>\{)
  | (?P<close>\})
  | (?P<sub>_)
  | (?P<sup>\^)
  | (?P<amp>&)
  | (?P<char>[\s\S])
""", re.VERBOSE)


def tokenize(s):
    out = []
    for m in TOKEN_RE.finditer(s):
        kind = m.lastgroup
        out.append((kind, m.group()))
    return out


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- 语法

class Parser:
    def __init__(self, tokens, display):
        self.t = tokens
        self.i = 0
        self.display = display
        self.unknown = set()

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def skip_space(self):
        while self.i < len(self.t) and self.t[self.i][0] == "char" and self.t[self.i][1].isspace():
            self.i += 1

    # ---- 取一个"参数": {…} 或单个 token
    def arg(self):
        self.skip_space()
        kind, val = self.peek()
        if kind is None:
            return ""
        if kind == "open":
            self.i += 1
            return self.parse_until_close()
        self.i += 1
        return self.atom(kind, val)

    def parse_until_close(self):
        parts = []
        depth = 0
        while self.i < len(self.t):
            kind, val = self.peek()
            if kind == "close" and depth == 0:
                self.i += 1
                break
            parts.append(self.one())
        return "".join(parts)

    def parse_all(self):
        parts = []
        while self.i < len(self.t):
            parts.append(self.one())
        return "".join(parts)

    # ---- 解析一个单元, 并把紧跟其后的 _ / ^ 挂上去
    def one(self):
        kind, val = self.next()
        if kind is None:
            return ""
        base = self.atom(kind, val)
        return self.attach_scripts(base)

    def attach_scripts(self, base):
        sub = sup = None
        while True:
            # 试探性跳空白找 _ / ^；没找到要把位置退回去, 否则 \text{ 且 } 的
            # 尾随空格会被吃掉, 变成「且X」黏在一起。
            save = self.i
            self.skip_space()
            kind, val = self.peek()
            if kind == "sub" and sub is None:
                self.i += 1
                sub = self.arg()
            elif kind == "sup" and sup is None:
                self.i += 1
                sup = self.arg()
            else:
                self.i = save
                break
        if sub is None and sup is None:
            return base
        out = base
        if sup is not None:
            out += f"<sup>{sup}</sup>"
        if sub is not None:
            out += f"<sub>{sub}</sub>"
        return out

    # ---- 把一个 token 变成 HTML
    def atom(self, kind, val):
        if kind == "open":
            return self.parse_until_close()
        if kind == "close":
            return ""
        if kind == "amp":
            return ""
        if kind == "sub" or kind == "sup":       # 裸的 _ / ^ (不该出现)
            return esc(val)
        if kind == "esc":
            c = val[1]
            if c == "\\":
                return "<br/>"
            if c in SPACES:
                return SPACES[c] or ""
            if c in "{}%$#&_":
                return esc(c)
            return esc(c)
        if kind == "char":
            return esc(val)
        # kind == "cmd"
        return self.command(val[1:])

    def command(self, name):
        if name in SPACES:
            if name == "hspace":
                self.arg()
                return " "
            return SPACES[name] or ""
        if name in DROP:
            if name in ("left", "right", "middle"):
                self.skip_space()
                k, v = self.peek()
                if k is not None:
                    self.i += 1
                    d = v if k != "esc" else v
                    return esc(DELIMS.get(d, d if k == "char" else ""))
            return ""
        if name in GREEK:
            return GREEK[name]
        if name in SYMBOLS:
            return esc(SYMBOLS[name])
        if name in ACCENTS:
            body = self.arg()
            return body + ACCENTS[name]
        if name in OPNAMES:
            return f'<span class="m-op">{name}</span> '
        if name in BIGOPS:
            return self.bigop(name)
        if name in FONTS:
            body = self.arg()
            return f'<span class="{FONTS[name]}">{body}</span>'
        if name in ("frac", "dfrac", "tfrac", "cfrac"):
            num, den = self.arg(), self.arg()
            return (f'<span class="m-frac"><span class="m-num">{num}</span>'
                    f'<span class="m-den">{den}</span></span>')
        if name == "binom":
            a, b = self.arg(), self.arg()
            return (f'<span class="m-paren">(</span>'
                    f'<span class="m-frac m-nobar"><span class="m-num">{a}</span>'
                    f'<span class="m-den">{b}</span></span>'
                    f'<span class="m-paren">)</span>')
        if name == "sqrt":
            body = self.arg()
            return f'<span class="m-sqrt">{body}</span>'
        if name in ("underbrace", "overbrace"):
            return self.brace(name)
        if name in ("underset", "overset", "stackrel"):
            first, second = self.arg(), self.arg()
            lab, base = (first, second) if name != "underset" else (first, second)
            if name == "underset":
                return (f'<span class="m-stack"><span class="m-sbase">{second}</span>'
                        f'<span class="m-slab">{first}</span></span>')
            return (f'<span class="m-stack"><span class="m-slab">{first}</span>'
                    f'<span class="m-sbase">{second}</span></span>')
        if name == "boxed":
            return f'<span class="m-boxed">{self.arg()}</span>'
        if name == "cancel":
            return f'<span class="m-cancel">{self.arg()}</span>'
        if name == "operatorname":
            return f'<span class="m-op">{self.arg()}</span> '
        if name == "not":
            nxt = self.one()
            return f'<span class="m-not">{nxt}</span>'
        if name in ("i", "j"):
            return name          # \i \j 在数学里就是字母 (本仓来自 \i 误写)
        if name == "begin":
            return self.environment()
        if name == "end":
            self.arg()
            return ""
        if name == "substack":
            body = self.arg()
            return f'<span class="m-substack">{body}</span>'
        self.unknown.add(name)
        return f'<span class="m-unknown">\\{esc(name)}</span>'

    def bigop(self, name):
        sym, stacked = BIGOPS[name]
        sub = sup = None
        while True:
            self.skip_space()
            kind, _ = self.peek()
            if kind == "sub" and sub is None:
                self.i += 1
                sub = self.arg()
            elif kind == "sup" and sup is None:
                self.i += 1
                sup = self.arg()
            else:
                break
        cls = "m-bigop" if name != "lim" else "m-bigop m-oplim"
        if stacked and self.display and (sub or sup):
            top = f'<span class="m-lim">{sup}</span>' if sup else ""
            bot = f'<span class="m-lim">{sub}</span>' if sub else ""
            return (f'<span class="m-limits">{top}'
                    f'<span class="{cls}">{sym}</span>{bot}</span>')
        out = f'<span class="{cls}">{sym}</span>'
        if sup:
            out += f"<sup>{sup}</sup>"
        if sub:
            out += f"<sub>{sub}</sub>"
        return out

    def brace(self, name):
        body = self.arg()
        self.skip_space()
        lab = ""
        kind, _ = self.peek()
        want = "sub" if name == "underbrace" else "sup"
        if kind == want:
            self.i += 1
            lab = self.arg()
        cls = "m-underbrace" if name == "underbrace" else "m-overbrace"
        if name == "underbrace":
            inner = (f'<span class="m-bbody">{body}</span>'
                     f'<span class="m-blab">{lab}</span>')
        else:
            inner = (f'<span class="m-blab">{lab}</span>'
                     f'<span class="m-bbody">{body}</span>')
        return f'<span class="{cls}">{inner}</span>'

    def environment(self):
        env = self.arg().strip()
        if env not in ENVIRONMENTS:
            self.unknown.add("begin{" + env + "}")
        # 收集到匹配的 \end{env}
        depth = 1
        start = self.i
        while self.i < len(self.t):
            kind, val = self.t[self.i]
            if kind == "cmd" and val == "\\begin":
                depth += 1
            elif kind == "cmd" and val == "\\end":
                depth -= 1
                if depth == 0:
                    break
            self.i += 1
        body_tokens = self.t[start:self.i]
        self.i += 1                     # 吃掉 \end
        if self.i < len(self.t) and self.t[self.i][0] == "open":
            self.i += 1
            while self.i < len(self.t) and self.t[self.i][0] != "close":
                self.i += 1
            self.i += 1

        rows = self.split_rows(body_tokens)
        if env in ("cases",):
            cells = "".join(
                "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
            return (f'<span class="m-cases"><span class="m-cbrace">{{</span>'
                    f'<table class="m-envtable">{cells}</table></span>')
        cls = "m-envtable m-aligned" if env.startswith(("align", "split")) else "m-envtable"
        cells = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
        return f'<table class="{cls}">{cells}</table>'

    def split_rows(self, toks):
        rows, row, cell = [], [], []
        i = 0
        depth = 0
        while i < len(toks):
            kind, val = toks[i]
            if kind == "open":
                depth += 1
            elif kind == "close":
                depth -= 1
            if depth == 0 and kind == "esc" and val == "\\\\":
                row.append(cell)
                rows.append(row)
                row, cell = [], []
                i += 1
                continue
            if depth == 0 and kind == "amp":
                row.append(cell)
                cell = []
                i += 1
                continue
            cell.append((kind, val))
            i += 1
        row.append(cell)
        rows.append(row)

        out = []
        for r in rows:
            cells = []
            for c in r:
                sub = Parser(c, self.display)
                cells.append(sub.parse_all())
                self.unknown |= sub.unknown
            if any(x.strip() for x in cells):
                out.append(cells)
        return out


# ---------------------------------------------------------------- 对外接口

def latex_to_html(src, display=False):
    """返回 (html, unknown_commands)。"""
    p = Parser(tokenize(src), display)
    return p.parse_all(), p.unknown


# ---------------------------------------------------------------- MD 里的定位

NL = chr(10)
FENCE_RE = re.compile(r"^\s*```")

# 整行就是一条 display 公式: 可带 blockquote 前缀 `> `
LINE_BLOCK_RE = re.compile(r"^(?P<q>(?:\s*>\s?)*)\s*\$\$(?P<body>.+?)\$\$\s*$")
# 多行 display 块的界符: 整行只有 $$
FENCE_MATH_RE = re.compile(r"^(?P<q>(?:\s*>\s?)*)\s*\$\$\s*$")
# 行内: \( … \)
INLINE_PAREN_RE = re.compile(r"\\\((.+?)\\\)")
# 夹在句子中间的 $$ … $$（不独占一行）—— 按行内数学渲染
INLINE_DD_RE = re.compile(r"\$\$(.+?)\$\$")
# 行内: $ … $ —— 收得很紧, 避免吃到「GPU $$$」「$300」这类散文
#   开界符后不许空白, 闭界符前不许空白, 中间不许再出现 $ 或换行, 长度 <= 120
INLINE_DOLLAR_RE = re.compile(r"(?<![\$\\])\$(?!\s)([^\$\n]{1,120}?)(?<![\s\\])\$(?!\$)")


def _is_math_dollar(s):
    """$…$ 里得像数学。避免把货币 ($5M-$100M) 和散文里的美元号误判成公式。"""
    if "\\" in s:                       # 有 LaTeX 命令, 一定是数学
        return True
    if not re.fullmatch(r"[A-Za-z0-9_^{}(),.+\-*/=<>|'\s]+", s):
        return False
    if re.match(r"^\d", s) and "=" not in s:
        return False                    # 「5M-」「100M」这类是金额, 不是公式
    if any(c in s for c in "_^{}="):
        return True
    # 函数式写法: P(e) / P(V, e) / f(x) —— 没有下标也没有等号, 但确实是公式。
    # 不放行的话整段 $…$ 会原样印进 PDF (真实事故)。
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,3}\s*\([^()]{1,40}\)", s.strip()))


def convert_math_blocks(md_text):
    r"""把代码块之外的数学换成 HTML。返回 (新文本, 未知命令集合)。

    三种记法都认: 独占一行的 $$…$$ / 跨行的 $$ … $$ / 行内 \(…\) 与 $…$。
    代码块 (``` 围栏) 内一律不动 —— 那里的美元符号是内容。
    blockquote 里的公式保留 `> ` 前缀, 否则会掉出引用框。
    """
    unknown = set()

    def render(body, display, quote=""):
        html, unk = latex_to_html(body.strip(), display=display)
        unknown.update(unk)
        tag = "div" if display else "span"
        cls = "math-block" if display else "math-inline"
        return quote + '<' + tag + ' class="' + cls + '">' + html + '</' + tag + '>'

    def inline_pass(line):
        def sub_paren(m):
            return render(m.group(1), False)

        def sub_dollar(m):
            if not _is_math_dollar(m.group(1)):
                return m.group(0)
            return render(m.group(1), False)

        line = INLINE_PAREN_RE.sub(sub_paren, line)
        # 夹在句子中间的 $$…$$: 整行规则接不住, 这里按行内数学收掉
        line = INLINE_DD_RE.sub(lambda m: render(m.group(1), False), line)
        if "$$" not in line:
            line = INLINE_DOLLAR_RE.sub(sub_dollar, line)
        return line

    out = []
    infence = False
    i = 0
    lines = md_text.split(NL)
    while i < len(lines):
        ln = lines[i]
        if FENCE_RE.match(ln):
            infence = not infence
            out.append(ln)
            i += 1
            continue
        if infence:
            out.append(ln)
            i += 1
            continue

        m = LINE_BLOCK_RE.match(ln)
        if m:
            out.append(render(m.group("body"), True, m.group("q")))
            i += 1
            continue

        m = FENCE_MATH_RE.match(ln)
        if m:                                   # 跨行块: 收到下一个单独的 $$
            quote = m.group("q")
            body, j = [], i + 1
            while j < len(lines) and not FENCE_MATH_RE.match(lines[j]):
                body.append(re.sub(r"^\s*>\s?", "", lines[j]))
                j += 1
            out.append(render(NL.join(body), True, quote))
            i = j + 1
            continue

        out.append(inline_pass(ln))
        i += 1
    return NL.join(out), unknown


def collect_unsupported(md_text):
    """只做扫描, 不改文本 —— 给 verify_teach.py 当门禁用。"""
    _, unk = convert_math_blocks(md_text)
    return unk


def leftover_math(md_text):
    """转换之后代码块之外还残留的数学界符 -> [(行号, 行内容)]。

    行级规则接不住的写法 (比如夹在句子中间的 $$…$$) 会在这里现形。
    宁可门禁失败, 也不要让一坨 LaTeX 源码印进 PDF。
    """
    html, _ = convert_math_blocks(md_text)
    out, infence = [], False
    for i, ln in enumerate(html.split(NL), 1):
        if FENCE_RE.match(ln):
            infence = not infence
            continue
        if infence:
            continue
        probe = re.sub(r"\${3,}", "", ln)      # 「GPU $$$」这类散文里的美元号不是界符
        if "$$" in probe or re.search(r"\\[(\[]", probe):
            out.append((i, ln.strip()[:90]))
            continue
        # 单个 $…$ 的残留: 只在"看着像公式"时报, 免得把 $300 这类金额当成漏网
        for m in re.finditer(r"\$([^\$\n]{1,120})\$", probe):
            body = m.group(1)
            if "\\" in body or re.search(r"[A-Za-z][A-Za-z0-9]{0,3}\s*\(", body):
                out.append((i, ln.strip()[:90]))
                break
    return out


def count_math(md_text):
    """(display 块数, 行内数) —— 门禁报告用。"""
    html, _ = convert_math_blocks(md_text)
    return html.count('class="math-block"'), html.count('class="math-inline"')


# ---------------------------------------------------------------- CSS

MATH_CSS = r"""
/* ---------- LaTeX 数学 (latex_to_html.py 产出) ---------- */
.math-block {
  text-align: center;
  margin: 0.9em 0;
  font-size: 10.5pt;
  line-height: 2.0;
  page-break-inside: avoid;
}
.math-inline { white-space: nowrap; }
.math-block, .math-inline {
  font-family: "Cambria Math", "STIX Two Math", "DejaVu Serif", "CourseCJK", serif;
}
.math-block sub, .math-inline sub, .math-block sup, .math-inline sup {
  font-size: 0.68em;
  line-height: 0;
}
.m-text, .m-textbf, .m-textit, .m-textsc {
  font-family: "CourseCJK", "Microsoft YaHei", sans-serif;
  font-size: 0.92em;
  font-style: normal;
}
.m-textbf { font-weight: bold; }
.m-textit { font-style: italic; }
.m-textsc { font-variant: small-caps; }
.m-bf { font-weight: bold; }
.m-it { font-style: italic; }
.m-cal { font-style: italic; }
.m-bb  { font-weight: bold; }
.m-sf  { font-family: sans-serif; }
.m-tt  { font-family: "DejaVu Sans Mono", monospace; }
.m-op  { font-style: normal; }

/* 分数 */
.m-frac {
  display: inline-block;
  vertical-align: -0.55em;
  text-align: center;
  margin: 0 0.15em;
}
.m-frac > .m-num {
  display: block;
  padding: 0 0.3em 0.08em;
  border-bottom: 0.6pt solid currentColor;
}
.m-frac > .m-den { display: block; padding: 0.08em 0.3em 0; }
.m-frac.m-nobar > .m-num { border-bottom: none; }
.m-paren { font-size: 1.6em; vertical-align: -0.25em; }

/* 大算符带上下限 */
.m-limits {
  display: inline-block;
  text-align: center;
  vertical-align: middle;
  margin: 0 0.18em;
}
.m-limits > .m-lim { display: block; font-size: 0.62em; line-height: 1.1; }
.m-limits > .m-bigop { display: block; line-height: 1; }
.m-bigop { font-size: 1.35em; }
.m-oplim { font-size: 1em; font-style: normal; }

/* 上/下花括注 */
.m-underbrace, .m-overbrace {
  display: inline-block;
  text-align: center;
  vertical-align: middle;
}
.m-underbrace > .m-bbody { display: block; border-bottom: 0.6pt solid #888; }
.m-underbrace > .m-blab  { display: block; font-size: 0.62em; color: #555; line-height: 1.25; }
.m-overbrace  > .m-bbody { display: block; border-top: 0.6pt solid #888; }
.m-overbrace  > .m-blab  { display: block; font-size: 0.62em; color: #555; line-height: 1.25; }

/* underset / overset */
.m-stack { display: inline-block; text-align: center; vertical-align: middle; }
.m-stack > .m-slab  { display: block; font-size: 0.65em; line-height: 1.1; }
.m-stack > .m-sbase { display: block; line-height: 1.1; }

.m-sqrt { border-top: 0.6pt solid currentColor; padding: 0 0.15em; }
.m-sqrt::before { content: "\221A"; border-top: none; }
.m-boxed { border: 0.6pt solid currentColor; padding: 0.1em 0.3em; }
.m-cancel { text-decoration: line-through; }
.m-not::after { content: "\0338"; }
.m-substack { display: inline-block; font-size: 0.7em; }

/* aligned / cases 环境 */
table.m-envtable {
  display: inline-table;
  border-collapse: collapse;
  margin: 0 auto;
  width: auto;
  border: none;
  font-size: 1em;
}
table.m-envtable td {
  border: none;
  padding: 0.14em 0.16em;
  vertical-align: middle;
  text-align: left;
  background: transparent;
}
table.m-aligned td:nth-child(odd)  { text-align: right; }
table.m-aligned td:nth-child(even) { text-align: left; }
.m-cases { display: inline-block; vertical-align: middle; }
.m-cases > .m-cbrace {
  display: inline-block;
  font-size: 2.4em;
  vertical-align: middle;
  font-weight: 300;
}
.m-unknown { color: #c00; font-family: "DejaVu Sans Mono", monospace; font-size: 0.85em; }
"""


if __name__ == "__main__":
    import sys
    src = sys.stdin.read() if len(sys.argv) < 2 else open(sys.argv[1], encoding="utf-8").read()
    html, unk = convert_math_blocks(src)
    sys.stdout.write(html)
    if unk:
        sys.stderr.write("未识别命令: " + ", ".join(sorted(unk)) + NL)

