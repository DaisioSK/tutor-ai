# compose/book — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-BOOK-01 | 产物在 `output/<课程>/full-learn/book/`，恰有 `00-front.md`、`99-back.md` 与每章一个 `NN-<slug>.md`（两位编号、英文 slug、编号与 spine 章号一一对应）；不存在按讲或按知识点拆的文件；分卷时每卷各有书首书尾 | script: verify_book.py#files | 理论 1；方法 3 格式统一 |
| E-BOOK-04 | 书首有终极理解专属块，内容与 `tree.json` 的 apex.statement 一致；书尾再次出现并回收 | script: verify_book.py#apex_front_back | 理论 2；方法 1 终极理解；方法 4 |
| E-BOOK-08 | 书首列出全部 generators，每个标注展开章节，且所标章节确实含 derives_from 指向它的节点 | script: verify_book.py#generator_chapters | 理论 2；方法 1 生成元 |
| E-BOOK-09 | 书首目录每章恰一行，含解锁能力 / 回答的问题 / 覆盖材料三项，且与实际章文件和 spine 一致 | script: verify_book.py#toc_matches | 方法 1 目录 |
| E-BOOK-10 | 读法只在书首出现一次：写明从第一章顺读、本书自足、三条路径各自读哪些块（块名用 devices 词汇表）与耗时、哪些块可跳；路径说明不用内部代号（写"每节开头的问题"而非"入口问题"）；任何章文件不含读法指南，也不含发散参数等全书配置（只在书首声明一次）；🎯 的用法说明仅在 reader.md 声明考试时出现，且不标频次 | script: verify_book.py#reading_guide_once | 理论 4；方法 1 读法 |
| E-BOOK-11 | 书首具备定位 / 前置 / 大图 / 生成元四要素（材料仅一讲时可压缩为一小节，但定位、前置、生成元仍在） | script: verify_book.py#front_elements | 方法 1 |
| E-BOOK-12 | 书首篇幅短于各章篇幅中位数 | script: verify_book.py#front_length | 方法 1 压缩 |
| E-BOOK-13 | 书首或书尾给全书规模：章数、节数、节点数、各路径阅读时间，数字与实际产物一致；不给"高频节点数"一类重要度统计 | script: verify_book.py#stats | 方法 1 规模 |
| E-BOOK-15 | 全书引用只用 `§N.M` / `第 N 章` / `N-xx` 三种格式；无"第 N 弧""前面第 X 节""KP" 等写法；远距离引用带位置 | script: verify_book.py#xref_format | 方法 3 格式统一 |
| E-BOOK-16 | 每个引用目标真实存在；每个前指的目标节在 spine 中 | script: verify_book.py#xref_targets | 理论 6；方法 3 终检 |
| E-BOOK-22 | 附录"材料 → 本书反查表"由 tree sources 生成：每份材料（含客座讲座）的每个非豁免页都映射到节，一讲可映射到多节；表前一句说明其用途，豁免页给理由 | script: verify_book.py#reverse_index | 理论 3；方法 4 附录 |
| E-BOOK-23 | 附录节点索引覆盖全部节点，四列 id / 名称（中文 · English）/ 所在节 / 出处，出处与 tree sources 一致；合并讲的节点指向同一节 | script: verify_book.py#node_index | 方法 4 附录 |
| E-BOOK-24 | 附录有英文关键词索引，按板块分表，每行 关键词 / 位置 / 一句提示，位置均可跳转 | script: verify_book.py#keyword_index | 方法 4 附录 |
| E-BOOK-25 | 考试附录（考察维度 → 章节：维度 / 题号作出处 / 一句话答案 / 指回节）当且仅当 reader.md 声明考试信息时存在；无占比、频次、"高频/必考" | script: verify_book.py#exam_appendix | 方法 4 附录；判断准则 |
| E-BOOK-26 | 审计类表格只在书尾附录，且每张守 render 列数上限（≤4 列） | script: verify_book.py#appendix_narrow | 理论 3 |
| E-BOOK-32 | 除整本 book.pdf 外，每卷一册 book-vol<K>.pdf（该卷各章 + 卷串讲）与 book-map.pdf 均已编出 | script: compile_story_pdf.py --volumes | 方法 5、6 |
