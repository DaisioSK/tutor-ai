#!/usr/bin/env python3
"""
ingest/register — 把材料登记表合并进 _manifest.json，并给 _figures.json 每条记录补 short。

LLM 的判断（短名、角色、豁免页）写在 raw/_register.json，脚本产物重跑后再跑本脚本即可重新合并，
判断本身不会丢。

用法:
    python register.py <raw_dir>

_register.json:
    {"materials": [{"short": "L4", "file": "lectures/L4-MarkovModels.pdf", "role": "lecture",
                    "high_value": false, "locator": "p", "exempt_pages": [{"page": 1, "reason": "封面"}]}]}
"""

import json
import os
import re
import sys


def slugify_stem(rel):
    stem = os.path.splitext(rel)[0].replace("/", "_").replace(os.sep, "_")
    stem = re.sub(r"\s+", "_", stem.strip())
    stem = re.sub(r"[^A-Za-z0-9_-]", "", stem)
    stem = re.sub(r"_{2,}", "_", stem)
    stem = re.sub(r"-{2,}", "-", stem)
    return stem.strip("_-") or "file"


ROLES = {"lecture", "practice", "solution", "exam", "assignment", "code", "pool"}
EXEMPT_REASONS = {"封面", "目录", "分节", "路标", "学习目标", "总结", "致谢", "参考文献", "logo", "重复", "动画帧"}


def count_pages(txt_path):
    if not os.path.exists(txt_path):
        return None
    with open(txt_path, encoding="utf-8") as f:
        return sum(1 for line in f if line.startswith("--- Page "))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    raw = sys.argv[1]
    with open(os.path.join(raw, "_register.json"), encoding="utf-8") as f:
        spec = json.load(f)
    man_path = os.path.join(raw, "_manifest.json")
    with open(man_path, encoding="utf-8") as f:
        manifest = json.load(f)

    extracted = {e["file"] for e in manifest.get("files", [])}
    errors, shorts, materials = [], set(), []
    for m in spec["materials"]:
        if m["short"] in shorts:
            errors.append(f"短名重复: {m['short']}")
        shorts.add(m["short"])
        if m.get("role") not in ROLES:
            errors.append(f"{m['short']}: role 非法 {m.get('role')}")
        if m["file"] not in extracted:
            errors.append(f"{m['short']}: {m['file']} 不在提取清单里")
        stem = slugify_stem(m["file"])
        for ex in m.get("exempt_pages", []):
            if ex.get("reason") not in EXEMPT_REASONS:
                errors.append(f"{m['short']} p{ex.get('page')}: 豁免理由不在枚举里 ({ex.get('reason')})")
        materials.append({
            "short": m["short"], "file": m["file"], "stem": stem,
            "pages": count_pages(os.path.join(raw, stem + ".txt")),
            "locator": m.get("locator", "p"), "role": m["role"],
            "high_value": bool(m.get("high_value", False)),
            "exempt_pages": m.get("exempt_pages", []),
        })
    missing = extracted - {m["file"] for m in materials}
    for f in sorted(missing):
        errors.append(f"已提取但未登记短名: {f}")

    manifest["materials"] = materials
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    fig_path = os.path.join(raw, "_figures.json")
    if os.path.exists(fig_path):
        with open(fig_path, encoding="utf-8") as f:
            figs = json.load(f)
        by_stem = {m["stem"]: m["short"] for m in materials}
        unmapped = 0
        for rec in figs:
            stem = rec["file"].rsplit("_p", 1)[0] if "file" in rec else slugify_stem(rec.get("source", ""))
            rec["short"] = by_stem.get(stem)
            unmapped += rec["short"] is None
        with open(fig_path, "w", encoding="utf-8") as f:
            json.dump(figs, f, ensure_ascii=False, indent=2)
        if unmapped:
            errors.append(f"_figures.json 有 {unmapped} 条记录映射不到短名")
    else:
        errors.append("_figures.json 不存在")

    print(f"登记 {len(materials)} 份材料 → {man_path}")
    for e in errors:
        print(f"[FAIL] {e}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
