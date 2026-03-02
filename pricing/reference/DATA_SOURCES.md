# 外部市场数据与官方对比源（建议）

## 推荐对比口径
优先使用同日、同市场、同报价口径的“净价”或“估值全价”。

## 可选数据源
- 中债估值（ChinaBond）
  - 官网：`https://yield.chinabond.com.cn/`
  - 可获取中债收益率曲线与债券估值数据（通常需授权/接口权限）。
- 银行间市场（CFETS）
  - 官网：`https://www.chinamoney.com.cn/`
  - 可获取银行间债券行情/收益率参考。
- 交易所债券行情（上交所/深交所）
  - 用于交易所挂牌债券的成交价、收盘价对比。
- Wind / iFinD / CSMAR / 聚源
  - 商业终端数据，适合批量历史回溯与高质量字段映射。

## 字段映射建议
- 键：`instrumentId/secID`（先做代码标准化）
- 日期：`pricingDate`
- 价格：`marketPrice`（净价或全价，需统一）
- 可选：`ytm`, `duration`, `accruedInterest`

## 对比注意事项
- 市场口径差异：净价 vs 全价。
- 估值时点差异：收盘估值 vs 日间成交。
- 应计利息处理：不同系统可能默认不同。
- 停牌或无成交时，建议退化为估值曲线价。

## 接入方式建议
1. 先落一张标准化外部行情表：`pricing_market_external(pricingDate, instrumentId, marketPrice, source, priceType)`。
2. 再与 `pricing_result` 做按日按券 join。
3. 统一计算误差指标与可视化。
