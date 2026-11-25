"""故事表门禁（SPEC 里能机读的那几条）。
用法：python3 check.py <story-table.md> <book_dir> [--quiet]
  coverage    书里每个 `## §N.M` 都出现在某行第 1 列（§a.b–c 展开）           FAIL
  columns     每个表格行恰好 5 列                                              FAIL
  where       第 1 列以 **第N章** 起头、带至少一个性质记号 🧠🧮📋🎯             FAIL
  story_len   故事格去掉括号注后 60–140 字（拆行的半格 30–140）                    WARN
  symbols     技术格含 `=` 的公式，同格要有「符号」一条                          FAIL
  selfsuff    每张卡自足：任何格里不许"见上 / 同上"                              FAIL
              计算样例的「公式：」那步要写出字母含义（"X = <中文>"）              WARN
  calc        🧮 行必有计算样例；样例要有 题 / 公式 / 代入 / 结果 四步             FAIL
              技术格有公式（含"符号"）但样例空着                                  WARN
  lead        技术格要有「💡 洞察」与「↩ 承接」两行（全书第一行可无承接）           WARN
  derive      技术格有公式（含"符号"），同格要有「推导：」或标「（定义）」「（不推」     WARN
  prep        技术格有「它原来解决什么问题」的前置准备行，三问要齐                 FAIL
  bullets     技术 + 联系两列里 • 开头的行 ≤ 一半                               WARN
  （超前引用另由 forward.py 查）
  jargon      故事格括号外的专业词（只报，不判）                                 INFO
"""
import re
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith("--")]
quiet = "--quiet" in sys.argv
table, book = Path(args[0]), Path(args[1])
t = table.read_text(encoding="utf-8")
rows = [r for r in t.split("\n") if re.match(r"^\|\s*\*\*第", r)]
cols = [[c.strip() for c in re.split(r"(?<!\\)\|", r.strip())[1:-1]] for r in rows]
fails, warns = [], []

secs = set()
for f in sorted(book.glob("[0-9][0-9]-*.md")):
    secs |= set(re.findall(r"^## §(\d+\.\d+)", f.read_text(encoding="utf-8"), re.M))
got = set()
for c in cols:
    for a, b, e in re.findall(r"§(\d+)\.(\d+)(?:\s*[–-]\s*(?:\d+\.)?(\d+))?", c[0] if c else ""):
        got |= {f"{a}.{k}" for k in range(int(b), int(e or b) + 1)}
miss = sorted(secs - got, key=lambda x: tuple(map(int, x.split("."))))
(fails if miss else []).append(f"coverage: 缺 {len(miss)} 节 {miss[:15]}")

bad = [i for i, c in enumerate(cols) if len(c) != 5]
if bad:
    fails.append(f"columns: {len(bad)} 行不是 5 列（第 {[i + 1 for i in bad[:8]]} 行）")
badw = [c[0][:24] for c in cols if len(c) == 5 and not (re.match(r"^\*\*第\d+章\*\*", c[0]) and re.search("[🧠🧮📋🎯]", c[0]))]
if badw:
    fails.append(f"where: {len(badw)} 行第 1 列缺加粗章号或性质记号（如 {badw[:3]}）")

lens = [(c[0][:40], len(re.sub(r"（[^）]*）|\([^)]*\)|<br>|[•\s]", "", c[1]))) for c in cols if len(c) == 5]
off = [x for x in lens if not (30 if re.search(r"（\d+/\d+）", x[0]) else 60) <= x[1] <= 140]
if off:
    warns.append(f"story_len: {len(off)} 格字数越界（如 {[(w[:20], n) for w, n in off[:4]]}）")

nosym = [c[0][:20] for c in cols if len(c) == 5 and re.search(r"[A-Za-zα-ωΑ-Ω]\s*=", c[2])
         and "符号" not in c[2]]
seeup = [c[0][:20] for c in cols if len(c) == 5 and re.search(r"见上|同上", "".join(c[1:]))]
if seeup:
    fails.append(f"selfsuff: {len(seeup)} 行写了「见上 / 同上」，卡片要自足（如 {seeup[:4]}）")
calcdef = []
for c in cols:
    if len(c) == 5 and c[4] not in ("", "—", "-"):
        for step in re.findall(r"公式[：:]([^<]*)", c[4]):
            if re.search(r"[A-Za-zα-ωΑ-Ω]", step) and not re.search(r"[A-Za-zα-ωΑ-Ωᵢⱼ₀-₉_]+\s*=\s*[^=<]*[一-鿿]", step.split("；", 1)[-1] if "；" in step else ""):
                calcdef.append(c[0][:20])
                break
if calcdef:
    warns.append(f"selfsuff: {len(calcdef)} 个计算样例的「公式：」没写出字母含义（如 {calcdef[:4]}）")
if nosym:
    fails.append(f"symbols: {len(nosym)} 个技术格有公式没解释符号（如 {nosym[:4]}）")

has_calc = lambda c: c[4] not in ("", "—", "-")  # noqa: E731
nocalc = [c[0][:20] for c in cols if len(c) == 5 and "🧮" in c[0] and not has_calc(c)]
badcalc = [c[0][:20] for c in cols if len(c) == 5 and has_calc(c)
           and not all(re.search(rf"(^|<br>)\s*(\d\.\s*)?{k}[：:]", c[4]) for k in ("题", "公式", "代入", "结果"))]
if nocalc:
    fails.append(f"calc: {len(nocalc)} 个 🧮 行没有计算样例（如 {nocalc[:4]}）")
if badcalc:
    fails.append(f"calc: {len(badcalc)} 个样例缺 题/公式/代入/结果 某步（如 {badcalc[:4]}）")
soft = [c[0][:20] for c in cols if len(c) == 5 and "🧮" not in c[0] and "符号" in c[2] and not has_calc(c)]
if soft:
    warns.append(f"calc: {len(soft)} 行有公式但没样例，确认是不是真不用算（如 {soft[:4]}）")

nolead = [c[0][:20] for c in cols if len(c) == 5 and "💡" not in c[2]]
nolink = [c[0][:20] for k, c in enumerate(cols) if len(c) == 5 and k > 0 and "↩" not in c[2]]
if nolead or nolink:
    warns.append(f"lead: {len(nolead)} 行缺 💡 洞察、{len(nolink)} 行缺 ↩ 承接（如 {(nolead or nolink)[:4]}）")
nodrv = [c[0][:20] for c in cols if len(c) == 5 and "符号" in c[2] and not re.search(r"推导[：:]|（定义）|（不推", c[2])]
if nodrv:
    warns.append(f"derive: {len(nodrv)} 行有公式没推导、也没标（定义）/（不推，直接用）（如 {nodrv[:4]}）")
prep = [c[0][:20] for c in cols if len(c) == 5 and "它原来解决什么问题" in c[2]
        and not ("核心思想" in c[2] and "为什么正好用得上" in c[2])]
if prep:
    fails.append(f"prep: {len(prep)} 个前置准备行三问不齐（如 {prep[:4]}）")

lines = [x.strip() for c in cols if len(c) == 5 for x in re.split(r"<br\s*/?>", c[2] + "<br>" + c[3]) if x.strip()]
nb = sum(1 for x in lines if x.startswith("•") and "↔" not in x)   # 映射行（意象 ↔ 概念）不算 bullet
if lines and nb > len(lines) / 2:
    warns.append(f"bullets: • 行占 {nb}/{len(lines)}，超过一半——并列才用 •")

# 专业词 = 技术要点里以「名称（English」定义过的名称，再加任何 3 个字母以上的英文词；课程无关
terms = {m for c in cols if len(c) == 5 for m in re.findall(r"([一-鿿]{2,8})（[A-Za-z]", c[2])}
JAR = re.compile("|".join(map(re.escape, sorted(terms, key=len, reverse=True))) + r"|[A-Za-z]{3,}" if terms else r"[A-Za-z]{3,}")
jar = [c[0][:16] for c in cols if len(c) == 5 and JAR.search(re.sub(r"（[^）]*）|\([^)]*\)", "", c[1]))]

print(f"rows {len(rows)} · 覆盖 {len(secs & got)}/{len(secs)} · ⚠️ {t.count('⚠️')} · ∵ {t.count('∵')}"
      f" · 计算样例 {sum(1 for c in cols if len(c) == 5 and has_calc(c))} · 故事格括号外专业词 {len(jar)}")
for f in fails:
    print("[FAIL]", f)
for w in warns:
    print("[WARN]", w)
if jar and not quiet:
    print("[INFO] jargon:", jar[:20])
print("结果:", "FAIL" if fails else "PASS")
sys.exit(1 if fails else 0)
