```skill
---
name: ficc_instru_maket_modeling
description: 构建 FICC 定价所需的资产和市场数据结构，构建字段映射过程，是数据准备到定价计算的中间过程，支持用户去按照定价模型的需求来构建和调整数据结构。
license: MIT
metadata:
  author: ddb-user
  version: "1.0.0"
---

## 技能概述 / Overview

这个技能用于把“原始资产表 + 原始行情表”标准化成定价引擎可直接消费的两张核心表：

- `Instrument(instrumentId, instrumentType, instrument, ...)`
- `MarketData(referenceDate, name, mktDataType, data, ...)`

重点不是“机械字段改名”，而是把业务含义对齐到 `parseInstrument` / `parseMktData` 的输入契约。

## 什么时候用

- 你已有债券/曲线原始表，但列名和枚举不符合 DolphinDB 定价接口。
- 你要在入库前先做统一清洗，保证后续 `instrumentPricer` / `portfolioPricer` 稳定运行。
- 你希望把 mapping 逻辑文档化，便于后续换数据源时快速复用。

## 核心流程

### 1) 先定义目标契约（标准表 + parse 入参）
- 先看说明文档，明确哪些字段是“必填且有语义约束”。
- 参考文档：[`reference/parseinstru.md`](reference/parseinstru.md)、[`reference/parsemarketdata.md`](reference/parsemarketdata.md)

### 2) 按原始表做 mapping（必须人工确认）
- 枚举映射：例如 `couponTypeCD -> bondType`，不是字符串替换，而是产品分类规则。
- 数值映射：例如收益率是否从百分比转小数（`/100`）。
- 时间映射：`start/maturity/referenceDate/dates` 必须是 DATE 类型。

### 3) 执行模板并看失败样本
- Instrument 模板：[`reference/instrument_standardize_template.dos`](reference/instrument_standardize_template.dos)
- MarketData 模板：[`reference/marketdata_standardize_template.dos`](reference/marketdata_standardize_template.dos)
- 每次先跑小样本，查看 fail 表，再补映射。

## 和“跨节点同步”技能的边界

本技能聚焦“字段语义标准化”。
如果你还需要 `8671 -> 7731` 这类跨节点拉取，请配合技能：

- [`../ddb-cross-node-sync/SKILL.md`](../ddb-cross-node-sync/SKILL.md)

## 快速入口

- 流程总览：[`reference/README.md`](reference/README.md)
- Instrument 详解：[`reference/parseinstru.md`](reference/parseinstru.md)
- MarketData 详解：[`reference/parsemarketdata.md`](reference/parsemarketdata.md)

```