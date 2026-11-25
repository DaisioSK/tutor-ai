# compose — 成书（组合类）

## 职责
按脊柱把全书写出来。本身不写内容，只定义四个子类如何协作：

```
book     全书层：书首 / 运行案例的线 / 书尾 / 跨章引用
 └ chapter   章层：开章 → 节序列（节奏）→ 收章
    └ section    节层：一个节点的推理链
         └ devices  表达器件（被 chapter/section 调用）
```

## 继承 / 覆写
继承 core。覆写：无。

## 输入
T3 `spine.md` · T2 `tree.json` · T1 `raw/`

## 输出
T4 `book/*.md`

## 依赖
spine · tree · ingest

## 协作顺序
1. book 先写书首，立终极理解与运行案例。
2. 按块派工（一个作者一个块，2–3 章，`templates/write.md`）；每章：chapter 定开章与节奏 → 逐节调用 section → chapter 收章，出手块与块小结一遍写全。
3. 全部章写完，一个作者按章序补世界模型 vN（`templates/world-model.md`）；book 写卷串讲、总纲与书尾，统一跨章引用。
4. 每章完成即交 audit：脚本门禁（`--quiet`）+ self 条目；冷读按块。

## 扩展点
别的成品形态（速查册、讲义）→ 新增 compose 的兄弟模块，复用 devices。
