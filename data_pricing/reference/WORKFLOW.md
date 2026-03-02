# data_pricing 工作流分解

## Phase 0: API 探测与字段确认

- 脚本：`scripts/01_probe_api.py`
- 输出：`sample_data/api_probe_summary.json`
- 作用：确认每个 API 的最小可用参数、字段和当日可用性。

## Phase 1: 拉取最小样本（可复核）

- 脚本：`scripts/02_download_min_samples.py`
- 输出：
  - `sample_data/raw_irs_curve.json`
  - `sample_data/raw_bond_info.json`
  - `sample_data/raw_cfets_valuation.json`
  - `sample_data/raw_ib_bond_market.json`
  - `sample_data/case2_bond_basket.json`
- 作用：
  - 案例1：IRS 曲线 + 指定债券
  - 案例2：国债篮子（用于 `bondYieldCurveBuilder`）

## Phase 2: 建库建表（含完整 comment）

- DOS：`scripts/01_create_schema.dos`
- 覆盖表：
  - 原始表：`raw_bond_info`, `raw_cfets_valuation`, `raw_irs_curve`, `raw_ib_bond_market`
  - 中间表：`case2_bond_basket`, `instrument_cache`, `curve_cache`
  - 结果表：`pricing_result_case1`, `pricing_result_case2`

## Phase 3: Python 直连导入（不经 CSV 上传）

- 脚本：`scripts/03_ingest_raw_to_ddb.py`
- 方式：`dolphindb.session.upload + append!`
- 特点：
  - 直接从 JSON 导入 DFS
  - 自动处理 `curveDate`（由 `tradeDate + maturity` 生成）

## Phase 4: 案例1（IRS 曲线 + bondPricer）

- DOS：`scripts/02_case1_irs_bond_pricer.dos`
- 逻辑：
  1. 用 `raw_irs_curve` 构建 `IrYieldCurve`
  2. 用 `raw_bond_info + raw_cfets_valuation` 组装债券输入
  3. 调用 `bondPricer`（含 Delta/Gamma/KRD）
  4. 写入 `pricing_result_case1`

## Phase 5: 案例2（bondYieldCurveBuilder 反推 + 定价）

- DOS：`scripts/03_case2_bond_yield_curve_builder.dos`
- 逻辑：
  1. 用 `case2_bond_basket` 的 `YTM` 与剩余期限构建国债收益率曲线
  2. 调用 `bondYieldCurveBuilder(..., method="Bootstrap")`
  3. 再用 `bondPricer` 对篮子逐只定价
  4. 写入 `pricing_result_case2`

## execute-dlang 执行顺序

```bash
# 1) 建表
python .github/skills/execute-dlang/scripts/ddb_runner/execute.py \
  .github/DDB-skills/data_pricing/scripts/01_create_schema.dos \
  --host 127.0.0.1 --port 8848 --user admin --password 123456

# 2) 导入
python .github/DDB-skills/data_pricing/scripts/03_ingest_raw_to_ddb.py

# 3) 案例1
python .github/skills/execute-dlang/scripts/ddb_runner/execute.py \
  .github/DDB-skills/data_pricing/scripts/02_case1_irs_bond_pricer.dos \
  --host 127.0.0.1 --port 8848 --user admin --password 123456

# 4) 案例2
python .github/skills/execute-dlang/scripts/ddb_runner/execute.py \
  .github/DDB-skills/data_pricing/scripts/03_case2_bond_yield_curve_builder.dos \
  --host 127.0.0.1 --port 8848 --user admin --password 123456
```
