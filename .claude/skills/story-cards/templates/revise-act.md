# revise-act — 按新要求修一幕（读者反馈后，各幕并行）

> 调度者：读者提了新要求，先改 `SPEC.md`（与能机读的检查），再每幕发一份。`{改什么}` 写 SPEC 的条号和一句话，不在这里重述规则。原作者还在就用 SendMessage 续用它；不在就发这份给新 agent。

根目录 R = `{R}`，书 B = `{B}`，产物目录 O = `{O}`，skill S = `R/.claude/skills/story-cards`。跑 Python：`{PY}`。用 Write/Edit 改文件（经 shell 写文本会吞反斜杠）。

## 你改什么
只改 `O/parts/act{NN}.md`（第 {a}–{b} 章）。这次要做到：{改什么，如"SPEC 第 5 条 不超前引用；第 6、12a 条 加第 5 列计算样例"}。

## 先读
1. `S/SPEC.md` 里上面点到的那几条（其余规则照旧，改的时候别破坏）。
2. 你这一幕的文件。
3. 调度者附上的脚本报告（下面"候选"），以及书里相关的 `## §N.M`（grep 定位，按需读）。

## 候选
{脚本输出，如 forward.py --only 的那几行；没有就写"无"}

## 怎么改
- 候选要逐条判，判断依据写在 SPEC 对应条里；不是问题的留着，在交付里说一句为什么。
- 只动要改的格；其他格一字不改。表头要跟 SPEC 第 6 条一致。

## 自查
`python3 S/scripts/check.py O/parts/act{NN}.md B --quiet`（coverage 报其他幕"缺"可忽略）、`python3 S/scripts/concepts.py O/parts/act{NN}.md`，都不比改之前差。

## 交付（≤5 行）
改了几行、每类改法各几处、留着没改的候选及理由、最没把握的 1 行。
