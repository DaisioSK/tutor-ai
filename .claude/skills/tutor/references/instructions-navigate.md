# 图谱导航命令: map

---

## map — 生成并展示全课程知识图谱

### 如果 `output/{课程名}/knowledge-graph.md` 不存在:

按 `concepts.json` 手写一张 Mermaid 图（原来的生成脚本是为单门课写死的，开源版未收录）:
- 按**角色分组**（如原理 / 分类 / 架构 / 实战），不按 Lecture
- 用不同线型标注关系: 实线=依赖递进、粗线=实现支撑、虚线=对比并列、点线=组成使用
- 依赖边取 `concepts.json` 里的前置关系，对比 / 组成 / 实现关系只加课件里讲过的
- 产出: `knowledge-graph.mmd` (源码) + `knowledge-graph.md` (嵌 Mermaid 代码块)；需要 PNG 时用任意 Mermaid 渲染器导出为 `knowledge-graph.png`

如果 concepts.json 不存在 → 提示先执行 `scan`

### 如果已存在:

直接展示 `knowledge-graph.md` 的内容。

### 嵌入 PDF:

`compile_story_pdf.py` 会自动检测 `output/{课程名}/knowledge-graph.png`，如果存在就放在**目录页和 Arc 1 之间**。不需要手动操作。

---

## ~~where~~、~~path~~、~~review~~ 已废弃

如果用户喊出这些老命令，告诉他们替代方案:

- `where X` — 用 `teach X`，输出顶部就有"📍 大图定位"（包含模块、依赖、被依赖、下一步建议）
- `path A B` — teach/ 故事链本身就是依赖序列，按 Arc 阅读即可
- `review` — `teach/full-story.pdf` + `teach/index.md`（含 KP 索引）已全面取代
