#!/usr/bin/env python3
"""
spine 的脚本门禁。

用法:
    python verify_spine.py <full-learn 工作区> [--max-sections 8]

检查名与 audit PARADIGM「脚本注册表」一致:
    input · schema · node_coverage · topo · cite_earlier · cells_filled · entry_concrete ·
    unlock_action · unlock_vague · unlock_len · source_order · chapter_size ·
    divergence_adjacent · weight_placement
退出码: 有 FAIL 为 1，否则 0（WARN 不阻断）。
"""

import json
import os
import re
import sys

ID_RE = re.compile(r"\b[A-Z]+-\d+\b")
ACTION_RE = re.compile(r"[会能][^。；\n]{0,4}(?:算|判|写|推|说|认|选|验|估|读|画|拆|排|指|用|"
                       r"按|查|默|列|换|解|把|试|定位|重算)|算出|写出|推出|说出|认出|判断|重算")
VAGUE_RE = re.compile(r"理解了|理解|熟悉|掌握|了解一下|有个印象|有所了解")
FUZZY_ENTRY_RE = re.compile(r"当你需要|涉及.{0,12}时|^关于")
CHAPTER_RE = re.compile(r"^## 第\s*(\d+)\s*章\s*(.+?)\s*—\s*解锁[:：]\s*(.+)$")
SRC_RE = re.compile(r"(\S+) p(\d+)")

results = []


def report(check, status, msg=""):
    results.append((check, status, msg))


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


VOLUME_RE = re.compile(r"^#\s+第\s*([一二三四五六七八九十\d]+)\s*卷\s*(.*?)\s*(?:[—–]+\s*解锁[:：].*)?$")
_CN_DIGIT = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_NUM = "零一二三四五六七八九十"


def cn_to_int(s):
    """'三' → 3，'十二' → 12，'7' → 7。"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    if "十" in s:
        a, _, b = s.partition("十")
        return (_CN_DIGIT.get(a, 1) if a else 1) * 10 + (_CN_DIGIT.get(b, 0) if b else 0)
    return _CN_DIGIT.get(s, 0)


def int_to_cn(n):
    if n <= 10:
        return CN_NUM[n]
    if n < 20:
        return "十" + (CN_NUM[n - 10] if n > 10 else "")
    return CN_NUM[n // 10] + "十" + (CN_NUM[n % 10] if n % 10 else "")


def parse_volumes(text):
    """spine 的卷划分：`# 第 一 卷 <卷标题> — 解锁: …` 之后的 `## 第 N 章` 属于该卷。
    → [{"k": 1, "title": "性能是什么、该怎么研究", "chs": [1, 2, 3]}]；spine 不分卷时返回 []。"""
    vols, cur = [], None
    for line in text.splitlines():
        m = VOLUME_RE.match(line)
        if m:
            cur = {"k": cn_to_int(m.group(1)), "title": m.group(2).strip(), "chs": []}
            vols.append(cur)
            continue
        m = CHAPTER_RE.match(line)
        if m and cur is not None:
            cur["chs"].append(int(m.group(1)))
    return [v for v in vols if v["chs"]]


def parse_spine(text):
    chapters, cur, table = [], None, None
    header_lines = []
    for line in text.splitlines():
        m = CHAPTER_RE.match(line)
        if m:
            cur = {"num": int(m.group(1)), "title": m.group(2), "unlock": m.group(3).strip(),
                   "entry": "", "main": [], "machine": []}
            chapters.append(cur)
            table = None
            continue
        if cur is None:
            header_lines.append(line)
            continue
        if line.startswith("章入口问题"):
            cur["entry"] = re.sub(r"^章入口问题[:：]\s*", "", line).strip()
            continue
        if line.startswith("|"):
            c = cells(line)
            if c and c[0] == "§":
                table = "main" if any("入口问题" in x for x in c) else ("machine" if any("分量" in x for x in c) else None)
                continue
            if set("".join(c)) <= set("-: "):
                continue
            if table:
                cur[table].append(c)
        elif line.strip():
            table = None
    return "\n".join(header_lines), chapters


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    ws = args[0]
    max_sec = 8
    if "--max-sections" in sys.argv:
        max_sec = int(sys.argv[sys.argv.index("--max-sections") + 1])

    tpath, spath = os.path.join(ws, "tree.json"), os.path.join(ws, "spine.md")
    if not os.path.exists(tpath):
        report("input", "FAIL", "tree.json 不存在，先跑 tree")
        return finish()
    tree = json.load(open(tpath, encoding="utf-8"))
    nodes = {n["id"]: n for n in tree["nodes"]}
    if not os.path.exists(spath):
        report("input", "FAIL", "spine.md 不存在")
        return finish()
    report("input", "PASS", f"tree.json {len(nodes)} 个节点")
    header, chapters = parse_spine(open(spath, encoding="utf-8").read())

    # schema
    errs = []
    if "## 运行案例" not in header:
        errs.append("缺「## 运行案例」段")
    if not re.search(r"发散参数[:：]", header):
        errs.append("头部缺发散参数行")
    if not chapters:
        errs.append("没有解析到任何 `## 第 N 章 … — 解锁: …`")
    nums = [c["num"] for c in chapters]
    if nums != list(range(1, len(nums) + 1)):
        errs.append(f"章号不连续: {nums}")
    for c in chapters:
        if not c["entry"]:
            errs.append(f"第 {c['num']} 章缺章入口问题")
        if not c["main"]:
            errs.append(f"第 {c['num']} 章缺主表")
        ms = [r[0] for r in c["main"]]
        mm = [r[0] for r in c["machine"]]
        if ms != mm:
            errs.append(f"第 {c['num']} 章主表与机读表 § 不对齐")
        for r in c["main"]:
            if len(r) != 6:
                errs.append(f"§{r[0]} 主表应 6 列，实为 {len(r)}")
        for r in c["machine"]:
            if len(r) != 5:
                errs.append(f"§{r[0]} 机读表应 5 列，实为 {len(r)}")
    report("schema", "FAIL" if errs else "PASS", "; ".join(errs[:12]) or f"{len(chapters)} 章结构合规")

    # 展平成节序列
    seq = []  # (sec, chapter, node_ids, row, machine_row)
    for c in chapters:
        mach = {r[0]: r for r in c["machine"]}
        for r in c["main"]:
            if len(r) < 6:
                continue
            seq.append({"sec": r[0], "ch": c["num"], "nodes": ID_RE.findall(r[1]), "entry": r[2],
                        "cite": r[3], "unlock": r[4], "next": r[5], "mach": mach.get(r[0])})
    pos = {}
    for i, s in enumerate(seq):
        for k, n in enumerate(s["nodes"]):
            pos.setdefault(n, (i, k))

    # node_coverage
    missing = [n for n in nodes if n not in pos]
    ghost = [n for s in seq for n in s["nodes"] if n not in nodes]
    msg = []
    if missing:
        msg.append(f"{len(missing)} 个节点没有落点: {', '.join(missing[:15])}")
    if ghost:
        msg.append(f"引用不存在的节点: {', '.join(ghost[:10])}")
    report("node_coverage", "FAIL" if msg else "PASS", "; ".join(msg) or f"{len(nodes)} 个节点全部落位")

    # topo
    errs = []
    for nid, (i, k) in pos.items():
        for r in nodes.get(nid, {}).get("requires", []):
            if r in pos and pos[r] > (i, k):
                errs.append(f"{nid}(§{seq[i]['sec']}) 依赖 {r}(§{seq[pos[r][0]]['sec']}) 排在后面")
    report("topo", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or "所有依赖都排在前面")

    # cite_earlier
    errs = []
    for i, s in enumerate(seq):
        cited = set(ID_RE.findall(s["cite"]))
        for c in cited:
            if c not in pos or pos[c][0] > i:
                errs.append(f"§{s['sec']} 引用了排在后面或不存在的 {c}")
        need = set()
        for n in s["nodes"]:
            need |= {r for r in nodes.get(n, {}).get("requires", []) if r not in s["nodes"]}
        lack = need - cited
        if lack:
            errs.append(f"§{s['sec']} 「凭什么现在能懂」缺 {', '.join(sorted(lack))}")
    report("cite_earlier", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or "依据列只引前文且覆盖直接依赖")

    # cells_filled
    errs = [s["sec"] for s in seq if not all(x.strip() for x in (s["entry"], s["cite"], s["unlock"], s["next"]))]
    report("cells_filled", "FAIL" if errs else "PASS", "空格的节: " + ", ".join(errs) if errs else "四格全满")

    # entry_concrete
    errs = []
    for s in seq:
        e = s["entry"].strip()
        if not re.search(r"[？?]$", e) or FUZZY_ENTRY_RE.search(e):
            errs.append(f"§{s['sec']}: {e[:30]}")
    for c in chapters:
        if c["entry"] and not re.search(r"[？?]$", c["entry"]):
            errs.append(f"第 {c['num']} 章入口: {c['entry'][:30]}")
    report("entry_concrete", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or "入口问题都是具体问句")

    # unlock_action / unlock_vague / unlock_len
    units = [(f"§{s['sec']}", s["unlock"]) for s in seq] + [(f"第 {c['num']} 章", c["unlock"]) for c in chapters]
    errs = [f"{k}: {u[:30]}" for k, u in units if not ACTION_RE.search(u)]
    report("unlock_action", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or "解锁都是可检验动作")
    warns = [k for k, u in units if VAGUE_RE.search(u)]
    report("unlock_vague", "WARN" if warns else "PASS", "含不可验词: " + ", ".join(warns[:10]) if warns else "")
    fails = [f"{k}({len(u)}字)" for k, u in units if len(u) > 60]
    warns = [f"{k}({len(u)}字)" for k, u in units if 40 < len(u) <= 60]
    report("unlock_len", "FAIL" if fails else ("WARN" if warns else "PASS"), "; ".join(fails + warns)[:400])

    # source_order
    man = json.load(open(os.path.join(ws, "raw", "_manifest.json"), encoding="utf-8"))
    order = {m["short"]: k for k, m in enumerate(man.get("materials", []))}
    keys, cross_ch = [], 0
    for c in chapters:
        shorts = set()
        for r in c["machine"]:
            shorts |= {m.group(1) for m in SRC_RE.finditer(r[3])}
        cross_ch += len(shorts & set(order)) > 1
    for s in seq:
        m = SRC_RE.search(s["mach"][3]) if s["mach"] else None
        if m and m.group(1) in order:
            keys.append((order[m.group(1)], int(m.group(2))))
    monotone = keys == sorted(keys)
    if monotone and not cross_ch and "顺序理由" not in header:
        report("source_order", "FAIL", "章节顺序与材料顺序完全一致且无跨材料章，头部未写「顺序理由」")
    else:
        report("source_order", "PASS", f"{cross_ch} 章跨材料；顺序{'与材料一致（已写理由）' if monotone else '按认知重排'}")

    # chapter_size
    errs = [f"第 {c['num']} 章 {len(c['main'])} 节" for c in chapters if len(c["main"]) > max_sec]
    report("chapter_size", "FAIL" if errs else "PASS", "; ".join(errs) or f"每章 ≤{max_sec} 节（阅读时长由作者自查）")

    # divergence_adjacent（spine 方法 2：前置扎成前置包；延伸紧跟核心）
    errs = []
    users = {}
    for nid, n in nodes.items():
        for r in n.get("requires", []):
            users.setdefault(r, []).append(nid)
    is_pre = lambda x: nodes.get(x, {}).get("role") == "prerequisite"  # noqa: E731
    pure_pre = [bool(s["nodes"]) and all(is_pre(x) for x in s["nodes"]) for s in seq]
    vol_of = {ch: v["k"] for v in parse_volumes(open(spath, encoding="utf-8").read()) for ch in v["chs"]}
    ch_secs = {}
    for i, s in enumerate(seq):
        ch_secs.setdefault(s["ch"], []).append(i)
    for nid, n in nodes.items():
        if nid not in pos:
            continue
        i = pos[nid][0]
        if is_pre(nid):
            if not pure_pre[i]:
                errs.append(f"前置 {nid} 混在材料节 §{seq[i]['sec']} 里，应拆进前置包")
                continue
            first = min((pos[u][0] for u in users.get(nid, []) if u in pos), default=None)
            if first is None:
                continue
            ch = seq[i]["ch"]
            idx = ch_secs[ch]
            at_head = all(pure_pre[j] for j in idx[: idx.index(i) + 1])  # 本章开头连续一段纯前置节
            if not at_head:
                errs.append(f"前置 {nid}（§{seq[i]['sec']}）不在第 {ch} 章开头的前置包里")
            if vol_of and vol_of.get(ch) != vol_of.get(seq[first]["ch"]):
                errs.append(f"前置 {nid}（§{seq[i]['sec']}）与首个使用者（§{seq[first]['sec']}）不同卷")
            for r in n.get("relations", []):
                if r.get("type") == "pair" and r.get("to") in pos and pos[r["to"]][0] != i:
                    errs.append(f"成对前置 {nid} 与 {r['to']} 不同节")
        if n.get("role") == "extension":
            cores = [pos[r][0] for r in n.get("requires", []) if r in pos]
            if cores and not (max(cores) <= i <= max(cores) + 1):
                errs.append(f"延伸 {nid} 在 §{seq[i]['sec']}，离核心节点太远")
    for c in chapters:
        ids = [x for r in c["main"] for x in ID_RE.findall(r[1]) if x in nodes]
        if ids and all(nodes[x].get("role") == "extension" for x in ids):
            errs.append(f"第 {c['num']} 章全是延伸节点")
    report("divergence_adjacent", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or "前置都在使用者同卷的前置包里，成对同节；延伸紧跟核心")

    # weight_placement
    ws_sorted = sorted((n.get("weight", 0) for n in nodes.values()), reverse=True)
    cut = ws_sorted[max(0, len(ws_sorted) // 5 - 1)] if ws_sorted else 0
    errs = []
    for nid, n in nodes.items():
        if n.get("weight", 0) >= cut and cut > 0 and nid in pos and pos[nid][1] != 0:
            errs.append(f"{nid}(w={n['weight']}) 不是 §{seq[pos[nid][0]]['sec']} 的主节点")
    median = ws_sorted[len(ws_sorted) // 2] if ws_sorted else 0
    for c in chapters:
        ids = [x for r in c["main"] for x in ID_RE.findall(r[1]) if x in nodes]
        if ids and all(nodes[x].get("weight", 0) < median for x in ids) and median > 0:
            errs.append(f"第 {c['num']} 章只含低分量节点")
    report("weight_placement", "WARN" if errs else "PASS", "; ".join(errs[:10]) or f"前 20%（w≥{cut}）都是节主节点")

    return finish()


def finish():
    fails = 0
    for check, status, msg in results:
        print(f"[{status}] verify_spine.py#{check}  {msg}")
        fails += status == "FAIL"
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
