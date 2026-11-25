#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assignment prep 门禁 (instructions-assignment-prep.md Phase 3)。

用法:
    verify_prep.py <assignment_dir> <prep_dir> [--stub-marker "YOUR CODE HERE"]

十一项检查, 任一 FAIL 退出码 1:
  1. 单元全覆盖   每个待完成单元在附录对照表和某一章正文里都出现
  2. 认知配比     代码块 + 表格 ≤ 30% 篇幅 (实现是廉价的, 不许把认知挤掉)
  3. 一个念头     每章章首声明"这一章只装一个念头"
  4. 交接点       每个单元都有 ▶ 且含具体验法 (测试函数 / 命令)
  5. 契约对齐     测试文件里每条 assert 消息在正文被引用
  6. 参考实现     每个单元有参考实现, 切成 ≤14 行的块, 每块有"第 N 块"标记与讲解
  7. 对账表       测试数据里的参考数值出现在附录或收口章
  8. 表格宽度     任何表 ≤ 4 列 (A5 页宽装不下第 5 列, 会被压成一字一行)
  9. 无填空槽     正文不出现 `① 契约` `② 原理` 这类编号小标题 (那是报告, 不是心路历程)
 10. 读题先拆题   读题章第一个正文小节是"说成人话"式拆题, 标课件/Arc 出处, 有图或架构图
 11. 自足         正文不把读者推回作业文件 ("去看一眼 test_x.py") —— PDF 只依赖课件

变体 A (stub + 自动测试) 的实现。变体 B/C 的 rubric 版本以后补。
"""
import glob
import io
import json
import os
import re
import sys

fails, warns, infos = [], [], []
FAIL = fails.append
WARN = warns.append
INFO = infos.append

CODE_TABLE_MAX = 0.30      # 代码块 + 表格占比上限 (含分块参考实现)
MAX_TABLE_COLS = 4         # A5 页宽上限
SLOT_HEADING = re.compile(r"^#{2,4}\s*[①②③④⑤⑥⑦⑧⑨]", re.M)


def read(p):
    return io.open(p, encoding="utf-8").read()


def find_units(assignment_dir, marker):
    """待完成单元 = 含 marker 的函数名。按文件里出现顺序。"""
    units = []
    for py in sorted(glob.glob(os.path.join(assignment_dir, "*.py"))):
        if os.path.basename(py).startswith("test_"):
            continue
        src = read(py)
        if marker not in src:
            continue
        for m in re.finditer(r"^def (\w+)\(.*?(?=^def |\Z)", src, re.M | re.S):
            if marker in m.group(0):
                units.append(m.group(1))
    return units


def find_test_messages(assignment_dir):
    msgs = set()
    for py in sorted(glob.glob(os.path.join(assignment_dir, "test_*.py"))):
        src = read(py)
        consts = dict(re.findall(r"^([A-Z_]+)\s*=\s*['\"]([^'\"]+)['\"]", src, re.M))
        for m in re.finditer(r"(?:assert\b[^\n]*?,|AssertionError\()\s*(['\"]([^'\"]+)['\"]|([A-Z_]+))", src):
            if m.group(2):
                msgs.add(m.group(2))
            elif m.group(3) in consts:
                msgs.add(consts[m.group(3)])
    return sorted(msgs)


def find_reference_numbers(assignment_dir):
    nums = set()
    for js in glob.glob(os.path.join(assignment_dir, "data", "*_tests.json")):
        try:
            d = json.load(io.open(js, encoding="utf-8"))
        except Exception:
            continue

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("log_prob", "logprob", "expected", "answer") and isinstance(v, (int, float)):
                        nums.add(f"{v:.3f}")
                    else:
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(d)
    return sorted(nums)


def split_prose_code(txt):
    """返回 (正文字符数, 代码块+表格字符数)。空白不计。"""
    prose, heavy, in_fence = 0, 0, False
    for ln in txt.split("\n"):
        n = len(re.sub(r"\s", "", ln))
        if re.match(r"^\s*```", ln):
            in_fence = not in_fence
            heavy += n
        elif in_fence or ln.lstrip().startswith("|"):
            heavy += n
        else:
            prose += n
    return prose, heavy


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    adir, pdir = sys.argv[1], sys.argv[2]
    marker = "YOUR CODE HERE"
    if "--stub-marker" in sys.argv:
        marker = sys.argv[sys.argv.index("--stub-marker") + 1]

    units = find_units(adir, marker)
    if not units:
        FAIL(f"在 {adir} 里没找到含 '{marker}' 的函数 —— 不是变体 A, 或 marker 不对")
    INFO(f"待完成单元 {len(units)} 个: {', '.join(units)}")

    md_files = sorted(glob.glob(os.path.join(pdir, "*.md")))
    if not md_files:
        FAIL(f"{pdir} 下没有 .md")
        report(pdir)
    texts = {os.path.basename(f): read(f) for f in md_files}
    all_text = "\n".join(texts.values())
    appendix = "\n".join(v for k, v in texts.items() if "附录" in k or "appendix" in k)
    closeout = "\n".join(v for k, v in texts.items()
                         if any(w in k for w in ("回头看", "closeout", "收口")))

    # 1. 单元全覆盖 -------------------------------------------------------
    for u in units:
        if u not in appendix:
            FAIL(f"单元 {u} 没出现在附录对照表")
        body_hits = [k for k, v in texts.items()
                     if u in v and "附录" not in k and "appendix" not in k]
        if not body_hits:
            FAIL(f"单元 {u} 只在附录出现, 正文里没人讲它")

    # 2. 认知配比 ---------------------------------------------------------
    tp, th = 0, 0
    for fname, txt in texts.items():
        p, h = split_prose_code(txt)
        is_appendix = "附录" in fname or "appendix" in fname
        if is_appendix:          # 附录本来就是查账表, 不计入配比也不单独告警
            continue
        tp += p
        th += h
        if p + h and h / (p + h) > CODE_TABLE_MAX + 0.10:
            WARN(f"{fname}: 代码块+表格占 {h/(p+h):.0%}, 这一篇偏实现手册")
    share = th / max(tp + th, 1)
    INFO(f"篇幅: 正文 {tp} 字符 · 代码块+表格 {th} 字符 ({share:.0%})")
    if share > CODE_TABLE_MAX:
        FAIL(f"代码块 + 表格占 {share:.0%} > {CODE_TABLE_MAX:.0%} —— "
             f"实现是廉价的, 它挤掉了认知的篇幅 (规范 §篇幅按贵重程度分配)")

    # 3. 一个念头 ---------------------------------------------------------
    for fname, txt in texts.items():
        if "附录" in fname or "appendix" in fname:
            continue
        if "一个念头" not in txt.split("\n## ")[0] and "一个念头" not in txt[:1500]:
            FAIL(f"{fname}: 章首没有「一个念头」声明 —— 这一章的认知锚点是什么?")

    # 4. 交接点 -----------------------------------------------------------
    for u in units:
        hit = False
        for txt in texts.values():
            for m in re.finditer(r"▶[^\n]*(?:\n(?!\n)[^\n]*){0,12}", txt):
                blk = m.group(0)
                if u in blk or re.search(rf"test_{u}\b", blk):
                    if re.search(r"test_\w+|pytest|python[ -]", blk):
                        hit = True
                        break
            if hit:
                break
        if not hit:
            FAIL(f"单元 {u}: 找不到带具体验法的 ▶ 交接点")

    # 5. 契约对齐 ---------------------------------------------------------
    msgs = find_test_messages(adir)
    INFO(f"测试 assert 消息 {len(msgs)} 条")
    for msg in msgs:
        if msg not in all_text:
            FAIL(f"测试消息未被引用 (隐藏要求可能漏了): '{msg}'")

    # 6. 参考实现: 给, 但必须分块 + 带讲解 -------------------------------
    #    旧版规则是"不许给成品"; 用户 2026-09-09 明确要求给答案, 但要能
    #    "带着意义一块一块 paste"。所以这里改成检查"给了没 + 分块了没"。
    REF_HEAD = re.compile(r"^#{3,4}\s*参考实现", re.M)
    CHUNK = re.compile(r"^\*\*第\s*\d+\s*块")
    ref_text = []
    for fname, txt in texts.items():
        lines = txt.split("\n")
        heads = [i for i, l in enumerate(lines) if REF_HEAD.match(l)]
        for h in heads:
            end = next((i for i in range(h + 1, len(lines))
                        if lines[i].startswith("## ") or REF_HEAD.match(lines[i])), len(lines))
            region = lines[h:end]
            ref_text.append("\n".join(region))
            if not any(CHUNK.match(l) for l in region):
                FAIL(f"{fname} L{h+1}: 「参考实现」里没有「**第 N 块**」标记 —— "
                     f"整段甩出去就是要避免的那种 paste")
            # 每个围栏: 长度 + 前后要有讲解
            infence, start = False, 0
            for i, l in enumerate(region):
                if not re.match(r"^\s*```", l):
                    continue
                if not infence:
                    infence, start = True, i
                    continue
                infence = False
                n = i - start - 1
                if n > 14:
                    FAIL(f"{fname} L{h+start+2}: 参考实现的一块有 {n} 行 > 14 —— "
                         f"按思考的拍子再切细一点")
                before = [x for x in region[max(0, start - 4):start] if x.strip()]
                after = [x for x in region[i + 1:i + 7]
                         if x.strip() and not x.strip().startswith("```")]
                if not any(CHUNK.match(x) for x in before):
                    FAIL(f"{fname} L{h+start+2}: 这块代码前面没有「第 N 块」标记")
                if not after or all(CHUNK.match(x) for x in after):
                    FAIL(f"{fname} L{h+i+2}: 这块代码后面没有讲解 —— "
                         f"要说它承担什么语义、贴完能验什么")
    ref_all = "\n".join(ref_text)
    if not ref_all:
        FAIL("全篇没有「参考实现」小节 —— 规范要求给分块参考实现")
    for u in units:
        if u not in ref_all:
            FAIL(f"单元 {u} 没有参考实现")

    # 7. 对账表 -----------------------------------------------------------
    nums = find_reference_numbers(adir)
    INFO(f"测试数据参考标量 {len(nums)} 个: {', '.join(nums)}")
    where = appendix + "\n" + closeout
    for n in nums:
        if n not in where and n.lstrip("-") not in where:
            FAIL(f"参考值 {n} 没出现在附录 / 收口章的对账表")

    # 8. 表格宽度 ---------------------------------------------------------
    for fname, txt in texts.items():
        in_f = False
        for i, ln in enumerate(txt.split("\n"), 1):
            if re.match(r"^\s*```", ln):
                in_f = not in_f
                continue
            if in_f or not ln.lstrip().startswith("|"):
                continue
            cols = len(ln.strip().strip("|").split("|"))
            if cols > MAX_TABLE_COLS:
                FAIL(f"{fname} L{i}: 表格 {cols} 列 > {MAX_TABLE_COLS} —— "
                     f"A5 页宽装不下, PDF 里每格会被压成一字一行; 拆成两张窄表或改写成列表")
                break

    # 9. 无填空槽 ---------------------------------------------------------
    for fname, txt in texts.items():
        hits = SLOT_HEADING.findall(txt)
        if len(hits) >= 3:
            FAIL(f"{fname}: 出现 {len(hits)} 个 ①②③ 编号小标题 —— "
                 f"那是填空表单的形状, 规范要求写成连贯的思考线")

    # 10. 读题章先拆题 (用户 2026-09-12: 小白可能看了原题也没看懂) ------------
    #     第一个正文 ## 小节必须是拆题 (人话/拆解/说清楚), 且在"先做什么"之前。
    PLAIN = re.compile(r"人话|拆解|拆开|说清楚|说成")
    for fname, txt in texts.items():
        if not re.match(r"^1-", fname):
            continue
        h2 = [l for l in txt.split("\n") if l.startswith("## ")]
        if not h2:
            FAIL(f"{fname}: 读题章没有 ## 小节")
            break
        plain_i = next((i for i, h in enumerate(h2) if PLAIN.search(h)), None)
        how_i = next((i for i, h in enumerate(h2)
                      if re.search(r"先做什么|怎么读|读题的思路|开工前", h)), None)
        if plain_i is None:
            FAIL(f"{fname}: 读题章没有「先把题目说成人话」式的拆题小节 —— "
                 f"读者可能看了原题也没看懂 (规范 §读题章)")
        elif how_i is not None and plain_i > how_i:
            FAIL(f"{fname}: 拆题小节「{h2[plain_i][3:]}」排在「{h2[how_i][3:]}」之后 —— "
                 f"先让读者懂题, 再讲读题的思路")
        if plain_i is not None:
            sec = txt.split(h2[plain_i], 1)[1]
            nxt = next((h for h in h2[plain_i + 1:]), None)
            if nxt:
                sec = sec.split("\n" + nxt, 1)[0]
            if not re.search(r"^```", sec, re.M) and not re.search(r"!\[", sec):
                WARN(f"{fname}: 拆题小节没有架构图 (代码块) 也没有题面原图 —— 光靠文字不够直观")
            if not re.search(r"Arc\s*\d+|课件|L\d+\s*p\d+", sec):
                FAIL(f"{fname}: 拆题小节没有标课件/Arc 出处 —— 与课程重合要引用, 不要绕开")

    # 11. 自足 (用户 2026-09-12: PDF 不依赖课件以外的任何外部文件) ------------
    #     正文里 "去看一眼 / 参见 / 自己看 …" 和作业文件名同现 → 把读者推回了文件。
    ext_files = set()
    for root, _, fs in os.walk(adir):
        for f in fs:
            if f.endswith((".py", ".json", ".ipynb", ".csv")) and "Zone.Identifier" not in f:
                ext_files.add(f)
    PUSH = re.compile(r"看一眼|自己看|去看|参见|详见|里有(?:一个)?(?:具体)?例子|自己打印|打开\s*`")
    for fname, txt in texts.items():
        in_f = False
        for i, ln in enumerate(txt.split("\n"), 1):
            if re.match(r"^\s*```", ln):
                in_f = not in_f
                continue
            if in_f:
                continue
            if PUSH.search(ln) and any(f in ln for f in ext_files):
                FAIL(f"{fname} L{i}: 让读者去看作业文件 —— PDF 必须自足, "
                     f"把那段原文抄进来并紧跟解读 (规范 硬规矩 2)")

    report(pdir)


def report(pdir):
    print(f"# verify_prep — {pdir}\n")
    for s in infos:
        print("ℹ️  " + s)
    for s in warns:
        print("⚠️  WARN " + s)
    for s in fails:
        print("❌ FAIL " + s)
    print(f"\n结果: {'FAIL' if fails else 'PASS'} ({len(fails)} fail, {len(warns)} warn)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
