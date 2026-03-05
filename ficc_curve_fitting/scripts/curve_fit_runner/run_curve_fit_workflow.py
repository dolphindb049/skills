#!/usr/bin/env python3
import argparse
from datetime import date

import numpy as np
import pandas as pd
import dolphindb as ddb


TERM_YEAR_MAP = {
    "1M": 1 / 12,
    "3M": 0.25,
    "6M": 0.5,
    "1Y": 1.0,
    "2Y": 2.0,
    "3Y": 3.0,
    "5Y": 5.0,
    "7Y": 7.0,
    "10Y": 10.0,
}

TERM_DDB_MAP = {
    "1M": "1M",
    "3M": "3M",
    "6M": "6M",
    "1Y": "1y",
    "2Y": "2y",
    "3Y": "3y",
    "5Y": "5y",
    "7Y": "7y",
    "10Y": "10y",
}


def parse_args():
    parser = argparse.ArgumentParser(description="FICC curve fitting workflow")
    parser.add_argument("--src-host", default="192.168.100.43")
    parser.add_argument("--src-port", type=int, default=8671)
    parser.add_argument("--tgt-host", default="192.168.100.43")
    parser.add_argument("--tgt-port", type=int, default=7731)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--db-path", default="dfs://curve_fit_skill")
    parser.add_argument("--reference-date", default="")
    parser.add_argument("--curve-name", default="")
    parser.add_argument("--curve-keyword", default="国债")
    parser.add_argument("--terms", default="1M,3M,6M,1Y,2Y,3Y,5Y,7Y,10Y")
    parser.add_argument("--show-details", action="store_true")
    return parser.parse_args()


def connect(host: str, port: int, user: str, password: str):
    sess = ddb.session()
    sess.connect(host, port, user, password)
    return sess


def ddb_date_literal(dt: date):
    return pd.Timestamp(dt).strftime("%Y.%m.%d")


def normalize_terms(raw: str):
    terms = [x.strip().upper() for x in raw.split(",") if x.strip()]
    if not terms:
        raise ValueError("No terms provided")
    bad = [t for t in terms if t not in TERM_YEAR_MAP or t not in TERM_DDB_MAP]
    if bad:
        raise ValueError(f"Unsupported terms: {bad}. Supported: {list(TERM_YEAR_MAP.keys())}")
    return terms


def choose_reference_date(src, reference_date: str):
    if reference_date:
        return pd.to_datetime(reference_date).date()
    dt = src.run(
        'exec max(dataDt) from loadTable("dfs://instrument_dbtest2","BondYieldCurveSh") where curveType=="到期"'
    )
    return pd.to_datetime(dt).date()


def choose_curve_name(src, ref_lit: str, curve_name: str, curve_keyword: str):
    if curve_name:
        return curve_name
    cands = src.run(
        f'''select curveName, count(*) as n
            from loadTable("dfs://instrument_dbtest2","BondYieldCurveSh")
            where dataDt={ref_lit}, curveType=="到期"
            group by curveName order by n desc'''
    )
    if cands.empty:
        raise RuntimeError("No 到期曲线可用")
    for x in cands["curveName"].astype(str).tolist():
        if curve_keyword in x:
            return x
    return str(cands.iloc[0]["curveName"])


def extract_curve_data(src, ref_lit: str, curve_name: str, terms):
    term_list_expr = "[" + ",".join([f'"{x}"' for x in terms]) + "]"
    ytm = src.run(
        f'''select dataDt as referenceDate, curveName, curveType, maturityDesc as termLabel, yieldSpread as y
            from loadTable("dfs://instrument_dbtest2","BondYieldCurveSh")
            where dataDt={ref_lit}, curveName="{curve_name}", curveType=="到期", maturityDesc in {term_list_expr}'''
    )
    spot = src.run(
        f'''select dataDt as referenceDate, curveName, curveType, maturityDesc as termLabel, yieldSpread as y
            from loadTable("dfs://instrument_dbtest2","BondYieldCurveSh")
            where dataDt={ref_lit}, curveName="{curve_name}", curveType=="即期", maturityDesc in {term_list_expr}'''
    )

    for df in (ytm, spot):
        df["referenceDate"] = pd.to_datetime(df["referenceDate"]).dt.date
        df["termLabel"] = df["termLabel"].astype(str).str.upper()
        df["termYears"] = df["termLabel"].map(TERM_YEAR_MAP)
        df.dropna(subset=["termYears"], inplace=True)

    ytm = ytm.sort_values("termYears").drop_duplicates("termLabel", keep="last")
    spot = spot.sort_values("termYears").drop_duplicates("termLabel", keep="last")

    missing = [t for t in terms if t not in set(ytm["termLabel"])]
    if missing:
        raise RuntimeError(f"Missing YTM terms: {missing}")

    raw_curve = pd.concat([ytm, spot], ignore_index=True)[
        ["referenceDate", "curveName", "curveType", "termLabel", "termYears", "y"]
    ].rename(columns={"y": "yield"})
    return ytm, spot, raw_curve


def select_sample_bonds(src, ref_date: date, ref_lit: str, terms, ytm):
    inst = src.run(
        f'''select secID as instrumentId, typeName, typeID, couponTypeCD, cpnFreqCD, coupon,
                   firstAccrDate as startDate, maturityDate
            from loadTable("dfs://instrument_dbtest2","instrument")
            where maturityDate>{ref_lit}, isValid(secID), isValid(firstAccrDate), isValid(maturityDate),
                  couponTypeCD in ["FIXED","ZERO"],
                  (typeName in ["国债","记账式国债","利率债"] or typeID in ["02020101","02020201","02020401"])'''
    )
    if inst.empty:
        raise RuntimeError("No eligible bonds found")

    inst["startDate"] = pd.to_datetime(inst["startDate"]).dt.date
    inst["maturityDate"] = pd.to_datetime(inst["maturityDate"]).dt.date
    inst = inst[inst["startDate"] <= ref_date].copy()
    inst["remainYears"] = (pd.to_datetime(inst["maturityDate"]) - pd.Timestamp(ref_date)).dt.days / 365.0
    inst = inst[inst["remainYears"] > 0].sort_values("remainYears").drop_duplicates("instrumentId", keep="first")

    freq_map = {"1PY": "Annual", "2PY": "Semiannual", "4PY": "Quarterly", "12PY": "Monthly", "MAT": "Once"}
    rows = []
    used = set()
    for t in terms:
        target = TERM_YEAR_MAP[t]
        cand = inst[~inst["instrumentId"].isin(used)].copy()
        if cand.empty:
            break
        cand["gap"] = (cand["remainYears"] - target).abs()
        r = cand.sort_values(["gap", "remainYears"]).iloc[0]
        used.add(r["instrumentId"])

        coupon = 0.0 if pd.isna(r["coupon"]) else float(r["coupon"])
        if coupon > 1:
            coupon /= 100.0

        bond_type = "DiscountBond" if str(r["couponTypeCD"]).upper() == "ZERO" else "FixedRateBond"
        rows.append(
            {
                "referenceDate": ref_date,
                "instrumentId": str(r["instrumentId"]),
                "bondType": bond_type,
                "start": r["startDate"],
                "maturity": r["maturityDate"],
                "issuePrice": 100.0,
                "coupon": coupon if bond_type == "FixedRateBond" else np.nan,
                "frequency": freq_map.get(str(r["cpnFreqCD"]), "Annual"),
                "dayCountConvention": "ActualActualISDA",
                "targetTermYears": float(target),
                "quoteTerm": t,
                "quoteYTM": float(ytm.loc[ytm["termLabel"] == t, "y"].iloc[0]),
            }
        )

    if not rows:
        raise RuntimeError("No sample bonds selected")
    return pd.DataFrame(rows)


def prepare_target_tables(tgt, db_path: str):
    script = f'''
if(!existsDatabase("{db_path}")){{
    db=database("{db_path}", RANGE, [2010.01.01, 2040.01.01]);
    schemaCurve=table(1:0, `referenceDate`curveName`curveType`termLabel`termYears`yield, [DATE,STRING,STRING,STRING,DOUBLE,DOUBLE]);
    db.createPartitionedTable(schemaCurve, `raw_curve, `referenceDate);

    schemaBond=table(1:0, `referenceDate`instrumentId`bondType`start`maturity`issuePrice`coupon`frequency`dayCountConvention`targetTermYears`quoteTerm`quoteYTM,
        [DATE,STRING,STRING,DATE,DATE,DOUBLE,DOUBLE,STRING,STRING,DOUBLE,STRING,DOUBLE]);
    db.createPartitionedTable(schemaBond, `sample_bond, `referenceDate);

    schemaCmp=table(1:0, `referenceDate`curveName`termLabel`benchmarkSpot`fittedSpot`diffBp, [DATE,STRING,STRING,DOUBLE,DOUBLE,DOUBLE]);
    db.createPartitionedTable(schemaCmp, `fit_compare, `referenceDate);
}}
'''
    tgt.run(script)


def upsert_input_data(tgt, db_path: str, ref_lit: str, raw_curve: pd.DataFrame, sample_bond: pd.DataFrame):
    cleanup = f'''
delete from loadTable("{db_path}","raw_curve") where referenceDate={ref_lit};
delete from loadTable("{db_path}","sample_bond") where referenceDate={ref_lit};
delete from loadTable("{db_path}","fit_compare") where referenceDate={ref_lit};
'''
    tgt.run(cleanup)
    tgt.upload({"rawCurvePy": raw_curve, "sampleBondPy": sample_bond})
    tgt.run(
        f'loadTable("{db_path}","raw_curve").append!(rawCurvePy); '
        f'loadTable("{db_path}","sample_bond").append!(sampleBondPy);'
    )


def run_fitting(tgt, db_path: str, ref_lit: str, curve_name: str, terms):
    ddb_terms_expr = "[" + ",".join([TERM_DDB_MAP[t] for t in terms]) + "]"
    fit_script = f'''
refDate={ref_lit};
curveName="{curve_name}";

ytm=select * from loadTable("{db_path}","raw_curve") where referenceDate=refDate, curveName=curveName, curveType=="到期" order by termYears;
bondTb=select * from loadTable("{db_path}","sample_bond") where referenceDate=refDate order by targetTermYears;
if(size(ytm)<4){{throw "Insufficient YTM points";}}
if(size(bondTb)<4){{throw "Insufficient sample bonds";}}

bondsTmp=array(ANY,0);
for(i in 0..(size(bondTb)-1)){{
    d=dict(STRING,ANY);
    d["productType"]="Cash";
    d["assetType"]="Bond";
    d["bondType"]=string(bondTb.bondType[i]);
    d["instrumentId"]=string(bondTb.instrumentId[i]);
    d["start"]=bondTb.start[i];
    d["maturity"]=bondTb.maturity[i];
    d["issuePrice"]=double(bondTb.issuePrice[i]);
    d["dayCountConvention"]=string(bondTb.dayCountConvention[i]);
    if(string(bondTb.bondType[i])!="DiscountBond"){{
        d["coupon"]=double(bondTb.coupon[i]);
        d["frequency"]=string(bondTb.frequency[i]);
    }}
    bondsTmp.append!(d);
}}
bonds=parseInstrument(bondsTmp);

terms={ddb_terms_expr};
quotes=exec yield from ytm / 100.0;
curveBoot=bondYieldCurveBuilder(refDate, `CNY, bonds, terms, quotes, "ActualActualISDA", method="Bootstrap");

spot=select * from loadTable("{db_path}","raw_curve") where referenceDate=refDate, curveName=curveName, curveType=="即期" order by termYears;
pred=curvePredict(curveBoot, spot.termYears);
cmp=select
      take(refDate,size(spot)) as referenceDate,
      take(curveName,size(spot)) as curveName,
      spot.termLabel as termLabel,
      spot.yield/100.0 as benchmarkSpot,
      pred as fittedSpot,
      (pred-spot.yield/100.0)*10000 as diffBp
    from spot;

loadTable("{db_path}","fit_compare").append!(cmp);
select max(abs(diffBp)) as maxAbsBp, avg(abs(diffBp)) as meanAbsBp, count(*) as nPts from cmp;
'''
    return tgt.run(fit_script)


def fetch_details(tgt, db_path: str, ref_lit: str):
    cmp = tgt.run(
        f'''select * from loadTable("{db_path}","fit_compare")
            where referenceDate={ref_lit}
            order by termLabel'''
    )
    bond = tgt.run(
        f'''select * from loadTable("{db_path}","sample_bond")
            where referenceDate={ref_lit}
            order by targetTermYears'''
    )
    return cmp, bond


def main():
    args = parse_args()
    terms = normalize_terms(args.terms)

    src = connect(args.src_host, args.src_port, args.user, args.password)
    tgt = connect(args.tgt_host, args.tgt_port, args.user, args.password)

    ref_date = choose_reference_date(src, args.reference_date)
    ref_lit = ddb_date_literal(ref_date)
    curve_name = choose_curve_name(src, ref_lit, args.curve_name, args.curve_keyword)

    ytm, spot, raw_curve = extract_curve_data(src, ref_lit, curve_name, terms)
    sample_bond = select_sample_bonds(src, ref_date, ref_lit, terms, ytm)

    prepare_target_tables(tgt, args.db_path)
    upsert_input_data(tgt, args.db_path, ref_lit, raw_curve, sample_bond)
    summary = run_fitting(tgt, args.db_path, ref_lit, curve_name, terms)

    print(f"referenceDate={ref_date}")
    print(f"curveName={curve_name}")
    print(f"dbPath={args.db_path}")
    print("fitSummary:")
    print(summary.to_string(index=False))

    if args.show_details:
        cmp, bond = fetch_details(tgt, args.db_path, ref_lit)
        print("\nfitCompare:")
        print(cmp.to_string(index=False))
        print("\nsampleBond:")
        print(bond.to_string(index=False))


if __name__ == "__main__":
    main()
