---
name: full-learn
description: >
  把一整个给定范围（一门课的全部课件、一本书、一个陌生领域的材料堆）写成一本"跟着作者一起想一遍"的书（PDF）。
  先由 AI 建出全范围的科技树（谁依赖谁、懂什么才能看懂什么、终极理解是什么），
  再在树上推出一条叙事路径，按好书的展开方式成书，最后用冷读者顺读验收。
  当用户说"从头学""完整学一遍""full-learn""写成一本书"时触发。
argument-hint: "<course-name> [build|ingest|tree|spine|write <ch>|audit|render]"
allowed-tools: Read Glob Grep Bash Write Edit Agent TodoWrite
effort: max
---

# full-learn

## 一句话

范围是给定的全部；路径由 AI 从完整的依赖认知推出来；产物是一本顺读即懂的书。
读者不需要实时反馈——书好不靠亮点，靠展开顺序、讲述角度、节奏和推理链，让读者像跟着作者想了一遍。

---

## 架构：用 Markdown 写的 OOP

| OOP 概念 | 在本 skill 里 | 文件 |
|---|---|---|
| 基类 | `core` — 所有模块继承的人设、读者模型、保真、范围、文风 | `core/` |
| 类 | 一个模块 = 一个目录，单一职责 | `modules/<name>/` |
| 接口 | 职责 / 输入 / 输出 / 依赖 / 公开方法 / 扩展点 | `MODULE.md` |
| 实现 | 这个模块怎么想、怎么做的**范式**（一套方法理论，照着做就行，不是要求清单） | `PARADIGM.md` |
| 单元测试 | 范式对应的验收标准，每条可检验 | `EXPECT.md` |
| 类型 | 模块之间传递的产物 schema | `CONTRACTS.md` |
| 组合 | `compose` 由 `book / chapter / section / devices` 四个子类组成 | `modules/compose/*/` |

**继承规则**: 每个模块默认继承 `core` 的 PARADIGM 与 EXPECT。模块要偏离 core，必须在自己的 MODULE.md「覆写」一栏显式声明并给理由；没声明就按 core 来。

**变体规则（common + special）**: 同一模块里有一类对象要换写法（如前置节），不另起一套范式，而是在模块下 `variants/<名>.md` 写一张覆盖表：每行点名被覆盖的 common 条目（范式锚点或 E-ID）、动作（替换 / 关闭 / 收紧 / 新增）、内容、理由、被覆盖条目的指纹。special 优先于 common；**没列出的一律继承**，common 以后新增或修改的规则自动作用到变体上。指纹对不上（common 那条改了或删了）时 `verify_checklist.py` 报"变体待复核"，覆盖项不会悄悄过期。脚本对属于变体的对象先读覆盖表，再决定关哪些检查、换哪些阈值。

**封装规则**: 模块只通过 CONTRACTS.md 定义的产物交流。下游模块不读上游模块的 PARADIGM，只读它的产物。

---

## 模块注册表

| # | 模块 | 一句话职责 | 产物 |
|---|---|---|---|
| — | [core](core/MODULE.md) | 基类：作者是谁、读者是谁、什么能写什么不能写、怎么说话 | — |
| 1 | [ingest](modules/ingest/MODULE.md) | 把材料堆变成逐页可引用的原文与原图；抽出每讲的讲者脉络 | `raw/`、`lecture-flow/` |
| 2 | [tree](modules/tree/MODULE.md) | 建全范围的科技树：节点、依赖边、生成元、终极理解、分量 | `tree.json` · `tree.md` |
| 3 | [spine](modules/spine/MODULE.md) | 在树上选一条拓扑序，使每一步都是上一步留下的疑问；切章 | `spine.md` |
| 4 | [compose](modules/compose/MODULE.md) | 按脊柱成书（组合下面四个子类） | `book/*.md` |
| 4.1 | [compose/book](modules/compose/book/MODULE.md) | 全书层：书首（终极理解、科技树图、读法）、运行案例、书尾 | `book/00-*.md` · `book/99-*.md` |
| 4.2 | [compose/chapter](modules/compose/chapter/MODULE.md) | 章层：一章解锁一项能力；开章、节奏编排、收章 | 每章文件的章级结构 |
| 4.3 | [compose/section](modules/compose/section/MODULE.md) | 节层：一个节点的推理链——从疑问到洞见到结论 | 每节正文 |
| 4.4 | [compose/devices](modules/compose/devices/MODULE.md) | 表达器件：类比、例子、图、公式记法、块类型、出处脚注 | 被 section/chapter 调用 |
| 5 | [audit](modules/audit/MODULE.md) | 自查执行器：汇总各模块 EXPECT、跑脚本门禁、派冷读者顺读 | `audit/*.md` |
| 6 | [render](modules/render/MODULE.md) | MD → A5 PDF，排版门禁 | `book.pdf` |

---

## 加载规则（按角色，各读一次）

token 主要花在"每个 agent 都把 skill 重读一遍"上，所以按角色只读该读的：

| 角色 | 读 | 不读 |
|---|---|---|
| 调度者（主会话） | 本文件、`CONTRACTS.md`、要派的那份 `templates/*.md` | 各模块范式（由干活的 agent 读） |
| 阶段作者（ingest / tree / spine / render） | `core/PARADIGM.md` + `core/EXPECT.md`、本模块 `PARADIGM.md` + `EXPECT.md`、CONTRACTS 里本模块产物那一节 | 本文件、`GATES.md`、别的模块 |
| 写书作者（compose） | 照 `templates/write.md` 的清单：core + chapter + section + devices 的 PARADIGM 与 EXPECT、CONTRACTS T4 | 本文件、`GATES.md`、`MODULE.md`、`dev/` |
| 冷读者 | 只读书（`templates/cold-read.md`） | 一切规范 |

- `EXPECT.md` 只列人要做的验收（self / cold-read / 脚本未实现）；纯脚本检查在同目录 `GATES.md`，**写作时不读**——跑脚本，FAIL 的那条带着"修法见 PARADIGM …"回来，再去读那一段。改脚本、调阈值时才读 GATES。
- `MODULE.md` 是接口说明，给改 skill 的人看；运行时的 agent 由模板告诉它读什么，不必读。
- `dev/` 是开发者文档（来历、清点表、覆盖索引 `dev/index-<模块>.md`），运行时不读。开源版不附 `dev/`（原始开发笔记绑定了具体课程）；要用下文的升级协议，先自建 `dev/atoms-*.md`，否则 `verify_checklist.py` 无从核对。
- 脚本自查一律加 `--quiet`（只印 FAIL / WARN），编译输出只看末几行。

---

## 命令与流水线

`/full-learn <课程名> [命令]`，课程名对应 `courses/<课程名>/`，产物在 `output/<课程名>/full-learn/`。

| 命令 | 执行的模块 | 结束时 |
|---|---|---|
| `build`（默认） | core(reader.md) → ingest → tree → spine → ⏸ → compose(样章) → audit → ⏸ → compose(其余) → audit → render | 两个 ⏸ 是用户检查点 |
| `ingest` | ingest | 跑 ingest/EXPECT |
| `tree` | tree | 跑 tree/EXPECT |
| `spine` | spine | 跑 spine/EXPECT，⏸ 交用户审脊柱 |
| `write <章号\|块\|all>` | compose | 按块派工（templates/write.md），每章写完跑 verify --quiet 与 self 条目 |
| `audit [模块]` | audit | 输出 `audit/` 报告 |
| `render` | render | 跑 render/EXPECT |

**两个检查点为什么在那里**:
- ⏸1 脊柱审阅——脊柱是几页的"章 → 节 → 入口问题"清单，路径错了在这里改最便宜。
- ⏸2 样章审阅——用户读第一章，确认"顺不顺、爽不爽"，反馈回写到对应模块的 PARADIGM 再批量写。

**写书的派工单位是块，不是章。** spine 定下的块（2–5 章同一个问题）就是一份活：一个作者照 `templates/write.md` 读一次范式，按章序写完块里的章（块超过 3 章就拆成两份，块末那份写 🌳 块小结）；块与块并行。每章**一遍写全**——骨架、出手块（⚔️ 🗺️ 🤔 🧠）、块小结都在写作时写，不事后补一轮。全部写完，派**一个** agent 照 `templates/world-model.md` 按章序补世界模型 vN 与先回忆（它只读骨架段与卡片）；冷读按块派（`templates/cold-read.md`）。调度者发模板，不另写长说明；跨章协调靠工作区的 case-bible / xchapter-notes / errata / decisions 四个文件。

**每个模块的完成定义**: 产物符合 CONTRACTS.md + 本模块 EXPECT 全过 + core EXPECT 全过。没过就修，不交付。

---

## 升级与扩展协议

- **改一条规则** → 找到它属于哪个模块，改该模块的 PARADIGM（范式本身）和 EXPECT（对应验收），两边一起改。不在 SKILL.md 或别的模块里打补丁。
- **加一个模块** → 新建目录写三件，在本文件注册表加一行，在 CONTRACTS.md 声明它的产物。
- **用户反馈** → 先定位到模块，再整合进该模块范式已有的结构里（不 append 散条）；用户原话与日期记到 `dev/provenance.md`。
- **定位一个问题** → 产物哪里不好 → 看是哪个 EXPECT 没拦住 → 该 EXPECT 所属模块的范式就是要改的地方。
- **新增一条要点** → 先在 `dev/atoms-*.md` 登记（id、归属模块、处置），再整合进范式/验收，最后跑 `scripts/verify_checklist.py` 保持 100% 覆盖。写法见 `dev/authoring.md`。

---

## 目录结构

```
full-learn/
├── SKILL.md            入口：架构、注册表、加载规则、命令、升级协议
├── CONTRACTS.md        类型：模块间产物 schema
├── core/               基类
│   ├── MODULE.md · PARADIGM.md · EXPECT.md · GATES.md
├── modules/
│   ├── ingest/  tree/  spine/  audit/  render/      每个都是 MODULE · PARADIGM · EXPECT（· GATES）
│   └── compose/
│       ├── MODULE.md                                组合类：只定义子类怎么协作
│       └── book/  chapter/  section/  devices/      子类
├── templates/          派工模板：write（写一个块）· cold-read（冷读一个块）· world-model（世界模型一遍）
├── scripts/            可执行工具（从 tutor 复制后独立迭代）+ verify_checklist.py（要点覆盖核对）
└── dev/                开发者文档（运行时不读）
    ├── provenance.md   来历：用户原话与关键决策
    ├── authoring.md    模块文件怎么写（范式结构、EXPECT / GATES 格式、覆盖核对）
    ├── index-*.md      覆盖索引：范式段落与验收条目各吸收了哪些原子要点
    ├── backlog.md      待办：跑新 topic 前先处理
    └── atoms-*.md      新旧原子要点清点表（checklist），每条有 id、归属模块、处置
```

工作区:

```
output/<课程名>/full-learn/
├── reader.md           core 产物（读者起点、目的、发散刻度）
├── raw/                ingest 产物（逐页文本、原图、manifest；_register.json 是登记判断的源）
├── work/               中间产物（分组收割片段、分工说明），可删
├── tree.json · tree.md
├── spine.md
├── book/               00-front.md · 01-*.md … · 99-back.md
├── audit/              各模块自查报告 + 冷读者报告
└── book.pdf
```
