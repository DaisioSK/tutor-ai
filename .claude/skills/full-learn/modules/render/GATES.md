# render — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-RENDER-01 | 编译前，每章最新 audit 内容门禁与 `layout_check` 均无 FAIL；有 FAIL 时没有生成或覆盖 `book.pdf` | script: compile_story_pdf.py#gate（编前调用 layout_check + 读 audit/ 结论，任一 FAIL 拒编） | 理论 3 · 方法 0 |
| E-RENDER-09 | 正文中的 `第 N 章`、`§N.M`、节点 id 与 MD 文件链接全部变成可跳转链接且目标存在；pre/code/a/标题/属性内不替换；标题自身 § 不成链接；锚点 `ch-N`/`sec-N-M` 无重复 | script: verify_pdf.py#links（href→id 未命中数与重复 id 须为 0） | 方法 3 |
| E-RENDER-17 | 全书没有转换器不认识的 LaTeX 命令或环境（含 `\sqrt[n]`、array 列格式等已知静默缺口），FAIL 时列出命令名 | script: verify_teach.py#layout(unsupported_latex) | 理论 2 · 方法 2 |
| E-RENDER-18 | 转换后代码块外无残留 `$$`、`\(`、`\[` 或像公式的 `$…$`，FAIL 给行号（`\[…\]` 不被转换，写作侧禁用） | script: verify_teach.py#layout(leftover_math) | 方法 2 |
| E-RENDER-19 | 表格行先模拟数学转换再数竖线，列数不增加（条件概率用 `\mid`） | script: verify_teach.py#layout(table_pipe) | 方法 2 |
| E-RENDER-20 | 门禁通过时打印"数学: display N 块 · 行内 M 处"回执 | script: verify_teach.py#layout(math_receipt) | 方法 7 |
| E-RENDER-22 | 代码块每行渲染宽度 ≤ 70 等宽单位（CJK 按 1.661） | script: verify_teach.py#layout(pre_width) | 理论 1 |
| E-RENDER-23 | ``` 围栏数为偶数 | script: verify_teach.py#layout(fences) | 方法 7 |
| E-RENDER-25 | ASCII 图右边框对齐：连续框线行渲染宽差 ≤ 0.5 或边框前无 CJK | script: verify_teach.py#layout(ragged_border) | 方法 7 |
| E-RENDER-26 | PDF 中没有任何文字 span 的 x1 > 页宽 − 8pt | script: verify_pdf.py#overflow | 方法 7 |
| E-RENDER-32 | 全部 MD 写完已编过 PDF，且 PDF 修改时间 ≥ `book/*.md` 最新修改时间 | script: verify_pdf.py#fresh（PDF mtime ≥ book/*.md 最新 mtime） | 方法 1 |
