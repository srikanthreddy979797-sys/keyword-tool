import gspread
import os
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheets_client():
    try:
        import streamlit as st
        creds_dict = dict(st.secrets["sheets_credentials"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file(
            "sheets_credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)

def export_to_sheets(df: pd.DataFrame, seed_keyword: str) -> str:
    try:
        client = get_sheets_client()
        sheet_id = os.getenv("SHEETS_MASTER_ID")
        spreadsheet = client.open_by_key(sheet_id)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        tab_title = f"{seed_keyword} {timestamp}"

        # ===== Add new worksheet for this search =====
        try:
            ws = spreadsheet.add_worksheet(title=tab_title, rows=1000, cols=25)
        except Exception:
            ws = spreadsheet.get_worksheet(0)
            ws.clear()

        # ===== Sheet 1: Keyword Research =====
        research_cols = ["keyword", "volume", "cpc", "low_bid", "high_bid",
                        "competition", "competition_index", "intent",
                        "trend_score", "is_rising", "data_source"]
        research_cols = [c for c in research_cols if c in df.columns]
        research_df = df[research_cols].copy()
        headers = [c.replace("_", " ").title() for c in research_cols]

        ws.update([headers] + research_df.fillna("").values.tolist())

        ws.format("A1:Z1", {
            "backgroundColor": {"red": 0.07, "green": 0.47, "blue": 0.93},
            "textFormat": {
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "bold": True
            },
            "horizontalAlignment": "CENTER"
        })

        # ===== Add Ads Editor sheet =====
        ads_tab_title = f"Ads Editor - {seed_keyword}"
        try:
            ws2 = spreadsheet.add_worksheet(title=ads_tab_title, rows=1000, cols=10)
        except Exception:
            ws2 = spreadsheet.get_worksheet(1)
            ws2.clear()

        ads_data = []
        for _, row in df.iterrows():
            intent = row.get("intent", "MOFU")
            match_type = {"BOFU": "Exact", "MOFU": "Phrase", "TOFU": "Broad"}.get(intent, "Phrase")
            ads_data.append([
                f"Campaign - {seed_keyword.title()}",
                f"{intent} - {str(row['keyword'])[:30]}",
                row["keyword"],
                match_type,
                row.get("cpc", 1.0),
                "Enabled",
                intent
            ])

        ads_headers = ["Campaign", "Ad Group", "Keyword", "Match Type",
                      "Max CPC", "Status", "Labels"]
        ws2.update([ads_headers] + ads_data)

        ws2.format("A1:G1", {
            "backgroundColor": {"red": 0.13, "green": 0.55, "blue": 0.13},
            "textFormat": {
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "bold": True
            }
        })

        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        return sheet_url

    except Exception as e:
        return f"Error: {str(e)}"
