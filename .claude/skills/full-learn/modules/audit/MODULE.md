# audit — 自查执行器

## 职责
不定义标准，只执行标准：汇总 core 与各模块的 EXPECT，按检验方式分派（脚本 / 冷读者 agent / 作者自查），出报告，把失败项指回对应模块的 PARADIGM。

## 继承 / 覆写
继承 core。

## 输入
任一模块的产物 + 该模块与 core 的 EXPECT.md

## 输出
T5 `audit/*.md`

## 依赖
`scripts/verify_*.py` 等（唯一的脚本注册表在 PARADIGM 方法 2）

## 公开方法
1. `collect` — 收集要跑的 EXPECT
2. `run_scripts` — 跑脚本类检验
3. `cold_read` — 派零背景冷读者 agent 顺读
4. `self_review` — 作者自查类检验
5. `report` — 出报告，失败项指回 PARADIGM

## 扩展点
新 EXPECT 的检验方式若可脚本化 → 加进 verify 脚本，EXPECT 里标 `script`。
