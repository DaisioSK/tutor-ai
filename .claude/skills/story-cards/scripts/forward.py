"""超前引用核对：一行不许用到后面才讲的东西。
用法：python3 forward.py <story-table.md> [--only <parts/actNN.md>]
  按总表行序给每个术语定"首讲行"：第一次写成 `名称（English…` 的那一行。
  term     某行提到了一个术语，而它的首讲行在后面                          → 改写成不依赖它，或把定义挪到这里
  pointer  某行写了"第三卷 / §12.3 / 后面会讲"之类，指向后面的章          → 删掉，或只说眼下能说清的
  --only：只报这一幕的行（并行修各幕时用；首讲行仍按整张总表算）。候选要人判：同名不同义、只是字面相同的，留着。"""
import re
import sys
from pathlib import Path

args = sys.argv[1:]
table = Path(args[0])
only = Path(args[args.index("--only") + 1]) if "--only" in args else None
ROW = re.compile(r"^\|\s*\*\*第")


def rows_of(p):
    return [[x.strip() for x in re.split(r"(?<!\\)\|", r.strip())[1:-1]]
            for r in p.read_text(encoding="utf-8").split("\n") if ROW.match(r)]


rows = rows_of(table)
mine = {r[0] for r in rows_of(only)} if only else None
chap = [int(re.match(r"^\*\*第(\d+)章", r[0]).group(1)) for r in rows]
CN = "一-鿿"
# 术语：`中文名（English` 的中文名（取括号前最后一段 2–10 个汉字/字母），以及英文名本身
DEF = re.compile(rf"([{CN}A-Za-z0-9'’]+(?: [A-Za-z0-9'’]+)*?)\s*（([A-Z][A-Za-z0-9'’\- /]{{2,40}}?)[，,）)]")
STOP = re.compile(rf"^(的|是|和|与|即|或|为|在)|^[A-Za-z]{{1,2}}$|^[{CN}]$")


def is_term(t):
    """只收像术语的：≥3 个汉字、或带定律/分布/过程等后缀；英文要多词、缩写或带记号（M/M/1）。
    单个英文词（Rate、Mode）和两字常用词（完成、到达）字面上太常见，不收。"""
    if re.fullmatch(rf"[{CN}]+", t):
        return len(t) >= 3 or bool(re.search(r"律|分布|过程|模型|界$", t))
    if re.fullmatch(r"[A-Za-z]+", t):
        return t.isupper() and len(t) >= 3
    return len(t) >= 3


home = {}
for i, r in enumerate(rows):
    for cell in r[2:]:
        for cn, en in DEF.findall(cell):
            cn = re.sub(rf"^.*?([{CN}A-Za-z0-9'’ ]{{2,10}})$", r"\1", cn).strip()
            for t in {cn, en.strip()}:
                if not STOP.search(t) and is_term(t):
                    home.setdefault(t, i)

# 别的定义写法也算首讲：`术语（…）` 带任何括号注、符号行里的 `X = 术语`、`术语 即 …`
for t in list(home):
    form = re.compile(rf"{re.escape(t)}\s*[（(]|=\s*{re.escape(t)}|{re.escape(t)}\s*即")
    first = next((i for i, r in enumerate(rows) if any(form.search(c) for c in r[2:])), home[t])
    home[t] = min(home[t], first)

LATER = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8}
vol_of = {}
for i, r in enumerate(rows):
    m = re.search(r"卷([一二三四五六七八])", r[0])
    if m:
        vol_of[i] = LATER[m.group(1)]
hits = []
for i, r in enumerate(rows):
    if mine is not None and r[0] not in mine:
        continue
    text = " ".join(r[1:])
    terms = sorted({t for t, h in home.items() if h > i and chap[h] > chap[i] and t in text}, key=len, reverse=True)
    terms = [t for t in terms if not any(t != u and t in u for u in terms)]      # 只报最长的那个
    ptr = [m.group(0) for m in re.finditer(r"第[一二三四五六七八]卷|卷[一二三四五六七八]", text)
           if LATER[m.group(0).strip("第卷")] > vol_of.get(i, 0)]
    ptr += [m.group(0) for m in re.finditer(r"§(\d+)\.\d+|第\s*(\d+)\s*章", text)
            if int(m.group(1) or m.group(2)) > chap[i]]
    ptr += re.findall(r"后面(?:会|再|才)讲|之后(?:会|再)讲|稍后|下一卷|后文", text)
    if terms or ptr:
        hits.append((r[0].replace("**", "")[:22], [f"{t}→第{chap[home[t]]}章" for t in terms], ptr))
print(f"{(only or table).name}: 行 {sum(1 for r in rows if mine is None or r[0] in mine)} · 超前引用候选 {len(hits)} 行")
for w, ts, ps in hits:
    print(f"  {w}  " + "；".join(ts + [f"指向:{p}" for p in ps]))
