# tree — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-TREE-17 | 全书覆盖全部生成元：每个 generator 节点 id 至少出现在一节的 `<!-- nodes: … -->` 注释里（audit 阶段跑） | script: verify_book.py#generators_in_book | PARADIGM §方法 3 末句 |
