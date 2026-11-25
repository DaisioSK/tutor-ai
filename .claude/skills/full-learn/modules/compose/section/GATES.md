# compose/section — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-SEC-01 | 每节标题形如 `## §N.M 中文 (English)`，下一行紧跟 `<!-- nodes: … \| sources: … -->`，nodes 里的 id 在 tree.json 存在 | script: verify_book.py#section_header | §方法 2 入口 |
| E-SEC-28 | 节内执行 chapter 的节奏尺子（阈值归 chapter E-CHAP-15/16）：硬核连续不超过约 25 行就换质地；负载重的节在最重一步之后至少一个换气；负载轻的节没有换气块 | script: verify_book.py#texture_run · #breather | §方法 2 节奏 |
| E-SEC-29 | 质地按分量档达到 devices 的质地下限（E-DEV-40，核心/常规/背景各自的规格以那里为准）；背景节同时守 chapter 的单节上限（E-CHAP-09）；没有为凑质地硬配的块 | script: verify_book.py#texture_floor · #weight_budget | §方法 2 节奏 · §判断准则 |
| E-SEC-31 | 篇幅落在按负载的参考区间（轻 150-300 / 中 300-500 / 重 500-800 / 合并对比 ≤1000 字），越界时有差距上的理由 | script: verify_book.py#length_band（越界 WARN，不 FAIL） | §理论 6 · §判断准则 |
| E-SEC-33 | 每节最后一块是 ✅ 目标行：一行、长度守 spine 解锁格阈值（E-SPINE-11，≤40 字）、可检验动词（会算/能判断/能写出/能推出/能说出为什么）、不含"理解/熟悉/掌握"；带公式的节写"给{输入}能算{输出}"不复述公式；背景节也有、更轻；MD 里一律保留 | script: verify_book.py#goal_line（存在、位于末块、长度、动词白名单、禁词） | §方法 1 · §方法 4 |
| E-SEC-41 | 后文第一次用到某前置（反查 requires 得到的最早材料使用者所在节）时，正文有一处 `§X.Y` 回指到该前置节 | script: verify_book.py#prereq_backref | PARADIGM §方法 2 入口（前置回指） |
| E-SEC-42 | 前置节不往后引用：正文不出现比本节靠后的节号 / 章号、比本节晚出场的材料节点名称（中英）、本书只在后文材料节才出现的希腊字母符号、指向材料页的脚注 | script: verify_book.py#prereq_no_forward | variants/prereq.md V-PRE-19 |
| E-SEC-43 | 前置节形状：节首 📍「前置 · 约 N 分钟 · 够用线：…」、🔑 一句念头、正文至少一处「够用线」、正文 ≤40 行、不含 ☕ 🎓 🤔 🔍 ⚔️ 块 | script: verify_book.py#prereq_shape | variants/prereq.md「前置节长这样」、V-PRE-09/12/13/20 |
