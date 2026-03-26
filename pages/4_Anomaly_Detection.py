import streamlit as st
import pandas as pd
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from dotenv import load_dotenv
from anomaly_detector import (
    save_to_bigquery,
    get_historical_data,
    run_anomaly_detection,
    format_telegram_message
)
from read_google_ads_sheet import read_google_ads_sheet
from telegram_alerts import send_whatsapp_alert

load_dotenv()

st.set_page_config(
    page_title="Anomaly Detection",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Campaign Anomaly Detection")
st.caption("Reads Google Ads data from Google Sheets → BigQuery → Telegram alerts")

st.info("""
**Data source:** Google Ads campaign report pasted into the `anomaly_detector` tab  
**Sheet:** `1vkVHgBorxZWfeuFPqWLu1frrYZ9_bJnoBzgI_FfoDJM`  
Paste fresh data into the sheet, then click **Run Anomaly Detection**.
""")

st.divider()

# ------------------ STATUS INDICATORS ------------------
st.markdown("### System Status")
col1, col2, col3, col4 = st.columns(4)
col1.success("✅ Google Ads Sheet")
col2.success("✅ BigQuery")
col3.success("✅ Telegram")
col4.success("✅ Anomaly Engine")

st.divider()

# ------------------ ALERT RULES ------------------
st.markdown("### Detection Rules")
rc1, rc2 = st.columns(2)

with rc1:
    st.markdown("#### 🔴 Critical Alerts")
    st.markdown("""
    - ROAS dropped > 25% vs previous snapshot
    - ROAS dropped > 20% vs 7-day average
    - CPA spiked > 30% vs previous snapshot
    - CPC spiked > 30% vs 7-day average
    - Revenue dropped > 30% vs previous snapshot
    - CTR dropped > 30% vs 7-day average
    - Impression Share below 40%
    - Coverage below 70%
    - Scrub rate above 35%
    """)

with rc2:
    st.markdown("#### 🟡 Warning Alerts")
    st.markdown("""
    - Conversion Rate dropped > 20% vs 7-day average
    - CPA spiked > 20% vs 7-day average
    - Quality Score below 5
    - LTV:CAC ratio below 3x
    - Churn Rate above 10%
    - Bid coverage below 50%
    """)

st.divider()

# ------------------ RUN DETECTION ------------------
if st.button("🔍 Run Anomaly Detection", use_container_width=True):

    # Step 1 — Read Google Ads sheet
    with st.spinner("Reading Google Ads data from sheet..."):
        try:
            current_df = read_google_ads_sheet()
            st.success(f"✅ Loaded {len(current_df)} rows from 'anomaly_detector' tab")
            with st.expander("Preview loaded data"):
                st.dataframe(current_df.head(10), use_container_width=True)
        except Exception as e:
            st.error(f"Failed to read sheet: {e}")
            st.stop()

    # Step 2 — Save to BigQuery
    with st.spinner("Saving snapshot to BigQuery..."):
        try:
            save_to_bigquery(current_df)
            st.success("✅ Snapshot saved to BigQuery")
        except Exception as e:
            st.warning(f"BigQuery: {e}")

    # Step 3 — Load history
    with st.spinner("Loading historical data..."):
        history_df = get_historical_data(days=7)
        if history_df.empty:
            st.info("ℹ️ First run — no history yet. Anomaly comparison available after 2+ runs.")
        else:
            st.success(f"✅ {len(history_df)} historical snapshots loaded")

    # Step 4 — Run detection
    with st.spinner("Running anomaly detection..."):
        alerts = run_anomaly_detection(current_df, history_df)

    # Step 5 — Results
    st.divider()
    st.markdown("### Detection Results")

    total_critical = len(alerts["CRITICAL"])
    total_warning  = len(alerts["WARNING"])
    total_info     = len(alerts["INFO"])

    ac1, ac2, ac3 = st.columns(3)
    ac1.metric("Critical Alerts", total_critical)
    ac2.metric("Warning Alerts",  total_warning)
    ac3.metric("Info Signals",    total_info)

    if total_critical == 0 and total_warning == 0:
        st.success("✅ All metrics within normal range — no anomalies detected")

    if alerts["CRITICAL"]:
        st.markdown("#### 🔴 Critical Alerts")
        for a in alerts["CRITICAL"]:
            with st.expander(f"🔴 {a['metric']} — {a['rule']}", expanded=True):
                st.error(a["message"])
                st.write(f"**Now:** {a['current']} | **Was:** {a['previous']}")
                st.write(f"**Rule:** {a['rule']}")

    if alerts["WARNING"]:
        st.markdown("#### 🟡 Warning Alerts")
        for a in alerts["WARNING"]:
            with st.expander(f"🟡 {a['metric']} — {a['rule']}"):
                st.warning(a["message"])
                st.write(f"**Now:** {a['current']} | **Was:** {a['previous']}")
                st.write(f"**Rule:** {a['rule']}")

    if alerts["INFO"]:
        st.markdown("#### ℹ️ Campaign Intelligence")
        for a in alerts["INFO"]:
            st.write(f"**{a['metric']}:** {a['message']}")

    # Step 6 — Telegram
    st.divider()
    st.markdown("### Telegram Alert")

    summary = {
        "revenue"          : float(current_df["Revenue"].sum()) if "Revenue" in current_df.columns else 0,
        "spend"            : float(current_df["Spend"].sum()) if "Spend" in current_df.columns else 0,
        "roas"             : float(current_df["ROAS"].mean()) if "ROAS" in current_df.columns else 0,
        "cpa"              : float(current_df["CPA"].mean()) if "CPA" in current_df.columns else 0,
        "ctr"              : float(current_df["CTR"].mean()) if "CTR" in current_df.columns else 0,
        "cpc"              : float(current_df["CPC"].mean()) if "CPC" in current_df.columns else 0,
        "conversions"      : float(current_df["Conversions"].sum()) if "Conversions" in current_df.columns else 0,
        "impression_share" : 0,
        "quality_score"    : 0,
        "ltv_cac"          : 0,
        "churn_rate"       : 0,
    }
    message = format_telegram_message(alerts, summary)

    st.markdown("**Message being sent:**")
    st.code(message)

    with st.spinner("Sending Telegram alert..."):
        success = send_whatsapp_alert(message)
        if success:
            st.success("✅ Telegram alert sent!")
        else:
            st.warning("Telegram not configured or failed to send")

# ------------------ SHEET SETUP GUIDE ------------------
st.divider()
st.markdown("### How to update data")
st.markdown("""
1. Download your Google Ads campaign report as CSV
2. Open the sheet: [anomaly_detector tab](https://docs.google.com/spreadsheets/d/1vkVHgBorxZWfeuFPqWLu1frrYZ9_bJnoBzgI_FfoDJM/edit)
3. Paste the full CSV data into the `anomaly_detector` tab (replace old data)
4. Come back here and click **Run Anomaly Detection**

**Expected columns in the sheet:**
`Ad status, Campaign, Ad group, Status, Clicks, Impr., CTR, Avg. CPC, Cost, Conv. rate, Conversions, Cost / conv.`
""")
