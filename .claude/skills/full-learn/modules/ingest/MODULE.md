# ingest — 采集

## 职责
把材料堆变成逐页可引用的原文、原图与视觉描述，供下游引用和嵌入；另外抽出每讲的讲者脉络（唯一一份解读产物，单独成文件）。

## 继承 / 覆写
继承 core。覆写：无。

## 输入
`courses/<课程名>/`（PDF / DOCX / PPTX / MD / TXT；`references/` 等参考书目录跳过提取但登记）

## 输出
T1 `raw/`、T1b `lecture-flow/`（见 CONTRACTS）

## 依赖
`scripts/extract.py` · `scripts/extract_figures.py`

## 公开方法
1. `extract` — 文本 + 图重页截图
2. `figures` — 裁原图
3. `describe` — 给图重页写视觉描述（文本层抓不到的图意）
4. `register` — 登记材料短名，供全书统一出处格式
5. `flow` — 每讲一份讲者脉络（`templates/lecture-flow.md`，2–3 讲派一个 agent 并行）

## 扩展点
新材料类型（视频字幕、网页）→ 加提取器，产物仍须符合 T1。
