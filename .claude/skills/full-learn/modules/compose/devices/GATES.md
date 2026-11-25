# compose/devices — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-DEV-02 | 正文不描述载体：不出现"课件/幻灯片/slide/这页/红框/左上角"等描述材料版面的话；页码只出现在节注释与脚注，不进节标题、不替代内容 | script: verify_book.py#slide_narration（关键词 + 标题页码正则） | 理论 5；J 出处 |
| E-DEV-04 | 每个核心节至少一个指向延伸材料（references/、大纲参考书）的深度提示脚注 | script: verify_book.py#depth_hint（核心节无 references 类脚注 → WARN） | J 深度提示 |
| E-DEV-24 | 本章节点 sources 页内有非表格候选原图而本章零嵌图（只计 `../raw/figures/` 链接）→ WARN，需写明理由 | script: verify_book.py#figure_candidates（移植 verify_teach L275-280、L548-553，改为按章、按 sources 页筛，排除 looks_like_table） | D 用哪张 |
| E-DEV-25 | 一节嵌图 ≤3 张 | script: verify_book.py#figures_per_section | D 用哪张 |
| E-DEV-26 | 图格式：独占一行 `![alt](src)` 且文件存在；原图注为 `<图意> · 课件 <短名> p<N>`，自绘图注以 `自绘 · ` 开头 | script: verify_book.py#figure_format（移植 verify_teach L527-537，正则按新格式重写） | D 怎么用 |
| E-DEV-34 | 每章代码块 + 表格字符占比 ≤20%，>30% WARN | script: verify_book.py#heavy_device_ratio（移植 VP-004 逻辑，阈值重标） | F 何时不用 |
| E-DEV-36 | 只使用词汇表中的块标记：emoji 只在 blockquote 首字、拼写与表一致（emoji + 加粗名），写完按块统计核对无拼错；标题无 emoji；无 tip/note/重要 等空标签；🎯 未启用时不出现 | script: verify_book.py#block_vocab（词汇表与 compile 角色表同源配置） | I 词汇表 |
| E-DEV-38 | 🧭 形式：章首为 `> 🧭 本章: {念头} · 约 N 分钟`；节级 🧭 若启用（chapter 决定），为 `> 🧭 本节: {核心\|常规\|背景} · 约 N 分钟 · {读法}`——分量在前、全用文字、不含负载评级、不含课件页 | script: verify_book.py#guide_line | I 🧭 |
| E-DEV-39 | 导读条时长 = 正文字数 ÷ 速率（轻 300 / 中 250 / 重 180 字/分）向上取整 + 每张 ASCII 图或表格 1 分钟，误差 ≤1 分钟 | script: verify_book.py#guide_minutes | I 🧭 |
| E-DEV-41 | 每章 ☕ ≤8%、🎓 ≤15%（按字符）；每章 🎓 至多一个 | script: verify_book.py#aside_budget（移植 verify_teach L517-518，改按章） | I 预算 |
| E-DEV-49 | 🎯 仅在 reader.md 声明考试信息时出现；≤80 字；只讲该知识点的常见问法，无分值、频次、"必考"字样，与 ⚠️ 内容不重复 | script: verify_book.py#exam_block（reader.md 开关 + 字数 + 禁词） | I 🎯；判断准则 6 |
