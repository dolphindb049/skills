````skill
---
name: prepare_data_for_pricing
description: 债券定价前的数据准备技能（最小可跑通版）：建库建表、样本导入、双案例验证与报告输出。
license: MIT
metadata:
  author: jrzhang
  version: "1.1.0"
  tags: ["DolphinDB", "Bond", "Pricing", "execute-dlang", "ficc", "minimal"]
---

# prepare_data_for_pricing

这个 skill 只做“定价前准备与校验基线”，不做交易策略与执行。

## 什么时候用

- 你需要先准备标准化输入数据，再交给 `pricing` 做定价。
- 你希望验证环境是否可支持债券定价流程。

## 不适用场景

- 你要直接做生产级定价服务编排。
- 你要实时行情接入与交易联动。

## 最小跑通（默认离线样本）

默认使用 `reference/sample_data`，不依赖外部 API。

```bash
python3 -m pip install -r .github/skills/prepare_data_for_pricing/scripts/requirements.txt
python3 .github/skills/execute-dlang/scripts/ddb_runner/execute.py .github/skills/prepare_data_for_pricing/scripts/30_create_pricing_schema.dos --host 127.0.0.1 --port 8848 --user admin --password 123456
python3 .github/skills/prepare_data_for_pricing/scripts/40_ingest_raw_to_ddb.py
python3 .github/skills/execute-dlang/scripts/ddb_runner/execute.py .github/skills/prepare_data_for_pricing/scripts/50_run_case1_irs_pricing.dos --host 127.0.0.1 --port 8848 --user admin --password 123456
python3 .github/skills/execute-dlang/scripts/ddb_runner/execute.py .github/skills/prepare_data_for_pricing/scripts/60_run_case2_curve_bootstrap.dos --host 127.0.0.1 --port 8848 --user admin --password 123456
python3 .github/skills/prepare_data_for_pricing/scripts/70_generate_standard_report.py
```

## 可选在线数据刷新（有 token 时）

```bash
python3 .github/skills/prepare_data_for_pricing/scripts/10_probe_uqer_api.py
python3 .github/skills/prepare_data_for_pricing/scripts/20_download_minimal_samples.py
```

运行在线刷新前，请设置环境变量 `DATAYES_TOKEN`。

## 产出

- 数据库：`dfs://data_pricing_skill`
- 结果表：`pricing_result_case1`、`pricing_result_case2`
- 报告：`reference/reports/pricing_report_*.md`

## 与 `pricing` 的关系

- 先运行 `prepare_data_for_pricing` 生成标准输入。
- 再运行 `pricing` 完成统一定价与风险分析。

## 目录（精简）

```text
prepare_data_for_pricing/
├── SKILL.md
├── reference/
│   ├── API文档/
│   ├── API_CATALOG.md
│   ├── WORKFLOW.md
│   ├── TABLE_SCHEMA_AND_WORKFLOW.md
│   └── sample_data/
└── scripts/
    ├── requirements.txt
    ├── pricing_common.py
    ├── 10_probe_uqer_api.py
    ├── 20_download_minimal_samples.py
    ├── 30_create_pricing_schema.dos
## 对业务的直接含义（报告会给出）

- 模型价格（NPV）与 CFETS 净价偏差是否可接受
- 贴现曲线（IRS）与同类券曲线（bondYieldCurveBuilder）哪个更贴合样本
- 偏差最大的券种与可能原因（期限段、票息频率、报价口径）

## 参考文档

- 流程：`reference/WORKFLOW.md`
- 库表结构：`reference/TABLE_SCHEMA_AND_WORKFLOW.md`
- API字典：`reference/API_CATALOG.md`
- 联合调试：`reference/COMPATIBILITY_WITH_PRICING_SKILL.md`
- 函数文档：
  - `bondPricer`: https://docs.dolphindb.cn/zh/funcs/b/bondPricer.html
  - `bondYieldCurveBuilder`: https://docs.dolphindb.cn/zh/funcs/b/bondYieldCurveBuilder.html

````
