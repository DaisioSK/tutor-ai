# ingest — 验收

`verify_ingest.py`（脚本名以 audit PARADIGM「脚本注册表」为准）尚未实现，下表 `script(todo)` 项即其待实现检查名；实现前由作者按括号里的动作手工执行。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-INGEST-01 | 无参数时列出 `courses/` 下全部课程；课程目录不存在时提示创建并放入课件后停止；找不到 Python 时提示安装 Python 3.8+；Python 按 `which python3 \|\| which python` → Windows 安装目录 → miniconda → pyenv 定位；缺依赖由脚本自动安装、失败只告警 | self（分别以无参数、不存在的课程名调用一次，核对输出文案；查 extract.py 的 `ensure_dependency` 与 UTF-8 设置仍在） | PARADIGM §方法 0 |
| E-INGEST-02 | 已有 `_manifest.json` 且文件清单与源目录一致时不重新提取，只补缺失产物；新课件到达时裁图用 `--only` 增量补 | script(todo): verify_ingest.py#idempotent（比对 manifest.files + skipped 与源目录 walk 结果的文件集与大小/mtime） | PARADIGM §方法 0 |
| E-INGEST-03 | 用自带 `extract.py` / `extract_figures.py` 提取，两个脚本都传课程根目录，产物落在 `output/<课>/full-learn/raw/`，且 T1 列出的文件（`*.txt`、`visuals/`、`_manifest.json`、`_visual_pages.json`、`_visual_notes.md`）齐全；ingest 只搬运，不产出节点/图谱 | script(todo): verify_ingest.py#layout | PARADIGM §方法 1 |
| E-INGEST-04 | `raw/_figures.json` 与 `raw/figures/` 存在且晚于所有源 PDF 的 mtime；缺席即 FAIL；`_figures.json` 中每条记录指向的 PNG 存在且名为 `<stem>_p<N>_f<k>.png` | script(todo): verify_ingest.py#figures_present | PARADIGM §方法 2 |
| E-INGEST-05 | 所有 `*.txt`（含 PPTX）用统一分隔符 `--- Page N ---`，N 从 1 连续递增、为物理页码；每份 PDF 的分隔行数 = 其物理页数 = manifest 记录的页数 | script(todo): verify_ingest.py#page_separators（用 fitz 读页数对照分隔行计数；grep `--- Slide` 应为 0） | PARADIGM §理论 1 · §方法 1 |
| E-INGEST-06 | 目录约定一致：有 `lecture/` 时以它为根、stem 与平铺一致；递归扫描无子目录漏跑；`extract.py` 与 `extract_figures.py` 对同一文件给出同一 stem（`[A-Za-z0-9_-]`），`figures/` 下每个 stem 都能在 `*.txt` 中找到 | script(todo): verify_ingest.py#stem_consistency | PARADIGM §方法 1 · §方法 2 · 判断准则 |
| E-INGEST-07 | 每个未提取的文件都在 `manifest.skipped` 且带原因：`references/ books/ textbooks/` 逐文件登记；不支持扩展名写明扩展名；隐藏文件与 `Zone.Identifier` 不出现在 files 中 | script(todo): verify_ingest.py#skipped_registered（源目录 walk 的每个非隐藏文件 ∈ files ∪ skipped） | PARADIGM §理论 4 · §方法 1 |
| E-INGEST-08 | 作业 / labs 目录的处理与用户声明的范围一致：纳入则每份以独立短名登记、页码只在自己的短名下计；不纳入则整目录登记 skipped；纳入的题面原文保真、题面图已裁出，考务信息未搬入 | self（对照用户范围声明逐目录检查 manifest；抽一份作业核对其短名与页码不与课件共用、`_figures.json` 含其图） | PARADIGM §判断准则 · §方法 4 |
| E-INGEST-09 | `practical/ tutorial/ practice` 中的练习与 solution、考题 PDF 均已提取并登记，role 正确，练习与 solution 配对，带 solution 的练习标 `high_value` | script(todo): verify_ingest.py#roles（目录名或文件名含 practice/tutorial/practical/solution/exam 的文件 role 非空） | PARADIGM §方法 4 |
| E-INGEST-10 | manifest 中每个纳入材料有唯一短名、源文件、stem、页数与定位单元；无页概念的 DOCX/MD/TXT 声明了 `§` 等定位单元；`_figures.json` 每条带 `short` 字段，且等于其 stem 在 manifest 中对应的短名 | script(todo): verify_ingest.py#registry | PARADIGM §方法 4 · §方法 1 |
| E-INGEST-11 | 图重页按去模板后 <300 字符且有位图/≥5 矢量路径、或公式坍缩（正文行 ≥8 且 ≤2 字符碎片 ≥40%）判定；`_visual_pages.json` 每条有 file/page/source/前 200 字/原因，且（PDF 的）截图 PNG 存在 | script(todo): verify_ingest.py#visual_index | PARADIGM §方法 1 |
| E-INGEST-12 | `_visual_pages.json` 的每个页在 `_visual_notes.md` 中恰有一行，格式为 `- pN: [图: …]` 或 `- pN: 跳过 — <理由>`，按源文件分节；`*.txt` 中不含 `[图:` 字样 | script(todo): verify_ingest.py#visual_trace | PARADIGM §方法 3 · §理论 2 |
| E-INGEST-13 | 视觉描述的取舍正确：文本近空且来自正课的架构/流程/对比/层级图都有一句话图意；装饰图、纯表格、网页截图、文本已说清的页标为跳过 | self（随机抽 10 个跳过行和 10 个描述行，Read 对应 PNG 核对取舍与图意是否准确） | PARADIGM §方法 3 |
| E-INGEST-14 | 提取失败与降级可见：全部回退失败的文件在输出中点名；疑似扫描版有 warn；回退产物（无页分隔）在 manifest 标 warn；单文件异常不中断全局；无可提取文件时 WARN 退出 0 | self（读 manifest 中 status≠ok 的条目，逐条确认原因已报告给用户；grep txt 中的 `[ERROR]`） | PARADIGM §方法 1 |
| E-INGEST-15 | 裁图质量：抽查的图不含 logo/小图标（<3% 页面）、不含单条分隔线、不把带边框文字框当图、涂白没有盖住图本身墨迹 | self（每份 PDF 随机打开 5 张 `figures/*.png` 逐条核对四项；发现问题记录文件名回到 extract_figures 阈值） | PARADIGM §方法 2 |
| E-INGEST-16 | 课程目录中的代码与配置文件（.ipynb/.py/docker-compose/Makefile/requirements 等）在 skipped 中标为"LLM 直接 Read"，并在 manifest 以 role=code 登记短名，出处单元为 cell/行号 | script(todo): verify_ingest.py#code_registered | PARADIGM §方法 4 |
| E-INGEST-17 | 每个豁免页都有理由，理由属于枚举（封面/目录/分节/路标/学习目标/总结/致谢/参考文献/logo/重复/动画帧） | script(todo): verify_ingest.py#exempt_reasons | PARADIGM §方法 4 |
| E-INGEST-18 | 若登记了旧产物素材库，它们 role=pool，不作为任何材料的出处短名、不出现在 T1 的出处格式中 | self（grep manifest 中 role=pool 的条目，确认其短名未被 `_figures.json` / 豁免表 / 下游 sources 引用） | PARADIGM §方法 4 · §判断准则 |
