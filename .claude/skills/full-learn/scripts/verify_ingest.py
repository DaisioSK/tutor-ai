#!/usr/bin/env python3
"""
ingest 的脚本门禁。

用法:
    python verify_ingest.py <raw 目录>

检查名与 audit PARADIGM「脚本注册表」一致:
    layout · page_separators · stem_consistency · figures_present · skipped_registered · roles ·
    registry · visual_index · visual_trace · code_registered · exempt_reasons
（idempotent 需要比对两次运行，留给人工：重跑 extract 后再跑本脚本应仍全过。）
退出码: 有 FAIL 为 1，否则 0。
"""

import json
import os
import re
import sys

ROLES = {"lecture", "practice", "solution", "exam", "assignment", "code", "pool"}
EXEMPT_REASONS = {"封面", "目录", "分节", "路标", "学习目标", "总结", "致谢", "参考文献", "logo", "重复", "动画帧"}
CODE_EXT = {".ipynb", ".py", ".java", ".js", ".ts", ".yml", ".yaml", ".json", ".toml"}

results = []


def report(check, status, msg=""):
    results.append((check, status, msg))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    raw = sys.argv[1]

    need = ["_manifest.json", "_figures.json", "_visual_pages.json", "_visual_notes.md"]
    miss = [f for f in need if not os.path.exists(os.path.join(raw, f))]
    miss += [d + "/" for d in ("visuals", "figures") if not os.path.isdir(os.path.join(raw, d))]
    report("layout", "FAIL" if miss else "PASS", "缺: " + ", ".join(miss) if miss else "T1 文件齐全")
    if "_manifest.json" in miss:
        return finish()

    manifest = json.load(open(os.path.join(raw, "_manifest.json"), encoding="utf-8"))
    materials = manifest.get("materials", [])
    files = manifest.get("files", [])

    # page_separators: 每个 PDF 文本都有物理页分隔，且与登记页数一致
    errs = []
    for m in materials:
        p = os.path.join(raw, m["stem"] + ".txt")
        if not os.path.exists(p):
            errs.append(f"{m['short']}: {m['stem']}.txt 不存在")
            continue
        nums = [int(x) for x in re.findall(r"^--- Page (\d+) ---$", open(p, encoding="utf-8").read(), re.M)]
        if m.get("locator", "p") == "p":
            if not nums:
                errs.append(f"{m['short']}: 无页分隔")
            elif nums != list(range(1, len(nums) + 1)):
                errs.append(f"{m['short']}: 页号不连续")
            elif m.get("pages") != len(nums):
                errs.append(f"{m['short']}: 登记 {m.get('pages')} 页，文本 {len(nums)} 页")
    report("page_separators", "FAIL" if errs else "PASS", "; ".join(errs) or f"{len(materials)} 份材料页分隔一致")

    # stem_consistency: stem 只含安全字符，visuals/figures 的前缀都能对上某个 stem
    stems = {m["stem"] for m in materials}
    errs = [s for s in stems if not re.fullmatch(r"[A-Za-z0-9_-]+", s)]
    for d in ("visuals", "figures"):
        for f in os.listdir(os.path.join(raw, d)) if os.path.isdir(os.path.join(raw, d)) else []:
            if f.endswith(".png") and re.sub(r"_p\d+(_f\d+)?\.png$", "", f) not in stems:
                errs.append(f"{d}/{f}")
    report("stem_consistency", "FAIL" if errs else "PASS",
           f"{len(errs)} 个对不上: " + ", ".join(errs[:6]) if errs else "stem 安全且与图片前缀一致")

    # figures_present
    figs = json.load(open(os.path.join(raw, "_figures.json"), encoding="utf-8")) if "_figures.json" not in miss else []
    lost = [r["file"] for r in figs if not os.path.exists(os.path.join(raw, "figures", r["file"]))]
    noshort = [r["file"] for r in figs if not r.get("short")]
    msg = []
    if lost:
        msg.append(f"{len(lost)} 张登记了但文件不在")
    if noshort:
        msg.append(f"{len(noshort)} 条缺 short（跑 register.py）")
    report("figures_present", "FAIL" if msg or not figs else "PASS", "; ".join(msg) or f"{len(figs)} 张原图齐全且带短名")

    # skipped_registered
    skipped = manifest.get("skipped", [])
    errs = [s.get("file") for s in skipped if not s.get("reason")]
    report("skipped_registered", "FAIL" if errs else "PASS",
           "无理由: " + ", ".join(errs) if errs else f"{len(skipped)} 个跳过项都有理由")

    # roles / registry
    errs = [m["short"] for m in materials if m.get("role") not in ROLES]
    report("roles", "FAIL" if errs else "PASS", "role 非法: " + ", ".join(errs) if errs else "角色合法")
    shorts = [m["short"] for m in materials]
    extracted = {f["file"] for f in files if f.get("status") in ("ok", "warn")}
    errs = []
    if len(shorts) != len(set(shorts)):
        errs.append("短名重复")
    errs += [f"未登记: {f}" for f in sorted(extracted - {m['file'] for m in materials})]
    report("registry", "FAIL" if errs else "PASS", "; ".join(errs) or f"{len(shorts)} 个短名唯一且覆盖全部提取文件")

    # visual_index / visual_trace
    vp = json.load(open(os.path.join(raw, "_visual_pages.json"), encoding="utf-8")) if "_visual_pages.json" not in miss else []
    lost = [v["file"] for v in vp if not os.path.exists(os.path.join(raw, "visuals", v["file"]))]
    report("visual_index", "FAIL" if lost else "PASS",
           f"{len(lost)} 张截图缺失" if lost else f"{len(vp)} 个图重页截图齐全")
    if "_visual_notes.md" in miss:
        report("visual_trace", "FAIL", "_visual_notes.md 不存在")
    else:
        notes = open(os.path.join(raw, "_visual_notes.md"), encoding="utf-8").read()
        traced = set()
        current = None
        for line in notes.splitlines():
            h = re.match(r"^##\s+(\S+?)(?:\.pdf)?\s*$", line)
            if h:
                current = h.group(1)
                continue
            p = re.match(r"^-\s*p(\d+)\s*:", line)
            if p and current:
                traced.add((current, int(p.group(1))))
        untraced = [v["file"] for v in vp if (re.sub(r"_p\d+\.png$", "", v["file"]), v["page"]) not in traced]
        report("visual_trace", "FAIL" if untraced else "PASS",
               f"{len(untraced)}/{len(vp)} 个图重页没有描述或跳过行: " + ", ".join(untraced[:6]) if untraced
               else f"{len(vp)} 个图重页全部留痕")

    # code_registered
    code_files = [s.get("file") for s in skipped if os.path.splitext(s.get("file", ""))[1].lower() in CODE_EXT]
    unreg = [f for f in code_files if f not in {m["file"] for m in materials}]
    report("code_registered", "FAIL" if unreg else "PASS",
           "代码材料未登记短名: " + ", ".join(unreg) if unreg else f"{len(code_files)} 份代码材料")

    # exempt_reasons
    errs = [f"{m['short']} p{e.get('page')}: {e.get('reason')}" for m in materials
            for e in m.get("exempt_pages", []) if e.get("reason") not in EXEMPT_REASONS]
    report("exempt_reasons", "FAIL" if errs else "PASS", "; ".join(errs) or "豁免理由均在枚举内")

    return finish()


def finish():
    fails = 0
    for check, status, msg in results:
        print(f"[{status}] verify_ingest.py#{check}  {msg}")
        fails += status == "FAIL"
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
