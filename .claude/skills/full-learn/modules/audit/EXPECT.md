# audit — 验收

本表只列人要做的条目（self / cold-read / 脚本未实现）；纯脚本检查在同目录 `GATES.md`，写作时不必读。

本表验的是**自查过程本身**是否做到位，以及 audit 代各模块执行的**通用门禁**（覆盖对账、依赖门禁、保真抽验、数字复核、冷读）。具体内容标准的阈值以所属模块 EXPECT 为准；"不过时回到"一栏指向真正要改的范式段落。

脚本名以 audit PARADIGM「脚本注册表」为准（未实现的标 `todo`）；全 skill 的 `script` 引用都必须能在注册表里找到。

## A. 过程：收集、门序、报告、闭环

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-01 | 每次 audit 收齐 core + 目标模块的全部 EXPECT（compose 每章 = book/chapter/section/devices 四子类 + core），报告里每条 EXPECT 恰有一行结果，无"未跑"条目 | script(todo): audit_collect.py#all_run | audit PARADIGM §方法 1 |
| E-AUDIT-02 | 每份报告是 T5 格式（EXPECT id / PASS·FAIL·WARN / 证据含位置与摘录 / 修法指向某模块 PARADIGM 的具体段）；修法指向不得为空或只写模块名；覆盖类条目的证据引用 `coverage.md` 的汇总行与未覆盖/豁免明细 | script(todo): audit_collect.py#t5_format | audit §方法 6 |
| E-AUDIT-03 | 脚本输出 INFO/WARN/FAIL 三级，末行 `结果: PASS/FAIL (n fail, m warn)`，任一 FAIL 退出码 1，FAIL 明细 ≤20 行，每条 FAIL 消息含"为什么错 + 怎么修 + PARADIGM 段" | script(todo): audit_collect.py#script_output（对注册表内每个 verify_* 的输出格式与退出码自测） | audit §方法 2 |
| E-AUDIT-04 | 门按 0 内容 → 1 看懂 → 2 工艺 → 3 排版 顺序执行：门 0 中脚本先于删块测试；门 0 有 FAIL 时报告中不出现后续门的结论 | self: 核对报告各门的时间戳/顺序与门 0 结果 | audit §理论 5 |
| E-AUDIT-05 | 任一 FAIL 未清零不交付、不进下一章、不编 PDF；修复只重写出问题的节；修后从门 0 全部重跑；读者用途（如备考）不豁免任何门 | self: 对比修前修后 git diff 只涉及 FAIL 所在节，且修后有一份新的完整报告 | audit §方法 6 |
| E-AUDIT-06 | 冷读者报的"卡住"类，修法是换讲述角度重写该节（diff 显示该节推理链改写），而不是在节尾追加一段；跨章高频卡点节点汇总到报告并指回对应 PARADIGM | self: 读修复 diff，检查改动位置与性质 | audit §方法 4 |
| E-AUDIT-07 | 交付前打开 PDF 抽看每章至少首页 + 最长表格页 + 最长公式页，无标题孤悬页底、无挤扁表格、无图贴图；发现即记入 render 报告 | self: 列出看过的页码与结论 | render PARADIGM · audit §方法 6 |

## B. 覆盖对账（页 → 节点 → 节）

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-09 | 对每个 raw 文本数出物理页数；每页恰属 已覆盖/豁免/未覆盖 之一；全范围所有材料的页并集 = 物理页总数，少一页 FAIL 并逐页列出 | script(todo): verify_tree.py#page_coverage | tree PARADIGM（harvest）· audit §方法 2a |
| E-AUDIT-10 | 豁免只属于封面/目录/分节/学习目标·路标/重述型总结/致谢·参考文献/纯 logo/重复动画帧，每条有理由词；成块豁免有理由，超过 10% 的成块豁免有用户批准记录 | script(todo): verify_tree.py#page_coverage · verify_ingest.py#exempt_reasons | audit §方法 2a |
| E-AUDIT-11 | 任一源文件未覆盖页 >10% → FAIL，回 ingest/tree 补提取，不得静默通过 | script(todo): verify_tree.py#page_coverage | ingest / tree PARADIGM |
| E-AUDIT-12 | `_manifest.json` 中每个 skipped 文件有"已处理/未处理 + 理由"记录；图重页消费记录写明 共 N / 已描述 M / 跳过 K 及逐条理由 | script(todo): verify_ingest.py#skipped_registered · #visual_trace | ingest PARADIGM |

## C. 依赖与自足

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-24 | 冷读者报告中"用不懂的概念解释概念"类问题为零（语义版依赖门禁） | cold-read | compose/section PARADIGM |
| E-AUDIT-25 | 正文无推诿句式（"详见课件 pXX""与 §X 相同不重复""记住结论即可，推导见课件""去看一眼/参见/自己打印一下 + 文件名"等，词表在脚本里维护）；读者从头到尾不需跳出书 | script: verify_book.py#self_sufficient（与 core E-CORE-06 同一检查） | core PARADIGM（自足） |
| E-AUDIT-27 | 删块测试通过：盖住全部块类型后，每节正文仍覆盖其节点的全部材料要点（定义、公式、表格、算例、边界警告），无一项只活在块里 | self: 逐节用 `verify_book.py --strip-blocks` 导出的纯正文对照该节 sources 页逐项打勾 | compose/section · compose/devices PARADIGM |

## E. 保真：数字、代码、抽验

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-36 | 书中每个算例数字由脚本重算一致；与官方 solution 对不上处有结论（己错已改 / 材料笔误已照抄加注） | script(todo): verify_numbers.py#recompute + self（对不上项逐条结论） | core PARADIGM（保真） |
| E-AUDIT-37 | 书中代码块按出现顺序从 `book/*.md` 抽出拼合后能跑通、输出与书中所印一致（验的是印出的那份，不是本地那份） | script(todo): verify_numbers.py#run_code | compose/devices PARADIGM |
| E-AUDIT-38 | 每章抽 5 个具体数字/专有名词回 raw grep 命中；未命中且未标外部记号者按材料外内容处理（标记或删）；豁免仅限声明的虚构演示数、带算式推导数、已标外部；公式写法与表格逐格对照原页；core 保真清单逐项打勾 | script(todo): verify_fidelity.py#spot + self（公式/表格对照） | core PARADIGM（保真） |

## F. 看懂：冷读者与作者复盘

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-39 | 每章有 `audit/cold-read-<章>.md`，由零背景 agent 按 PARADIGM §方法 4 的提示词骨架顺读产出（提示词随报告存档）；每节都有"能否到达本节目标"的判定，判定只用本节及之前内容 | cold-read（存档提示词可核） | audit §方法 4 |
| E-AUDIT-40 | 冷读者对每节回答：入口问题读到时是否已是自己的疑问；引用的例子/场景能否画出来；无"卡住"类未处理项 | cold-read | spine PARADIGM（入口问题）· compose/section |
| E-AUDIT-41 | 冷读报告每条带位置（§N.M + 原文摘录）、类别（卡住/无聊/断裂/❌/✂️/➕/🔧）与一句修改建议；无客套与夸奖；无问题的类别不出现；全无问题只写"没问题" | self: 扫报告格式 | audit §方法 4 |
| E-AUDIT-42 | 冷读覆盖四个审阅维度：准确性错误直接指出并给正确理解；对心智模型无用的细节给删减理由；缺失的高价值认知说明为何重要；章节结构与 tree 依赖不一致时给具体重组建议 | cold-read | compose/chapter · tree PARADIGM |
| E-AUDIT-43 | 门 2 工艺的作者自查记录齐全：每节一行推理链复盘表（section E-SEC-36）、文风回看（core E-CORE-18）、长度与负载自查（chapter E-CHAP-11/12），缺任何一份即该章门 2 不过；报告引用这些记录而不另立标准 | self: 逐章核对三份记录存在且每节有行 | compose/section · core · compose/chapter PARADIGM |
