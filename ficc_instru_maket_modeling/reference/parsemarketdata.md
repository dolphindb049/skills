# MarketData Mapping 说明（为什么这样映射）

MarketData mapping 的核心是：
把“原始收益率/估值序列”重构成标准 Curve 对象，让 `parseMktData` 可以稳定解析。

---

## 1. 为什么不是直接存原表

原表通常是“点状记录”：
- 某日、某期限、某曲线、某值。

而标准 `Curve` 需要的是“曲线快照”：
- `referenceDate`
- `curveName`
- `dates`（节点日期向量）
- `values`（节点值向量）

所以 mapping 的关键动作是：按 `(curveName, referenceDate)` 分组聚合成向量，再 parse。

---

## 2. 两类常见来源及语义转换

### A) 收益率曲线（BondYieldCurveSh -> IrYieldCurve）

| parse 字段 | 常见源字段 | 为什么 | 常见坑 |
|---|---|---|---|
| referenceDate | dataDt | 曲线估值基准日 | 日期不是 DATE |
| curveName | curveName | 统一命名便于风险汇总 | 同义名称未归一 |
| dates | dataDt + termDays | 曲线节点日期 | term 解析错误 |
| values | yieldSpread/100 | 百分比转小数 | 漏 `/100` |
| frequency | 常量 Annual | Curve 构造要求 | 缺字段报错 |

### B) 资产价格曲线（CFETSValuation -> AssetPriceCurve）

| parse 字段 | 常见源字段 | 为什么 | 常见坑 |
|---|---|---|---|
| name | "PRICE_" + secID | 资产独立命名 | 代码特殊字符未清洗 |
| referenceDate | max(tradeDate) | 以最新观测作为基准 | tradeDate 混类型 |
| dates | tradeDate 序列 | 时间轴 | 未排序 |
| values | ytm/100 | 百分比转小数 | 把收益率当价格用 |

---

## 3. curveName 映射为什么必要

不同供应商对同一条曲线可能叫不同名字，例如“国债曲线”“上海清算所国债收益率曲线”。
如果不归一，后续就会出现：
- 同类风险被拆成多条名称；
- 曲线查找失败（名称不匹配策略配置）。

示例：

```dos
curveNameDict = {
    "上海清算所国债收益率曲线": "CNY_TREASURY_BOND",
    "国债": "CNY_TREASURY_BOND",
    "上海清算所国开债收益率曲线": "CNY_CDB_BOND",
    "上海清算所进出口行债收益率曲线": "CNY_EIBC_BOND",
    "上海清算所农发行债收益率曲线": "CNY_ADBC_BOND"
}

def normCurveName(rawName){
    if(rawName in keys(curveNameDict)) return curveNameDict[rawName]
    return "CNY_" + regexReplace(string(rawName), "[^0-9A-Za-z_+\\-]", "_")
}
```

---

## 4. 解析前必须做的结构校验

1) 每条曲线至少 2 个点：
- 少于 2 个点通常无法构成有效插值曲线。

2) 日期向量和数值向量长度一致：
- `count(dates) == count(values)`。

3) 节点日期严格可转 DATE：
- `dates = date(...)`。

4) 节点有序：
- 先按期限或日期升序，避免插值顺序异常。

---

## 5. 小样本验证建议

先跑最新 1-3 天：

```dos
curveTb = loadTable("dfs://instrument_dbtest2", "BondYieldCurveSh")
sample = select * from curveTb where dataDt >= temporalAdd(today(), -3, "d")
```

检查点：
- 映射后 `name` 是否明显重复或异常；
- `dates/values` 是否长度一致；
- fail 是否集中在少数 `curveName`。

---

## 6. 常见报错 -> 根因 -> 修复

1) `Value type of key 'dates' must be a string or date vector`
- 根因：dates 不是 DATE 向量。
- 修复：`dates = date(...)`。

2) `The dict must contain the 'frequency' field`
- 根因：Curve 字典缺 `frequency`。
- 修复：统一补 `Annual`。

3) `referenceDate` 类型错误
- 根因：源字段是 temporal/string。
- 修复：`referenceDate = date(...)`。

---

## 7. 对应可执行模板

- 本地同节点模板：`marketdata_standardize_template.dos`
- 跨节点拉数模板：[`../../ddb-cross-node-sync/reference/ficc_cross_node_pull_template.dos`](../../ddb-cross-node-sync/reference/ficc_cross_node_pull_template.dos)
- 跨节点拉数模板：请看技能 `ddb-cross-node-sync`- 本地同节点模板：`marketdata_standardize_template.dos`## 7. 对应可执行模板---- 修复：`referenceDate = date(...)`。- 根因：源字段是 temporal/string。3) `referenceDate` 类型错误- 修复：统一补 `Annual`。- 根因：Curve 字典缺 `frequency`。2) `The dict must contain the 'frequency' field`- 修复：`dates = date(...)`。- 根因：dates 不是 DATE 向量。1) `Value type of key 'dates' must be a string or date vector`## 6. 常见报错 -> 根因 -> 修复---- fail 是否集中在少数 `curveName`。- `dates/values` 是否长度一致；- 映射后 `name` 是否明显重复或异常；检查点：```sample = select * from curveTb where dataDt >= temporalAdd(today(), -3, "d")curveTb = loadTable("dfs://instrument_dbtest2", "BondYieldCurveSh")```dos先跑最新 1-3 天：## 5. 小样本验证建议---- 先按期限或日期升序，避免插值顺序异常。4) 节点有序：- `dates = date(...)`。3) 节点日期严格可转 DATE：- `count(dates) == count(values)`。2) 日期向量和数值向量长度一致：- 少于 2 个点通常无法构成有效插值曲线。1) 每条曲线至少 2 个点：## 4. 解析前必须做的结构校验---```}    return "CNY_" + regexReplace(string(rawName), "[^0-9A-Za-z_+\\-]", "_")    if(rawName in keys(curveNameDict)) return curveNameDict[rawName]def normCurveName(rawName){}    "上海清算所农发行债收益率曲线": "CNY_ADBC_BOND"    "上海清算所进出口行债收益率曲线": "CNY_EIBC_BOND",    "上海清算所国开债收益率曲线": "CNY_CDB_BOND",    "国债": "CNY_TREASURY_BOND",    "上海清算所国债收益率曲线": "CNY_TREASURY_BOND",curveNameDict = {```dos示例：- 曲线查找失败（名称不匹配策略配置）。- 同类风险被拆成多条名称；如果不归一，后续就会出现：不同供应商对同一条曲线可能叫不同名字，例如“国债曲线”“上海清算所国债收益率曲线”。## 3. curveName 映射为什么必要---| values | ytm/100 | 百分比转小数 | 把收益率当价格用 || dates | tradeDate 序列 | 时间轴 | 未排序 || referenceDate | max(tradeDate) | 以最新观测作为基准 | tradeDate 混类型 || name | "PRICE_" + secID | 资产独立命名 | 代码特殊字符未清洗 ||---|---|---|---|| parse 字段 | 常见源字段 | 为什么 | 常见坑 |### B) 资产价格曲线（CFETSValuation -> AssetPriceCurve）| frequency | 常量 Annual | Curve 构造要求 | 缺字段报错 || values | yieldSpread/100 | 百分比转小数 | 漏 `/100` || dates | dataDt + termDays | 曲线节点日期 | term 解析错误 || curveName | curveName | 统一命名便于风险汇总 | 同义名称未归一 || referenceDate | dataDt | 曲线估值基准日 | 日期不是 DATE ||---|---|---|---|| parse 字段 | 常见源字段 | 为什么 | 常见坑 |### A) 收益率曲线（BondYieldCurveSh -> IrYieldCurve）## 2. 两类常见来源及语义转换---所以 mapping 的关键动作是：按 `(curveName, referenceDate)` 分组聚合成向量，再 parse。- `values`（节点值向量）- `dates`（节点日期向量）- `curveName`- `referenceDate`而标准 `Curve` 需要的是“曲线快照”：- 某日、某期限、某曲线、某值。原表通常是“点状记录”：## 1. 为什么不是直接存原表---把“原始收益率/估值序列”重构成标准 Curve 对象，让 `parseMktData` 可以稳定解析。MarketData mapping 的核心是：
本文给出“原始曲线/估值表 -> MKTDATA（Curve）-> 规范 MarketData 表”的可复用模板。

> 目标：把不同来源曲线统一成
> - `referenceDate`
> - `name`
> - `mktDataType`
> - `data (MKTDATA)`

---

## 1. 规范表结构（目标）

```dos
if(existsDatabase("dfs://marketdata_std")) dropDatabase("dfs://marketdata_std")
db = database("dfs://marketdata_std", VALUE, 2022.01.01..2030.12.31, , "TSDB")

schemaTb = table(1:0,
    `referenceDate`name`mktDataType`data`sourceTable`updateTime,
    [DATE, STRING, STRING, MKTDATA, STRING, TIMESTAMP]
)

db.createPartitionedTable(schemaTb, "MarketData", `referenceDate, sortColumns=`name)
```

---

## 2. 必改 Mapping 点（按你的原始表）

### A. `BondYieldCurveSh` -> `IrYieldCurve`
- `referenceDate <- dataDt`
- `name <- curveName`（通常要经过 curveName 映射字典）
- `dates <- referenceDate + termDays`
- `values <- yieldSpread/100`

### B. `CFETSValuation` -> `AssetPriceCurve`
- `name <- "PRICE_" + secID`
- `referenceDate <- 该 secID 的最新 tradeDate`
- `dates <- tradeDate 序列`
- `values <- ytm/100`

> 注意：
> - `parseMktData` 对日期类型很严格，`referenceDate` 和 `dates` 都必须是 DATE
> - `Curve` 通常要给 `frequency`（例如 `Annual`）

---

## 3. curveName 映射模板

```dos
curveNameDict = {
    "上海清算所国债收益率曲线": "CNY_TREASURY_BOND",
    "国债": "CNY_TREASURY_BOND",
    "上海清算所国开债收益率曲线": "CNY_CDB_BOND",
    "上海清算所进出口行债收益率曲线": "CNY_EIBC_BOND",
    "上海清算所农发行债收益率曲线": "CNY_ADBC_BOND"
}

def normCurveName(rawName){
    if(rawName in keys(curveNameDict)) return curveNameDict[rawName]
    // 默认兜底：把特殊字符替换成下划线
    return "CNY_" + regexReplace(string(rawName), "[^0-9A-Za-z_+\\-]", "_")
}
```

---

## 4. BondYieldCurveSh -> MKTDATA

```dos
curveTb = loadTable("dfs://instrument_dbtest2", "BondYieldCurveSh")
curveInput = select * from curveTb where curveType in ["到期", "即期"] and yieldSpread is not NULL and maturityDesc is not NULL

mktResult = table(1:0, `referenceDate`name`mktDataType`data`sourceTable`updateTime,
                 [DATE, STRING, STRING, MKTDATA, STRING, TIMESTAMP])
mktFail = table(1:0, `name`referenceDate`error, [STRING, DATE, STRING])

curveKeys = select distinct curveName, dataDt from curveInput
for(r in curveKeys){
    try{
        grp = select maturityDesc, yieldSpread from curveInput where curveName=r.curveName and dataDt=r.dataDt
        grp = select double(maturityDesc) as term, yieldSpread from grp where isValid(double(maturityDesc)) and double(maturityDesc)>0 and yieldSpread is not NULL
        if(count(grp)<2) continue
        grp = select * from grp context by term limit -1
        grp = select cast(term*365, INT) as dterm, yieldSpread from grp order by dterm
        dates = date(temporalAdd(r.dataDt, grp.dterm, "d"))
        vals = grp.yieldSpread/100.0

        curve = dict(STRING, ANY)
        curve["mktDataType"] = "Curve"
        curve["curveType"] = "IrYieldCurve"
        curve["referenceDate"] = date(r.dataDt)
        curve["curveName"] = normCurveName(r.curveName)
        curve["currency"] = "CNY"
        curve["dayCountConvention"] = "ActualActualISDA"
        curve["compounding"] = "Compounded"
        curve["frequency"] = "Annual"
        curve["interpMethod"] = "Linear"
        curve["extrapMethod"] = "Flat"
        curve["dates"] = dates
        curve["values"] = vals

        obj = parseMktData(curve)
        row = table(date(r.dataDt) as referenceDate,
                    normCurveName(r.curveName) as name,
                    "Curve" as mktDataType,
                    [obj] as data,
                    "instrument_dbtest2.BondYieldCurveSh" as sourceTable,
                    now()$TIMESTAMP as updateTime)
        mktResult.append!(row)
    }catch(ex){
        mktFail.append!(table(string(r.curveName) as name, date(r.dataDt) as referenceDate, string(ex[0])+":"+string(ex[1]) as error))
    }
}
```

---

## 5. CFETSValuation -> MKTDATA

```dos
cfetsTb = loadTable("dfs://instrument_dbtest2", "CFETSValuation")
cfetsClean = select string(secID) as secID, date(tradeDate) as tradeDate, ytm from cfetsTb where ytm is not NULL
secs = select distinct secID from cfetsClean

for(s in secs.secID){
    try{
        g = select tradeDate, ytm from cfetsClean where secID=s order by tradeDate
        if(count(g)<2) continue

        dates = date(g.tradeDate)
        vals = g.ytm/100.0
        ref = max(dates)
        cname = "PRICE_" + regexReplace(string(s), "[\\.\\-]", "_")

        ac = dict(STRING, ANY)
        ac["mktDataType"] = "Curve"
        ac["curveType"] = "AssetPriceCurve"
        ac["curveName"] = cname
        ac["referenceDate"] = date(ref)
        ac["currency"] = "CNY"
        ac["dayCountConvention"] = "Actual365"
        ac["compounding"] = "Compounded"
        ac["frequency"] = "Annual"
        ac["interpMethod"] = "Linear"
        ac["extrapMethod"] = "Flat"
        ac["dates"] = dates
        ac["values"] = vals

        aobj = parseMktData(ac)
        row2 = table(date(ref) as referenceDate,
                     cname as name,
                     "Curve" as mktDataType,
                     [aobj] as data,
                     "instrument_dbtest2.CFETSValuation" as sourceTable,
                     now()$TIMESTAMP as updateTime)
        mktResult.append!(row2)
    }catch(ex){
        mktFail.append!(table(string(s) as name, 1970.01.01 as referenceDate, string(ex[0])+":"+string(ex[1]) as error))
    }
}

loadTable("dfs://marketdata_std", "MarketData").append!(mktResult)
```

---

## 6. 质检 SQL

```dos
select count(*) from loadTable("dfs://marketdata_std", "MarketData")
select sourceTable, count(*) as cnt from loadTable("dfs://marketdata_std", "MarketData") group by sourceTable
select top 50 * from mktFail
```

---

## 7. 常见报错与处理

1. `Value type of key 'dates' must be a string or date vector`
- 处理：`dates = date(...)`，确保是 DATE 向量。

2. `The dict must contain the 'frequency' field`
- 处理：对 Curve 类型补 `frequency`（常用 `Annual`）。

3. `referenceDate` 类型错误
- 处理：统一 `date(referenceDate)`。

---

## 8. 跨节点（8671→7731）建议

在 7731 侧用 `xdb + remoteRun` 拉取原始子集，再本地 parse：
- 优点：所有标准表和 parse 行为统一落在目标节点
- 可参考同目录脚本：`marketdata_standardize_template.dos`
