# DolphinDB 债券定价技能包（专业版）

## 你会得到什么
- 一套可复用的债券定价流水线：数据探索 → 建库建表 → 规范化 instrument → 批量定价 → 风险指标 → 可视化。
- 全流程不依赖共享内存表，结果持久化到 DFS：`dfs://bond_pricing_workflow_v2`。
- 支持按参数查询单资产价格与风险，并生成交互式 HTML 图表。

## 脚本入口
- [scripts/00_cleanup_shared_objects.dos](scripts/00_cleanup_shared_objects.dos)
- [scripts/01_data_discovery.dos](scripts/01_data_discovery.dos)
- [scripts/02_prepare_output_schema.dos](scripts/02_prepare_output_schema.dos)
- [scripts/03_run_pricing_pipeline.dos](scripts/03_run_pricing_pipeline.dos)
- [scripts/04_asset_pricing_detail.dos](scripts/04_asset_pricing_detail.dos)

## 理论与数据源
- [reference/THEORY.md](reference/THEORY.md)
- [reference/DATA_SOURCES.md](reference/DATA_SOURCES.md)

## Python 可视化
- [python/visualize_pricing.py](python/visualize_pricing.py)
- [python/requirements.txt](python/requirements.txt)

## 推荐执行顺序
1. 清理历史共享对象（兼容旧流程）
2. 做数据探索确认样本质量
3. 创建输出数据库与表结构
4. 执行主定价流水线并落盘
5. 用单资产脚本和 Python 图表验算

## 当前误差定义
- `priceDiff = modelPrice - marketProxyPrice`
- `diffBp = (modelPrice / marketProxyPrice - 1) * 10000`
- `modelVsIssue = modelPrice - issuePrice`

后续接入真实市场价后，可以把 `marketProxyPrice` 替换为 `marketPrice` 做正式模型评估。
