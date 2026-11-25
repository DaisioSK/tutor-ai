#!/usr/bin/env python3
"""
verify_checklist.py — 原子要点 → 模块范式/验收 的 100% 覆盖核对。

用法:
    python3 verify_checklist.py [skill_dir]          # 默认为本脚本上一级目录

读取 dev/atoms-*.md 里的所有表格行 (| id | 原子要点 | 来源 | 类型 | 归属模块 | 处置 | 备注 |)。

检查 (FAIL 任一项 → 退出码 1):
  1. 保留的要点 (处置 = 吸收 / 改写) 的 id 必须出现在其归属模块的 PARADIGM.md 或 EXPECT.md
  2. 类型 = 要求 的保留要点, 其 id 必须出现在该模块的 EXPECT.md (要求要进自查)
  3. 退役要点必须写明理由 ("退役: <理由>")
  4. 归属模块必须是注册过的模块
  5. PARADIGM/EXPECT 里引用的 id 必须真实存在 (防凭空编号)
  6. id 不重复
  7. 变体覆盖表（modules/**/variants/*.md）里每行点名的 common 条目仍存在、指纹对得上；
     对不上 = common 那条改了或删了，变体待复核。`--refresh-variants` 复核后重写指纹。
"""
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

MODULES = {
    "core": "core",
    "ingest": "modules/ingest",
    "tree": "modules/tree",
    "spine": "modules/spine",
    "compose/book": "modules/compose/book",
    "compose/chapter": "modules/compose/chapter",
    "compose/section": "modules/compose/section",
    "compose/devices": "modules/compose/devices",
    "audit": "modules/audit",
    "render": "modules/render",
}
ID_RE = re.compile(r"\b([A-Z]{2}-\d{3})\b")


def parse_atoms(dev: Path):
    atoms = []
    for f in sorted(dev.glob("atoms-*.md")):
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            if len(cells) < 6 or not ID_RE.fullmatch(cells[0]):
                continue
            atoms.append({
                "id": cells[0], "text": cells[1], "kind": cells[3],
                "module": cells[4].strip("` "), "disp": cells[5],
                "where": f"{f.name}:{ln}",
            })
    return atoms


VARIANT_ROW = re.compile(r"^\|\s*(V-[A-Z]+-\d+)\s*\|")


def split_cells(line):
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def anchor_line(root: Path, anchor: str):
    """`section/PARADIGM.md#行首片段` → 该文件里第一行以片段开头的行（相对 modules/compose/）。"""
    rel, _, key = anchor.partition("#")
    f = root / "modules" / "compose" / rel
    if not f.exists() or not key:
        return None
    key = key.strip("`")
    return next((ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip().startswith(key)), None)


def check_variants(root: Path, refresh: bool):
    fails = []
    for vf in sorted(root.glob("modules/**/variants/*.md")):
        lines = vf.read_text(encoding="utf-8").splitlines()
        changed = False
        for i, line in enumerate(lines):
            if not VARIANT_ROW.match(line):
                continue
            cells = split_cells(line)
            vid, anchor, fp = cells[0], cells[1], cells[-1]
            if anchor in ("—", "-", ""):
                continue
            target = anchor_line(root, anchor)
            if target is None:
                fails.append(f"{vf.name} {vid} 覆盖的条目已不存在：{anchor} —— 变体待复核")
                continue
            now = hashlib.sha1(target.encode("utf-8")).hexdigest()[:8]
            if now != fp:
                if refresh:
                    lines[i] = line.rstrip().rstrip("|").rstrip()
                    lines[i] = lines[i][: lines[i].rstrip().rfind("|")] + f"| {now} |"
                    changed = True
                else:
                    fails.append(f"{vf.name} {vid} 覆盖的 common 条目改过了（指纹 {fp} → {now}）：{anchor} —— 复核后跑 --refresh-variants")
        if changed:
            vf.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"已刷新指纹：{vf.relative_to(root)}")
    return fails


def main():
    args = sys.argv[1:]
    only = list_mod = None
    if "--module" in args:
        i = args.index("--module"); only = args[i + 1]; del args[i:i + 2]
    refresh = "--refresh-variants" in args
    if refresh:
        args.remove("--refresh-variants")
    if "--list" in args:
        i = args.index("--list"); list_mod = args[i + 1]; del args[i:i + 2]
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    atoms = parse_atoms(root / "dev")
    if list_mod:
        for a in atoms:
            if a["module"] == list_mod and not a["disp"].startswith(("退役", "已落实")):
                print(f"{a['id']} [{a['kind']}] {a['text']} || {a['disp']}")
        return
    if only:
        atoms = [a for a in atoms if a["module"] == only or a["disp"].startswith(("退役", "已落实"))]
    texts = {}
    rd = lambda p: p.read_text(encoding="utf-8") if p.exists() else ""  # noqa: E731
    for name, rel in MODULES.items():
        # 原子 id 不进运行时文件：PARADIGM 的覆盖索引与 EXPECT 的源要点在 dev/index-<模块>.md
        idx = rd(root / "dev" / f"index-{name.replace('/', '-')}.md")
        m = re.search(r"\n## EXPECT 源要点\n([\s\S]*)", idx)
        par_idx, exp_idx = (idx[:m.start()], m.group(1)) if m else (idx, "")
        texts[name] = (rd(root / rel / "PARADIGM.md") + par_idx,
                       rd(root / rel / "EXPECT.md") + rd(root / rel / "GATES.md") + exp_idx)

    fails, seen = [], set()
    stats = defaultdict(lambda: [0, 0])          # module -> [kept, covered]
    retired = landed = 0
    for a in atoms:
        if a["id"] in seen:
            fails.append(f"重复 id {a['id']} ({a['where']})")
        seen.add(a["id"])
        disp = a["disp"]
        if disp.startswith("退役"):
            retired += 1
            if not re.match(r"退役\s*[:：]\s*\S", disp):
                fails.append(f"{a['id']} 退役无理由 ({a['where']})")
            continue
        if disp.startswith("已落实"):
            landed += 1
            continue
        mod = a["module"]
        if mod not in MODULES:
            fails.append(f"{a['id']} 归属模块未注册: '{mod}' ({a['where']})")
            continue
        stats[mod][0] += 1
        par, exp = texts[mod]
        pat = re.compile(rf"\b{re.escape(a['id'])}\b")
        if not (pat.search(par) or pat.search(exp)):
            fails.append(f"{a['id']} 未被 {mod} 的 PARADIGM/EXPECT 覆盖 — {a['text']}")
            continue
        if a["kind"] == "要求" and not pat.search(exp):
            fails.append(f"{a['id']} 是要求但未进 {mod}/EXPECT — {a['text']}")
            continue
        stats[mod][1] += 1

    all_ids = {a["id"] for a in parse_atoms(root / "dev")}
    for name, (par, exp) in texts.items():
        if only and name != only:
            continue
        for m in set(ID_RE.findall(par + exp)):
            if m not in all_ids:
                fails.append(f"{name} 引用了不存在的 id {m}")

    fails += check_variants(root, refresh)

    total_kept = sum(k for k, _ in stats.values())
    total_cov = sum(c for _, c in stats.values())
    print(f"原子要点 {len(atoms)} 条 · 保留 {total_kept} · 已落实于架构 {landed} · 退役 {retired}")
    for mod in MODULES:
        k, c = stats[mod]
        if k:
            print(f"  {mod:18s} {c:4d}/{k:<4d} {100 * c / k:5.1f}%")
    pct = 100 * total_cov / total_kept if total_kept else 100.0
    print(f"覆盖率 {total_cov}/{total_kept} = {pct:.1f}%")
    if fails:
        print(f"\nFAIL × {len(fails)}")
        for f in fails:
            print("  - " + f, flush=True)
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
