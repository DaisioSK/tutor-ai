# tree — 验收

本表只列人要做的条目（self / cold-read / 脚本未实现）；纯脚本检查在同目录 `GATES.md`，写作时不必读。

脚本名以 audit PARADIGM「脚本注册表」为准：本表检查 tree.json/tree.md 的项在 `verify_tree.py`，需要读 book/ 的项在 `verify_book.py`（verify_book 已实现；仍标 `script(todo)` 的是尚未实现的项）。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-TREE-01 | 开工时 `raw/` 存在（缺失则停下并提示先跑 ingest）；harvest 记录列出全部 `raw/*.txt`，每份都标"已逐页读完"，且读完全部材料后才出现第一条 `requires` 边 | script(todo): verify_tree.py#raw_present · self: 把 `_manifest.json` 的文件清单与 harvest 记录逐行对照，数缺几份 | PARADIGM §方法 0、§方法 1 |
| E-TREE-02 | 每份非跳过材料的每一物理页，都落在某节点的 `sources` 区间内或出现在 `coverage.exempt`（理由属于 ingest 的豁免枚举，manifest 已登记的豁免页全部带入）；有未映射页即不交付 spine | script(todo): verify_tree.py#page_coverage | PARADIGM §方法 1 末条、§方法 6 |
| E-TREE-03 | `tree.json` 符合 T2：有 `scope / apex / generators / nodes`；每节点有 `id / name / en / kind / one_liner / why / requires / sources / weight`；id 唯一；`requires / derives_from / unfolds / generators` 引用的 id 都存在；不再产出 course-outline.md / mental-model.md / concepts.json | script(todo): verify_tree.py#schema | PARADIGM §方法 1、§方法 6 |
| E-TREE-04 | 节点覆盖四类内容：核心概念与定义、定律 / 公式、方法；作业 / 项目材料另有设计决策节点，其 `why` 写出"为什么选它不选别的" | self: 每份材料随机抽 3 页，逐页列出该页的概念 / 公式 / 决策，核对各自在 tree.json 的节点 | PARADIGM §方法 1 |
| E-TREE-05 | 材料中占满一页及以上的推导或解答，各自是独立节点（其 `sources` 覆盖该页段），没有被压进别的节点的一句话 | self: 列出材料里所有整页推导 / 解答页，逐个查是否有专属节点 | PARADIGM §方法 1 推论一、§判断准则 |
| E-TREE-06 | 材料作者自带的分类标签（如方括号题型标签、作者自己的分组名）全部原样出现在相应节点的 `labels` 或 `name` 中，没有被自创分类替换 | self: 在 raw 文本里 grep 方括号标签与分组标题，逐个在 tree.json 中查到原文 | PARADIGM §方法 1 推论二 |
| E-TREE-07 | `requires` 构成无环图且至少有一条跨讲边；对比 / 组成 / 实现关系只在 `relations` 中，不混入 `requires`；随机抽 10 条 `requires` 边，每条都能写出"不懂 X，读 Y 卡在哪一句" | script(todo): verify_tree.py#acyclic · self: 抽 10 条边写卡句，写不出的删边或改为 relation | PARADIGM §方法 2 |
| E-TREE-08 | 每个材料外前置节点都标 `kind=external, role=prerequisite`，且：被至少一个范围内节点直接 `requires`；材料内无讲解；不在 reader.md 起点内；`gap` 写明只补的那一截；`sources` 为空（用到它的页归使用者节点）；`mental_model` 是一句能推出全部规则的结构念头；互为逆运算或同一结构两面的前置互标 `relations: pair` 且二者间的 requires 边不漏；其讲解范围不超过一讲的复述 | script: verify_tree.py#external_required（role、被依赖、gap、sources 空、mental_model 非空）· self: 逐个 external 节点过三问、核对 gap，读一遍 mental_model 问"规则能从这句推出来吗"，列成对候选 | PARADIGM §方法 1 external（前置三样）、§判断准则 |
| E-TREE-09 | 没有漏标的前置：任一节点的公式 / 方法用到的每个符号与工具，要么是树上节点，要么在 reader.md 起点内 | self: 逐个 formula / method 节点列出所用符号与工具，查无着落的即补 external 节点 | PARADIGM §方法 1 external、§反例 |
| E-TREE-10 | 发散节点均为 `kind=external, role=extension`，`depth ≤` reader.md 层数，每个种子概念每层不超过 breadth 个，各附关联理由且过阈值；没有任何范围内节点 `requires` 发散节点 | script(todo): verify_tree.py#extension_bounds | PARADIGM §方法 1 发散节点 |
| E-TREE-11 | 生成元 3–5 个；每个写出它的"不得不这样"约束，并有若干节点以 `derives_from` 指向它，且这些节点跨两讲及以上 | script(todo): verify_tree.py#generators · self: 逐个生成元读约束句，确认能从它推出所列节点 | PARADIGM §方法 3 |
| E-TREE-12 | `apex.statement` 是一句话、`unfolds` 非空；只凭 apex + 生成元能推出至少 3 个非生成元节点的 one_liner；代码类范围的 apex 候选为"这是一个用 X 技术做 Y 事情的 Z"句式 | cold-read: 零背景 agent 只读 apex 与生成元，写出指定 3 个节点的一句话说明并与 tree.json 对照；再给一个新情境，看它能否问出对的问题 | PARADIGM §方法 3、§理论 2 |
| E-TREE-13 | 每个节点的 `weight` 等于脚本算出的下游传递闭包节点数，无手改；不存在"核心 / 常规 / 背景"之类手标分量 | script(todo): verify_tree.py#weight_closure | PARADIGM §方法 4 |
| E-TREE-14 | 考试 / 强调 / 重复等外部信号只存在于节点 `signals`，不改 `requires`；考试信号仅在 reader.md「考试信息」不为"无"时出现；信号强而 weight 位于后四分之一的节点都有一条"已复查依赖边"的记录 | script(todo): verify_tree.py#signals · self: 列出强信号低分量节点，逐个核对复查记录 | PARADIGM §方法 4、§判断准则 |
| E-TREE-15 | 代码类材料产生的节点都带 `layer`（What / Why / How / Deep，同 T2），且 `requires` 不以层序代替理解依赖 | script(todo): verify_tree.py#layer_attr | PARADIGM §方法 1 推论三 |
| E-TREE-16 | `tree.md` 由脚本从 tree.json 生成且与之同步：含 apex 句、生成元表、mermaid 分层科技树、节点表；图按角色分组而非按讲分组；线型按 实线=依赖 / 粗线=推论与实现 / 虚线=对比 / 点线=组成 区分 | script(todo): verify_tree.py#draw_sync | PARADIGM §方法 5 |
