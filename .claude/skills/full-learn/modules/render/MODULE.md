# render — 出 PDF

## 职责
把 book/*.md 编成 A5 手机可读 PDF：公式、原图、mermaid、可点目录、页眉面包屑；排版门禁。

## 继承 / 覆写
继承 core。

## 输入
T4 `book/*.md` · T2（科技树图）

## 输出
T6 `book.pdf`

## 依赖
`scripts/compile_story_pdf.py` · `scripts/latex_to_html.py` · `scripts/tree_figure.py` · `scripts/block_roles.py` · `scripts/verify_pdf.py`

## 公开方法
1. `compile` — 编译
2. `layout_check` — 排版门禁（代码块行宽、表格宽度、公式可渲染、框线对齐）
