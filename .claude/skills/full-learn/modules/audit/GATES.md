# audit — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

## B. 覆盖对账（页 → 节点 → 节）

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-08 | 开工即有覆盖清单（材料每页 + 每道练习题的每个子问），收尾每项都勾到某个 §；有未勾项即 FAIL | script: verify_book.py#exercises | audit §方法 1 |
| E-AUDIT-13 | tree 中每个非 external 节点出现在某节 `nodes` 注释里，并出现在书尾反查附录中 | script: verify_book.py#nodes | spine / compose/section PARADIGM |
| E-AUDIT-14 | `apex.unfolds` 每个节点都有落点节 | script: verify_book.py#apex | spine PARADIGM |
| E-AUDIT-15 | spine 表每行节点 ↔ book 节注释双向一致；节注释出现 spine 未安排给该节的节点 → WARN | script: verify_book.py#spine_sync | spine PARADIGM（cells） |
| E-AUDIT-16 | 节注释里每个 id 存在于 tree.json；有 id 无落点节 → WARN（悬空引用） | script: verify_book.py#ids | tree / spine PARADIGM |
| E-AUDIT-17 | 节内脚注与图注引用的页在该节 `sources` 内（否则 WARN）；任何页码超出该材料页数 → WARN | script: verify_book.py#sources | compose/devices PARADIGM（出处） |
| E-AUDIT-18 | 没有节点只出现在补充块内；对照表落点列不是补充块类型（☕/🎓/💡/📍 等由 devices 定义的块） | script: verify_book.py#position | compose/section PARADIGM |
| E-AUDIT-19 | `audit/coverage.md` 由脚本生成：每源文件一行汇总（总页/已覆盖/豁免/未覆盖/覆盖率）+ 明细（材料短名+页 / 一句话 / 节点 id / §N.M 可附块类型或 🖼）；一节点跨多页多行、一页多节点逗号分开、连续同主题页可合并区间；书尾附录含同表的读者版 | script: verify_book.py#coverage_table | audit §方法 2a · compose/book PARADIGM（back） |
| E-AUDIT-20 | 豁免与"不展开什么"只出现在 coverage.md 与书尾附录，章首与正文不列豁免页 | script: verify_book.py#no_exempt_in_body | compose/chapter PARADIGM |
| E-AUDIT-21 | 有往年题/练习题时，每题 → 考的节点 → 讲它的节 三级对账，任一题考到的节点无落点节 → FAIL | script: verify_book.py#exam_map | tree / spine PARADIGM |
| E-AUDIT-22 | 重写/改版时对比 baseline：旧版认领的页集合与节点集合在新版中都仍被认领，少一个 FAIL | script: verify_book.py --baseline | audit §方法 2b |

## C. 依赖与自足

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-23 | 每个节点的中英文名在全书首次出现的位置不早于其落点节（引用为 `requires` 的前驱另计）；早用即 FAIL；连续 3 个未解释术语 → WARN | script: verify_book.py#deps | spine PARADIGM（order）· core PARADIGM（读者模型） |
| E-AUDIT-26 | 无空壳节：盖住所有块后，节正文有实质（有定义/推理/公式/表格/算例之一，不只是"原则是 X"而不列 X）；字数下限按该节分量定 | script: verify_book.py#hollow | compose/section PARADIGM |

## D. 形状与比例（阈值归属各模块，audit 只执行）

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-AUDIT-28 | 无旧版残留标记（🧠 等）与元叙事禁词（词表归 core E-CORE-19）；块标记的拼写与词汇表一致性按 devices E-DEV-36 统计执行 | script: verify_book.py#meta_narrative · #block_vocab | core PARADIGM（文风）· compose/devices |
| E-AUDIT-29 | 块预算按章、按字符统计（不按行），阈值以所属模块为准：☕ / 🎓 占比（devices E-DEV-41，超即 FAIL）、外部补充总量（core E-CORE-05，超即 WARN 并先查正文是否写薄）、代码块 + 表格占比（devices E-DEV-34，超上限 WARN）；块名按 devices 词汇表识别 | script: verify_book.py#aside_budget · #external_share · #heavy_device_ratio | compose/devices · core PARADIGM |
| E-AUDIT-30 | 篇幅权重按章、按字符执行 chapter 的阈值（E-CHAP-09）：节按字符从长到短排，最长几节是分量最高的节点；背景节不长于核心节中位数；核心档合计不低于 chapter 规定的下限 | script: verify_book.py#weight_budget | compose/chapter PARADIGM |
| E-AUDIT-33 | 原图引用可核：文件存在；图注含 `<短名> p<N>` 或以"自绘"开头，且页码在该节 sources 内；`_figures.json` 有图而全书零嵌图 → WARN（图的取舍与位置标准归 devices E-DEV-23/26/27） | script: verify_book.py#figure_format · #figure_candidates | compose/devices PARADIGM（图） |
| E-AUDIT-35 | 不手写阅读时长：若章首给时长，由脚本按 devices 的时长口径（字数 ÷ 速率，图表加权）统一生成；源文件中无手写分钟数 | script: verify_book.py#reading_time · #guide_minutes | compose/chapter · compose/devices PARADIGM |
