# 债券定价与误差评估理论说明（工程版）

## 1. 为什么采用“贴现曲线 + 利差曲线”
- 在无套利框架下，债券价格是未来现金流在定价日贴现的现值：
  $$P=\sum_{k=1}^{N} CF_k\cdot DF(t_k)$$
- 贴现因子由收益率曲线决定，若考虑信用/流动性溢价，可写为：
  $$DF(t)=\exp\left(-\int_0^t(r(u)+s(u))du\right)$$
  其中 $r(u)$ 是无风险或基准利率曲线，$s(u)$ 是利差曲线。
- 在 DolphinDB 中，对应 `bondPricer(instrument, pricingDate, discountCurve, [spreadCurve])`。

## 2. 本技能中的建模假设
- 产品范围：`利率债` 且 `couponTypeCD in [FIXED, ZERO]`。
- 起息日/到期日有效，且到期日在定价日之后。
- 频率映射：`1PY->Annual`，`2PY->Semiannual`，`4PY->Quarterly`，`MAT->Once`。
- 日期计数：`ActualActualISDA`。
- 曲线插值：`Linear`，外插：`Flat`（可在脚本参数修改）。

## 3. 误差是怎么定义的
在 `pricing_result` 表中提供三类误差：
- `priceDiff = modelPrice - marketProxyPrice`
- `diffBp = (modelPrice / marketProxyPrice - 1) * 10000`
- `modelVsIssue = modelPrice - issuePrice`

对应统计量：
- 平均误差 `meanDiff`
- 波动 `stdDiff`
- 平均绝对基点误差 `meanAbsDiffBp`

## 4. 为什么要同时看这三类误差
- `priceDiff`：价格单位误差，便于交易上直观判断。
- `diffBp`：标准化误差，跨不同价位债券可比较。
- `modelVsIssue`：与发行价基准的长期偏离（更偏静态参考）。

## 5. 风险指标解释
调用 `bondPricer(..., setting=...)` 额外输出：
- `discountCurveDelta`：对曲线平移一阶敏感度。
- `discountCurveGamma`：对曲线平移二阶敏感度。
- `discountCurveKeyRateDuration`：关键期限久期向量（例如 1Y/3Y/5Y/10Y）。

## 6. 工程上的校准建议
- 若有真实市场净价/估值，可将 `marketProxyPrice` 替换成实盘 `marketPrice`。
- 可进一步做：
  - 按期限分桶误差（短端/中端/长端）
  - 按票息分层误差
  - 用最小化 $\sum (P_{model}-P_{mkt})^2$ 标定利差曲线参数
