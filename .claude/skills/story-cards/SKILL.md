---
name: story-cards
description: >
  把一门课（full-learn 写好的书）改编成"一个世界讲完整门课"的故事卡片 HTML：
  一节一张卡——左边是通俗故事（意象括号注对应概念），右边是真正的技术要点（核心、前提、陷阱、边界、符号）
  、"和故事的联系"（意象 ↔ 概念映射 + 共同结构 + ∵∴ 推理）和计算样例（口算题：题 → 公式 → 代入 → 结果），
  按幕 / 集组织、覆盖 100% 小节、不超前引用。
  当用户说"故事版""故事卡片""用故事过一遍整门课""story cards"时触发。
argument-hint: "<course-name> [all|world|write|check|render]"
allowed-tools: Read Glob Grep Bash Write Edit Agent
---

# story-cards

## 一句话
一个世界（如一家餐馆）从开业讲到扩张，每遇到一个麻烦就引出一节课的知识。读者先被故事带着走，再在同一张卡上拿到真正的知识、"这个比喻为什么成立、哪条前提不能丢"，以及一道口算题来对一遍自己理解的流程对不对。

## 输入与产物
- **输入**：full-learn 工作区 `output/<课程>/full-learn/`。要用到：
  - `book/NN-*.md`（`## §N.M` 小节、本章骨架、🧠 心智卡）；
  - `book/99-back.md` 附录 A（往年题 → 节，决定 🎯）；
  - `work/book-skeleton.md`（卷、块）；
  - `reader.md`；
  - **讲者脉络** `output/<课程>/lecture-flow/L*.md`（full-learn ingest / tutor scan 产出；没有就先按 `full-learn/templates/lecture-flow.md` 抽）：老师每讲的开场问题、过渡、例子、原话和逐步评价。世界、故事、前瞻章节都以它为底。
  
  有速查册（`output/<课程>/cheatsheet*/`）就一并用来对照陷阱。没有 full-learn 书时，先跑 full-learn。
- **产物**：`output/<课程>/story/`：
  - `world.md`（世界设定）
  - `parts/`（引子、前瞻章节 `1-preview.md`、各幕、结尾）
  - `story-table.md`（拼好的总表）
  - `story.html`（交付物，桌面浏览）、`story.pdf`（手机版）
  - `story-10min.md`（可选速读版）

## 规格
**`SPEC.md` 是唯一依据**（结构、五列各写什么、格内写法、保真）。读者改要求时先改 SPEC，再改产物，不在派工消息里零散追加。

## 流水线（`all` = 依次跑下面五步）

| 步 | 谁 | 做什么 | 模板 |
|---|---|---|---|
| `world` | 一个 agent | 选世界（2–3 个候选对着各章"一句话"和讲者脉络比），世界是外框、不替换老师的例子；写意象对照表（含"老师原例"列）、集表（开场麻烦 / 收尾钩子连成一条线）、引子与结尾；可选 10 分钟速读版 | `templates/world.md` |
| `preview` | 调度者（或一个 agent） | 用讲者脉络写前瞻章节 `parts/1-preview.md`：全课脉络，按幕和集、每集标课件页；先跑 `scripts/preview_index.py <O> <book_dir>` 得小节索引（每集的 §小节与课件页）；五步：拆集（课件的内容和例子，集内按读者的理解路线排）→ 补缺口 → 写（小块、多种形式穿插；复杂机制当黑箱）→ 查全（`scripts/preview_check.py <O>`：每集、每个 §小节都对号入座）+ 冷读者画大图 + 整体顺读 → 只修断掉的那一环；前瞻只求全和关联大图，机制细节留给正文，衔接的为什么不能省；工作文件 `src/work/preview-plan.md`；排在目录与第一幕之间（SPEC 第 1a 条） | `templates/preview.md` |
| `write` | 每幕一个 agent，**并行**；大幕（> 50 节）拆两份 | 照 SPEC 与 world.md 写 `parts/actNN.md`，一节一行（装不下就拆成 1/2）。第一遍就写全：<br>• 技术要点：关键公式加符号、🎯 考过的知识、前提、⚠️、边界、概念的中英文名和解释<br>• 和故事的联系：意象 ↔ 概念映射，再加 ∵∴<br>• 计算样例：🧮 与有公式的行一道口算题<br>• 💡 洞察 + ↩ 承接（`links.py` 从科技树与书的开场抽线索）、推导小方块、前置准备三问、标准节名<br>• 不超前引用<br>自查跑 concepts.py 与 check.py | `templates/write-act.md` |
| `check` | 调度者 | `python3 scripts/assemble.py <O> <book_dir>` 拼表，出 HTML 与手机版 PDF；再跑 `python3 scripts/check.py <O>/story-table.md <book_dir>`、`python3 scripts/forward.py <O>/story-table.md`（超前引用，要全表才查得出），以及每幕各跑一次 `scripts/concepts.py`。有问题就把那几行发回对应幕的作者修 | `templates/revise-act.md` |
| `render` | 调度者 | `assemble.py` 已出 `story.html`（桌面：左侧目录，正文居中，技术要点 / 联系 / 计算样例三栏并排，卡片标签带章名与节名）和 `story.pdf`（手机：110×195mm 单栏）；抽一两页转 PNG 看。可选课件定位：`<book_dir>/../source-map.json`（§N.M → lecture、scribe 节号与页、slides 起止页；人工对过 slides 标题再定稿），有它时节名后加括号「（L2 Slides p.19–21）」、幕 / 集标题下加 📍 页段，目录与书签不放 | — |

调度者只发填好的模板，不另写长说明。world 那一步定下的意象对照表和集表，是各幕并行写作时彼此对齐的唯一依据。

**调度者清单（照着走，一轮做完）**
1. 确认 full-learn 工作区齐全：`book/`、`99-back.md` 附录 A、`work/book-skeleton.md`、`reader.md`；找出速查册路径（没有就写"无"）。
2. 确认讲者脉络 `lecture-flow/` 齐全（缺就先按 `full-learn/templates/lecture-flow.md` 并行抽）。发 `templates/world.md`（一个 agent），等它交回 `world.md`、`parts/0-head.md`、`parts/9-tail.md`。有了集表就跑 `scripts/preview_index.py`，再写 `parts/1-preview.md`（`templates/preview.md`），可与第 3 步并行。
3. 按 world.md 的集表划幕：每幕一份；超过 50 节的幕按集拆成 `actNNa`、`actNNb`。所有 `templates/write-act.md` **一次并行发出**。
4. 全部交回后，跑 `assemble.py <O> <book_dir>`、`check.py`、`forward.py`，再对每幕跑 `concepts.py`。有问题的，按 `templates/revise-act.md` **一次性**把各幕的问题行发回对应作者（`forward.py --only parts/actNN.md` 出该幕的候选；用 SendMessage 续用原作者，它手上有上下文）。
5. 抽 1–2 页 PDF 转 PNG 看排版，交付。读者再提要求时，先改 SPEC，再按"读者反馈怎么落"处理。

## 读者反馈怎么落
- 格式或写法类（"bullet 太多""公式字母要解释""加一列计算样例"）→ 改 `SPEC.md` 对应条，能机读的同时加进 `check.py`，再按 `templates/revise-act.md` 让各幕作者并行修自己那一份。
- 顺序类（"前面引用了还没讲的"）→ SPEC 第 5 条；`forward.py` 出候选，按幕发 revise-act。
- 漏知识类（"某条公式的成立前提没提""某个陷阱没点"）→ 这是 SPEC 第 11、12 条没做到：按幕并行补，每行对照书里那一节的前提和 ⚠️ 块。
- 呈现类（排版、配色）→ 改 `scripts/to_html.py`，重新 `assemble.py`。
- 映射行（`• 意象 ↔ 概念`）渲染成对照表、不计入 bullet 比例。

## 成本参考（一次实测：47 章 265 节 → 295 卡）
- **首跑实测约 280 万 token**：没有 SPEC 与模板，零散改了约十轮。
  - 一个作者从头写全表，约 50 万；
  - 按幕补前提与陷阱，约 65 万；
  - 按幕补概念、公式、考点、映射，约 125 万；
  - 其余是选世界、改格式等。
- **照这份流程一遍写齐，估计约 160 万**：world 约 15 万，每幕约 20–25 万 × 6 份，约省四成。省下的主要是"每加一条要求，就让六个作者各重读一遍书"的那部分。

## 回归样例
改了脚本以后，拿一份已经定稿的完整产物跑一次（仓库不附带这样的产物，用你自己跑出来的一份）：`check.py` 应为 PASS，`concepts.py` 各幕都应为 0，`forward.py` 剩下的候选都是判过、有理由留着的，PDF 里没有半页空白。
