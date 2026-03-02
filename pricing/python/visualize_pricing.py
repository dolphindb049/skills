#!/usr/bin/env python3
"""
参数化可视化：
- 误差分布直方图
- 曲线形状图（贴现 + 利差）
- 单资产价格/风险图
"""

import argparse
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    import dolphindb as ddb
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Please install dolphindb package first: pip install -r requirements.txt") from exc


def run_query(session, script: str) -> pd.DataFrame:
    result = session.run(script)
    if isinstance(result, pd.DataFrame):
        return result
    return pd.DataFrame(result)


def ddb_date_literal(s: str) -> str:
    return s.replace("-", ".")


def fetch_data(session, db_path: str, pricing_date: str, instrument_id: str):
    d = ddb_date_literal(pricing_date)
    q_result = f"select * from loadTable('{db_path}','pricing_result') where pricingDate={d}"
    q_curve = f"select * from loadTable('{db_path}','pricing_curve_points') where pricingDate={d} order by curveDate"
    q_asset = f"select * from loadTable('{db_path}','pricing_result') where pricingDate={d}, instrumentId='{instrument_id}'"
    q_risk = f"select * from loadTable('{db_path}','pricing_risk') where pricingDate={d}, instrumentId='{instrument_id}'"

    return {
        "result": run_query(session, q_result),
        "curve": run_query(session, q_curve),
        "asset": run_query(session, q_asset),
        "risk": run_query(session, q_risk),
    }


def plot_error_distribution(result_df: pd.DataFrame, out_dir: Path):
    fig = px.histogram(result_df, x="diffBp", nbins=40, title="Model vs MarketProxy Error (bp)")
    fig.update_layout(bargap=0.05)
    fig.write_html(out_dir / "error_distribution.html", include_plotlyjs="cdn")


def plot_curve(curve_df: pd.DataFrame, out_dir: Path):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve_df["curveDate"], y=curve_df["discountYield"], mode="lines+markers", name="Discount Yield"))
    fig.add_trace(go.Scatter(x=curve_df["curveDate"], y=curve_df["spreadYield"], mode="lines+markers", name="Spread Yield"))
    fig.update_layout(title="Curve Shape", xaxis_title="Curve Date", yaxis_title="Yield")
    fig.write_html(out_dir / "curve_shape.html", include_plotlyjs="cdn")


def plot_asset(asset_df: pd.DataFrame, risk_df: pd.DataFrame, out_dir: Path):
    if asset_df.empty:
        return

    row = asset_df.iloc[0]
    fig_price = go.Figure(
        data=[
            go.Bar(x=["Issue", "Model", "MarketProxy"], y=[row["issuePrice"], row["modelPrice"], row["marketProxyPrice"]])
        ]
    )
    fig_price.update_layout(title=f"Asset Price Comparison - {row['instrumentId']}")
    fig_price.write_html(out_dir / "asset_price_compare.html", include_plotlyjs="cdn")

    if not risk_df.empty:
        rr = risk_df.iloc[0]
        fig_risk = go.Figure(data=[go.Bar(x=["Delta", "Gamma"], y=[rr["discountCurveDelta"], rr["discountCurveGamma"]])])
        fig_risk.update_layout(title=f"Asset Risk (Delta/Gamma) - {rr['instrumentId']}")
        fig_risk.write_html(out_dir / "asset_risk.html", include_plotlyjs="cdn")


def main():
    parser = argparse.ArgumentParser(description="Visualize DolphinDB bond pricing outputs")
    parser.add_argument("--host", default="192.168.100.43")
    parser.add_argument("--port", type=int, default=8671)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--db-path", default="dfs://bond_pricing_workflow_v2")
    parser.add_argument("--pricing-date", default="2025-08-18")
    parser.add_argument("--instrument-id", default="109400.XSHE")
    parser.add_argument("--out-dir", default="./skills/pricing/python/output")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = ddb.session()
    session.connect(args.host, args.port, args.user, args.password)

    data = fetch_data(session, args.db_path, args.pricing_date, args.instrument_id)

    if data["result"].empty:
        raise RuntimeError("No pricing_result rows found for the given pricing date.")

    plot_error_distribution(data["result"], out_dir)
    plot_curve(data["curve"], out_dir)
    plot_asset(data["asset"], data["risk"], out_dir)

    data["result"].to_csv(out_dir / "pricing_result.csv", index=False)
    data["curve"].to_csv(out_dir / "pricing_curve_points.csv", index=False)
    data["asset"].to_csv(out_dir / "asset_price.csv", index=False)
    data["risk"].to_csv(out_dir / "asset_risk.csv", index=False)

    print(f"Saved visualizations to: {out_dir}")


if __name__ == "__main__":
    main()
