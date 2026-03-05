# FICC Instrument / MarketData 建模参考

本目录解决的问题不是“改列名”，而是“把原始数据语义转换成定价引擎理解的对象语义”。

在 DolphinDB 里：
- `parseInstrument` 期待的是“资产定义字典”
- `parseMktData` 期待的是“市场数据字典”

如果 mapping 只做字段搬运，不做语义校准（枚举、单位、日期类型），就会出现 parse 失败或定价偏差。

---

## 文档结构

- `parseinstru.md`
  - 讲清楚 Instrument mapping 的“为什么”和“怎么改”。
- `parsemarketdata.md`
  - 讲清楚 MarketData mapping 的“为什么”和“怎么改”。
- `instrument_standardize_template.dos`
  - 本地（同节点）版本的 Instrument 标准化模板。
- `marketdata_standardize_template.dos`
  - 本地（同节点）版本的 MarketData 标准化模板。

> 跨节点拉数（例如 8671 -> 7731）已拆分到单独技能：
> [`../../ddb-cross-node-sync/SKILL.md`](../../ddb-cross-node-sync/SKILL.md)

---

## 你最需要先理解的 3 件事

### 1) mapping 的本质是“契约对齐”

例如：
- 原表里 `couponTypeCD=ZERO`，并不只是文本 `ZERO`，它表达“贴现债”，必须映射成 `bondType=DiscountBond`。
- `yieldSpread=2.35` 多数情况下代表 2.35%，而曲线输入 `values` 要的是小数 0.0235。

### 2) parse 函数对类型非常严格

- `start/maturity/referenceDate/dates` 不要依赖隐式转换，统一显式 `date(...)`。
- `dates` 必须是 DATE 向量，不能混入 NULL 或字符串。

### 3) 失败样本是最重要反馈

每次先跑小样本（例如最新 1-3 天 + 前 200 条），看 fail 表：
- 是枚举不认识？补映射。
- 是单位错？补 `/100`。
- 是类型错？补 `date()`/`double()`。

---

## 推荐执行顺序

1. 阅读 `parseinstru.md` 与 `parsemarketdata.md` 的“字段语义表”。
2. 在 `.dos` 模板顶部替换库名、表名、字段名、字典映射。
3. 先小样本执行，确认 fail 数量可解释。
4. 全量跑并产出成功/失败统计。

---

## 验收标准

至少输出以下检查结果：
- Instrument：总数、按 `instrumentType` 分布、失败 TopN。
- MarketData：总数、按 `sourceTable` 分布、失败 TopN。
- 脚本可重复执行（参数化，不依赖手工中间状态）。
