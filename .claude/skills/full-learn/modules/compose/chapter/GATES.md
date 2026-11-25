# compose/chapter — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-CHAP-01 | 每章恰好一个文件 `book/NN-<slug>.md`，以 `# 第 N 章` 开头，含一个不编号的开章 h2 与一个不编号的收章 h2，单独读也有完整的开头与收束；文件内无课件逐页对照表（该表属 audit） | script: verify_book.py#structure | PARADIGM §方法 1、4 |
| E-CHAP-02 | 文件首行是一句话的本章核心问题（开章先立问题）；首个 `## §` 之前（且在前 1500 字内）有章首 🧭 导读条，写明"本章只装的一个念头 / 解锁的能力"与阅读时长，能力表述与 spine.md 本章标题行"解锁:"一致；导读条不写出处 | script: verify_book.py#head | PARADIGM §方法 1 |
| E-CHAP-03 | 章首阅读时长由脚本按字数计算；若有节带分钟标注，章首时长 = 各节分钟之和，误差 0 | script: verify_book.py#reading_time | PARADIGM §方法 1 |
| E-CHAP-04 | 开章有本章骨架：引导语「本章骨架」后一段连词成句的话（约 80–160 字），3–6 个大概念各在段中加粗出现一次，并按图中的关系连起来；不另列平铺的「带走」清单，不用 🎯 | script: verify_book.py#skeleton | PARADIGM §方法 1、理论 5 |
| E-CHAP-07 | 骨架图：首行 `%% skeleton` 的 mermaid，3–6 个 subgraph（大概念；节数 <6 的章可为 2）、每个 1–4 个子题节点（1 个时 WARN，提示确认该概念确由一节承担，不为凑数挂节），子题标签 `短名 · §N.M`；本章每个 § 恰好挂在一片叶子上（不漏不重），所标 § 均存在；大概念之间每条边带关系词（包含/递进/并列/因果/对比/前提/应用）+ 短语，图连通；图后一句写明哪些只略写不展开；位置在开章场景之后、首个 `## §` 之前；不画节的先后路线，不出现节点 id、「分量」字样 | script: verify_book.py#skeleton | PARADIGM §方法 1、理论 5 |
| E-CHAP-09 | 篇幅预算按章计：核心档合计 ≥55%（<45% FAIL，45-55% WARN），常规约 30%，背景合计 ≤15%；背景单节 ≤800 字且不长于核心节字数中位数 | script: verify_book.py#weight_budget | PARADIGM §方法 2、理论 2 |
| E-CHAP-13 | 序列上不出现连续 3 个重节，也不出现连续 3 个以上轻节；为此做的调序不违反 spine 拓扑序（"凭什么现在能懂"只引用前面的节点），调不开则插轻节 / 合并 / 回 spine 改切章 | script: verify_book.py#load_sequence | PARADIGM §方法 2、判断准则 |
| E-CHAP-14 | 两个重节相邻时，交界处有 ☕，且 ☕ 位于前节过渡句之前 | script: verify_book.py#heavy_junction | PARADIGM §方法 2 |
| E-CHAP-15 | 每个重节内至少一个 ☕，位于最重一步 / 深度例子之后；轻节不放 ☕ | script: verify_book.py#breather | PARADIGM §方法 2 |
| E-CHAP-16 | 硬核内容（推导 / 公式 / 定义堆）连续不超过约 25 行不换质地；超过 25 行的推导链中段有一次质地切换（数值代入或 💡），链末有 ☕ | script: verify_book.py#texture_run | PARADIGM §方法 2、理论 3 |
| E-CHAP-19 | 正文不出现"接下来我们讲 / 下面介绍 / 下一节我们来看"类机械过渡 | script: verify_book.py#mechanical_transition | PARADIGM §方法 3 |
| E-CHAP-23 | 收章有阶段地图：到此为止科技树上已点亮的局部图，包含本章及之前所有章的节点 | script: verify_book.py#stage_map | PARADIGM §方法 4、理论 5 |
| E-CHAP-25 | 章末思考题 3-5 道，基础 → 应用 → 综合递进，综合题跨本章与前章节点；所涉节点全部排在本章末之前且以本章节点及其依赖为主；答案不在题后（在书尾） | script: verify_book.py#questions | PARADIGM §方法 4 |
| E-CHAP-28 | 每个节标题下一行有 `<!-- nodes: … \| sources: … -->`（格式检查归 section E-SEC-01）；文件头不另列"覆盖知识点""来源: Lecture" | script: verify_book.py#section_header | PARADIGM §方法 4 |
| E-CHAP-32 | 开章有 ⚔️ 押一注：情境题 + 3–4 个选项（错误项为常见直觉）+ 揭晓（每个选项的对错与理由，末句引出正文）+ 跳到心智卡的链接；非首章开章有"先回忆 vN−1"一行；有"本章 boss"一行 | script: verify_book.py#challenge | PARADIGM 理论 6、方法 1 |
| E-CHAP-33 | 收章第一块是 🧠 心智卡：一个问题、2–3 条 ❌（各带"不对，因为"）、1 条 ✅（带"因为"）、一行"一句话"；用 bullet，不写成段落 | script: verify_book.py#mind_card | PARADIGM 方法 4 |
| E-CHAP-34 | 收章有"世界模型 vN"（N = 章号，本章新增加粗）与拼图进度图；有"现在去打"指向本章 boss | script: verify_book.py#world_model | PARADIGM 方法 4 |
| E-CHAP-36 | 两章及以上的块，块末章收章在 🧠 之后、世界模型之前有 🌳 块小结（这块在问 / 合起来的答案 / 往上挂 / 往下接 / 一句话），后接小树图：框恰为块内各章、框内只有"留下：…"、每框至少一条边；一章的块与非块末章没有 🌳 | script: verify_book.py#block_summary | PARADIGM 方法 4 |
