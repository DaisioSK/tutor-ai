# core — 脚本门禁

纯脚本检查的验收条目。写作时不必读：跑脚本，FAIL 的那条会带着「修法见 PARADIGM …」回来；审脚本、改阈值时读这里。人要做的（self / cold-read / 脚本未实现）在 EXPECT.md。

| id | 验收标准（可判定的一句话） | 检验方式 | 不过时回到 |
|---|---|---|---|
| E-CORE-01 | `reader.md` 在 tree 开跑前存在，含：范围声明（仅课程名 + 覆盖范围）、读者起点、`divergence_layers`∈0–3、`divergence_breadth`∈1–8、`relevance_threshold`∈{严格,中等,宽松}，以及推出这组值的信号；用户未声明时为中等默认，读者起点未声明时为"AI 行业半工半读、时间紧" | script: verify_book.py#reader_md | PARADIGM §方法 1 · §理论 2 |
| E-CORE-04 | 删掉全部外部补充块与带外部标记的句子后，正文仍覆盖 E-CORE-03 的每一项；没有任何材料内容只存在于补充块里 | script: verify_book.py#strip_external_coverage | PARADIGM §理论 3 |
| E-CORE-05 | 按章统计，外部补充（补充块 + 带外部标记的非引用行）占比 ≤25%，超过则 WARN 并复查正文是否写薄 | script: verify_book.py#external_share | PARADIGM §判断准则 |
| E-CORE-11 | 正文中每个具体数字、专有名词、公司名、时间线、引语，要么能在 `raw/` 搜到，要么紧邻给出由材料数值算出的算式，要么声明"编个数演示"，要么带外部标记；否则 FAIL。材料的定性表述没有被写成具体数 | script: verify_book.py#ungrounded_tokens | PARADIGM §方法 5 |
| E-CORE-16 | 全书（含书首、读法页与附录）不出现考务信息与重要度标签：考试日期、地点、时长、卷面题型构成、分值、押题、"必考/高频"；reader.md 声明考试时的 🎯 问法块与书尾"往年题 → 节"映射不算违例 | script: verify_book.py#exam_logistics | PARADIGM §判断准则 |
| E-CORE-19 | 标题、引用块前缀、正文标签中不出现技法名（对照式发散 / 痛点-方案-效果 / raise + reject / 插件式补充 / 结构化叙事）与本 skill 内部代号与节点 id（N-xxx）/分量/负载字段（入口问题 / 凭什么现在能懂 / 留下的新问题 / 生成元 / 脊柱 / 四格） | script: verify_book.py#meta_narrative（旧版同名检查见 verify_teach.py META_NARRATIVE） | PARADIGM §判断准则（禁止清单） |
| E-CORE-20 | 句段形态：≥3 个术语用顿号串接 → FAIL；一段 >4 行（A5 正文约 140 字）、一句 >30 字（按 。？！；切句）→ WARN 并复核是否该拆；技术深度不因拆句而降 | script: verify_book.py#sentence_shape | PARADIGM §方法 2 |
| E-CORE-30 | 跨章提前出现的材料术语，首现处有一句白话解释并写明落点节（§N.M 或第 N 章）；没有回指的跨章提前使用为 0 | script: verify_book.py#deps（有回指 WARN、无回指 FAIL） | PARADIGM §方法 4 |
