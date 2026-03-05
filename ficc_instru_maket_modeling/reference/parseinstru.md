# Instrument Mapping 说明（为什么这样映射）

本文回答两个问题：
1) Instrument mapping 到底在做什么；
2) 为什么必须按这种方式做。

---

## 1. mapping 本质：把“原始字段”变成“可定价定义”

`parseInstrument` 并不关心你的源字段名叫 `secID` 还是 `bondCode`，它关心的是：
- 这是什么资产（`bondType/subType/assetType/productType`）
- 什么时候起息、到期（`start/maturity`）
- 现金流规则是什么（`coupon/frequency/dayCountConvention`）

所以 mapping 的目标是“语义正确”，不是“列名对齐”。

---

## 2. 字段语义映射表（需按源表改）

| parse 字段 | 常见源字段 | 为什么要这样映射 | 常见坑 |
|---|---|---|---|
| instrumentId | secID | 资产唯一标识，后续和持仓/估值关联 | 代码含空格或后缀不一致 |
| bondType | couponTypeCD | 决定解析分支（FixedRateBond/DiscountBond） | 未识别枚举直接 parse 会失败 |
| start | firstAccrDate | 现金流起点，影响应计和贴现 | 不是 DATE 类型 |
| maturity | maturityDate | 现金流终点，影响期限结构 | maturity 早于 start |
| frequency | cpnFreqCD | 决定付息频率和现金流节点 | `MAT`、`0`、空值需兜底 |
| coupon | coupon | 固息债票面利率（通常需 `/100`） | 把 3.2 当成 320% |
| issuePrice | issuePrice | 贴现债核心参数 | DiscountBond 缺失 issuePrice |
| nominal | par | 名义本金 | 字段为空或单位不一致 |
| subType | typeName(+issuer) | 曲线/风险分组标签 | subtype 过粗导致后续聚合失真 |
| creditRating | rating | 信用债定价/分组常用 | 多来源评级冲突未去重 |

---

## 3. 必须做的 4 类转换

### A) 枚举转换（业务分类）

示例：
- `couponTypeCD: FIXED -> FixedRateBond`
- `couponTypeCD: ZERO -> DiscountBond`

原因：`parseInstrument` 接受的是标准枚举，不接受你内部编码。

### B) 单位转换（数学含义）

示例：
- `coupon=3.25`（百分比） -> `0.0325`（小数）

原因：定价函数按小数计算，单位错会产生数量级错误。

### C) 类型转换（引擎约束）

示例：
- `start/maturity/listingDate -> date(...)`

原因：DolphinDB 对 `INSTRUMENT` 字段类型严格，不要依赖隐式转换。

### D) 规则兜底（可运行性）

示例：
- `dayCountConvention` 默认 `ActualActualISDA`
- `frequency` 未知时给 `Annual`（并记日志）

原因：先确保 parse 可执行，再通过失败样本反向细化规则。

---

## 4. 建议的 mapping 函数写法（向量化）

```dos
def getBondType(couponType){
    return iif(couponType=="FIXED","FixedRateBond",
           iif(couponType=="ZERO","DiscountBond",""))
}

def getFreq(freq){
    return iif(freq=="MAT","Once",
           iif(freq=="1PY","Annual",
           iif(freq=="2PY","Semiannual",
           iif(freq=="4PY","Quarterly","Annual"))))
}

def getSubType(typeName, issuer){
    return iif(typeName=="国债" or typeName=="中央国库现金管理", "TREASURY_BOND",
           iif(typeName=="地方政府债", "LOC_GOV_BOND",
           iif(typeName=="同业存单", "NCD", "CORP_BOND")))
}
```

说明：
- 用向量化 `iif`，不要在 select 中混入标量 Python 逻辑。
- 未识别的枚举返回空串，然后在 where 里过滤，避免脏数据进入 parse。

---

## 5. 小样本验证策略（强烈建议）

先取小样本再全量：

```dos
raw = loadTable("dfs://instrument_dbtest2", "instrument")
sample = select top 300 * from raw where firstAccrDate is not NULL and maturityDate is not NULL order by updateTime desc
```

检查点：
- `bondType` 是否仍有空值；
- `start/maturity` 是否都为 DATE；
- 失败是否集中在某几个 `couponTypeCD/typeName`。

---

## 6. 常见报错 -> 根因 -> 修复

1) `Value type of key 'start' must be a string or date scalar`
- 根因：传了 temporal/string 而非 DATE。
- 修复：`d["start"] = date(ins.start)`。

2) `The dict must contain the 'frequency' field`
- 根因：曲线/债券字典缺频率。
- 修复：映射函数补齐，未知值先默认 `Annual`。

3) `bondType` 非法
- 根因：`couponTypeCD` 未覆盖。
- 修复：先扩映射，再把未知值放入 fail 表人工核对。

---

## 7. 对应可执行模板

- 本地同节点模板：`instrument_standardize_template.dos`
- 跨节点拉数模板：[`../../ddb-cross-node-sync/reference/ficc_cross_node_pull_template.dos`](../../ddb-cross-node-sync/reference/ficc_cross_node_pull_template.dos)
- 跨节点拉数模板：请看技能 `ddb-cross-node-sync`- 本地同节点模板：`instrument_standardize_template.dos`## 7. 对应可执行模板---- 修复：先扩映射，再把未知值放入 fail 表人工核对。- 根因：`couponTypeCD` 未覆盖。3) `bondType` 非法- 修复：映射函数补齐，未知值先默认 `Annual`。- 根因：曲线/债券字典缺频率。2) `The dict must contain the 'frequency' field`- 修复：`d["start"] = date(ins.start)`。- 根因：传了 temporal/string 而非 DATE。1) `Value type of key 'start' must be a string or date scalar`## 6. 常见报错 -> 根因 -> 修复---- 失败是否集中在某几个 `couponTypeCD/typeName`。- `start/maturity` 是否都为 DATE；- `bondType` 是否仍有空值；检查点：```sample = select top 300 * from raw where firstAccrDate is not NULL and maturityDate is not NULL order by updateTime descraw = loadTable("dfs://instrument_dbtest2", "instrument")```dos先取小样本再全量：## 5. 小样本验证策略（强烈建议）---- 未识别的枚举返回空串，然后在 where 里过滤，避免脏数据进入 parse。- 用向量化 `iif`，不要在 select 中混入标量 Python 逻辑。说明：```}           iif(typeName=="同业存单", "NCD", "CORP_BOND")))           iif(typeName=="地方政府债", "LOC_GOV_BOND",    return iif(typeName=="国债" or typeName=="中央国库现金管理", "TREASURY_BOND",def getSubType(typeName, issuer){}           iif(freq=="4PY","Quarterly","Annual"))))           iif(freq=="2PY","Semiannual",           iif(freq=="1PY","Annual",    return iif(freq=="MAT","Once",def getFreq(freq){}           iif(couponType=="ZERO","DiscountBond",""))    return iif(couponType=="FIXED","FixedRateBond",def getBondType(couponType){```dos## 4. 建议的 mapping 函数写法（向量化）---原因：先确保 parse 可执行，再通过失败样本反向细化规则。- `frequency` 未知时给 `Annual`（并记日志）- `dayCountConvention` 默认 `ActualActualISDA`示例：### D) 规则兜底（可运行性）原因：DolphinDB 对 `INSTRUMENT` 字段类型严格，不要依赖隐式转换。- `start/maturity/listingDate -> date(...)`示例：### C) 类型转换（引擎约束）原因：定价函数按小数计算，单位错会产生数量级错误。- `coupon=3.25`（百分比） -> `0.0325`（小数）示例：### B) 单位转换（数学含义）原因：`parseInstrument` 接受的是标准枚举，不接受你内部编码。- `couponTypeCD: ZERO -> DiscountBond`- `couponTypeCD: FIXED -> FixedRateBond`示例：### A) 枚举转换（业务分类）## 3. 必须做的 4 类转换---| creditRating | rating | 信用债定价/分组常用 | 多来源评级冲突未去重 || subType | typeName(+issuer) | 曲线/风险分组标签 | subtype 过粗导致后续聚合失真 || nominal | par | 名义本金 | 字段为空或单位不一致 || issuePrice | issuePrice | 贴现债核心参数 | DiscountBond 缺失 issuePrice || coupon | coupon | 固息债票面利率（通常需 `/100`） | 把 3.2 当成 320% || frequency | cpnFreqCD | 决定付息频率和现金流节点 | `MAT`、`0`、空值需兜底 || maturity | maturityDate | 现金流终点，影响期限结构 | maturity 早于 start || start | firstAccrDate | 现金流起点，影响应计和贴现 | 不是 DATE 类型 || bondType | couponTypeCD | 决定解析分支（FixedRateBond/DiscountBond） | 未识别枚举直接 parse 会失败 || instrumentId | secID | 资产唯一标识，后续和持仓/估值关联 | 代码含空格或后缀不一致 ||---|---|---|---|| parse 字段 | 常见源字段 | 为什么要这样映射 | 常见坑 |## 2. 字段语义映射表（需按源表改）---所以 mapping 的目标是“语义正确”，不是“列名对齐”。- 现金流规则是什么（`coupon/frequency/dayCountConvention`）- 什么时候起息、到期（`start/maturity`）- 这是什么资产（`bondType/subType/assetType/productType`）`parseInstrument` 并不关心你的源字段名叫 `secID` 还是 `bondCode`，它关心的是：## 1. mapping 本质：把“原始字段”变成“可定价定义”---2) 为什么必须按这种方式做。1) Instrument mapping 到底在做什么；本文回答两个问题：
本文是“把原始债券/期货等基础信息表解析为 INSTRUMENT 并入规范表”的可复用模板。

> 适用场景：
> - 原始资产基础信息在 `dfs://instrument_dbtest2.instrument`（或同类结构）
> - 目标是产出规范表：`instrumentId + instrumentType + instrument(INSTRUMENT)`
> - 后续用于 `instrumentPricer/portfolioPricer` 等定价函数

---

## 1. 规范表结构（目标）

```dos
if(existsDatabase("dfs://instrument_std")) dropDatabase("dfs://instrument_std")
db = database("dfs://instrument_std", VALUE, ["FixedRateBond","DiscountBond","Other"], , "TSDB")

schemaTb = table(1:0,
    `instrumentId`instrumentType`instrument`isRegular`instrumentName`listingDate`market`sourceTable`updateTime,
    [STRING, STRING, INSTRUMENT, BOOL, STRING, DATE, STRING, STRING, TIMESTAMP]
)

db.createPartitionedTable(schemaTb, "Instrument", `instrumentType, sortColumns=`instrumentId`listingDate)
```

---

## 2. 必改 Mapping 点（按你的原始表）

下面这些映射**不是固定值**，换原始表时必须改：

1. 代码与日期字段
- `instrumentId <- secID`
- `start <- firstAccrDate`
- `maturity <- maturityDate`

2. 枚举字段映射
- `bondType <- couponTypeCD`（例如 `FIXED -> FixedRateBond`, `ZERO -> DiscountBond`）
- `frequency <- cpnFreqCD`（例如 `1PY -> Annual`, `2PY -> Semiannual`）

3. 数值缩放
- `coupon <- coupon / 100`
- `nominal <- par`

4. 业务字段
- `subType <- typeName(+issuer)`
- `creditRating <- rating`（可来自评级表 latest join）

5. 必填兜底
- `DiscountBond` 必须有 `issuePrice`
- `dayCountConvention` 通常先统一 `ActualActualISDA`

---

## 3. 映射函数模板

```dos
def getBondType(couponType){
    return iif(couponType=="FIXED","FixedRateBond",
           iif(couponType=="ZERO","DiscountBond",""))
}

def getFreq(freq){
    return iif(freq=="MAT","Once",
           iif(freq=="1PY","Annual",
           iif(freq=="2PY","Semiannual",
           iif(freq=="4PY","Quarterly","Annual"))))
}

def getSubType(typeName, issuer){
    return iif(typeName=="国债" or typeName=="中央国库现金管理", "TREASURY_BOND",
           iif(typeName=="地方政府债", "LOC_GOV_BOND",
           iif(typeName=="同业存单", "NCD", "CORP_BOND")))
}
```

---

## 4. 原始表转 parseInstrument 输入（向量化）

```dos
rawInst = loadTable("dfs://instrument_dbtest2", "instrument")
rawRating = loadTable("dfs://instrument_dbtest2", "getBondRating")

ratingLatest = select secID, rating from rawRating context by secID csort publishDate limit -1

instRated = select a.*, b.rating from rawInst a left join ratingLatest b on a.secID=b.secID

instParsedInput = select
    secID as instrumentId,
    secShortName as instrumentName,
    exchangeCD as market,
    listDate as listingDate,
    getBondType(couponTypeCD) as bondType,
    firstAccrDate as start,
    maturityDate as maturity,
    iif(currencyCD is NULL, "CNY", string(currencyCD)) as currency,
    getFreq(cpnFreqCD) as frequency,
    iif(coupon is NULL, 0.0, coupon/100.0) as coupon,
    iif(par is NULL, 100.0, double(par)) as nominal,
    "Cash" as productType,
    "Bond" as assetType,
    "ActualActualISDA" as dayCountConvention,
    getSubType(typeName, issuer) as subType,
    iif(rating is NULL, "", string(rating)) as creditRating
from instRated
where firstAccrDate is not NULL and maturityDate is not NULL and getBondType(couponTypeCD)!=""
```

---

## 5. 批量 parse + 捕捉失败

```dos
instResult = table(1:0,
    `instrumentId`instrumentType`instrument`isRegular`instrumentName`listingDate`market`sourceTable`updateTime,
    [STRING, STRING, INSTRUMENT, BOOL, STRING, DATE, STRING, STRING, TIMESTAMP]
)
instFail = table(1:0, `instrumentId`error, [STRING, STRING])

for(ins in instParsedInput){
    try{
        d = dict(STRING, ANY)
        d["productType"] = ins.productType
        d["assetType"] = ins.assetType
        d["bondType"] = ins.bondType
        d["instrumentId"] = string(ins.instrumentId)
        d["start"] = date(ins.start)
        d["maturity"] = date(ins.maturity)
        d["dayCountConvention"] = ins.dayCountConvention
        d["frequency"] = ins.frequency
        if(ins.bondType=="DiscountBond") d["issuePrice"] = 100.0 else d["coupon"] = ins.coupon
        d["nominal"] = ins.nominal
        d["currency"] = ins.currency
        d["subType"] = ins.subType
        if(strlen(ins.creditRating)>0) d["creditRating"] = ins.creditRating

        insObj = parseInstrument(d)
        row = table(string(ins.instrumentId) as instrumentId,
                    string(ins.bondType) as instrumentType,
                    [insObj] as instrument,
                    true as isRegular,
                    string(ins.instrumentName) as instrumentName,
                    date(ins.listingDate) as listingDate,
                    string(ins.market) as market,
                    "instrument_dbtest2.instrument" as sourceTable,
                    now()$TIMESTAMP as updateTime)
        instResult.append!(row)
    }catch(ex){
        instFail.append!(table(string(ins.instrumentId) as instrumentId, string(ex[0])+":"+string(ex[1]) as error))
    }
}

loadTable("dfs://instrument_std", "Instrument").append!(instResult)
```

---

## 6. 质检 SQL

```dos
select count(*) as total from loadTable("dfs://instrument_std", "Instrument")
select instrumentType, count(*) as cnt from loadTable("dfs://instrument_std", "Instrument") group by instrumentType
select top 50 * from instFail
```

---

## 7. 常见报错与处理

1. `Value type of key 'start' must be a string or date scalar`
- 处理：`d["start"] = date(ins.start)`，`maturity` 同理。

2. `The dict must contain the 'frequency' field`
- 处理：确保所有债券都填了 `frequency`，并且枚举值合法（如 Annual/Semiannual）。

3. `bondType` 不合法
- 处理：检查 `couponTypeCD -> bondType` 映射，未知值不要直接 parse，先过滤。

---

## 8. 跨节点（8671→7731）建议

如果原表在 8671、规范表在 7731：
- 在 7731 建表
- 用 `xdb + remoteRun` 从 8671 拉取子集
- 在 7731 做 parse + append

可直接参考同目录脚本：`instrument_standardize_template.dos`
