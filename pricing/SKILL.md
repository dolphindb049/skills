---
name: pricing
description: 债券定价与风险分析技能。提供从数据探索、规范化建模、建库建表、批量定价到可视化的可复用流水线。
license: MIT
metadata:
  author: ddb-user
  version: "1.1.0"
  tags: ["bond", "pricing", "risk", "dolphindb", "visualization"]
---

# 债券定价技能（Pricing Workflow）

本技能遵循 `execute-dlang` 的执行方式，优先使用命令行直连模式，所有核心流程均为 `.dos` 脚本，支持可重复执行与结果落盘（DFS 表），不依赖共享内存表（默认输出到 `dfs://bond_pricing_workflow_v2`）。

## 目录结构

```text
pricing/
├── SKILL.md
├── README.md
├── scripts/
│   ├── 00_cleanup_shared_objects.dos
│   ├── 01_data_discovery.dos
│   ├── 02_prepare_output_schema.dos
│   ├── 03_run_pricing_pipeline.dos
│   └── 04_asset_pricing_detail.dos
├── reference/
│   ├── THEORY.md
│   └── DATA_SOURCES.md
└── python/
    ├── requirements.txt
    └── visualize_pricing.py
```

## 快速执行顺序

```bash
python3 ./skills/execute-dlang/scripts/ddb_runner/execute.py ./skills/pricing/scripts/00_cleanup_shared_objects.dos --host 192.168.100.43 --port 8671 --user admin --password 123456
python3 ./skills/execute-dlang/scripts/ddb_runner/execute.py ./skills/pricing/scripts/01_data_discovery.dos --host 192.168.100.43 --port 8671 --user admin --password 123456
python3 ./skills/execute-dlang/scripts/ddb_runner/execute.py ./skills/pricing/scripts/02_prepare_output_schema.dos --host 192.168.100.43 --port 8671 --user admin --password 123456
python3 ./skills/execute-dlang/scripts/ddb_runner/execute.py ./skills/pricing/scripts/03_run_pricing_pipeline.dos --host 192.168.100.43 --port 8671 --user admin --password 123456
python3 ./skills/execute-dlang/scripts/ddb_runner/execute.py ./skills/pricing/scripts/04_asset_pricing_detail.dos --host 192.168.100.43 --port 8671 --user admin --password 123456
```

## Python 可视化

```bash
pip install -r ./skills/pricing/python/requirements.txt
python3 ./skills/pricing/python/visualize_pricing.py --host 192.168.100.43 --port 8671 --user admin --password 123456 --pricing-date 2025-08-18 --instrument-id 019554.XSHG
```

输出目录默认：`./skills/pricing/python/output`

## 设计原则
- 先建库建表，再写结果。
- 不用 shared table，避免会话生命周期问题。
- 参数集中在脚本顶部，便于批量回放。
- 将理论、数据源、实现和可视化分层维护。
