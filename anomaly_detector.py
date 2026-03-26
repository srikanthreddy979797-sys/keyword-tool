import os
import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
from typing import Dict, List
import gspread
from dotenv import load_dotenv
from credentials_helper import get_credentials_file

load_dotenv()

PROJECT_ID = "keyword-tool-project-490609"
DATASET = "campaign_performance"
TABLE = "hourly_snapshots"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/bigquery"
]

def get_bq_client():
    creds = Credentials.from_service_account_file(
        get_credentials_file(), scopes=SCOPES)
    return bigquery.Client(project=PROJECT_ID, credentials=creds)

def get_sheets_client():
    creds = Credentials.from_service_account_file(
        get_credentials_file(), scopes=SCOPES)
    return gspread.authorize(creds)

def read_performance_sheet() -> pd.DataFrame:
    client = get_sheets_client()
    sheet_id = os.getenv("PERFORMANCE_SHEET_ID")
    spreadsheet = client.open_by_key(sheet_id)
    ws = spreadsheet.sheet1
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = [c.strip() for c in df.columns]

    numeric_cols = [
        "Impressions", "Clicks", "Spend", "Conversions", "Revenue",
        "CPC", "CTR", "CPA", "ROAS", "Conversion Rate",
        "Quality Score", "Impression Share", "Lost IS Budget",
        "Lost IS Rank", "View Through Conversions",
        "Sold", "Outbound Total", "Outbound NBot",
        "Sold ScrubRate Total", "Sold ScrubRate NBot",
        "RPC", "Coverage", "Bought",
        "Inbound Total", "Inbound NBot",
        "Bought ScrubRate Total", "Bought ScrubRate NBot",
        "opCTR", "opCTR Total", "opCTR NBot",
        "Total Searches", "Total Bidded Searches",
        "Leads", "CPL", "CAC", "LTV", "LTV_CAC_Ratio",
        "Churn Rate", "Retention Rate"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Calculate derived metrics if raw columns exist
    if "Clicks" in df.columns and "Impressions" in df.columns:
        df["CTR"] = np.where(df["Impressions"] > 0,
                              df["Clicks"] / df["Impressions"], 0)
    if "Spend" in df.columns and "Clicks" in df.columns:
        df["CPC"] = np.where(df["Clicks"] > 0,
                              df["Spend"] / df["Clicks"], 0)
    if "Spend" in df.columns and "Conversions" in df.columns:
        df["CPA"] = np.where(df["Conversions"] > 0,
                              df["Spend"] / df["Conversions"], 0)
    if "Revenue" in df.columns and "Spend" in df.columns:
        df["ROAS"] = np.where(df["Spend"] > 0,
                               df["Revenue"] / df["Spend"], 0)
    if "Conversions" in df.columns and "Clicks" in df.columns:
        df["Conversion Rate"] = np.where(df["Clicks"] > 0,
                                          df["Conversions"] / df["Clicks"], 0)

    # Map existing columns to standard names if needed
    if "Bought" in df.columns and "Clicks" not in df.columns:
        df["Clicks"] = df["Bought"]
    if "Sold" in df.columns and "Conversions" not in df.columns:
        df["Conversions"] = df["Sold"]
    if "Revenue" not in df.columns and "RPC" in df.columns:
        df["Revenue"] = df["RPC"] * df.get("Clicks", df.get("Bought", 0))

    return df

def create_bq_dataset_if_needed():
    client = get_bq_client()
    dataset_ref = f"{PROJECT_ID}.{DATASET}"
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "asia-south1"
        client.create_dataset(dataset)

def create_bq_table_if_needed():
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    schema = [
        bigquery.SchemaField("snapshot_time", "TIMESTAMP"),
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("campaign", "STRING"),
        bigquery.SchemaField("ad_group", "STRING"),
        bigquery.SchemaField("site", "STRING"),
        bigquery.SchemaField("source", "STRING"),
        bigquery.SchemaField("impressions", "FLOAT64"),
        bigquery.SchemaField("clicks", "FLOAT64"),
        bigquery.SchemaField("spend", "FLOAT64"),
        bigquery.SchemaField("conversions", "FLOAT64"),
        bigquery.SchemaField("revenue", "FLOAT64"),
        bigquery.SchemaField("cpc", "FLOAT64"),
        bigquery.SchemaField("ctr", "FLOAT64"),
        bigquery.SchemaField("cpa", "FLOAT64"),
        bigquery.SchemaField("roas", "FLOAT64"),
        bigquery.SchemaField("conversion_rate", "FLOAT64"),
        bigquery.SchemaField("quality_score", "FLOAT64"),
        bigquery.SchemaField("impression_share", "FLOAT64"),
        bigquery.SchemaField("leads", "FLOAT64"),
        bigquery.SchemaField("cpl", "FLOAT64"),
        bigquery.SchemaField("cac", "FLOAT64"),
        bigquery.SchemaField("ltv", "FLOAT64"),
        bigquery.SchemaField("ltv_cac_ratio", "FLOAT64"),
        bigquery.SchemaField("churn_rate", "FLOAT64"),
        bigquery.SchemaField("retention_rate", "FLOAT64"),
        bigquery.SchemaField("coverage", "FLOAT64"),
        bigquery.SchemaField("scrub_rate", "FLOAT64"),
    ]
    try:
        client.get_table(table_ref)
    except Exception:
        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="snapshot_date"
        )
        client.create_table(table)

def save_to_bigquery(df: pd.DataFrame):
    create_bq_dataset_if_needed()
    create_bq_table_if_needed()
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    now = datetime.utcnow()
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "snapshot_time": now.isoformat(),
            "snapshot_date": str(date.today()),
            "campaign": str(row.get("Campaign", "")),
            "ad_group": str(row.get("AdGroup", "")),
            "site": str(row.get("Site", "")),
            "source": str(row.get("Source", "")),
            "impressions": float(row.get("Impressions", row.get("Inbound Total", 0))),
            "clicks": float(row.get("Clicks", row.get("Bought", 0))),
            "spend": float(row.get("Spend", 0)),
            "conversions": float(row.get("Conversions", row.get("Sold", 0))),
            "revenue": float(row.get("Revenue", 0)),
            "cpc": float(row.get("CPC", row.get("Avg CPC", 0))),
            "ctr": float(row.get("CTR", row.get("opCTR Total", 0))),
            "cpa": float(row.get("CPA", 0)),
            "roas": float(row.get("ROAS", 0)),
            "conversion_rate": float(row.get("Conversion Rate", 0)),
            "quality_score": float(row.get("Quality Score", 0)),
            "impression_share": float(row.get("Impression Share", 0)),
            "leads": float(row.get("Leads", 0)),
            "cpl": float(row.get("CPL", 0)),
            "cac": float(row.get("CAC", 0)),
            "ltv": float(row.get("LTV", 0)),
            "ltv_cac_ratio": float(row.get("LTV_CAC_Ratio", 0)),
            "churn_rate": float(row.get("Churn Rate", 0)),
            "retention_rate": float(row.get("Retention Rate", 0)),
            "coverage": float(row.get("Coverage", 0)),
            "scrub_rate": float(row.get("Sold ScrubRate Total", 0)),
        })
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        print(f"BQ errors: {errors}")

def get_historical_data(days: int = 7) -> pd.DataFrame:
    try:
        client = get_bq_client()
        query = f"""
        SELECT * FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
        WHERE snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY snapshot_time DESC
        """
        return client.query(query).to_dataframe()
    except Exception as e:
        print(f"No history: {e}")
        return pd.DataFrame()

def run_anomaly_detection(current_df: pd.DataFrame,
                           history_df: pd.DataFrame) -> Dict:
    alerts = {"CRITICAL": [], "WARNING": [], "INFO": []}
    has_history = not history_df.empty

    # Aggregate current snapshot
    def safe_sum(col):
        return float(current_df[col].sum()) if col in current_df.columns else 0
    def safe_mean(col):
        return float(current_df[col].mean()) if col in current_df.columns else 0
    def safe_wavg(num_col, den_col):
        n = current_df[num_col].sum() if num_col in current_df.columns else 0
        d = current_df[den_col].sum() if den_col in current_df.columns else 0
        return float(n / d) if d > 0 else 0

    curr = {
        "impressions": safe_sum("Impressions"),
        "clicks": safe_sum("Clicks"),
        "spend": safe_sum("Spend"),
        "conversions": safe_sum("Conversions"),
        "revenue": safe_sum("Revenue"),
        "cpc": safe_wavg("Spend", "Clicks"),
        "ctr": safe_wavg("Clicks", "Impressions"),
        "cpa": safe_wavg("Spend", "Conversions"),
        "roas": safe_wavg("Revenue", "Spend"),
        "conv_rate": safe_wavg("Conversions", "Clicks"),
        "quality_score": safe_mean("Quality Score"),
        "impression_share": safe_mean("Impression Share"),
        "leads": safe_sum("Leads"),
        "cpl": safe_wavg("Spend", "Leads"),
        "cac": safe_mean("CAC"),
        "ltv": safe_mean("LTV"),
        "ltv_cac": safe_mean("LTV_CAC_Ratio"),
        "churn_rate": safe_mean("Churn Rate"),
        "retention_rate": safe_mean("Retention Rate"),
        "coverage": safe_mean("Coverage"),
        "scrub_rate": safe_mean("Sold ScrubRate Total"),
        "total_searches": safe_sum("Total Searches"),
        "bidded_searches": safe_sum("Total Bidded Searches"),
    }

    # Previous snapshot for comparison
    prev = {}
    if has_history:
        latest = history_df.sort_values(
            "snapshot_time", ascending=False).iloc[0]
        prev = {
            "spend": float(latest.get("spend", 0)),
            "revenue": float(latest.get("revenue", 0)),
            "cpc": float(latest.get("cpc", 0)),
            "ctr": float(latest.get("ctr", 0)),
            "cpa": float(latest.get("cpa", 0)),
            "roas": float(latest.get("roas", 0)),
            "conv_rate": float(latest.get("conversion_rate", 0)),
            "impressions": float(latest.get("impressions", 0)),
            "clicks": float(latest.get("clicks", 0)),
            "conversions": float(latest.get("conversions", 0)),
        }

    # 7-day averages
    avg7 = {}
    if has_history and len(history_df) >= 3:
        avg7 = {
            "roas": float(history_df["roas"].mean()),
            "cpa": float(history_df["cpa"].mean()),
            "ctr": float(history_df["ctr"].mean()),
            "cpc": float(history_df["cpc"].mean()),
            "conv_rate": float(history_df["conversion_rate"].mean()),
            "revenue": float(history_df["revenue"].mean()),
        }

    def pct_change(curr_val, prev_val):
        if prev_val and prev_val > 0:
            return (curr_val - prev_val) / prev_val * 100
        return 0

    def add_alert(level, metric, message, current, previous, rule):
        alerts[level].append({
            "metric": metric,
            "message": message,
            "current": current,
            "previous": previous,
            "rule": rule
        })

    # ============ CRITICAL ============

    # ROAS dropped > 25% vs previous snapshot
    if prev.get("roas", 0) > 0:
        pct = pct_change(curr["roas"], prev["roas"])
        if pct < -25:
            add_alert("CRITICAL", "ROAS",
                f"ROAS dropped {abs(pct):.1f}% vs previous snapshot",
                f"{curr['roas']:.2f}x", f"{prev['roas']:.2f}x",
                "ROAS dropped > 25% vs previous snapshot")

    # ROAS dropped > 20% vs 7-day average
    if avg7.get("roas", 0) > 0:
        pct = pct_change(curr["roas"], avg7["roas"])
        if pct < -20:
            add_alert("CRITICAL", "ROAS",
                f"ROAS dropped {abs(pct):.1f}% vs 7-day average",
                f"{curr['roas']:.2f}x", f"{avg7['roas']:.2f}x",
                "ROAS dropped > 20% vs 7-day average")

    # CPA spiked > 30% vs previous snapshot
    if prev.get("cpa", 0) > 0:
        pct = pct_change(curr["cpa"], prev["cpa"])
        if pct > 30:
            add_alert("CRITICAL", "CPA",
                f"CPA spiked {abs(pct):.1f}% vs previous snapshot",
                f"${curr['cpa']:.2f}", f"${prev['cpa']:.2f}",
                "CPA spiked > 30% vs previous snapshot")

    # CPC spiked > 30% vs 7-day average
    if avg7.get("cpc", 0) > 0:
        pct = pct_change(curr["cpc"], avg7["cpc"])
        if pct > 30:
            add_alert("CRITICAL", "CPC",
                f"CPC spiked {abs(pct):.1f}% vs 7-day average",
                f"${curr['cpc']:.2f}", f"${avg7['cpc']:.2f}",
                "CPC spiked > 30% vs 7-day average")

    # Revenue dropped > 30% vs previous snapshot
    if prev.get("revenue", 0) > 0:
        pct = pct_change(curr["revenue"], prev["revenue"])
        if pct < -30:
            add_alert("CRITICAL", "Revenue",
                f"Revenue dropped {abs(pct):.1f}% vs previous snapshot",
                f"${curr['revenue']:,.2f}", f"${prev['revenue']:,.2f}",
                "Revenue dropped > 30% vs previous snapshot")

    # CTR dropped > 30% vs 7-day average
    if avg7.get("ctr", 0) > 0:
        pct = pct_change(curr["ctr"], avg7["ctr"])
        if pct < -30:
            add_alert("CRITICAL", "CTR",
                f"CTR dropped {abs(pct):.1f}% vs 7-day average",
                f"{curr['ctr']*100:.2f}%", f"{avg7['ctr']*100:.2f}%",
                "CTR dropped > 30% vs 7-day average")

    # Impression Share dropped below 40%
    if curr["impression_share"] > 0 and curr["impression_share"] < 0.40:
        add_alert("CRITICAL", "Impression Share",
            f"Impression Share below 40% — losing significant auction volume",
            f"{curr['impression_share']*100:.1f}%", "40% threshold",
            "Impression Share below 40%")

    # Coverage dropped below 70%
    if curr["coverage"] > 0 and curr["coverage"] < 0.70:
        add_alert("CRITICAL", "Coverage",
            f"Feed coverage dropped below 70%",
            f"{curr['coverage']*100:.1f}%", "70% threshold",
            "Coverage below 70%")

    # Scrub rate spiked above 35%
    if curr["scrub_rate"] > 0.35:
        add_alert("CRITICAL", "Scrub Rate",
            f"Scrub rate above 35% threshold",
            f"{curr['scrub_rate']*100:.1f}%", "35% threshold",
            "Scrub rate > 35%")

    # ============ WARNING ============

    # Conversion Rate dropped > 20%
    if avg7.get("conv_rate", 0) > 0:
        pct = pct_change(curr["conv_rate"], avg7["conv_rate"])
        if pct < -20:
            add_alert("WARNING", "Conversion Rate",
                f"Conv rate dropped {abs(pct):.1f}% vs 7-day average",
                f"{curr['conv_rate']*100:.2f}%",
                f"{avg7['conv_rate']*100:.2f}%",
                "Conversion Rate dropped > 20%")

    # CPA spiked > 20% vs 7-day average
    if avg7.get("cpa", 0) > 0:
        pct = pct_change(curr["cpa"], avg7["cpa"])
        if pct > 20:
            add_alert("WARNING", "CPA",
                f"CPA elevated {abs(pct):.1f}% vs 7-day average",
                f"${curr['cpa']:.2f}", f"${avg7['cpa']:.2f}",
                "CPA spiked > 20% vs 7-day average")

    # Quality Score dropped below 5
    if curr["quality_score"] > 0 and curr["quality_score"] < 5:
        add_alert("WARNING", "Quality Score",
            f"Avg Quality Score below 5 — affects ad rank and CPC",
            f"{curr['quality_score']:.1f}/10", "5/10 threshold",
            "Quality Score below 5")

    # LTV:CAC ratio dropped below 3
    if curr["ltv_cac"] > 0 and curr["ltv_cac"] < 3.0:
        add_alert("WARNING", "LTV:CAC",
            f"LTV:CAC ratio below 3x — acquisition not profitable long-term",
            f"{curr['ltv_cac']:.2f}x", "3x threshold",
            "LTV:CAC below 3x")

    # Churn Rate spiked above 10%
    if curr["churn_rate"] > 0.10:
        add_alert("WARNING", "Churn Rate",
            f"Churn rate above 10% — review campaign audience quality",
            f"{curr['churn_rate']*100:.1f}%", "10% threshold",
            "Churn Rate > 10%")

    # Bid coverage ratio dropped below 50%
    if curr["total_searches"] > 0:
        bid_ratio = curr["bidded_searches"] / curr["total_searches"]
        if bid_ratio < 0.50:
            add_alert("WARNING", "Bid Coverage",
                f"Bidded/Total searches ratio low",
                f"{bid_ratio*100:.1f}%", "50% threshold",
                "Bid coverage below 50%")

    # ============ INFO ============

    if "Campaign" in current_df.columns:
        camp_df = current_df.copy()

        # Map columns for aggregation
        if "Revenue" not in camp_df.columns:
            camp_df["Revenue"] = 0
        if "Spend" not in camp_df.columns:
            camp_df["Spend"] = 0
        if "Conversions" not in camp_df.columns:
            camp_df["Conversions"] = camp_df.get("Sold", 0)
        if "Clicks" not in camp_df.columns:
            camp_df["Clicks"] = camp_df.get("Bought", 0)

        camp_perf = camp_df.groupby("Campaign").agg(
            revenue=("Revenue", "sum"),
            spend=("Spend", "sum"),
            conversions=("Conversions", "sum"),
            clicks=("Clicks", "sum"),
        ).reset_index()

        camp_perf["roas"] = np.where(
            camp_perf["spend"] > 0,
            camp_perf["revenue"] / camp_perf["spend"], 0)
        camp_perf["cpa"] = np.where(
            camp_perf["conversions"] > 0,
            camp_perf["spend"] / camp_perf["conversions"], 0)
        camp_perf["ctr"] = np.where(
            camp_perf["clicks"] > 0,
            camp_perf["conversions"] / camp_perf["clicks"], 0)

        camp_perf = camp_perf[camp_perf["revenue"] > 0]

        if not camp_perf.empty:
            best = camp_perf.loc[camp_perf["roas"].idxmax()]
            worst = camp_perf.loc[camp_perf["roas"].idxmin()]

            add_alert("INFO", "Best Campaign by ROAS",
                f"{best['Campaign']} — ROAS: {best['roas']:.2f}x | "
                f"CPA: ${best['cpa']:.2f} | Conv: {best['conversions']:.0f}",
                f"{best['roas']:.2f}x", "", "highest ROAS")

            add_alert("INFO", "Worst Campaign by ROAS",
                f"{worst['Campaign']} — ROAS: {worst['roas']:.2f}x | "
                f"CPA: ${worst['cpa']:.2f} | Conv: {worst['conversions']:.0f}",
                f"{worst['roas']:.2f}x", "", "lowest ROAS")

            # CPA leaders
            cpa_df = camp_perf[camp_perf["cpa"] > 0].sort_values("cpa")
            if not cpa_df.empty:
                best_cpa = " | ".join([
                    f"{r['Campaign'][:15]}: ${r['cpa']:.2f}"
                    for _, r in cpa_df.head(3).iterrows()
                ])
                worst_cpa = " | ".join([
                    f"{r['Campaign'][:15]}: ${r['cpa']:.2f}"
                    for _, r in cpa_df.tail(3).iterrows()
                ])
                add_alert("INFO", "Best CPA Campaigns", best_cpa,
                         "", "", "lowest CPA")
                add_alert("INFO", "Worst CPA Campaigns", worst_cpa,
                         "", "", "highest CPA")

            # ROAS ranking
            roas_sorted = camp_perf.sort_values("roas", ascending=False)
            roas_leaders = " | ".join([
                f"{r['Campaign'][:15]}: {r['roas']:.2f}x"
                for _, r in roas_sorted.head(3).iterrows()
            ])
            add_alert("INFO", "ROAS Leaders", roas_leaders,
                     "", "", "top 3 ROAS")

    return alerts


def format_telegram_message(alerts: Dict, summary: Dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_critical = len(alerts["CRITICAL"])
    total_warning = len(alerts["WARNING"])

    if total_critical > 0:
        header = "🚨 *CRITICAL ANOMALIES — ACTION REQUIRED*"
    elif total_warning > 0:
        header = "⚠️ *WARNING — Review Campaigns*"
    else:
        header = "✅ *All Metrics Normal*"

    lines = [
        header, f"🕐 {now}", "",
        "📊 *Snapshot Summary*",
        f"💰 Revenue: ${summary.get('revenue', 0):,.2f}",
        f"💸 Spend: ${summary.get('spend', 0):,.2f}",
        f"📈 ROAS: {summary.get('roas', 0):.2f}x",
        f"🎯 CPA: ${summary.get('cpa', 0):.2f}",
        f"👆 CTR: {summary.get('ctr', 0)*100:.2f}%",
        f"💡 CPC: ${summary.get('cpc', 0):.2f}",
        f"✅ Conversions: {summary.get('conversions', 0):.0f}",
        f"🔍 Impression Share: {summary.get('impression_share', 0)*100:.1f}%",
        f"📊 Quality Score: {summary.get('quality_score', 0):.1f}/10",
        f"🔄 LTV:CAC: {summary.get('ltv_cac', 0):.2f}x",
        f"📉 Churn Rate: {summary.get('churn_rate', 0)*100:.1f}%",
        ""
    ]

    if alerts["CRITICAL"]:
        lines.append("🔴 *CRITICAL ALERTS*")
        for a in alerts["CRITICAL"]:
            lines.append(f"• *{a['metric']}*: {a['message']}")
            lines.append(f"  Now: {a['current']} | Was: {a['previous']}")
        lines.append("")

    if alerts["WARNING"]:
        lines.append("🟡 *WARNING ALERTS*")
        for a in alerts["WARNING"]:
            lines.append(f"• *{a['metric']}*: {a['message']}")
            lines.append(f"  Now: {a['current']} | Was: {a['previous']}")
        lines.append("")

    if alerts["INFO"]:
        lines.append("ℹ️ *Campaign Intel*")
        for a in alerts["INFO"]:
            lines.append(f"• *{a['metric']}*: {a['message']}")

    if total_critical == 0 and total_warning == 0:
        lines.append("No anomalies — all metrics within normal range ✅")

    return "\n".join(lines)