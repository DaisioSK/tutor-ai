# ingest — 范式

## 一句话

把材料堆变成一个**可寻址的原文空间**（citable address space）：任何下游论断都能落到 `<短名> p<N>` 这样一个读者翻得到的地址，地址背后是逐字保真的文本、原图或经过留痕的视觉描述。只搬运，不解读——唯一例外是讲者脉络（理论 6），它单独成文件。

## 理论

**1. 产物是地址，不是文本。** 下游（tree 抽节点、compose 写节、audit 对账）真正依赖的是"这句话出自哪里"。地址要稳定（重跑、整理目录都不变）、可翻（物理页码 physical page；幻灯片页脚编号会因隐藏页错位）、统一（全书一种格式）。stem、短名（short name）、页分隔符任一不一致，图片路径与出处就成片断裂。

**2. raw 是可重生成的派生物（derived, regenerable）。** 脚本产物随时会被重跑覆盖，所以 LLM 的判断（视觉描述、短名、豁免、角色）写进独立文件或 manifest / `_figures.json` 的独立字段（重跑后重新合并），不写进脚本产物。往 `*.txt` 追加会被下次提取冲掉，还让文件与 manifest 失配、误判重提取。

**3. 文本层是有损的（lossy text layer）。** 架构图只剩零星标签，推导坍缩成单字符碎片，扫描版几乎为空。所以有三条并行保真通道：逐页文本、图重页整页截图 + 视觉描述、裁出的独立原图（供正文直接嵌入，原图优先于自绘）。视觉描述有成本，按教学价值取舍，但取舍必须留痕。

**4. 没进管线的东西必须可审计（absence must be visible）。** 静默丢失最危险：漏扫子目录、跳过一本书、四百张截图没人看，都不报错。所以每个不提取的文件进 `skipped` 写原因，每个图重页有"描述 / 跳过 + 理由"一行，`_figures.json` 缺席本身就是失败。

**5. 范围由用户声明，材料有等级。** 范围是"给定的全部"，纳入哪些目录是声明出来的，不是硬编码跳过。带 solution 的练习题是老师亲手写的题型样本与口径，最高价值的一等材料；往年考题同属一等；课件是主干；作业可纳入；参考书只登记不提取（几百页的书不是课件）；代码由 LLM 直接读；旧 tutor 产物只是素材库。每份材料各有短名，页码命名空间互不污染。

**6. 讲者的组织方式也是材料（the lecturer's flow is material）。** 关键词、定义、公式人人能讲；一门课独有的是主讲人怎样把它组织起来：用什么问题开场、为什么从 A 转到 B、哪个例子承担哪一步、老师的直觉说法、哪里埋伏笔。它散在路标页、过渡页（"Why …?""Limitation""Fallacy""But:"）和例子页里，不抽出来就会被下游的"按依赖重排"和"另造例子"冲掉。它是 ingest 里唯一的解读产物，所以单独成文件（T1b），不混进 raw，并且逐步评价老师哪里讲得好、哪里跳步——下游默认沿用、按评价有理由地改进，而不是照抄或推翻。

## 方法

### 0. 入口与环境

无参数 → 列出 `courses/` 下所有课程。`courses/<课>/` 不存在 → 提示创建并放入课件，停。定位 Python：`which python3 || which python` → Windows 安装目录 → miniconda → pyenv；都找不到 → 提示安装 Python 3.8+。Windows 用户建议经 WSL 跑 python3；以下命令都在仓库根目录下执行。脚本会自动 `pip install` 缺失的 pymupdf / python-docx / python-pptx，失败只告警；Windows 下 stdout 强制 UTF-8。

**幂等（idempotence）**：先看 `output/<课>/full-learn/raw/_manifest.json`——存在且文件清单与源目录一致（同一批文件、大小/修改时间未变），跳过提取，只补缺失产物（如 `_figures.json`）。新课件到了：重跑 extract（全量，便宜），裁图用 `--only` 只补那一讲。

### 1. extract — 文本 + 图重页截图

```bash
python3 .claude/skills/full-learn/scripts/extract.py courses/<课> output/<课>/full-learn/raw
```

传**课程根目录**，不要自己往下指；脚本处理目录约定：有 `lecture/` 就降层以它为根，stem 与平铺时一致（已写正文的图路径不失效）；递归扫描子目录；`references/ reference/ books/ textbooks/` 跳过提取但逐文件登记 `skipped`；`assignment*/ labs/ lab/` 是否纳入由范围声明决定（见判断准则）；隐藏文件与 `:Zone.Identifier` 跳过；`.ipynb .py .java .js .ts .yml .yaml .json .toml` 登记为"LLM 直接 Read"；其他扩展名登记 `skipped` 并写原因；无可提取文件 → WARN 并 0 退出。单文件异常不中断全局，记 `status=error`，有警告记 `warn`。

支持 PDF / DOCX / PPTX / MD / TXT。PDF 逐页写入，分隔符 `--- Page N ---`，N 为物理页码；课件总页数 = 该分隔行的计数。PyMuPDF 不可用时回退 pdftotext → pdfminer → `[ERROR]` 文本，并报告具体是哪个文件全部失败；回退产物无页分隔、无截图，manifest 标 `warn`（这份材料暂时无法按页引用）。≥3 页且平均每页 <20 字符 → 疑似扫描版，warn"文本不可信，需 OCR 或依赖截图"。

**图重页判据（visual-heavy page）**：先剔除模板行（≥6 页的文档里在 ≥50% 页面出现的行 + 纯页码行），然后①正文 <300 字符且含位图或 ≥5 条矢量路径；或②公式坍缩：正文行 ≥8 且 ≤2 字符的碎片行占比 ≥40%（数学推导页必须看图）。命中的页按 2× 渲染整页到 `visuals/<stem>_p<N>.png`，记入 `_visual_pages.json`（file / page / source / 前 200 字 / 判定原因），它是 describe 的输入索引。

非分页材料要有可引用的定位单元：PPTX 一张 slide = 一页（分隔符与 PDF 统一；有图且文字 <300 的 slide 只标图重、无截图）；能用 LibreOffice 时 DOCX/PPTX 先转 PDF 再走 PDF 路径，得到物理页、截图与原图。否则 DOCX / MD / TXT 按标题切成节，定位写 `§<N>`，在 manifest 声明该材料的定位单元。

### 2. figures — 裁原图

```bash
python3 .claude/skills/full-learn/scripts/extract_figures.py courses/<课> output/<课>/full-learn/raw [--only <子串>] [--dpi 220]
```

分工：extract 管文本 + 整页截图；extract_figures 只读 PDF、不改 txt 与 manifest、可随时重跑，把图形区域（位图 / 矢量簇 + 贴边标签）裁成 `figures/<stem>_p<N>_f<k>.png`（k 从上到下、从左到右）并写 `_figures.json`（每条记 source / page / index / kind / bbox / page_ratio / text_inside / looks_like_table）。只从 PDF 裁。两个脚本的目录约定与 stem 规则必须一致（stem 统一 slugify 为 `[A-Za-z0-9_-]`，防空格断开 Markdown 图片路径）。

核心张力：**宁漏不脏，宁漏脏字不盖图**。判据速览：模板元素（≥6 页时同位置 4pt 量化、≥50% 页重复）剔除；位图 <0.2% 页面忽略；矢量路径占页 >90% 或宽/高 >70% 页（背景、分隔线、装饰框）剔除；间距 ≤14pt 的路径迭代聚为一张图；无位图的矢量簇至少 3 条路径；区域 <3% 页面不算图（logo、图标）。标签吸附：≤10pt 内的文字块并入，最多 3 轮，>12% 页面的文字块（正文/标题）不并；宽块（>30% 页宽）须 ≥50% 落在图内，除非形似轴刻度/图下标题；吸附后重叠簇再合并。带边框文字框不是图（无位图、路径 <6、单路径占簇 ≥85%、框内文字 ≥80 字符）。裁框外扩 6pt、截到页内，宽或高 <20pt 丢弃；≥85% 页面标 `fullpage`，否则 `bitmap`/`vector`。涂白邻栏残字、被切断的宽块、页眉页脚模板行，图内窄标签不动；与图自身墨迹相交的部分挖掉，挖后涂白仍 >25% 裁框则整张放弃；无 PIL 跳过涂白。默认 220 dpi。`--only` 增量重跑保留其余文件旧记录、先删该 stem 旧图；结果按 source/page/index 排序写回，并打印每文件图数与疑似表格数（矢量路径多且框内文字密度高的区域标 `looks_like_table`，提示下游改抄成 Markdown 表而不是贴图）。

ingest 不消费原图，只保证 `_figures.json` 存在且新鲜；compose 只读它。

### 3. describe — 图重页的视觉描述

遍历 `_visual_pages.json` 逐页决定：已有文本足以说明该页 → 跳过；装饰性（人像、logo、无信息增量的截图）、纯表格（文本层能抽到）、网页截图（URL 已在文本里）→ 跳过；架构图、流程图、对比图、层级/拓扑关系图、数据图表 → Read 其 PNG，一句话写出图意。启发：`vector` 页多为文本可重建的简单示意，跳过率高；`bitmap` 且文本近空的多为必看。

全部写进 `_visual_notes.md`，按源文件分节，**每个图重页一行**：`- pN: [图: 一句话图意]` 或 `- pN: 跳过 — <理由>`。这行就是视觉消费的痕迹，audit 用它对账。不往 `*.txt` 里追加。

### 4. register — 短名、角色、豁免、素材库

跑完脚本后，在 `_manifest.json` 里合并写入登记字段（独立字段，不改脚本写的部分；重跑 extract 后重新合并）：

- **短名**：每个纳入材料一个唯一短名（`L4`、`T3`、`T3-sol`、`Exam2023`、`A1`），记源文件、stem、页数、定位单元（`p` / `§` / 代码的 `cell`·`行`）。全书出处统一为 `<短名> <定位>`，如 `L4 p28`。`_figures.json` 的每条记录经 stem 映射后合并写入 `short` 字段（T1 的原图清单带短名，下游才能按 `L4 p28` 与节 sources 匹配图）。
- **角色（role）**：`lecture` / `practice` / `solution` / `exam` / `assignment` / `code` / `pool`。`practical/ tutorial/ practice` 目录与考题 PDF 一并纳入；练习与 solution 配对，带 solution 的标 `high_value`。
- **代码材料**：课程目录里有 `.ipynb/.py`、`docker-compose`、`Makefile`、`requirements` 等时，它们与课件并行进入范围，由 LLM 直接 Read，登记短名，出处写文件 + cell/行号。
- **作业**：题面原文保真；题面里有图就同样裁出（作业 PDF 也走 extract_figures）；考务信息（截止、评分、荣誉守则）不是知识，不搬。
- **豁免页**：不承载知识的页（封面 / 目录 / 分节 / 路标 / 学习目标 / 总结 / 致谢 / 参考文献 / logo / 重复 / 动画帧）在此登记理由，理由只能取自这张枚举，供覆盖审计扣除。
- **豁免 ≠ 无用**：路标 / 学习目标 / 过渡 / 总结页不进知识点覆盖，但它们是讲者脉络的主要证据，`flow` 必须读到并引用。
- **素材库（reference pool）**：若存在旧 tutor 产物（`output/<课>/teach/`、`drill/` 等），可选登记为 `pool`：compose 写例子与推导时可取用，但必须回到 raw 核对，它不进阅读路径、不作出处。

### 5. flow — 讲者脉络

register 之后、tree 之前跑。按 `templates/lecture-flow.md` 每 2–3 讲派一个 agent 并行，产出 `output/<课程>/lecture-flow/L<N>.md`（T1b）。已存在且课件没变就跳过（tutor scan 可能已经产出）。调度者收回后抽查：每讲随机 3 条引文与数字回原 PDF 核对；"为什么转到这里"一栏不能全是"未给理由"（那说明没读过渡页）。

## 判断准则

- **范围声明 > 目录惯例。** 用户声明的范围包含作业/labs → 纳入并给独立短名；未声明 → 按惯例跳过并登记。页码污染的根源是共用地址空间，独立短名让各材料的物理页码互不干扰，因此"纳入"和"不污染"不冲突。
- **保真 > 美观。** 原图裁不干净就放弃，不涂掉图的墨迹；描述写图意，不臆测图外内容。
- **留痕 > 省事。** 可以跳过一个图重页，不可以不留一行。
- **地址稳定 > 文件整洁。** 整理目录前先想 stem 会不会变；会变就让脚本吸收（如 `lecture/` 降层）。
- 新材料类型：问"它能被翻到哪一页/哪一行"，给出定位单元并在 manifest 声明，产物仍符合 T1。

## 反例

- 视觉描述追加进 `*.txt`，下次提取被冲掉、manifest 失配（理论 2）。
- 数百张截图零消费痕迹，无法证明图里的知识进了教学链（理论 4）。
- 课件挪进 `lecture/` 后 stem 变了，正文图片路径全部失效（理论 1）。
- 作业指导书页码混进课件页码，出处翻不到（理论 1、5）。
- 用幻灯片页脚编号做页码，隐藏页让引用整体错位（理论 1）。
- 缺 `_figures.json` 没人发现，下游一路自绘（理论 4）。
- 旧讲义被当成阅读路径或出处（理论 5）。
