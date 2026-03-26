# read_google_ads_sheet.py
# Drop this file into your keyword-tool/ folder.
# Then in anomaly_detector.py, replace the call to read_performance_sheet()
# with read_google_ads_sheet() — or call both and concat.

import os
import pandas as pd
import numpy as np
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from credentials_helper import get_credentials_file
import gspread

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Config ────────────────────────────────────────────────────────────────────
GOOGLE_ADS_SHEET_ID  = "1vkVHgBorxZWfeuFPqWLu1frrYZ9_bJnoBzgI_FfoDJM"
GOOGLE_ADS_TAB_NAME  = "anomaly_detector"
# ─────────────────────────────────────────────────────────────────────────────

# Google Ads column → anomaly_detector.py standard column
COLUMN_MAP = {
    "Campaign"      : "Campaign",
    "Ad group"      : "AdGroup",
    "Clicks"        : "Clicks",
    "Impr."         : "Impressions",
    "CTR"           : "CTR",
    "Avg. CPC"      : "CPC",
    "Cost"          : "Spend",
    "Conversions"   : "Conversions",
    "Cost / conv."  : "CPA",
    "Conv. rate"    : "Conversion Rate",
    "Ad status"     : "Ad Status",
    "Status"        : "Status",
    "Ad strength"   : "Ad Strength",
    "Ad type"       : "Ad Type",
    "Currency code" : "Currency",
}

# Columns that need % stripped and /100 conversion (Google exports as "3.45%")
PCT_COLS = {"CTR", "Conv. rate", "Conversion Rate"}

# Columns to coerce to numeric after mapping
NUMERIC_COLS = [
    "Clicks", "Impressions", "CTR", "CPC", "Spend",
    "Conversions", "CPA", "Conversion Rate",
]


def _clean_pct(val):
    """'3.45%' → 0.0345"""
    if isinstance(val, str):
        val = val.replace("%", "").replace(",", "").strip()
    try:
        return float(val) / 100.0
    except (ValueError, TypeError):
        return 0.0


def _clean_num(val):
    if isinstance(val, str):
        val = val.replace(",", "").replace("$", "").strip()
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def get_sheets_client():
    creds = Credentials.from_service_account_file(
        get_credentials_file(), scopes=SCOPES)
    return gspread.authorize(creds)


def read_google_ads_sheet() -> pd.DataFrame:
    """
    Reads Google Ads campaign data from the configured sheet/tab,
    maps columns to anomaly_detector.py standard names,
    and returns a clean DataFrame ready for run_anomaly_detection().
    """
    client      = get_sheets_client()
    spreadsheet = client.open_by_key(GOOGLE_ADS_SHEET_ID)
    ws          = spreadsheet.worksheet(GOOGLE_ADS_TAB_NAME)

    raw  = ws.get_all_values()
    if not raw or len(raw) < 2:
        raise ValueError(f"Sheet '{GOOGLE_ADS_TAB_NAME}' is empty or has no data rows.")

    # Build DataFrame from raw rows (handles duplicate headers safely)
    headers = [h.strip() for h in raw[0]]
    rows    = raw[1:]

    # Filter out Google Ads summary/footer rows (e.g. "Total", empty rows)
    data_rows = []
    for r in rows:
        if not r or all(c.strip() == "" for c in r):
            continue
        first = r[0].strip().lower() if r else ""
        if first in ("total", "totals", ""):
            continue
        data_rows.append(r)

    df = pd.DataFrame(data_rows, columns=headers)

    # Rename columns using map
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Clean percentage columns BEFORE numeric coercion
    for col in PCT_COLS:
        if col in df.columns:
            df[col] = df[col].apply(_clean_pct)

    # Coerce all numeric columns
    for col in NUMERIC_COLS:
        if col in df.columns:
            if col not in PCT_COLS:   # already cleaned above
                df[col] = df[col].apply(_clean_num)

    # Derive missing columns the detector needs
    # Revenue — not in basic Ads export; set 0 (detector handles gracefully)
    if "Revenue" not in df.columns:
        df["Revenue"] = 0.0

    # ROAS — can't compute without Revenue
    if "ROAS" not in df.columns:
        df["ROAS"] = np.where(df["Spend"] > 0, df["Revenue"] / df["Spend"], 0)

    # RPC
    if "RPC" not in df.columns:
        df["RPC"] = np.where(df["Clicks"] > 0, df["Revenue"] / df["Clicks"], 0)

    # Sold — treat Conversions as Sold for PropellerAds-style rules
    if "Sold" not in df.columns:
        df["Sold"] = df.get("Conversions", 0)

    # Coverage / Scrub Rate — not in Ads export; default 0
    for col in ["Coverage", "Sold ScrubRate Total", "Total Searches",
                "Total Bidded Searches", "Quality Score", "Impression Share",
                "Leads", "CPL", "CAC", "LTV", "LTV_CAC_Ratio",
                "Churn Rate", "Retention Rate"]:
        if col not in df.columns:
            df[col] = 0.0

    print(f"✅ Loaded {len(df)} rows from '{GOOGLE_ADS_TAB_NAME}' tab")
    print(f"   Columns: {list(df.columns)}")
    return df


if __name__ == "__main__":
    df = read_google_ads_sheet()
    print(df.head())
    print(df.dtypes)
