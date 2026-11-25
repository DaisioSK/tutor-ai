# render — 验收

本表只列人要做的条目（self / cold-read / 脚本未实现）；纯脚本检查在同目录 `GATES.md`，写作时不必读。

源码排版检查在 layout_check（`verify_teach.py --layout-only`），成品检查在 `verify_pdf.py`，编译期门与生成在 `compile_story_pdf.py`；检查名以 audit PARADIGM「脚本注册表」为准。版面常量（≤4 列、长串 ≤36 字符、代码行 ≤70 单位、章短名 ≤8 字、节标题 ≤12 字）只在本模块定义，别的模块引用。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-RENDER-02 | 产物是 `output/<课>/full-learn/book.pdf`（A5），由 `book/` 原地编出，封面课程名不是 "full-learn" | script: compile_story_pdf.py#output_path（默认输出路径与课程名取 `book_dir.parent.parent.name`）；self: `ls` 路径 + 看第 1 页 | 方法 1 |
| E-RENDER-03 | 环境探测：按 `python3`→`python`→常见路径找解释器；缺依赖时打印含 markdown/weasyprint/pymdown-extensions 的 pip 命令 | self: 在 WSL 跑 `python3 -c "import markdown, weasyprint, pymdownx"`，失败时核对提示文案 | 方法 0 |
| E-RENDER-04 | 文件顺序为 00-front → NN 按序 → 99-back；`book/` 无 index.md、MD 无手写目录；`--only` 能单章出 PDF；空目录退出、成功打印清单与大小 | script: compile_story_pdf.py#collect（front/NN/back 顺序）；self: 对照 stderr 文件清单 | 方法 1 |
| E-RENDER-05 | 封面文案只有课程名与书名，不含"故事链""KP""作业预备""考试"等别的产品用语 | self: 读 PDF 第 1 页逐词核对 | 方法 1 |
| E-RENDER-06 | 封面后第二页是自动生成的可点目录，含书首 / 每章 / 每节 / 书尾，随机点 5 条均跳到对应位置 | self: 点目录 5 条（首、中、尾章各至少 1）；script: verify_pdf.py#links（目录 href 全部有对应 id） | 方法 1 · 方法 3 |
| E-RENDER-07 | 书首有章表（章 / 解锁能力 / 阅读时间 / 最重节），行数 = 章数且数据与 spine、tree 一致 | self: 数行数并抽 2 章对照 spine.md 与 tree.json 分量 | 方法 1 |
| E-RENDER-08 | 书首目录之后有科技树图，由 tree.json 离线生成、着色类与 tree.md 一致，编译全程不联网 | script: compile_story_pdf.py#tree_figure（离线分层出图，断网编译一次）；self: 看该页 | 方法 3 |
| E-RENDER-10 | 每页页眉显示"第N章 短名 · <大概念> · §N.M 中文"（大概念取本章骨架里该节所在的 subgraph；无骨架时为"第N章 短名 · §N.M 中文"），与所在节一致，无英文副标题；超长只截大概念，章名与节名不截 | self: 抽 3 页（不同章）读页眉对照该页节标题 | 方法 3 |
| E-RENDER-11 | 章短名 ≤ 8 字、节中文标题 ≤ 12 字，超出 WARN | script(todo): verify_teach.py#layout(header_len) | 理论 1 · 方法 3 |
| E-RENDER-12 | 章首骨架图（`%% skeleton`）与书首全书/卷骨架图离线画成 PNG：大概念为圆角框、框顶概念名、框内子题与节/章（core 强调 + ★），概念间箭头标「关系词：短语」，框不重叠、标签不压字、中文不乱码、字号 ≥ 8.5pt；图下说明按章/卷/全书区分；无 matplotlib 时退化为卡片。旧格式章首地图（§ 开头标签）仍渲成分段卡片 + 按分量上色的 § 胶囊 | self: 看一章章首页与书首骨架页（skeleton_figure.py 可单独出图调试） | 方法 3 |
| E-RENDER-13 | PDF 文本层中不出现 `[^`、`<!--`、成段删除线；`<s>` 等记号成行内代码；相邻引用块各自着色；引用块内列表不塌；并列的输入/输出行在 MD 中是列表项 | script: verify_pdf.py#text_residue（PDF 文本中 `[^` 与 `<!--` 计数为 0）；self: 抽查 1 处相邻 callout | 方法 2 |
| E-RENDER-14 | 每个引用块首标记都属于已知块类型并带固定视觉签名与顶部标签；标签无考试口径；📌 为蓝色速查样式 | script(todo): verify_teach.py#layout(block_marker)（与 verify_book.py#block_vocab 读同一份角色表）列出未知/拼错的标记；self: 看 1 页含多块的页 | 方法 4 |
| E-RENDER-15 | ✅ 目标块默认印成一行小字、无 chip；加 `--no-goals` 时不印且 MD 未改动 | self: 两种开关各编 1 章比对 | 方法 4 |
| E-RENDER-16 | 独占一段的图都成 figure：alt 含 `课件 <短名> p<N>` 的挂"课件原图" chip，"自绘"开头的挂灰 chip；图不跨页 | script: verify_pdf.py#figure_chips（PDF 大图数 = MD 图引用 + 科技树；"课件原图"/"自绘" chip 数 = 对应 alt 数）；self: 看 2 张图 | 方法 4 |
| E-RENDER-21 | 行内公式渲染宽度不超过正文宽（超长改 display 或允许折行） | script(todo): verify_teach.py#layout(inline_math_len) | 理论 1 · 方法 7 |
| E-RENDER-24 | 任何表 ≤ 4 列；单元格无 > 36 字符无空格 token（WARN） | script(todo): verify_teach.py#layout(table_cols)；script: verify_teach.py#layout(long_token) | 理论 1 |
| E-RENDER-27 | 字体分配正确：中文由 CourseCJK 排，数字与拉丁字母不落在 emoji 字族；emoji 字族带 unicode-range；无 CJK 字体时有告警与安装提示 | script: verify_pdf.py#font_assignment；self: 看 1 页含 `CS1234` 类编号的页 | 方法 5 |
| E-RENDER-28 | 版式参数：A5、边距 16/12mm、页脚"页码 / 总页数"；每章新起一页；h1/h2 样式到位且不孤悬页底；正文 ≥ 9pt、代码与图注 ≥ 7pt | self: 读 build_css 核对数值 + 看 1 个章首页与 1 个节首页 | 方法 6 |
| E-RENDER-29 | 长表可跨页、单行不劈开、续页重复表头，标题不被孤留上一页 | self: 找全书最长的表看跨页处 | 方法 6 |
| E-RENDER-30 | 为压页数做的改动只在 CSS；压缩前后 `book/*.md` 无 diff，先调间距后调字号 | self: `git diff --stat book/` 为空 + 列出调了哪些 CSS 量 | 判断准则 |
| E-RENDER-31 | 打开 PDF 抽查：无整页只剩标题、无一字一行的表、A5 上看得清每张裁图（看不清的已抄成 markdown 表）、原图标签未被裁掉 | self: Read 渲染页，每章至少看章首页 + 含表页 + 含图页，逐项打勾 | 方法 8 |
| E-RENDER-33 | PDF 尾部有自动生成的术语索引，每条跳到对应节 | script: compile_story_pdf.py#term_index（从 tree.json 生成）；self: 点 3 条 | 方法 1 |
| E-RENDER-34 | `layout_check` 能对 `book/` 下全部章批量跑、逐章汇总、只查排版 | script(todo): verify_teach.py#layout(batch)（接受 book/ 目录、逐章汇总） | 方法 7 |
| E-RENDER-35 | 交付消息含章数、总阅读时间、页数、PDF 路径与大小、audit 结论 | self: 对照交付消息逐项勾 | 方法 9 |
