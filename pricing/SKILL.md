---
name: pricing
description: 债券定价与风险分析技能（最小可跑通版）。聚焦标准化输入、定价、风险和偏差评估。
license: MIT
metadata:
  author: ddb-user
  version: "1.3.0"
  tags: ["bond", "pricing", "risk", "dolphindb", "ficc", "minimal"]
---

# pricing（FICC 定价）

定位：
- 本 skill 只负责“定价与风险计算”。
- 输入数据准备建议交给 `prepare_data_for_pricing`。
- 执行方式统一使用 `execute-dlang`。

默认输出库：`dfs://bond_pricing_workflow_v2`。

## 什么时候用

- 你已经有了可用债券样本和曲线数据。
- 你希望快速得到 `modelPrice / diffBp / Greeks`。

## 不适用场景

- 还没有可用输入数据（先跑 `prepare_data_for_pricing`）。
- 你要做交易执行、风控审批或生产级服务编排（本 skill 不覆盖）。

## 最小跑通（推荐）

在仓库根目录执行：

```bash
python3 .github/skills/execute-dlang/scripts/ddb_runner/execute.py .github/skills/pricing/scripts/02_prepare_output_schema.dos --host 127.0.0.1 --port 8848 --user admin --password 123456
python3 .github/skills/execute-dlang/scripts/ddb_runner/execute.py .github/skills/pricing/scripts/05_run_unified_pipeline.dos --host 127.0.0.1 --port 8848 --user admin --password 123456
```

完成后核心结果表：
- `pricing_result`
- `pricing_risk`
- `pricing_curve_points`

## 可选步骤

- 单券细节：

```bash
python3 .github/skills/execute-dlang/scripts/ddb_runner/execute.py .github/skills/pricing/scripts/04_asset_pricing_detail.dos --host 127.0.0.1 --port 8848 --user admin --password 123456
```

- 外部市场价对比：

```bash
python3 .github/skills/pricing/python/ingest_external_market_csv.py --csv /path/to/market_price.csv --host 127.0.0.1 --port 8848 --user admin --password 123456
python3 .github/skills/execute-dlang/scripts/ddb_runner/execute.py .github/skills/pricing/scripts/06_compare_with_external_market.dos --host 127.0.0.1 --port 8848 --user admin --password 123456
```

## 与 `prepare_data_for_pricing` 的关系

- `prepare_data_for_pricing`：生成/导入定价输入数据。
- `pricing`：基于输入数据做定价、风险和偏差分析。

## 目录（保留）

```text
pricing/
├── SKILL.md
├── README.md
├── scripts/
│   ├── 00_cleanup_shared_objects.dos
│   ├── 01_data_discovery.dos
│   ├── 02_prepare_output_schema.dos
│   ├── 03_run_pricing_pipeline.dos
│   ├── 04_asset_pricing_detail.dos
│   ├── 05_run_unified_pipeline.dos
│   └── 06_compare_with_external_market.dos
├── reference/
│   ├── THEORY.md
│   ├── DATA_SOURCES.md
│   ├── INTERFACE_CONTRACT.md
│   └── ORCHESTRATION.md
└── python/
    ├── requirements.txt
    ├── visualize_pricing.py
    └── ingest_external_market_csv.py
```
