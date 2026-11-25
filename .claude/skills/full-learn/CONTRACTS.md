# CONTRACTS — 模块间产物的类型定义

模块之间只通过这里定义的产物交流。改 schema = 改接口，必须同时检查所有消费方。

---

## T0 `reader.md` — core 产出（流水线开始时推断一次，⏸1 时随脊柱交用户确认）

```markdown
# 读者
起点: <读者已经会什么；决定哪些前置算 external>
目的: <学完全范围 / 备考 / 答辩 / 探索 —— 只影响材料外内容的多少，不影响写法>
范围: <课程名 + 覆盖范围>
发散: divergence_layers=<0-3> · divergence_breadth=<1-8> · relevance_threshold=<严格|中等|宽松>
考试信息: <有则写（日期、形式、题型）；无则写"无"。只有这里声明了，考试信号才参与分量旁证与 🎯 块>
偏好: <可选。用户对本课程的呈现偏好，如"原图要全"；由对应模块按其范式执行>
```

---

## T1 `raw/` — ingest 产出

```
raw/
├── <stem>.txt            逐页文本，页分隔符 "--- Page N ---"（物理页码；PPTX 一张 slide = 一页）
├── visuals/<stem>_pN.png 图重页整页截图
├── figures/<stem>_pN_fK.png  裁出的原图
├── _manifest.json        源文件清单 + 材料登记表（见下）+ 跳过的文件及理由
├── _figures.json         原图清单：源文件 / 短名 / 页码 / bbox / 框内文字 / 是否疑似表格
├── _visual_pages.json    图重页索引（describe 的输入）
└── _visual_notes.md      图重页的视觉描述（文本层抓不到的图意），每个图重页一行，跳过也留痕
```

`_manifest.json` 的材料登记表（register 写入；extract 重跑后必须重新合并，不得丢失）：

```jsonc
"materials": [{
  "short": "L4",                    // 唯一短名
  "file": "lectures/L4-MarkovModels.pdf", "stem": "lectures_L4-MarkovModels",
  "pages": 74,
  "locator": "p",                   // p（物理页）| §（按标题切的节）| cell / 行（代码）
  "role": "lecture",                // lecture | practice | solution | exam | assignment | code | pool
  "high_value": false,              // 带 solution 的练习、往年题为 true
  "exempt_pages": [{"page": 1, "reason": "封面"}]
}]
```

**出处引用格式（全 skill 统一）**: `<短名> <定位>`，如 `L4 p28`、`Notes §3`、`A1 cell 12`。短名在 `_manifest.json` 登记。

### T1b `output/<课程>/lecture-flow/L<N>.md` — ingest `flow` 产出（课程级共享）

每讲一份讲者脉络：老师这讲要回答的问题；按"一个新念头一步"切的脉络链，每步写 问题 / 做法 / 为什么转到这里（过渡页原话）/ 例子及其承担的概念 / 老师的直觉说法 / 回指与伏笔 / 评价（好·跳步·缺动机·例子不贴切）；例子清单；跨讲衔接；老师没讲透的地方。格式见 `templates/lecture-flow.md`。放在课程根而不是 `full-learn/` 下：tutor、story-cards 也读它，谁先跑谁产出。

---

## T2 `tree.json` — tree 产出

```jsonc
{
  "scope": "CS1234 L1-L12 + 练习题",           // 范围声明
  "apex": {                                       // 终极理解（科技树的顶）
    "statement": "一句话：学完整个范围，脑中应有的那个模型",
    "unfolds": ["N-xx", "..."]                    // 直接支撑它的节点
  },
  "generators": ["N-01", "..."],                  // 生成元：少数根思想，大量节点是它们的推论
  "nodes": [{
    "id": "N-12",                                 // 稳定 id，全 skill 引用它
    "name": "M/M/1 稳态分布",
    "en": "M/M/1 Steady-State Distribution",
    "kind": "concept|law|formula|method|model|fact|external",   // external = 材料默认你会但没讲的前置
    "one_liner": "一句话说清它是什么",
    "why": "它回答什么问题（没有它会卡在哪）",
    "requires": ["N-08", "N-10"],                 // 理解依赖：不懂这些就看不懂它
    "derives_from": ["N-03"],                     // 可选：它是哪个生成元/节点的推论
    "sources": ["L4 p27-29", "L4 p32-33"],     // 材料里讲它的页；external 前置为空（用到它的页归使用者）
    "weight": 7,                                  // 分量 = 下游传递闭包里的节点数（脚本算）

    // —— 可选字段：下游不依赖也能工作，有则参考 ——
    "labels": ["[M/M/1]"],                        // 材料作者自带的分类/标签，原样保留
    "layer": "What|Why|How|Deep",                 // 代码类材料的收割视角
    "relations": [{"type": "contrast|part_of|implements|pair", "to": "N-13"}],  // 非理解依赖的关系，不进 requires；pair = 互逆/同构的两个前置，同节讲
    "role": "prerequisite|extension",             // 仅 kind=external：前置缺口 / 追问链发散
    "gap": "只补等比级数求和这一截",               // 仅 role=prerequisite：补的是哪一截
    "mental_model": "指数/对数是在加法世界与乘法世界之间换坐标",  // 仅 role=prerequisite（必填）：能推出全部规则的一句结构念头
                                                  // 使用者（used_by）不存字段：反查 requires 得到，只给后端用，不进正文
    "depth": 1,                                   // 仅 role=extension：发散层号，越外越浅
    "signals": ["formula-sheet", "repeated-L3-L4", "exam"],  // 外部重要度旁证，不改分量与顺序，不入书
    "group": "原理|模型|方法|工具|基础…",           // 科技树图的角色分组（draw 用），缺省按 kind
    "figures": ["lectures_L4-MarkovModels_p28_f1.png"]  // 承载本节点知识的原图（raw/figures），spine 据此预选原图
  }],
  "coverage": {
    "exempt": [{"source": "L4 p1", "reason": "封面"}]          // 不进任何节点的页及理由
  }
}
```

`tree.md` = 人读版：终极理解 + 生成元 + 分层的 mermaid 科技树 + 节点表。

---

## T3 `spine.md` — spine 产出

```markdown
# 脊柱: <范围>
发散参数: layers=<n> · breadth=<n> · threshold=<…>（取自 reader.md，发散节点在表中可见）

## 运行案例
<贯穿全书的一个具体案例，一段话；取自老师的开场例子时注页码>

## 偏离讲者脉络
| 位置 | 老师的顺序（T1b 步 / 页） | 本书的顺序 | 类型（目的后置 / 动机缺失 / 前置倒挂 / 理由偏弱） | 理由 |
|---|---|---|---|---|

## 第 N 章 <标题> — 解锁: <这一章让读者获得的能力>
章入口问题: <读者此刻真实的困惑>

| § | 节点 | 入口问题 | 凭什么现在能懂 | 解锁了什么 | 留下的新问题 |
|---|---|---|---|---|---|
| N.1 | N-08 | ... | N-03, N-05 | ... | ... |

机读列（同章第二张表，按 § 对齐）:
| § | 分量 | 负载 | sources | 预选原图 |
|---|---|---|---|---|
| N.1 | 7 | 重 | L4 p27-29 | lectures_L4-MarkovModels_p28_f1.png |
```

分卷时（范围太大），在章之上加卷头，章号全书连续编号：

```markdown
# 第 K 卷 <标题> — 解锁: <这一卷让读者获得的大能力>
卷入口问题: <…>
```

规则：
- "凭什么现在能懂"列只允许出现排在前面的节点 id。
- "解锁了什么"是一行可检验动作（约 40 字内，推理类动词优先）。
- 分量取自 tree weight；负载（轻/中/重）是阅读难度，供 chapter 排节奏，不出现在正文。
- 与 T1b 讲序不同的每一处都在「偏离讲者脉络」表里有一行；表外的顺序默认与讲者脉络一致。

---

## T4 `book/*.md` — compose 产出

- 文件：`00-front.md`（书首）、`NN-<slug>.md`（第 NN 章）、`NNv-<slug>.md`（卷串讲，NN = 该卷最后一章的章号，排在该章之后）、`98-map.md`（总纲卷）、`99-back.md`（书尾）。
- 章标题：`# 第 N 章 <标题>`；卷串讲：`# 第 K 卷串讲：<卷标题>`；总纲卷：`# 总纲：全书归位`。卷串讲与总纲卷的节用不编号的 `## `，不带节注释。
- 节标题：`## §N.M <中文标题> (<English>)`，紧跟一行机读注释：
  `<!-- nodes: N-08, N-09 | sources: L4 p27-29 -->`
- 出处：正文不描述课件；需要指向课件时用脚注 `[^L4p28]`，脚注内容 `L4 p28`。
- 课件原图：`![<图意一句话> · 课件 L4 p28](../raw/figures/<file>.png)`。
- 外部补充（材料之外的内容）用块类型标记（见 compose/devices），删掉后正文仍完整覆盖材料。

---

## T5 `audit/*.md` — audit 产出

每份报告一个模块：

```markdown
# audit: <模块> · <日期>
| EXPECT id | 结果 PASS/FAIL/WARN | 证据（位置 + 摘录） | 修法指向（PARADIGM 哪一段） |
```

冷读者报告 `audit/cold-read-<章>.md`：卡住 / 无聊 / 断裂 三类，每条带位置。

---

## T6 `book.pdf` — render 产出

A5，可点目录，书首含全书骨架图，页眉面包屑（章 · 大概念 · 节）；另出每卷一册 `book-vol<K>.pdf`（该卷各章 + 卷串讲）与 `book-map.pdf`（总纲卷）。节点级科技树不进书。
