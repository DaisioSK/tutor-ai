# audit — 范式

## 一句话

验收靠对账，不靠自觉：把每个模块写下的"做对了长什么样"变成可执行的检查——能脚本化的交给脚本，"看不看得懂"交给零背景冷读者，剩下的给出具体自查动作——失败项沿着 EXPECT 指回它所属范式的那一段，修完从头再跑，全过才交付。

## 理论

**1. 意愿不是保障。** "我逐页过了一遍""我觉得讲清楚了"是作者的感觉，不是事实。旧版里一份三讲合一的 204 页材料，只建模了前 46 页，后 158 页静默蒸发，下游全链看不见。门禁的作用是把"覆盖了""算对了""读得懂"变成可以对账、可以复现的事实。所以验证用脚本，不用自信。

**2. audit 不定义标准，只执行标准。** 内容标准住在各模块的 EXPECT 里（core 的保真与文风、section 的推理链、devices 的块预算……）。audit 的职责是：收齐这些 EXPECT，按检验方式分派，出报告，把失败指回源头。这样任何产物问题都能定位：产物哪里不好 → 哪条 EXPECT 没拦住 → 那条 EXPECT 所属模块的范式就是要改的地方。规则改在范式里，不在 audit 里打补丁。

**3. 两个维度，四种仪器，各自只看得见一部分。** 旧版的根因是门禁量覆盖（recall）不量看懂：524 页讲义过了全部覆盖门禁，读者仍然靠死记硬背过关。反过来也成立：读得顺不等于覆盖全，顺读完的读者无法确信自己没漏。所以验收必须同时量两个维度，而每种仪器只对一类问题敏感：

| 仪器 | 看得见 | 看不见 |
|---|---|---|
| 脚本 | 结构：页是否被认领、节点是否落节、注释与出处是否合法、比例与残留 | 内容对不对、懂不懂 |
| 抽验回查（grep 回 raw/、重算数字、重跑代码） | 细节走样：数字、名字、公式写法、表格格子 | 整块缺失 |
| 冷读者 agent | 看懂：卡住、无聊、断裂 | 是否忠于材料 |
| 打开 PDF 看 | 排版：标题孤悬页底、表格被挤扁、图贴图 | 源文件里的一切 |

脚本防整块蒸发，抽验防细节走样，冷读者防"覆盖了但看不懂"，眼睛防"源文件对但印出来坏"。缺一种，就有一类问题没人拦。

**4. 验证对象永远是印出来的那一份。** 作者本地的代码、草稿里的数字和书里印的那份，在誊抄中容易分叉，分叉的代价由读者承担。所以代码从 `book/*.md` 按序抽出拼回去跑，数字从书里抽出来重算，排版在 PDF 上看。

**5. 门的顺序就是优先级。** 内容门不过，后面的检查没有意义——排版再好也是在装饰一份漏了材料的书。顺序固定为：门 0 内容（脚本对账 → 删块测试 → 保真抽验）→ 门 1 看懂（冷读者）→ 门 2 工艺（推理链复盘、文风）→ 门 3 排版（render 的 layout_check + 打开 PDF 看）。

## 方法

### 1 collect — 收齐要跑的 EXPECT

对目标产物收集 core EXPECT + 本模块 EXPECT；compose 每写完一章，收集 compose 全部子类（book / chapter / section / devices）+ core。把它们按检验方式分成三堆：`script` / `cold-read` / `self`，并按门 0–3 排序。三堆已经分好放：各目录 `GATES.md` 是纯脚本那堆（跑脚本即执行，不必逐条读），`EXPECT.md` 是 self、cold-read 与脚本未实现的那几堆。凡是 `script(todo)`，记下来当作脚本欠账，这一轮由作者按 EXPECT 写明的动作手工执行，不许跳过。

开工时还要立一张**覆盖清单**：材料每一页、每道练习题的每一个子问，在书里都要有归宿；开工列清单，收尾逐条勾。只做 (a)(b)(c) 漏掉 (d) 是最常见的失手——清单就是为它而设。

**做对了**：报告里每条 EXPECT 都有一行结果，没有"没跑"的条目。

### 2 run_scripts — 脚本门禁

脚本以整个 full-learn 目录为输入（读 `tree.json`、`spine.md`、`book/*.md`、`raw/`），逐章 + 全书两级检查。输出分 INFO / WARN / FAIL 三级，末行汇总 `结果: PASS/FAIL (n fail, m warn)`，任一 FAIL 退出码 1。FAIL 明细最多列 20 行，其余计数"另有 N 行"。每条 FAIL 消息带三件事：为什么错、怎么修、指向哪个模块 PARADIGM 的哪一段。依赖缺失（如公式转换模块导入失败）时，相关检查静默跳过并 INFO 一句，不阻塞其余检查；公式检查只扫描、计数，不改文本。

脚本查的东西分五组：

**(a) 覆盖对账：两步，而不是正文结构。** 覆盖是事后审计，不约束正文怎么组织——正文的组织由脊柱决定。

- 第一步 页 → 节点（tree 阶段）。对每个 raw 文本数出总页数；每页归入且仅归入一类：已覆盖 / 显式豁免 / 未覆盖。可豁免的只有封面、目录、分节页、学习目标或路标页、内容已在别处讲的重述型总结页、致谢与参考文献、纯 logo、重复的动画帧，且每条豁免写明理由。任一源文件未覆盖页超过 10%，回去补提取，不许静默通过；成块豁免要写理由（如"该讲声明不考"），超过 10% 的成块豁免只有用户能批。同时对账 manifest 里被跳过的文件（要么已处理，要么留下未处理记录），并记录图重页的消费情况（共 N 页、已描述 M 页、跳过 K 页及逐条理由）。
- 第二步 节点 → 节（compose 阶段）。tree 里每个非 external 节点都出现在某节的 `nodes` 注释里；终极理解直接展开的每个节点都有落点；spine 表的节点与书中节注释双向一致；注释里的 id 必须存在于 tree；spine 没安排给该节的节点出现在注释里 → WARN；有 id 却找不到落点节 → WARN（悬空引用）。节内脚注与图注引用的页必须落在该节 `sources` 内，页码超出材料页数 → WARN。页码解析认带短名的 `L4 p27-29`，返回（短名, 页）集合。
- 节点必须落在正文里，不能只活在补充块里——补充块不是材料内容的载体。
- 有往年题时多做一层：题 → 节点 → 节。考卷是完整性的最终检验，考了但没讲，读者在考场上翻书也找不到。
- 对账结果由脚本从全书节注释、脚注与 tree 的 sources **生成** `audit/coverage.md`：每源文件一行汇总（总页 / 已覆盖 / 豁免 / 未覆盖 / 覆盖率），再列明细，列为"材料短名+页 / 该页一句话 / 节点 id / 落点 §N.M（可附块类型或 🖼 表示嵌了原图）"。一个节点跨多页就多行，一页多个节点逗号分开，连续同主题页可合并成区间；所有行的页并集 = 全范围所有材料的物理页数，少一页即 FAIL。豁免集中写在这里，不进章首。同一张表的读者版放进书尾附录（材料页 → 章节反查），让覆盖成为读者自己能核对的事实，而不是作者的保证。
- 这道门防的是整块蒸发；区间内弱相关的"混水页"它防不了，那要靠逐页提取与保真抽验兜底。

**(b) 只增不减。** 重写、改版、换风格时，用 baseline 对比旧书：旧版认领过的页和节点，新版一个不能少。表达改进只能增不能减。

**(c) 依赖门禁。** 每个术语首次使用的位置必须在它的定义之后：以 tree 节点的中英文名为词表，扫全书，首次出现早于其落点节（且不在其 `requires` 已讲的上下文中）即 FAIL。这是"不用新手听不懂的概念去解释概念"的机械版；语义版交冷读者。

**(d) 形状与比例：标准在各模块，audit 只管怎么量。** 章结构、节结构、块预算、篇幅权重、句段长度、图的位置、代码块长度——这些"长什么样才对"都写在所属模块的 EXPECT 里，阈值也只在那里出现一次；audit 跑各模块 EXPECT 里的脚本项，不另立一套更松或更严的口径。audit 自己负责的是量法统一：所有比例按字符算、不按行——一个引用块常是一个超长物理行，数行会严重低估；节长度 = 节标题到下一个 `## ` 之间的字符数；块按 devices 词汇表识别，拼错的标记按"未知块"计（拼错就不上色）。另有几条检查不属于任何单一模块的内容标准，是 audit 自己的仪器：旧版残留标记；推诿句式（"详见课件 pXX""与 §X 相同不重复""去看一眼/参见/自己打印一下 + 文件名"）——读者从第一页顺读到最后一页，中间不需要跳出去查任何东西；空壳节（盖住全部块后正文无实质：只写"原则是 X"却没列出 X）；原图引用的文件存在、图注页码落在该节 sources、`_figures.json` 有图而全书零嵌图 → WARN；连续三个未解释术语 → WARN。章首若给阅读时长，由脚本按 devices 的时长口径统一算，不手写，于是"各节之和对不上总时长"这类错误自动消失。

**(e) 数字与代码。** 书中出现的代码与数值必须真跑过：从书里抽出全部算例数字跑脚本重算，抽出代码块按序拼起来跑。与官方 solution 对不上时，查清是自己算错还是材料笔误；是笔误就照抄并加注。

**脚本注册表（全 skill 唯一来源）。** 一个检查只有一个名字、挂在一个脚本下、由一个模块拥有它的标准；各模块 EXPECT 的 `script` / `script(todo)` 引用必须能在这里找到，新增检查先登记再引用。分脚本的原则是按输入划界：只读 `raw/` 的归 ingest 脚本，只读 `tree.*` 的归 tree 脚本，只读 `spine.md` 的归 spine 脚本，凡要读 `book/` 的都进 `verify_book.py`（哪怕标准属于 tree 或 audit），排版源码检查进 layout_check，编出来的 PDF 进 `verify_pdf.py`。

| 脚本 | 检查（`#名`）→ 标准所属模块 | 状态 |
|---|---|---|
| `verify_ingest.py <raw/>` | ingest：layout · page_separators · idempotent · stem_consistency · figures_present · skipped_registered · roles · registry · visual_index · visual_trace · code_registered · exempt_reasons | 已实现（idempotent 人工；tree 另含 --weigh --draw）|
| `verify_tree.py <full-learn/>` | tree：raw_present · schema · page_coverage（页 → 节点、豁免枚举、单文件未覆盖 >10%）· acyclic · external_required · extension_bounds · generators · weight_closure · signals · layer_attr · draw_sync | 已实现（idempotent 人工；tree 另含 --weigh --draw）|
| `verify_spine.py <full-learn/>` | spine：input · schema · node_coverage · topo · cite_earlier · cells_filled · entry_concrete · unlock_action · unlock_vague · unlock_len · source_order · chapter_size · divergence_adjacent · weight_placement | 已实现（idempotent 人工；tree 另含 --weigh --draw）|
| `verify_book.py <full-learn/> [--chapter N] [--strip-blocks] [--baseline <旧书>]` | core：reader_md · strip_external_coverage · external_share · self_sufficient · term_first_use · ungrounded_tokens · supplement_history · exam_logistics · banned_words · meta_narrative · sentence_shape · comparatives · list_density；section：section_header · first_sentence_not_definition · hook_terms · formula_after_prose · numbered_slots · length_band · goal_line · route_line；section 前置变体：prereq_no_forward · prereq_shape · prereq_backref（覆盖表关掉的检查在前置节上自动摘除）；chapter：structure · head · reading_time · skeleton · weight_budget · load_sequence · heavy_junction · breather · texture_run · mechanical_transition · close · stage_map · questions · no_catchall · challenge · mind_card · world_model · block_summary；devices：slide_narration · footnote_defs · depth_hint · aside_only_content · reality_intro · figure_candidates · figures_per_section · figure_format · figure_context · math_notation · code_chunks · heavy_device_ratio · block_vocab · guide_line · guide_minutes · texture_floor · aside_budget · breather_length · master_length · def_lines · exam_block · clip_lines · external_marks；book：files · front_first_page · apex_front_back · prereq_covers_external · front_mermaid · book_skeleton · volume_synthesis · book_map · generator_chapters · toc_matches · reading_guide_once · front_elements · front_length · stats · case_thread · xref_format · xref_targets · reverse_index · node_index · keyword_index · exam_appendix · appendix_narrow；tree：generators_in_book；audit：nodes · apex · spine_sync · ids · sources · position · coverage_table · no_exempt_in_body · exam_map · exercises · deps · hollow · `--baseline`（只增不减）· `--strip-blocks`（删块测试导出） | 已实现（全部检查名；ungrounded_tokens · comparatives · list_density · length_band · depth_hint · case_thread 及 sentence_shape 长句长段、head 能力一致、close 回到开章问题、stage_map 完整度只报 WARN；skeleton 的段长（<60 / >260 字）、≥6 节只有 2 个大概念、1 或 5 个子题、子题短名 >12 字、一节挂多叶、大概念没在骨架段出现、没写略写句，close 的"开章大概念在收章重现"，book_skeleton 的卷间关系词不在词表、总纲卷缺卷概念名也只报 WARN（全书出现节点级科技树 mermaid 则 FAIL）；volume_synthesis 字数 2000–5000 之外、book_map 跨卷主线缺根思想与按问题找位置 <20 行只报 WARN；卷串讲 NNv-* 与总纲 98-map 不跑章级结构检查；skeleton 的核心叶子（:::core）即 weight_budget 的核心档；出手 challenge / mind_card / route_line / world_model 的「现在去打」缺则 FAIL，world_model 的「世界模型 vN」与 challenge 的「先回忆」暂只报 WARN；出手块与行（⚔️ 揭晓 🗺️ 🤔先猜 🧠 boss 现在去打 先回忆 世界模型）不计阅读时长、节字数、分量与硬核连续段，🗺️ 不当节首句、不查句式；spine 分量格多节点写法（0/30）取最大值；语义判断归 self / cold-read；exercises 只对账到页，子问粒度归 self；deps 不查"连续 3 个未解释术语"，归 cold-read；`--chapter` 时全书类检查报 SKIP） |
| `verify_numbers.py <full-learn/>` | audit：recompute · run_code | todo |
| `verify_fidelity.py <full-learn/>` | audit：spot | todo |
| `audit_collect.py <full-learn/> <模块>` | audit：all_run · t5_format · script_output | todo |
| `verify_teach.py <out> <md\|book/> --layout-only`（即 layout_check） | render：fences · table_pipe · table_cols · long_token · pre_width · ragged_border · unsupported_latex · leftover_math · inline_math_len · header_len · mermaid_subset · block_marker · math_receipt · batch | 部分已实现（table_cols、inline_math_len、header_len、mermaid_subset、block_marker、batch 为 todo） |
| `verify_pdf.py <book.pdf> [--book <book/>]` | render：text_layer · page_size · bookmarks · links · text_residue · figure_chips · overflow · font_assignment · fresh | 已实现（compile 编完自动跑；figure_chips 把科技树图与骨架图都算作非原图） |
| `compile_story_pdf.py <full-learn/\|book/> [--volumes]` | render（编译器自带的门与生成）：gate · output_path · collect · volumes（`--volumes` 另出 book-vol<K>.pdf × 卷 + book-map.pdf，册外引用降为纯文本）· skeleton_figure · term_index（tree_figure 停用：节点级科技树不进书） | 已实现（skeleton_figure 由 `skeleton_figure.py` 出图（骨架解析与 verify_book 共用；here / dim / done 三种块态），出手块渲染（挑战卡、揭晓另起一页、路线条、心智卡锚点 card-N、boss 徽章）与收章拼图进度图（本卷 L2 图按进度着色，不写进 MD），块角色表在 `block_roles.py`） |
| `extract.py` · `extract_figures.py` · `latex_to_html.py` | ingest / ingest / render 的工具，不是检查 | 已实现 |
| `verify_checklist.py` | dev：原子要点 → 模块范式/验收的覆盖核对（运行时不跑） | 已实现 |

`verify_book.py` 的 `block_vocab` 与 layout_check 的 `block_marker`、`compile_story_pdf.py` 的着色读同一份角色表（源头是 devices 词汇表）；版面常量（列数、长串、行宽、标题长度）只在 render 定义，devices 与 chapter 引用。

### 3 删块测试与保真抽验（门 0 的人工部分）

**删块测试**：把所有块类型盖住（导航、类比、换气、进阶、提示……），只读剩下的正文。正文仍须完整覆盖本节节点的全部材料要点——定义、公式、表格、算例、边界警告。有任何一项只活在补充块里，就是表达层在替换内容层，先补正文。这与"外部补充可删"是同一个原则。

**保真抽验**：每章写完抽 5 个具体数字或专有名词回 `raw/` grep。抽不到又没标外部记号的，按"材料外内容必须标"处理；三类可豁免：已声明的虚构演示数、带算式的推导数、已标外部的。公式是否照原写法、表格是否逐格照抄，也靠抽验。连同 core 的保真清单（外部标记、表格照抄、禁伪精确、出处不伪造、引用不空头、推导展示算式、笔误照抄加注）逐项过一遍。

### 4 cold_read — 冷读者顺读

书没有实时反馈；冷读者就是那个替代品。派一个**零背景**的 agent，只给它书，从第一页顺读。它做的就是**顺读自足测试**：每节结尾停下，只用"这一节 + 前面所有节给过的东西"，判断一个小白能不能到达这一节的目标（spine 中该节"解锁了什么"）。不许回翻材料、不许查外部、不许拿"常识"搪塞。判断的手感：像剧情马上进高潮却被夹断，像侦探剧推理站不住、关键处没交代——哪一步让你"嗯？"，就是要补的那一步；同一个意思第三次出现，就是要删的那一次。

派发提示词骨架（照填，不加背景知识）：

```
你是一个从没学过 <领域> 的读者，数学到 <读者起点>。下面是一本书的 <第 N 章 / 全书>，请从头顺读，不查任何外部资料，不用"常识"补洞。
每读完一个 `## §` 节，停下来回答：
1. 本节目标是「<解锁了什么>」。只凭本节和之前的内容，你能做到吗？做不到，卡在哪一句？
2. 本节开头那个问题，在你读到它时，你自己心里已经在问了吗？
3. 本节引用的例子/场景，你能凭文字画出它的样子吗？
4. 有没有哪个词、符号在解释之前就被用了？有没有用你不懂的概念去解释另一个概念？
5. 有没有哪段你想跳过（重复、离题、对你理解没用）？
6. 有没有哪一步推理是跳的、站不住的，或你觉得说错了？
只报问题，不夸。每条：位置（§N.M + 引一句原文）· 类别 · 一句话说为什么 · 一句话说怎么改。
类别：卡住 / 无聊 / 断裂 / ❌ 有误 / ✂️ 可删 / ➕ 缺失 / 🔧 结构。
某类没有问题就不写这一类；全章没有问题只回"没问题"。
```

冷读者的姿态是冷血客观：理解有误就直说"这里有误"并给正确理解；不说"写得不错"之类废话；某维度没问题就跳过，不写"无"。它审的维度——准确性、关系是否清晰、有无递归解释、哪些太细对心智模型无用、缺了哪块高价值认知、章节结构是否反映 tree 的真实依赖（不一致时给具体重组建议）——都落进上面七类。卡住类的修法是**换讲述角度重写那一节**，不是在后面补一段；无聊类指回 section 的取舍；断裂类指回 spine 的四格或节点覆盖缺口。跨章汇总高频卡点节点，指回对应模块的 PARADIGM。

### 5 self_review — 作者自查

`self` 类 EXPECT 必须是具体动作，不是"确保质量"。复盘什么由各模块的范式规定，audit 只要求复盘留下记录、并把记录收进门 2：

- **推理链复盘**：section 范式规定了逐节、逐拍的复盘（从入口问题到封节），每节一行 ✓/✗。audit 检查每节都有这一行、✗ 项已改，不在这里重列复盘项。
- **文风回看**：core 的文风与禁止清单，逐节列出违例位置。
- **分量与负载**：chapter 的编排表与再分配记录——把节按字数从长到短排，最长几节应正是高分量节点；负载评级是否诚实按 chapter 的定义判。

三份记录缺一份，该章门 2 不过。记录只写没过和改过的（一行一条：id · 问题 · 怎么改的），末行写"其余通过"；推理链复盘照旧每节一行。逐条抄一遍"PASS"不增加检查，只增加篇幅。

### 6 report — 出报告并闭环

每个模块一份 `audit/<模块>.md`，T5 格式：EXPECT id / PASS·FAIL·WARN / 证据（位置 + 摘录）/ 修法指向（PARADIGM 哪一段）。覆盖对账不另起体例：`coverage.md` 的每源文件汇总行与未覆盖、豁免明细，就是覆盖类 EXPECT 那几行的证据。冷读者报告单独成 `audit/cold-read-<章>.md`。

闭环规则：任何一条 FAIL 都不交付、不带着问题往下写；只重写出问题的那一节，不重写整章；重写后从门 0 再过一遍；四道门全过才进下一章或编 PDF。读者的用途（哪怕是"明天考试"）不改变门禁。最后一步，打开 PDF 真的看几页——源文件检查看不到标题孤悬页底、表格被挤扁。

## 判断准则

- **内容 > 看懂 > 工艺 > 排版。** 门之间冲突时，前面的门说了算。
- **能脚本化就脚本化。** 一条检查第二次靠人做，就该写进脚本；`self` 是暂时的。
- **超预算先查正文是否写薄。** 补充块超标说明表达层在挤内容层，回头补正课，而不是删补充凑数。
- **冷读者与材料冲突时：** 懂不懂听冷读者，对不对听材料。冷读者说"卡住"，改讲法；冷读者说"错了"，回 raw 核对后再决定。
- **测得到的覆盖 ≠ 理解。** 全部 PASS 只说明没有整块缺失；一本书交付前至少过一次冷读。
- **WARN 不阻塞，但要在报告里给处理意见**（已核实无碍 / 已修 / 留给用户）。

## 反例

- **整块蒸发**：204 页材料只建模 46 页，没有页 → 节点对账，没人发现。违反理论 1。
- **覆盖全过却看不懂**：只量了一个维度，违反理论 3。
- **验了本地那份**：作者本地代码跑通，书里印的那份少了一行。违反理论 4。
- **漏子问**：只做 (a)(b)(c)，(d) 不见了。违反方法 1 的覆盖清单。
- **对照表位置填补充块**，或改版后旧版有的页没了。违反方法 2 的落点规则与只增不减。
- **推诿与空壳**："详见课件 p28""原则是 X"而 X 没列出。读者被推出书外，违反自足。
- **先修排版再补内容**：排版在装饰一份漏了材料的书。违反理论 5。
