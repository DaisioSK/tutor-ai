# spine — 验收

`verify_spine.py`（检查名以 audit PARADIGM「脚本注册表」为准）尚未实现，下表标 `script(todo)` 的检查以它为目标；未实现前由作者按"自查动作"栏手工执行同一判定。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-SPINE-01 | 开工时 `tree.json` 存在且含 nodes / requires / weight / apex；缺失则停下先跑 tree，不凭材料自行排序 | script(todo): verify_spine.py#input | PARADIGM §方法 0 |
| E-SPINE-02 | 动笔排序前已写下四问的答案（apex 一句话、各章懂了什么、台阶与每步新念头、每步卡点），任一答不出则回 tree | self: 在 spine.md 头部注释里找这四个答案，逐个确认非空、非套话 | PARADIGM §方法 0 |
| E-SPINE-03 | `spine.md` 存在且符合 T3：含「运行案例」段、头部发散参数、每章 `## 第 N 章 <能力标题> — 解锁: …` + 章入口问题、每章一张主表（§/节点/四格）+ 一张按 § 对齐的机读表（§/分量/负载/sources/预选原图），两表 § 一一对应 | script(todo): verify_spine.py#schema | PARADIGM §方法 4 |
| E-SPINE-04 | tree 中每个节点在 spine 中至少有一个落点（节表的节点列），无节点留白；每章包含的节点与顺序由表给定 | script(todo): verify_spine.py#node_coverage | PARADIGM §方法 2 |
| E-SPINE-05 | 拓扑合法：每个节点（含 external 与发散节点）的全部 requires 都出现在它所在节之前（或同节且排在其前） | script(todo): verify_spine.py#topo | PARADIGM §方法 2、判断准则 1 |
| E-SPINE-06 | 每节「凭什么现在能懂」只含排在前面的节点 id，且覆盖本节节点的全部直接 requires（无 requires 的根节点写"—"） | script(todo): verify_spine.py#cite_earlier | PARADIGM §方法 4 |
| E-SPINE-07 | 每节四格全部非空（前置节的「留下的新问题」写「—（回到主线）」算填了） | script(todo): verify_spine.py#cells_filled | PARADIGM §方法 4 |
| E-SPINE-08 | 入口问题是读者能具体感到、带条件的问题（以问号结束），不含"当你需要/涉及…时/关于…"式模糊状态 | script(todo): verify_spine.py#entry_concrete + cold-read（只给入口问题列，问"每条你能感到这个困惑吗"） | PARADIGM §方法 4 |
| E-SPINE-09 | 「解锁了什么」格与章「解锁: <能力>」均为可检验动作（匹配 会算/能判断/能推出/能说出为什么… 的动作正则），优先推理类动词而非"实现/调用/做完" | script(todo): verify_spine.py#unlock_action（移植 verify_teach.py 的 ACTION_RE） | PARADIGM §理论 4、§方法 4 |
| E-SPINE-10 | 解锁格不含"理解/熟悉/掌握/了解一下/有个印象"等不可验词（出现即 WARN） | script(todo): verify_spine.py#unlock_vague（移植 VAGUE_RE） | PARADIGM §方法 4 |
| E-SPINE-11 | 解锁格长度：≤40 字 PASS，41-60 字 WARN，>60 字 FAIL（表格单元重标阈值） | script(todo): verify_spine.py#unlock_len | PARADIGM §方法 4 |
| E-SPINE-12 | 疑问链连续：第 k 节「留下的新问题」与第 k+1 节「入口问题」是同一个问题（或 k+1 是新章开头、由章入口问题接住）；整列入口问题顺读像一串自然追问 | cold-read: 零背景读者只读入口问题列与新问题列，标出"这一问从哪来的？"的断点 | PARADIGM §理论 2、§方法 2 |
| E-SPINE-13 | 章按认知递进排而非照搬材料顺序：若章序与节序同材料 / Lecture 顺序完全一致且无一章跨材料，须在 spine.md 头部写出"为什么这正是疑问链"的理由 | script(todo): verify_spine.py#source_order（对比 sources 顺序）+ self: 读理由是否指向具体疑问 | PARADIGM §理论 1、反例 |
| E-SPINE-14 | 每章只解锁一项能力：章标题写能力、章入口问题写真实困惑；章内节点都服务这项能力（可跨 Lecture） | self: 逐章把"解锁"读一遍，含"和/以及"并列两项无关能力的拆章；逐节问"它为这项能力贡献什么"，答不出的挪走 | PARADIGM §方法 3 |
| E-SPINE-15 | 章长受控：每章 ≤8 节且预估阅读 ≤60 分钟（默认值，可在 spine.md 头部改），超出则拆章 | script(todo): verify_spine.py#chapter_size | PARADIGM §方法 3 |
| E-SPINE-16 | 发散就位：前置节点都在前置包里——纯前置节连成一段，位于第一个使用者所在卷或章的开头、使用者之前且同卷（可独立成「补给站」章）；成对前置（`pair`）同节；没有前置混在材料节里；追问型延伸紧跟其核心节点之后；不存在全是延伸节点的"发散章"或章末发散堆 | script: verify_spine.py#divergence_adjacent · self: 读一遍前置包，问"包内顺序是否只按前置自己的依赖" | PARADIGM §方法 2（前置包） |
| E-SPINE-17 | 对比/强耦合节点同节：tree 中 one_liner/why 互相提及或形成"A vs B"的节点对，落在同一节或相邻两节且入口问题点名这组对比 | self: 列出 tree 中所有互相提及的节点对，逐对查其所在节号 | PARADIGM §方法 2 |
| E-SPINE-18 | 分量就位：分量排名前 20% 的节点各有独立节（或为所在节的主节点）；不存在只含低分量节点的章 | script(todo): verify_spine.py#weight_placement | PARADIGM §方法 4 |
| E-SPINE-19 | 运行案例存在且能贯穿：逐章能写出"这一章之后关于案例能多说什么"，写不出的章 ≤1/3 | self: 在 spine.md 运行案例段下逐章写这一句，数写不出的章 | PARADIGM §方法 1 |
| E-SPINE-20 | ⏸1 发生且只发生一次：spine 产出后、compose 开始前，向用户一次性展示科技树图、节点/章/卷数、脊柱表、发散参数，并得到 OK 或"收/放"反馈；未单独询问发散参数或"从哪开始"；收放反馈已回 tree 增删 external 后重排 | self: 查会话记录中 ⏸1 消息与用户回复先于任何 book/*.md 写入；查是否存在其他单独确认 | PARADIGM §方法 5 |
| E-SPINE-21 | ⏸1 消息含全书预估阅读时长与读者可用时间的对照；超出时给出的选项只调粒度/合并/发散，不缩范围；用户授权自主运行时，代拍的 ⏸1/⏸2 决定（含冷读者代行 ⏸2）逐条记入 work/decisions.md（决定/备选/理由） | self: 查 ⏸1 消息与 decisions.md | PARADIGM §方法 5 |
| E-SPINE-22 | spine.md 每章表格前有本章骨架（3–6 个大概念、各 2–4 个子题并标填它的节、概念间关系词、一段连词成句的话），本章每节恰挂一片叶子；每卷有块划分与一段话；骨架在 ⏸1 一并交审 | self: 逐章对照节表与骨架叶子，漏挂/重挂即 FAIL | PARADIGM §方法 3 |
| E-SPINE-23 | 每章有好奇心阶梯（0 技术 / 1 领域反常 / 2 跨领域 / 3 规律 / 读者世界），并标出本章取用的最高可答级；工具类章停在 1 级不硬拔；2、3 级说法标材料外 | self: 逐章检查阶梯与所取级别是否由本章机制推得出 | PARADIGM §方法 3 |
