# assignment ⟨N⟩ — 单个作业的"边做边学"教学故事链

## 这是什么

为**单个 assignment**生成"边做边学"的教学故事链。同时服务:
- **学习**: 学生懂自己写的每一行代码 + 为什么这么写
- **答辩/面试**: 顺着代码讲清楚每个技术决策

跟 `story` (lecture) 命令的根本不同:

| 维度 | `story` (lecture) | `assignment` (本指令) |
|---|---|---|
| **主线** | 概念依赖顺序 (架构 → 组件 → 实例) | **代码 implementation 顺序 (cell 1 → cell N)** |
| **粒度单元** | 知识点 KP | **代码块 / cell / 函数 / 步骤** |
| **教学姿态** | 老师讲故事 | **导师在身后边看你写边讲** |
| **学生终态** | 通用心智模型 | **能看懂自己每行代码 + 能讲清每个决策** |

**关键认知**: 四层写作规范（Layer 0 内容覆盖 → A/B 表达 → C 工艺，见 content-coverage.md / presentation.md / writing-craft.md）**全套保留**, 在此基础上**叠加** 5 个 assignment 专属规则。

---

## 输出位置

```
output/{课程名}/assignment{N}/teach/
├── index.md                       # Cell→Section 映射 + 答辩高频 🎯 + 阅读时间
├── 0-{topic}-fundamentals.md      # (按需) 基础铺垫 Arc 0
├── 1-{step1-name}.md              # Arc 1: 第一组代码块的教学
├── 2-{step2-name}.md              # Arc 2
├── ...
├── {N}-defense.md                 # (强制最后) 答辩 Arc
└── full-story.pdf                 # 编译产出
```

---

## 5 大专属规则 — 在四层写作规范之上叠加

### 规则 1: Cell-to-Section 映射 (index.md 顶部强制)

**index.md 顶部必有一张表**, 让学生写代码卡住时能直接定位:

```markdown
| Notebook Cell | 做什么 | teach 位置 |
|--------------|--------|-----------|
| cell 1-3 | 装库 / 导入 / config | Arc 1 §1 |
| cell 5 | 加载训练数据 | Arc 2 §1 |
| cell 6 | 数据增强 + DataLoader | Arc 2 §2 |
| cell 8 | 模型定义 (UNet 类) | Arc 3 §1-§3 |
| cell 12-14 | 训练循环 | Arc 4 §1 |
| cell 16-18 | 采样 + 可视化 | Arc 5 §1-§2 |
```

为什么强制: 学生写代码到 cell 12 卡住, **直接定位**到 Arc 4 §1, 不用读完全文找。

---

### 规则 2: 代码五问 (5Q for Code) — 主体写作循环 ⭐⭐

**这是 assignment 教学的核心**, 替代 lecture 的"问题 → 类比 → 定义 → 例子"循环。

**核心理念**: 不光告诉读者"做什么", 还要让读者**跟着思路一步步推导**到这个解法 — 像看一个老练的人在白板上推。

**每个核心 §** (= 一个代码块/步骤) **必按 5Q 展开**:

```markdown
## §N: ⟨步骤名⟩

```python
# 原代码 (3-20 行)
df = spark.read.csv("a.csv", header=True, inferSchema=True)
df = df.filter(col("price") > 0).na.drop(subset=["amount"])
```

> **[一行 hook]** — 一句精辟的话, 把这步的重要性勾出来 / 建立跟已学概念的关联。
> 例: "这步看似只是'读个 CSV', 实际是整个 pipeline 数据信号能不能保持的第一道关。"

**做什么** (What — 1-2 句, 纯技术描述)
读 CSV, filter price>0, drop amount=null 的行。

**怎么想到的** (How — 思路链, 3-5 句, 这是 5Q 的灵魂 ⭐)
> 显式呈现"看到问题 → 怎么推导出当前解法"

- 拿到的: 一份原始 CSV, 里面有脏数据 (负价、缺 amount)
- 直觉: 都用上呗 — 但负价是录入错, 算 mean 拉偏; null 在 amount 这种核心特征上整行没意义
- 退一步: 我真正要的是"signal-clean"的训练数据, 不是 "全量数据"
- 落到这: filter 掉负价 + 整行丢掉 amount-null, 简单且不引入虚假信号

**为什么** (Why — 这个选择的非显然好处, 1-2 段)
- 不 imputate 是因为 amount 缺值通常是"该样本就不应该参与训练"的信号
- 整行 drop 比按列 fill 更接近"这个样本数据质量不行"的真实语义

**为什么不别的** (Why-not — 2-3 个具体反例)
- ❌ **不 filter 负价**: 训出的回归被几个异常值带偏
- ❌ **mean 填 amount null**: 引入虚假信号, 模型学错语义
- ❌ **fillna(0)**: 变成"免费", 模型以为"价 0 = 真值"

**Big Picture** (1 段, 挂回 assignment 整体)
这是数据清洗阶段。后续 Arc 3 用这个 df 做 join + 特征工程, 任何脏数据会污染后续所有步骤。**这一步是流水线的基石**。
```

#### 5Q 写作要点

- **Hook**: 一行, 精辟, 给读者一个"为什么我要看这段"的理由
- **What**: 技术中性, 别夹意图
- **How** (灵魂, 通俗): **显式推导**, 让读者跟着想 — 直觉 → 不行的地方 → 退一步看真正需求 → 落到当前解法
- **Why** (深度, 专业): 抓**这个具体选择**的非显然好处。**复杂 § 必拆"细节 1 / 细节 2 / 细节 3"分项**, 每个细节配代码片段或数值具体例子
- **Why-not**: 至少 3-4 个具体方案 + 具体后果 (不是只说"不好")
- **Big Picture**: 必挂回 assignment 整体目标

#### 通俗 vs 专业的比例 — 6:4 原则 ⭐

整段读下来, **大约 60% 内容是通俗** (Hook + How + 类比 + 直觉 + 简单 What), **40% 是专业** (Why 的细节 N 分项 + Why-not 的代码级反例 + 数值 / 边界 / 量化分析)。

- **通俗**目的: 半年后忘了能重新进入。小白也读得下去
- **专业**目的: 答辩 / 工程实战时不空洞, 有"我懂底层"的细节支撑

**不要为了通俗砍专业**, 也不要为了专业堆术语。两者**并存**, 通俗在前引路, 专业在 Why 里给深度。

#### Why 的"细节 N"长什么样 (示例)

```markdown
**为什么** (Why)

**细节 1: `.copy_()` 不是 `=`**
```python
self.k_cache[:, :, start:end, :].copy_(new_k)   # ✅ 原地拷贝
self.k_cache[:, :, start:end, :] = new_k        # ❌ 也对但不优雅
```
两者效果对外一样, 但 `.copy_()` 显式说明"原地写入"。

**细节 2: 检查 overflow 而不是动态扩容**
推理时 max_seq_len 是事先知道的 (e.g. 2048)。如果超过, 是设计错误, raise 让 caller 知道, 不要静默扩容。

**细节 3: 返回视图, 不是拷贝**
`keys = self.k_cache[:b, :, :self.current_seq_len, :]` 这是 view 不是 copy。后续 attention 直接读 view, 不重复占内存。
```

每个"细节 N" 都是: **小标题 + 代码片段或数值 + 1-2 句解释**。这是专业含量的载体。

#### How 跟 Why-not 怎么区分

- **How** = "跟着我推一遍, 从问题到这个解法, 路径上每一步在想什么"
- **Why-not** = "其他人可能想到的别的解法, 列出来 + 一句 reject"

How 是**正向 narrative**, Why-not 是**横向比较**。

#### 何时省略

- 极简 § (e.g. import 库): 只留 What + Big Picture, 其它省
- 重复模式 § (e.g. 第 5 个 join): "跟 §X 同模式" + 只写差异
- **核心 §** (实现一个算法 / 关键设计决策): 5 项都不能省

---

### 规则 3: 两版对照 (DIY vs Production) — 核心 § 末尾的 📎 ⭐

Assignment 通常是**简化教学版**, 业界用的是**工程成熟版**。**学生写完后必须知道两者差异**, 否则面试被问"你这跟 vLLM 怎么对比" 会当场卡住。

每个**核心** § (不是每个) 末尾必有:

```markdown
> 📎 **DIY vs Production 对照**
>
> 你写的这版 (assignment): [一句话描述]
> - **简化在哪**: [2-3 点]
> - **工程缺什么**: [2-3 点 — thread safety / batching / 边界处理 / 数值稳定]
>
> 业界版本 (Production): **⟨工具/库名⟩** (详见 [Arc N §M](../teach/N-xxx.md#sec-m) 或 [外部 ref])
> - 真实场景就用这个
> - 改进点: [2-3 点]
>
> **教学价值**: [为什么 DIY 仍值得做 — 通常是"懂思想 / 懂底层 / 懂权衡"]
```

#### 哪些 § 必加 DIY vs Production

- 实现了一个**经典算法** (LoRA / Attention / Diffusion / KV Cache)
- 实现了一个**简化版库**功能 (用 numpy 实现 PyTorch 的 conv)
- 走了一个**工程 shortcut** (单 batch / 单 head / 假设 mask)

#### 哪些 § 不需要

- 纯数据 IO / 可视化
- 用了别人的成熟库的标准调用 (e.g. `pandas.read_csv`)

---

### 规则 4: 答辩 Arc (强制最后一章) ⭐

最后一个 Arc 必为 `{N}-defense.md`:

```markdown
# Arc N: 答辩篇 — 面试官会问什么

## §1 8-12 个典型问题 + 回答模板

### Q1: ⟨问题原文⟩
**核心答** (一句话):
[最简版本]

**展开** (3-4 个支撑点):
- 点 1: ...
- 点 2: ...
- 点 3: ...

**避雷** (常见错误回答):
- ❌ 别说 "[X]" — 听起来 [Y, 不严谨/外行]
- ❌ 别说 "我没想过" — 该说 "我没深究, 但方向是 [Z]"

---

### Q2: ⟨问题⟩
...

---

(共 8-12 题, 覆盖: 任务背景 / 数据决策 / 模型选择 / 训练优化 / 评估方法 / 工程权衡 / 局限性 / 业界对比)

## §2 答辩高频 🎯 知识点速查
[只列在前面 Arcs 里被标 🎯 的, 速查表]

## §3 时间分配建议 (5 min 自介)
- 60s 任务背景 + 数据
- 90s 主要技术决策 (3-5 个)
- 90s 结果 + 关键洞察
- 60s 局限 + 改进方向

## §4 心态 + 应对
- 不知道怎么办: "我没深究, 但方向是 X" 比 "不知道" 高级
- 被纠错怎么办: 接受 + 重新组织答案, 不要硬扛
```

#### 8-12 题的来源

1. **从 4-5 个 4Q 的 Why-not** 凝练 — "你为什么不用 Y" 必被问
2. **从 DIY vs Production 对照** 凝练 — "你这跟业界差在哪"
3. **从 lecture 的高频考点** 关联 — 已学过的概念在你 assignment 里怎么落地

---

### 规则 5: 基础铺垫 Arc 0 (按需)

跟 lecture Arc 0 (序章) **角色不同**:

| | Lecture Arc 0 | Assignment Arc 0 |
|---|---|---|
| **目标** | 课程全局大图 + 暗线 | **本作业用到的核心技术铺垫** |
| **何时写** | 强制 (每门课都要) | **按需** — 学生不熟悉技术才写 |
| **示例** | "这门课是 LLM 时代实践技术栈讲解器" | "Spark 基础给从未用过 Spark 的人" |

#### 判断要不要写 Arc 0

```
**问 1**: assignment 用到的核心技术 lecture 讲过吗?
- 是 → 不需要 Arc 0
- 否 → 继续

**问 2**: 是不是初学者就能直接上手?
- 是 → 不需要 Arc 0  
- 否 → 写 Arc 0

**问 3**: lecture 讲了概念, 但 implementation 细节没讲?
- 是 → 写 Arc 0 但只覆盖"实现细节铺垫" (不是从零讲概念)
```

#### Arc 0 的内容范围

- 本 assignment **直接需要**的概念/工具
- 不要扩到整门课的全部相关内容
- 长度: 通常 200-400 行 (比正常 Arc 短)

---

## Phase 工作流

### Phase 0: 读材料 + 主线规划

**Step 0.1 — 读取必备**:
1. **Notebook (.ipynb)** — 最重要 source, 看 cells + 输出
2. **Report (.pdf / .odt)** — 学生已写的解释 (重要！揭示意图)
3. **Assignment guide** — 题目要求 / scoring rubric
4. **关联 lecture** — assignment X 通常对应某个 lecture (e.g. Assignment 2 = Lecture 3)
5. **关联 teach/Arc** — 如果 lecture story 已写, 链接它

**Step 0.2 — 主线规划**:
1. 把 notebook 切成 **"代码组"** (logical groups), 每组 = 一个 Arc
   - 例: setup / data prep / model definition / training / evaluation / visualization
2. **Arc 0 判断** (是否需要基础铺垫)
3. **答辩 Arc 总是最后**
4. 输出 Arc 计划给用户确认 (在生成正文前)

### Phase 1: 逐 Arc 生成

**对每个 Arc**:

1. **抽取相关 cell 代码** (从 notebook)
2. **决定 § 切分**: 一个代码块 (3-20 行) = 一个 §
3. **每个 § 用 4Q 展开** (规则 2)
4. **核心 § 末尾加 DIY vs Production** (规则 3)
5. 四层写作规范全套适用（含课件对照表 / 🧭 导读条 / ☕ 换气节奏 / 🎓 师门心法）:
   - 概念分层
   - 核心角色锚点 (每 Arc 顶部一个)
   - 网状层级结构 (一个 Arc 内组件多时画图)
   - 数学公式思路优先
   - 痛点-方案-效果 (改进类时用)
   - 对照式发散 (跟 4Q 的 Why-not 配合)
   - 插件式补充 📎 (可加可不加)

### Phase 2: 答辩 Arc 生成

最后一个 Arc 用规则 4 模板:
- 8-12 题
- 每题 4 段 (核心答 / 展开 / 避雷 / 偶尔加示范)
- 速查表
- 时间分配 + 心态

### Phase 3: index.md 生成

按规则 1 模板生成顶部表 + 知识点索引 + 阅读路径。

### Phase 4: Quality Gate (Self-check)

**四层写作规范自检** (跟 story 一样: 先跑 verify_teach.py, 再过 Phase 2.5 四道门):
- ☐ 每 Arc 有核心角色锚点?
- ☐ 复合概念有结构图?
- ☐ 数学公式先讲思路?
- ☐ 比较语言开盒?
- ☐ 改进类技术用了痛点-方案-效果?
- ☐ 对照发散?
- ☐ 📎 插件式补充?

**5 大专属规则自检**:
- ☐ index.md 顶部 Cell→Section 映射齐全?
- ☐ 每个核心 § 都有完整 5Q (Hook + What + How + Why + Why-not + Big Picture)?
- ☐ How 部分有显式推导链 (不只是说"为什么", 而是"怎么想到")?
- ☐ 至少 3-5 个 § 有 DIY vs Production 对照?
- ☐ 最后一个 Arc 是 `{N}-defense.md` 含 8-12 题?
- ☐ Arc 0 该有就有 / 该省就省?

### Phase 5: 编 PDF

复用 `scripts/compile_story_pdf.py`:

```bash
python3 .claude/skills/tutor/scripts/compile_story_pdf.py output/{课程名}/assignment{N}/teach
```

输出: `output/{课程名}/assignment{N}/teach/full-story.pdf`

---

## 写作风格要点 — 跟 story 哪里不同

### 语气

- ❌ 不要"老师讲课的口吻": "现在让我们来看 attention 的核心思想"
- ✅ 用"导师在你身后看代码的口吻": "看这一段, 你写了 `q @ k.T / sqrt(d_k)`. 这个 √d_k 不是装饰..."

### 节奏

- 顺着 notebook 从上到下走, **不要乱跳**
- 每段都跟着代码片段
- 没有代码的"纯讲解"段要少 (跟 lecture 不同 — lecture 主体就是讲解)

---

## 通俗化 — 信息密度控制 (重要 ⭐)

assignment 教学不是写论文摘要。**信息密度过高 = 读者得停下来反复消化, 节奏断**。
目标: **段落短, 句子短, 术语后跟一句白话翻译**, 但**技术深度不降**。

### 5 条具体规则

**规则 A: 画面 / 类比 先于术语**

- ❌ "把 lecture 抽象的'tiling + online softmax + recompute' 变成 ~30 行可执行 PyTorch 代码"
- ✅ "lecture 里 FlashAttention 那几件事 — 分块算、边算边累 softmax、需要时再算一遍 — 在这 Arc 变成 30 行能跑的 PyTorch。"

**规则 B: 一句话讲一件事, 长句必拆**

- ❌ "tiling 把 N×N 矩阵分成 M×N 的小块, 每块在快内存里算完, 累加结果到 O, N×N 矩阵从来不真的存在过, 自然不占 HBM"
- ✅
  > Tiling 的招: 把 N×N 大矩阵拆成几十个 M×N 的小块。
  > 一块算完累加, 立刻丢掉。
  > 整张 N×N 矩阵从没被拼出来过, HBM 自然省了。

**规则 C: 术语首次出现配白话翻译 (一句话即可)**

- ❌ "用 `logit_scale = exp(learnable)` 控制 softmax temperature"
- ✅ "用 `logit_scale` 控制 softmax 多锐 (锐 = 答案集中, 钝 = 答案分散)。它本身是 `exp(可学参数)`, 让模型自己挑合适的锐度。"

**规则 D: 痛点先画场景, 不要直接抛复杂度符号**

- ❌ "vanilla attention 内存复杂度 O(N²)"
- ✅ "想象 N=4096 的 attention: 中间那个 N×N 矩阵就 32 MB, 每层来一份, GPU 内存秒爆。这就是 FlashAttention 要救的场。"

**规则 E: 不要顿号串接堆术语**

- ❌ "shape, stride, contiguity, alignment 全都得对齐"
- ✅ "shape 要对。stride 要对。contiguity 也要对。错一个就报错。"

### 自检 (写完一个 § 看一眼)

- ☐ 段落超 4 行 → 拆?
- ☐ 一句话超 30 字 → 拆?
- ☐ 连续出现 3 个未解释术语 → 加白话翻译?
- ☐ 用顿号串了 3+ 名词 → 改成短句?
- ☐ 开头第一句是不是"画面/类比", 不是"做什么"?

### 注意 — 不是降低技术含量

通俗化是**降低消化成本**, **不是删内容**:
- Why-not 的 3 个反例**不能省**
- DIY vs Production 对照**不能省**
- 数学/代码细节**不能省**
- 删的是: 长句、堆叠术语、装饰性前缀 ("非常"、"大家都知道"、"实际上")

### 答辩话术

- "可念" — 面试官问 X, 你照说出来不卡顿
- 用"我", 不要用"我们"或"开发者" (是你写的, 不是别人)
- 短句 + 结构化 (核心答 → 3 个支撑点) — 比一段长答好背

### 跟 lecture story 共通

- 概念出现仍要解释 (writing-craft 术语管控)
- 用类比仍要类比 (writing-craft 用类比打底)
- 比较仍要开盒 (writing-craft 比较开盒)
- 不说废话 / 语气 / 章节过渡 — 同 lecture

---

## 反模式 — 不要做

- ❌ 把 assignment 写成像 lecture (按概念切而不是按代码切)
- ❌ 4Q 只回答 2-3 个 (必须 4 个齐, 漏了重写)
- ❌ DIY vs Production 只提一笔 ("业界用 vLLM 的 PagedAttention") — 必须开盒讲改进点
- ❌ 答辩 Arc 流于"列问题", 不给回答模板
- ❌ Arc 0 该写不写, 学生卡 Arc 1 第一行
- ❌ Arc 0 写过头, 把整个 lecture 复述一遍 — Arc 0 只是铺垫, 不是教学
- ❌ 顶部 Cell→Section 映射缺漏, 学生找不到章节
- ❌ 用"我们" / "开发者" 这种第三人称 — 直接 "你" + "我"
- ❌ 把代码片段当装饰, 后面只放概念讲解; 应该**代码 + 4Q 紧密绑**

---

## 命令调用

`/tutor {课程名} assignment {N}`

例:
- `/tutor <课程名> assignment 2` → 生成 `output/<课程名>/assignment2/teach/`

参数:
- `{课程名}`: courses/ 下的课程目录名
- `{N}`: assignment 编号

如果 `courses/{课程名}/assignments/Assignment{N}/` 不存在, 报错并列出可用的 assignment.
