````skill
---
name: data-pricing
description: 通联API债券数据的模块化流程：API探测 -> 小样本下载 -> DDB建库建表 -> 直连导入 -> 双案例定价。
license: MIT
metadata:
  author: jrzhang
  version: "0.3.0"
  tags: ["DolphinDB", "Bond", "Pricing", "UQER", "execute-dlang"]
---

# Data Pricing Skill（精简结构版）

本 skill 只保留两类子目录：
- `reference/`：文档与样本数据
- `scripts/`：可执行脚本（Python + DOS）

## 目录

```text
data_pricing/
├── SKILL.md
├── reference/
│   ├── API文档/                     # 原始PDF
│   ├── API_CATALOG.md               # API用途/参数/字段说明
│   ├── WORKFLOW.md                  # 流程分解
│   └── sample_data/                 # 探测与下载结果
└── scripts/
    ├── requirements.txt
    ├── lib_data_pricing.py
    ├── 01_probe_api.py
    ├── 02_download_min_samples.py
    ├── 03_ingest_raw_to_ddb.py
    ├── 01_create_schema.dos
    ├── 02_case1_irs_bond_pricer.dos
    └── 03_case2_bond_yield_curve_builder.dos
```

## 一句话流程

1. `01_probe_api.py`：先看每个API真实返回什么。
2. `02_download_min_samples.py`：只拉验证定价所需最小样本。
3. `01_create_schema.dos`：建库建表（原始层/准备层/结果层）。
4. `03_ingest_raw_to_ddb.py`：Python 直连导入（不走 CSV 上传）。
5. `02_case1_irs_bond_pricer.dos`：IRS曲线 + `bondPricer`。
6. `03_case2_bond_yield_curve_builder.dos`：`bondYieldCurveBuilder` 反推曲线 + 定价。

## 运行顺序（可直接复制）

```bash
cd /hdd/hdd9/jrzhang

# Python依赖
/home/jrzhang/miniconda3/bin/python -m pip install -r .github/DDB-skills/data_pricing/scripts/requirements.txt
/home/jrzhang/miniconda3/bin/python -m pip install python-dotenv

# 0) API探测与下载
/home/jrzhang/miniconda3/bin/python .github/DDB-skills/data_pricing/scripts/01_probe_api.py
/home/jrzhang/miniconda3/bin/python .github/DDB-skills/data_pricing/scripts/02_download_min_samples.py

# 1) 建库建表（execute-dlang）
/home/jrzhang/miniconda3/bin/python .github/skills/execute-dlang/scripts/ddb_runner/execute.py \
  .github/DDB-skills/data_pricing/scripts/01_create_schema.dos \
  --host 127.0.0.1 --port 8848 --user admin --password 123456

# 2) 导入原始样本
/home/jrzhang/miniconda3/bin/python .github/DDB-skills/data_pricing/scripts/03_ingest_raw_to_ddb.py

# 3) 案例1
/home/jrzhang/miniconda3/bin/python .github/skills/execute-dlang/scripts/ddb_runner/execute.py \
  .github/DDB-skills/data_pricing/scripts/02_case1_irs_bond_pricer.dos \
  --host 127.0.0.1 --port 8848 --user admin --password 123456

# 4) 案例2
/home/jrzhang/miniconda3/bin/python .github/skills/execute-dlang/scripts/ddb_runner/execute.py \
  .github/DDB-skills/data_pricing/scripts/03_case2_bond_yield_curve_builder.dos \
  --host 127.0.0.1 --port 8848 --user admin --password 123456
```

## 环境变量（可选）

```bash
export DATAYES_TOKEN='4c89993d518c6cb4105870590b923416ecc61d0da7b438f6ace0bb036040a7c4'
export PRICING_DATE='20260105'
export PRICING_TICKERS='240025,250015,250401'
export DDB_HOST='127.0.0.1'
export DDB_PORT='8848'
export DDB_USER='admin'
export DDB_PASSWORD='123456'
export DDB_DB_PATH='dfs://data_pricing_skill'
```

## 结果表

- `pricing_result_case1`：IRS贴现曲线定价结果（含Delta/Gamma）
- `pricing_result_case2`：收益率曲线反推后定价结果

## 参考

- `reference/API_CATALOG.md`
- `reference/WORKFLOW.md`
- `https://docs.dolphindb.cn/zh/funcs/b/bondPricer.html`
- `https://docs.dolphindb.cn/zh/funcs/b/bondYieldCurveBuilder.html`

````
