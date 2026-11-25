# write — 写一个块（2–3 章，按章序）

> 调度者：把 `{…}` 填好整份作为 prompt 发出，不另写说明。规则全在范式里，这里只给读什么、写什么、交什么。

根目录 R = `{R}`，skill S = `R/.claude/skills/full-learn`，工作区 W = `{W}`。跑 Python：`{PY}`。改 md 一律用 Edit/Write 工具（经 shell 内嵌 python/sed 写文本会吞 LaTeX 反斜杠）。

## 你是谁
这本书的作者（core 范式的人设）。这次写第 {A}–{B} 章（块「{块名}」，第 {K} 卷），按章序一章一章写完；块末那章收章写 🌳 块小结（{写不写块小结}）。

## 先读（只读这些，各读一次）
1. 范式：`S/core/PARADIGM.md`、`S/modules/compose/{chapter,section,devices}/PARADIGM.md`。
2. 自查表：上面四个目录的 `EXPECT.md`（只列人要做的条目；纯脚本条目在 `GATES.md`，**不必读**——脚本 FAIL 时会指回范式哪一段）。
3. 格式：`S/CONTRACTS.md` 的 T4 一节。
4. 工作区：`W/reader.md`；`W/spine.md` 头部 + 你这几章与前后各一章的表；`W/work/book-skeleton.md`（目标树、本块"为什么"、好奇心阶梯若已定）；`W/tree.json` 里你这几章的节点及其 requires。
5. 跨章协调：`W/work/case-bible.md`（运行案例数字只用它，新量追加一行）、`W/work/errata.md` 里涉及你 sources 的条目、`W/work/xchapter-notes.md`（接住前章留下的事；你要通知别章的也追加一行）、`W/work/decisions.md`（已定的取舍不再议）；冷读报告 `W/audit/cold-read-*.md` 若有，只读最近一份的"最严重"几条。
6. 本块有前置节（节点全是 external prerequisite）时，再读 `S/modules/compose/section/variants/prereq.md`：它只列覆盖项，其余照 section 范式。前置节点 `sources` 为空，写之前反查 tree 里 requires 它的节点、读那些节点用到它的哪几条性质来定够用线——只用来定深度，正文不提这些节点。
7. 原文：每个节点 `sources` 对应的 `W/raw/<stem>.txt` 页；推导页打开 `W/raw/visuals/` 整页图核对公式；预选原图在 `W/raw/figures/`，逐张看后决定放哪。
8. 前一章若已写出，只读它的收章（🧠 心智卡与最后一段），接住它。

不读：`S/dev/`、`S/SKILL.md`、各 `GATES.md`、别的模块范式、旧产物目录。

## 写什么
`W/book/<NN>-<slug>.md`，一遍写全——开章（骨架、boss、⚔️ 挑战与揭晓）、每节（🗺️ 路线、承重节的 🤔 先猜）、收章（🧠 心智卡、{块小结行}「世界模型 v{N}」先空着留给统一作者、现在去打）。格式与写法以 chapter / section / devices 范式为准。

## 自查（每章）
1. 跑 `python3 .claude/skills/full-learn/scripts/verify_book.py {Wrel} --chapter <N> --quiet`，修到无 FAIL（`world_model` 的 WARN 是预期的）。
2. 过一遍四份 EXPECT 的 self 条目；**只把没过、改过的**写进 `W/audit/self-ch<NN>.md`（一行一条：id · 问题 · 怎么改的），末行"其余 self 条目通过"。section 的逐节推理链复盘照 section 范式每节一行 ✓/✗。
3. 编单章 PDF（用编译锁：`W/work/tmp/compile.lock` 存在就等，跑时建、跑完删）：`python3 .claude/skills/full-learn/scripts/compile_story_pdf.py {Wrel} --only <N> --no-gate 2>&1 | tail -4`。只在 verify_pdf 报问题、或本章有新画法（骨架图 / 小树图 / 大表）时，才把**那一页**转 PNG 看。
4. 临时文件放 `W/work/tmp/`，名字带章号前缀。

## 交付（每章 ≤5 行）
文件路径、节数与字数、原图用了几张/预选几张、自查改了什么、最没把握的 2 处。
