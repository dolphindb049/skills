---
name: ficc_curve_fitting
description: 基于 DolphinDB 的 FICC 曲线拟合验证技能。支持从 8671 抽样同步到 7731，建库建表、样本券选择、Bootstrap 曲线拟合，并与基准即期曲线做 bp 误差对比。
license: MIT
metadata:
  author: ddb-user
  version: "1.0.0"
---

# FICC 曲线拟合验证技能

本技能用于把“市场曲线 + 样本券 + 拟合对比”流程做成可重复执行的标准脚本。

能力范围：
- 从源端（默认 `192.168.100.43:8671`）抽取最小样本数据。
- 在目标端（默认 `192.168.100.43:7731`）自动建库建表。
- 按标准期限自动选择样本券（就近剩余期限）。
- 调用 `bondYieldCurveBuilder(..., method="Bootstrap")` 做拟合。
- 使用 `curvePredict` 与同日基准即期曲线逐期限对比，输出 bp 误差。

---

## 快速执行（推荐）

在工作区根目录执行：

```bash
uv run --with dolphindb --with pandas --with numpy \
  .github/skills/ficc_curve_fitting/scripts/curve_fit_runner/run_curve_fit_workflow.py
```

默认行为：
- 参考日：自动取源端 `BondYieldCurveSh` 的最新 `dataDt`
- 曲线：自动优先选择名称包含“国债”的到期曲线
- 期限：`1M,3M,6M,1Y,2Y,3Y,5Y,7Y,10Y`
- 目标库：`dfs://curve_fit_skill`

---

## 可选参数

```bash
uv run --with dolphindb --with pandas --with numpy \
  .github/skills/ficc_curve_fitting/scripts/curve_fit_runner/run_curve_fit_workflow.py \
  --src-host 192.168.100.43 --src-port 8671 \
  --tgt-host 192.168.100.43 --tgt-port 7731 \
  --user admin --password 123456 \
  --db-path dfs://curve_fit_skill \
  --curve-keyword 国债 \
  --terms 1M,3M,6M,1Y,2Y,3Y,5Y,7Y,10Y \
  --show-details
```

参数说明：
- `--reference-date`: 指定参考日，格式 `YYYY-MM-DD`；不传则自动使用最新交易日。
- `--curve-name`: 显式指定曲线名称；优先级高于 `--curve-keyword`。
- `--curve-keyword`: 自动选曲线时的关键词，默认 `国债`。
- `--terms`: 拟合期限列表（英文逗号分隔）。
- `--db-path`: 目标 DFS 库路径，默认 `dfs://curve_fit_skill`。
- `--show-details`: 打印样本券与分期限误差明细。

---

## 目标端落库结构

脚本会在目标端创建/写入 3 张表：
- `raw_curve`：原始曲线样本（到期/即期）
- `sample_bond`：样本券（含目标期限和报价）
- `fit_compare`：拟合结果与基准即期对比（`diffBp`）

默认分区：
- `RANGE` 分区，边界 `[2010.01.01, 2040.01.01]`

---

## 结果判断

脚本输出核心指标：
- `maxAbsBp`: 最大绝对误差（bp）
- `meanAbsBp`: 平均绝对误差（bp）
- `nPts`: 对比点数量

在一次实际运行中，结果为：
- `maxAbsBp ≈ 0.7424`
- `meanAbsBp ≈ 0.1834`
- `nPts = 9`

说明：在该数据切片下，拟合曲线与基准即期曲线误差整体处于亚 bp 到 1bp 以内水平。

---

## 常见问题

1) `ModuleNotFoundError: No module named 'dolphindb'`
- 解决：使用文档中的 `uv run --with ...` 命令执行。

2) `Missing YTM terms`
- 说明：目标期限在当日曲线上缺失。
- 解决：减少 `--terms` 或更换 `--reference-date` / `--curve-name`。

3) `No eligible bonds found`
- 说明：样本券筛选条件下无可用债券。
- 解决：切换参考日或放宽资产过滤（可在脚本中调整 typeName/typeID 条件）。
