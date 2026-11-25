#!/usr/bin/env python3
"""
tree 的脚本门禁 + 两个生成动作（weigh 算分量、draw 出 tree.md）。

用法:
    python verify_tree.py <full-learn 工作区>            # 只检查
    python verify_tree.py <full-learn 工作区> --weigh    # 先按下游传递闭包重算 weight 写回 tree.json，再检查
    python verify_tree.py <full-learn 工作区> --draw     # 从 tree.json 生成 tree.md，再检查

检查名与 audit PARADIGM「脚本注册表」一致:
    raw_present · schema · page_coverage · acyclic · external_required · extension_bounds ·
    generators · weight_closure · signals · layer_attr · draw_sync
退出码: 有 FAIL 为 1，否则 0。
"""

import json
import os
import re
import sys
from collections import defaultdict

REQUIRED = ["id", "name", "en", "kind", "one_liner", "why", "requires", "sources", "weight"]
KINDS = {"concept", "law", "formula", "method", "model", "fact", "external"}
EXEMPT_REASONS = {"封面", "目录", "分节", "路标", "学习目标", "总结", "致谢", "参考文献", "logo", "重复", "动画帧"}
SRC_RE = re.compile(r"^(\S+) p(\d+)(?:-p?(\d+))?$")

results = []


def report(check, status, msg=""):
    results.append((check, status, msg))


def parse_source(s):
    m = SRC_RE.match(s.strip())
    if not m:
        return None
    a = int(m.group(2))
    b = int(m.group(3) or a)
    return m.group(1), a, b


def load(ws):
    with open(os.path.join(ws, "tree.json"), encoding="utf-8") as f:
        return json.load(f)


def downstream_closure(nodes):
    """weight = 有多少节点（传递地）requires 它。"""
    children = defaultdict(set)
    for n in nodes:
        for r in n.get("requires", []):
            children[r].add(n["id"])
    memo = {}

    def down(i, stack=()):
        if i in memo:
            return memo[i]
        if i in stack:
            return set()
        acc = set()
        for c in children[i]:
            acc.add(c)
            acc |= down(c, stack + (i,))
        memo[i] = acc
        return acc

    return {n["id"]: len(down(n["id"])) for n in nodes}


def find_cycle(nodes):
    graph = {n["id"]: n.get("requires", []) for n in nodes}
    color = {}

    def dfs(u, path):
        color[u] = 1
        for v in graph.get(u, []):
            if color.get(v) == 1:
                return path + [u, v]
            if v in graph and not color.get(v):
                c = dfs(v, path + [u])
                if c:
                    return c
        color[u] = 2
        return None

    for u in graph:
        if not color.get(u):
            c = dfs(u, [])
            if c:
                return c
    return None


def reader_params(ws):
    p = os.path.join(ws, "reader.md")
    out = {"layers": None, "breadth": None, "exam": None}
    if not os.path.exists(p):
        return out
    text = open(p, encoding="utf-8").read()
    m = re.search(r"divergence_layers=(\d)", text)
    out["layers"] = int(m.group(1)) if m else None
    m = re.search(r"divergence_breadth=(\d)", text)
    out["breadth"] = int(m.group(1)) if m else None
    m = re.search(r"^考试信息:\s*(.+)$", text, re.M)
    out["exam"] = m.group(1).strip() if m else None
    return out


# ---------------------------------------------------------------------------
# draw
# ---------------------------------------------------------------------------

def transitive_reduction(nodes):
    """画图用：去掉能由别的路径推出的依赖边，否则几百个节点的图连成一团。"""
    req = {n["id"]: set(n.get("requires", [])) for n in nodes}
    anc = {}

    def ancestors(i, stack=()):
        if i in anc:
            return anc[i]
        acc = set()
        for r in req.get(i, ()):
            if r in stack:
                continue
            acc.add(r)
            acc |= ancestors(r, stack + (i,))
        anc[i] = acc
        return acc

    reduced = {}
    for i, rs in req.items():
        keep = set(rs)
        for r in rs:
            for other in rs:
                if other != r and r in ancestors(other):
                    keep.discard(r)
        reduced[i] = keep
    return reduced


def mm_id(i):
    return re.sub(r"[^A-Za-z0-9_]", "_", i)


def mm_label(s):
    return s.replace('"', "'").replace("[", "(").replace("]", ")")


def draw(ws, tree):
    nodes = tree["nodes"]
    byid = {n["id"]: n for n in nodes}
    gens = set(tree.get("generators", []))
    reduced = transitive_reduction(nodes)
    lines = [f"# 科技树: {tree.get('scope', '')}", "",
             "<!-- 由 scripts/verify_tree.py --draw 从 tree.json 生成，勿手改 -->", "",
             "## 终极理解", "", tree["apex"]["statement"], "",
             "直接支撑: " + "、".join(f"{byid[u]['name']}（{u}）" for u in tree["apex"].get("unfolds", []) if u in byid), "",
             "## 生成元", "", "| id | 生成元 | 不得不这样的约束 | 推出的节点 |", "|---|---|---|---|"]
    derived = defaultdict(list)
    for n in nodes:
        for d in n.get("derives_from", []):
            derived[d].append(n["id"])
    for g in tree.get("generators", []):
        if g in byid:
            n = byid[g]
            lines.append(f"| {g} | {n['name']} | {n['why']} | {', '.join(derived[g])} |")
    lines += ["", "## 科技树图", "",
              "实线 = 理解依赖（已做传递约简）· 粗线 = 推论（derives_from）/ 实现 · 虚线 = 对比 · 点线箭头 = 组成。图按角色分组。", "",
              "```mermaid", "flowchart BT"]
    groups = defaultdict(list)
    for n in nodes:
        groups[n.get("group") or n["kind"]].append(n)
    for g, ns in groups.items():
        lines.append(f'  subgraph {mm_id("G_" + g)}["{mm_label(g)}"]')
        for n in ns:
            shape = ('(["', '"])') if n["id"] in gens else (('[/"', '"/]') if n["kind"] == "external" else ('["', '"]'))
            lines.append(f'    {mm_id(n["id"])}{shape[0]}{mm_label(n["name"])}{shape[1]}')
        lines.append("  end")
    for i, rs in reduced.items():
        for r in sorted(rs):
            if r in byid:
                lines.append(f"  {mm_id(r)} --> {mm_id(i)}")
    for n in nodes:
        for d in n.get("derives_from", []):
            if d in byid and d not in n.get("requires", []):
                lines.append(f"  {mm_id(d)} ==> {mm_id(n['id'])}")
        for rel in n.get("relations", []):
            t = rel.get("to")
            if t not in byid:
                continue
            if rel.get("type") == "contrast":
                lines.append(f"  {mm_id(n['id'])} -.- {mm_id(t)}")
            elif rel.get("type") == "implements":
                lines.append(f"  {mm_id(n['id'])} ==> {mm_id(t)}")
            elif rel.get("type") == "part_of":
                lines.append(f"  {mm_id(n['id'])} -.-> {mm_id(t)}")
    lines += ["```", "", "## 节点表", "", "| id | 名称 | kind | 一句话 | 分量 | 出处 |", "|---|---|---|---|---|---|"]
    for n in sorted(nodes, key=lambda x: -x.get("weight", 0)):
        lines.append(f"| {n['id']} | {n['name']} ({n['en']}) | {n['kind']} | {n['one_liner'].replace('|', '/')} | "
                     f"{n.get('weight', '')} | {', '.join(n['sources'])} |")
    with open(os.path.join(ws, "tree.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    ws = args[0]
    raw = os.path.join(ws, "raw")

    # raw_present
    man_path = os.path.join(raw, "_manifest.json")
    if not os.path.exists(man_path):
        report("raw_present", "FAIL", "raw/_manifest.json 不存在，先跑 ingest")
        return finish()
    manifest = json.load(open(man_path, encoding="utf-8"))
    materials = {m["short"]: m for m in manifest.get("materials", [])}
    report("raw_present", "PASS" if materials else "FAIL", f"{len(materials)} 份已登记材料")

    tree = load(ws)
    nodes = tree.get("nodes", [])
    byid = {}

    # schema
    errs = []
    for k in ["scope", "apex", "generators", "nodes"]:
        if k not in tree:
            errs.append(f"缺顶层字段 {k}")
    for n in nodes:
        for k in REQUIRED:
            if k not in n:
                errs.append(f"{n.get('id', '?')} 缺 {k}")
        if n.get("kind") not in KINDS:
            errs.append(f"{n.get('id')} kind 非法: {n.get('kind')}")
        if n.get("id") in byid:
            errs.append(f"id 重复: {n['id']}")
        byid[n.get("id")] = n
    refs = []
    for n in nodes:
        refs += [(n["id"], "requires", r) for r in n.get("requires", [])]
        refs += [(n["id"], "derives_from", r) for r in n.get("derives_from", [])]
        refs += [(n["id"], "relations", r.get("to")) for r in n.get("relations", [])]
    refs += [("apex", "unfolds", u) for u in tree.get("apex", {}).get("unfolds", [])]
    refs += [("generators", "generators", g) for g in tree.get("generators", [])]
    for src, field, r in refs:
        if r not in byid:
            errs.append(f"{src}.{field} 引用不存在的 {r}")
    if not tree.get("apex", {}).get("statement") or not tree.get("apex", {}).get("unfolds"):
        errs.append("apex.statement 或 apex.unfolds 为空")
    report("schema", "FAIL" if errs else "PASS", "; ".join(errs[:15]) + (f" …共 {len(errs)} 条" if len(errs) > 15 else ""))

    # --weigh
    if "--weigh" in sys.argv and not find_cycle(nodes):
        w = downstream_closure(nodes)
        for n in nodes:
            n["weight"] = w[n["id"]]
        with open(os.path.join(ws, "tree.json"), "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)

    # page_coverage
    covered = defaultdict(set)
    bad_src = []
    for n in nodes:
        for s in n.get("sources", []):
            p = parse_source(s)
            if not p or p[0] not in materials:
                bad_src.append(f"{n['id']}: {s}")
                continue
            covered[p[0]].update(range(p[1], p[2] + 1))
    exempt = defaultdict(set)
    bad_reason = []
    for e in tree.get("coverage", {}).get("exempt", []):
        p = parse_source(e.get("source", ""))
        if not p or p[0] not in materials:
            bad_src.append(f"exempt: {e.get('source')}")
            continue
        if e.get("reason") not in EXEMPT_REASONS:
            bad_reason.append(f"{e['source']}: {e.get('reason')}")
        exempt[p[0]].update(range(p[1], p[2] + 1))
    for short, m in materials.items():
        for ex in m.get("exempt_pages", []):
            exempt[short].add(ex["page"])
    missing = {}
    for short, m in materials.items():
        pages = set(range(1, (m.get("pages") or 0) + 1))
        miss = sorted(pages - covered[short] - exempt[short])
        if miss:
            missing[short] = miss
    msg = []
    if bad_src:
        msg.append(f"出处格式错/短名未登记 {len(bad_src)}: " + "; ".join(bad_src[:8]))
    if bad_reason:
        msg.append(f"豁免理由不在枚举 {len(bad_reason)}: " + "; ".join(bad_reason[:8]))
    for short, miss in missing.items():
        msg.append(f"{short} 未映射 {len(miss)}/{materials[short]['pages']} 页: {compress(miss)}")
    report("page_coverage", "FAIL" if msg else "PASS", " | ".join(msg) or
           f"{sum(m.get('pages') or 0 for m in materials.values())} 页全部映射或豁免")

    # acyclic
    cyc = find_cycle(nodes)
    lec = lambda n: {parse_source(s)[0] for s in n.get("sources", []) if parse_source(s)}
    cross = sum(1 for n in nodes for r in n.get("requires", [])
                if r in byid and lec(n) and lec(byid[r]) and not (lec(n) & lec(byid[r])))
    if cyc:
        report("acyclic", "FAIL", "环: " + " → ".join(cyc))
    else:
        report("acyclic", "PASS" if cross else "FAIL", f"无环；跨讲依赖边 {cross} 条")

    # external_required
    required_by = defaultdict(list)
    for n in nodes:
        for r in n.get("requires", []):
            required_by[r].append(n["id"])
    errs = []
    for n in nodes:
        if n.get("kind") != "external":
            continue
        role = n.get("role")
        if role not in ("prerequisite", "extension"):
            errs.append(f"{n['id']} external 缺 role")
        if role == "prerequisite":
            if not required_by[n["id"]]:
                errs.append(f"{n['id']} 前置节点没有被任何节点 requires")
            if not n.get("gap"):
                errs.append(f"{n['id']} 缺 gap")
            if n.get("sources"):  # 用到它的页归使用者；挂在前置上会被脚注和页码账带进前置节
                errs.append(f"{n['id']} 前置的 sources 应为空（{', '.join(n['sources'][:3])} 归使用者节点）")
            if not (n.get("mental_model") or "").strip():
                errs.append(f"{n['id']} 缺 mental_model（一句结构念头）")
    for n in nodes:  # pair 只连前置，且成对的两端都得是前置
        for r in n.get("relations", []):
            if r.get("type") == "pair" and (n.get("role") != "prerequisite" or byid.get(r.get("to"), {}).get("role") != "prerequisite"):
                errs.append(f"{n['id']} ↔ {r.get('to')} 标了 pair，但不全是前置节点")
    report("external_required", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or
           f"{sum(1 for n in nodes if n.get('role') == 'prerequisite')} 个前置节点均被直接依赖，有 gap 与 mental_model，sources 为空")

    # extension_bounds
    rp = reader_params(ws)
    errs = []
    ext = [n for n in nodes if n.get("role") == "extension"]
    for n in ext:
        if rp["layers"] is not None and (n.get("depth") or 99) > rp["layers"]:
            errs.append(f"{n['id']} depth {n.get('depth')} > {rp['layers']}")
        for user in required_by[n["id"]]:
            if byid[user].get("kind") != "external":
                errs.append(f"范围内节点 {user} requires 发散节点 {n['id']}")
    seeds = defaultdict(int)
    for n in ext:
        for r in n.get("requires", []):
            seeds[(r, n.get("depth"))] += 1
    for (seed, d), c in seeds.items():
        if rp["breadth"] is not None and c > rp["breadth"]:
            errs.append(f"种子 {seed} 第 {d} 层发散 {c} 个 > breadth {rp['breadth']}")
    report("extension_bounds", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or f"{len(ext)} 个发散节点在刻度内")

    # generators
    gens = tree.get("generators", [])
    errs = []
    if not 3 <= len(gens) <= 5:
        errs.append(f"生成元 {len(gens)} 个，应 3–5")
    for g in gens:
        kids = [n for n in nodes if g in n.get("derives_from", [])]
        spans = set()
        for k in kids:
            spans |= lec(k)
        if len(kids) < 2 or len(spans) < 2:
            errs.append(f"{g} 推出 {len(kids)} 个节点、跨 {len(spans)} 讲")
    report("generators", "FAIL" if errs else "PASS", "; ".join(errs) or f"{len(gens)} 个生成元，各自跨讲推出")

    # weight_closure
    w = downstream_closure(nodes)
    diff = [n["id"] for n in nodes if n.get("weight") != w[n["id"]]]
    report("weight_closure", "FAIL" if diff else "PASS",
           f"{len(diff)} 个节点 weight 与闭包不符（跑 --weigh）: {', '.join(diff[:10])}" if diff else "全部等于下游闭包")

    # signals
    errs = []
    exam_on = rp["exam"] not in (None, "无")
    for n in nodes:
        for s in n.get("signals", []):
            if s.startswith("exam") and not exam_on:
                errs.append(f"{n['id']} 有考试信号但 reader.md 未声明考试")
    report("signals", "FAIL" if errs else "PASS", "; ".join(errs[:10]) or ("考试信号已启用" if exam_on else "无考试信号"))

    # layer_attr
    code = {s for s, m in materials.items() if m.get("role") == "code"}
    errs = [n["id"] for n in nodes if lec(n) & code and n.get("layer") not in ("What", "Why", "How", "Deep")]
    report("layer_attr", "FAIL" if errs else "PASS", ", ".join(errs[:10]) or ("无代码材料" if not code else "代码节点均带 layer"))

    # draw / draw_sync
    md_path = os.path.join(ws, "tree.md")
    if "--draw" in sys.argv:
        draw(ws, tree)
    if not os.path.exists(md_path):
        report("draw_sync", "FAIL", "tree.md 不存在（跑 --draw）")
    else:
        current = open(md_path, encoding="utf-8").read()
        expected = draw_text(tree)
        report("draw_sync", "PASS" if current == expected else "FAIL",
               "" if current == expected else "tree.md 与 tree.json 不同步（跑 --draw）")

    return finish()


def draw_text(tree):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        return draw(d, tree)


def compress(pages):
    out, start, prev = [], None, None
    for p in pages:
        if start is None:
            start = prev = p
        elif p == prev + 1:
            prev = p
        else:
            out.append(f"p{start}" if start == prev else f"p{start}-{prev}")
            start = prev = p
    if start is not None:
        out.append(f"p{start}" if start == prev else f"p{start}-{prev}")
    return ", ".join(out)


def finish():
    fails = 0
    for check, status, msg in results:
        print(f"[{status}] verify_tree.py#{check}  {msg}")
        fails += status == "FAIL"
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
