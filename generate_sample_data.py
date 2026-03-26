import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

np.random.seed(42)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Realistic Clicksco-style campaigns
# Structure matches your exact sheet columns
CAMPAIGNS = [
    # Digital Marketing Services
    {
        "campaign": "CW-DM-Brand-Search",
        "product": "Digital Marketing Services",
        "site": "clicksco.com",
        "source": "Brand",
        "ad_groups": [
            {"name": "Brand-Exact", "rpc": 4.20, "sold": 18, "bought": 280,
             "coverage": 0.88, "scrub": 0.04, "searches": 1200, "bidded": 1056},
            {"name": "Brand-Phrase", "rpc": 3.80, "sold": 12, "bought": 190,
             "coverage": 0.85, "scrub": 0.05, "searches": 950, "bidded": 808},
            {"name": "Brand-Services", "rpc": 3.50, "sold": 8, "bought": 145,
             "coverage": 0.82, "scrub": 0.06, "searches": 720, "bidded": 590},
        ]
    },
    {
        "campaign": "CW-DM-Generic-Search",
        "product": "Digital Marketing Services",
        "site": "clicksco.com",
        "source": "Generic",
        "ad_groups": [
            {"name": "Digital-Marketing", "rpc": 2.80, "sold": 22, "bought": 380,
             "coverage": 0.72, "scrub": 0.08, "searches": 2800, "bidded": 2016},
            {"name": "SEO-Services", "rpc": 2.60, "sold": 15, "bought": 290,
             "coverage": 0.68, "scrub": 0.09, "searches": 2200, "bidded": 1496},
            {"name": "PPC-Management", "rpc": 3.10, "sold": 19, "bought": 320,
             "coverage": 0.74, "scrub": 0.07, "searches": 2400, "bidded": 1776},
            {"name": "Social-Media-Mktg", "rpc": 2.40, "sold": 11, "bought": 240,
             "coverage": 0.65, "scrub": 0.10, "searches": 1800, "bidded": 1170},
        ]
    },
    {
        "campaign": "CW-DM-Competitor-Search",
        "product": "Digital Marketing Services",
        "site": "clicksco.com",
        "source": "Competitor",
        "ad_groups": [
            {"name": "vs-Agency-A", "rpc": 2.20, "sold": 8, "bought": 180,
             "coverage": 0.62, "scrub": 0.12, "searches": 1500, "bidded": 930},
            {"name": "vs-Agency-B", "rpc": 2.10, "sold": 6, "bought": 155,
             "coverage": 0.60, "scrub": 0.13, "searches": 1300, "bidded": 780},
            {"name": "Best-Alternative", "rpc": 2.50, "sold": 9, "bought": 195,
             "coverage": 0.64, "scrub": 0.11, "searches": 1600, "bidded": 1024},
        ]
    },
    {
        "campaign": "CW-DM-PMax",
        "product": "Digital Marketing Services",
        "site": "clicksco.com",
        "source": "PMax",
        "ad_groups": [
            {"name": "All-Audiences", "rpc": 3.20, "sold": 25, "bought": 420,
             "coverage": 0.78, "scrub": 0.06, "searches": 3200, "bidded": 2496},
            {"name": "Retargeting", "rpc": 3.80, "sold": 18, "bought": 280,
             "coverage": 0.82, "scrub": 0.05, "searches": 2100, "bidded": 1722},
            {"name": "Similar-Audiences", "rpc": 2.90, "sold": 14, "bought": 310,
             "coverage": 0.75, "scrub": 0.07, "searches": 2400, "bidded": 1800},
        ]
    },

    # SaaS Products
    {
        "campaign": "CW-SaaS-Brand-Search",
        "product": "SaaS",
        "site": "clicksco.com",
        "source": "Brand",
        "ad_groups": [
            {"name": "SaaS-Brand-Exact", "rpc": 3.60, "sold": 14, "bought": 220,
             "coverage": 0.90, "scrub": 0.03, "searches": 980, "bidded": 882},
            {"name": "SaaS-Brand-Phrase", "rpc": 3.20, "sold": 10, "bought": 168,
             "coverage": 0.87, "scrub": 0.04, "searches": 820, "bidded": 713},
        ]
    },
    {
        "campaign": "CW-SaaS-Generic-Search",
        "product": "SaaS",
        "site": "clicksco.com",
        "source": "Generic",
        "ad_groups": [
            {"name": "Marketing-Software", "rpc": 2.40, "sold": 16, "bought": 285,
             "coverage": 0.70, "scrub": 0.08, "searches": 2100, "bidded": 1470},
            {"name": "Automation-Tool", "rpc": 2.60, "sold": 18, "bought": 310,
             "coverage": 0.72, "scrub": 0.07, "searches": 2300, "bidded": 1656},
            {"name": "Analytics-Platform", "rpc": 2.80, "sold": 20, "bought": 340,
             "coverage": 0.74, "scrub": 0.07, "searches": 2500, "bidded": 1850},
            {"name": "Reporting-Tool", "rpc": 2.20, "sold": 12, "bought": 225,
             "coverage": 0.68, "scrub": 0.09, "searches": 1700, "bidded": 1156},
        ]
    },
    {
        "campaign": "CW-SaaS-Features-Search",
        "product": "SaaS",
        "site": "clicksco.com",
        "source": "Features",
        "ad_groups": [
            {"name": "Reporting-Feature", "rpc": 2.90, "sold": 15, "bought": 265,
             "coverage": 0.73, "scrub": 0.06, "searches": 1900, "bidded": 1387},
            {"name": "Automation-Feature", "rpc": 3.10, "sold": 17, "bought": 290,
             "coverage": 0.76, "scrub": 0.06, "searches": 2100, "bidded": 1596},
            {"name": "API-Integrations", "rpc": 2.70, "sold": 13, "bought": 240,
             "coverage": 0.71, "scrub": 0.07, "searches": 1800, "bidded": 1278},
        ]
    },
    {
        "campaign": "CW-SaaS-Retarget-Display",
        "product": "SaaS",
        "site": "clicksco.com",
        "source": "Retargeting",
        "ad_groups": [
            {"name": "Trial-Abandoners", "rpc": 3.40, "sold": 22, "bought": 380,
             "coverage": 0.84, "scrub": 0.04, "searches": 2800, "bidded": 2352},
            {"name": "Pricing-Page", "rpc": 3.80, "sold": 19, "bought": 310,
             "coverage": 0.86, "scrub": 0.04, "searches": 2300, "bidded": 1978},
            {"name": "Demo-Viewers", "rpc": 4.20, "sold": 25, "bought": 420,
             "coverage": 0.88, "scrub": 0.03, "searches": 3100, "bidded": 2728},
        ]
    },

    # Lead Gen — Traffic arbitrage model
    {
        "campaign": "CW-LG-Insurance-UK",
        "product": "Lead Gen",
        "site": "uk.srchhealth.com",
        "source": "PubMatic Display",
        "ad_groups": [
            {"name": "Car-Insurance", "rpc": 0.82, "sold": 68, "bought": 420,
             "coverage": 0.58, "scrub": 0.18, "searches": 3200, "bidded": 1856},
            {"name": "Life-Insurance", "rpc": 0.76, "sold": 52, "bought": 380,
             "coverage": 0.54, "scrub": 0.22, "searches": 2900, "bidded": 1566},
            {"name": "Home-Insurance", "rpc": 0.68, "sold": 45, "bought": 320,
             "coverage": 0.52, "scrub": 0.24, "searches": 2500, "bidded": 1300},
            {"name": "Health-Insurance", "rpc": 0.72, "sold": 58, "bought": 360,
             "coverage": 0.56, "scrub": 0.20, "searches": 2800, "bidded": 1568},
        ]
    },
    {
        "campaign": "CW-LG-Finance-US",
        "product": "Lead Gen",
        "site": "us.srchfinance.com",
        "source": "AppNexus",
        "ad_groups": [
            {"name": "Personal-Loans", "rpc": 0.92, "sold": 72, "bought": 450,
             "coverage": 0.62, "scrub": 0.16, "searches": 3400, "bidded": 2108},
            {"name": "Credit-Cards", "rpc": 0.85, "sold": 65, "bought": 410,
             "coverage": 0.60, "scrub": 0.18, "searches": 3100, "bidded": 1860},
            {"name": "Mortgage", "rpc": 0.78, "sold": 48, "bought": 350,
             "coverage": 0.56, "scrub": 0.22, "searches": 2700, "bidded": 1512},
            {"name": "Refinance", "rpc": 0.88, "sold": 60, "bought": 390,
             "coverage": 0.58, "scrub": 0.20, "searches": 2900, "bidded": 1682},
        ]
    },
    {
        "campaign": "CW-LG-Health-US",
        "product": "Lead Gen",
        "site": "us.srchhealth.com",
        "source": "OpenX",
        "ad_groups": [
            {"name": "Health-Insurance", "rpc": 0.75, "sold": 55, "bought": 380,
             "coverage": 0.55, "scrub": 0.22, "searches": 2900, "bidded": 1595},
            {"name": "Medicare", "rpc": 0.70, "sold": 48, "bought": 340,
             "coverage": 0.52, "scrub": 0.24, "searches": 2600, "bidded": 1352},
            {"name": "Dental-Plans", "rpc": 0.65, "sold": 42, "bought": 310,
             "coverage": 0.50, "scrub": 0.26, "searches": 2400, "bidded": 1200},
            {"name": "Vision-Plans", "rpc": 0.68, "sold": 45, "bought": 325,
             "coverage": 0.52, "scrub": 0.25, "searches": 2500, "bidded": 1300},
        ]
    },
    {
        "campaign": "CW-Display-Retarget-ALL",
        "product": "Lead Gen",
        "site": "clicksco.com",
        "source": "Display",
        "ad_groups": [
            {"name": "All-Visitors", "rpc": 0.52, "sold": 85, "bought": 820,
             "coverage": 0.48, "scrub": 0.28, "searches": 6200, "bidded": 2976},
            {"name": "High-Intent", "rpc": 0.68, "sold": 72, "bought": 650,
             "coverage": 0.55, "scrub": 0.22, "searches": 4800, "bidded": 2640},
            {"name": "Cart-Abandoners", "rpc": 0.82, "sold": 65, "bought": 520,
             "coverage": 0.62, "scrub": 0.18, "searches": 3800, "bidded": 2356},
        ]
    },
]


def add_variance(value: float, pct: float = 0.12) -> float:
    factor = np.random.normal(1.0, pct)
    factor = max(0.75, min(1.35, factor))
    return value * factor


def generate_row(campaign: dict, ag: dict) -> dict:
    sold = max(0, int(add_variance(ag["sold"], 0.15)))
    bought = max(sold, int(add_variance(ag["bought"], 0.12)))
    rpc = max(0.01, round(add_variance(ag["rpc"], 0.10), 5))
    revenue = round(sold * rpc * add_variance(1.0, 0.08), 2)
    coverage = max(0.1, min(1.0, round(add_variance(ag["coverage"], 0.08), 5)))
    scrub_rate = max(0.01, min(0.50, round(add_variance(ag["scrub"], 0.15), 5)))
    total_searches = max(100, int(add_variance(ag["searches"], 0.10)))
    bidded_searches = max(50, int(add_variance(ag["bidded"], 0.10)))
    outbound_total = max(sold, int(bought * add_variance(0.94, 0.04)))
    op_ctr = round(outbound_total / ag["searches"], 5) if ag["searches"] > 0 else 0
    inbound_total = int(total_searches * add_variance(1.1, 0.08))

    return {
        "Sold": sold,
        "Outbound Total": outbound_total,
        "Outbound NBot": int(outbound_total * add_variance(0.95, 0.03)),
        "Sold ScrubRate Total": scrub_rate,
        "Sold ScrubRate NBot": round(scrub_rate * add_variance(0.97, 0.03), 5),
        "Revenue": revenue,
        "RPC": rpc,
        "Coverage": coverage,
        "Site": campaign["site"],
        "Source": campaign["source"],
        "Campaign": campaign["campaign"],
        "AdGroup": ag["name"],
        "Bought": bought,
        "Inbound Total": inbound_total,
        "Inbound NBot": int(inbound_total * add_variance(0.95, 0.03)),
        "Bought ScrubRate Total": round(add_variance(ag["scrub"] * 0.85, 0.15), 5),
        "Bought ScrubRate NBot": round(add_variance(ag["scrub"] * 0.80, 0.15), 5),
        "opCTR": op_ctr,
        "opCTR Total": op_ctr,
        "opCTR NBot": round(op_ctr * add_variance(0.97, 0.03), 5),
        "Total Searches": total_searches,
        "Total Bidded Searches": bidded_searches,
        "Product": campaign["product"],
        "Snapshot": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def generate_dataset() -> pd.DataFrame:
    rows = []
    for campaign in CAMPAIGNS:
        for ag in campaign["ad_groups"]:
            row = generate_row(campaign, ag)
            rows.append(row)

    df = pd.DataFrame(rows)

    total_revenue = df["Revenue"].sum()
    total_sold = df["Sold"].sum()
    total_bought = df["Bought"].sum()
    avg_rpc = df["RPC"].mean()
    avg_coverage = df["Coverage"].mean()
    avg_scrub = df["Sold ScrubRate Total"].mean()

    print(f"\n{'='*50}")
    print(f"SYNTHETIC DATASET SUMMARY")
    print(f"{'='*50}")
    print(f"Total Rows:       {len(df)}")
    print(f"Total Revenue:    ${total_revenue:,.2f}")
    print(f"Total Sold:       {total_sold:,}")
    print(f"Total Bought:     {total_bought:,}")
    print(f"Avg RPC:          ${avg_rpc:.4f}")
    print(f"Avg Coverage:     {avg_coverage*100:.1f}%")
    print(f"Avg Scrub Rate:   {avg_scrub*100:.1f}%")
    print(f"\nBy Product:")

    for product in df["Product"].unique():
        pdf = df[df["Product"] == product]
        print(f"  {product}:")
        print(f"    Revenue: ${pdf['Revenue'].sum():,.2f} | "
              f"Sold: {pdf['Sold'].sum():,} | "
              f"RPC: ${pdf['RPC'].mean():.4f} | "
              f"Coverage: {pdf['Coverage'].mean()*100:.1f}%")

    print(f"\nBy Campaign:")
    for _, grp in df.groupby("Campaign"):
        camp = grp["Campaign"].iloc[0]
        print(f"  {camp}: Rev=${grp['Revenue'].sum():,.2f} | "
              f"Sold={grp['Sold'].sum():,} | "
              f"RPC=${grp['RPC'].mean():.4f}")

    return df


def upload_to_sheet(df: pd.DataFrame, sheet_id: str):
    creds = Credentials.from_service_account_file(
        "sheets_credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    # Clear and upload main sheet
    ws = spreadsheet.sheet1
    ws.clear()
    print(f"\nCleared existing sheet data")

    # Exact column order matching your real sheet
    cols = [
        "Sold", "Outbound Total", "Outbound NBot",
        "Sold ScrubRate Total", "Sold ScrubRate NBot",
        "Revenue", "RPC", "Coverage", "Site", "Source",
        "Campaign", "AdGroup", "Bought", "Inbound Total", "Inbound NBot",
        "Bought ScrubRate Total", "Bought ScrubRate NBot",
        "opCTR", "opCTR Total", "opCTR NBot",
        "Total Searches", "Total Bidded Searches",
        "Product", "Snapshot"
    ]
    cols = [c for c in cols if c in df.columns]
    upload_df = df[cols].fillna(0)

    ws.update([upload_df.columns.tolist()] +
              upload_df.values.tolist())
    print(f"Uploaded {len(upload_df)} rows to sheet")

    # Summary tab
    try:
        try:
            sum_ws = spreadsheet.worksheet("Summary")
            sum_ws.clear()
        except Exception:
            sum_ws = spreadsheet.add_worksheet(
                title="Summary", rows=100, cols=10)

        total_rev = df["Revenue"].sum()
        total_sold = df["Sold"].sum()
        total_bought = df["Bought"].sum()

        summary = [
            ["CLICKSCO DEMO — CAMPAIGN SNAPSHOT", ""],
            ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["", ""],
            ["OVERALL METRICS", ""],
            ["Total Revenue", f"${total_rev:,.2f}"],
            ["Total Sold", f"{total_sold:,}"],
            ["Total Bought", f"{total_bought:,}"],
            ["Avg RPC", f"${df['RPC'].mean():.4f}"],
            ["Avg Coverage", f"{df['Coverage'].mean()*100:.1f}%"],
            ["Avg Scrub Rate", f"{df['Sold ScrubRate Total'].mean()*100:.1f}%"],
            ["Total Searches", f"{df['Total Searches'].sum():,}"],
            ["Total Bidded", f"{df['Total Bidded Searches'].sum():,}"],
            ["", ""],
            ["BY PRODUCT", "Revenue", "Sold", "RPC", "Coverage"],
        ]

        for product in df["Product"].unique():
            pdf = df[df["Product"] == product]
            summary.append([
                product,
                f"${pdf['Revenue'].sum():,.2f}",
                f"{pdf['Sold'].sum():,}",
                f"${pdf['RPC'].mean():.4f}",
                f"{pdf['Coverage'].mean()*100:.1f}%"
            ])

        summary.append(["", ""])
        summary.append(["BY CAMPAIGN", "Revenue", "Sold", "RPC", "Scrub%"])

        for camp, grp in df.groupby("Campaign"):
            summary.append([
                camp,
                f"${grp['Revenue'].sum():,.2f}",
                f"{grp['Sold'].sum():,}",
                f"${grp['RPC'].mean():.4f}",
                f"{grp['Sold ScrubRate Total'].mean()*100:.1f}%"
            ])

        sum_ws.update(summary)
        print("Summary tab created")

    except Exception as e:
        print(f"Summary tab error: {e}")


if __name__ == "__main__":
    SHEET_ID = "1P4HxDToJNW5915oiD05TELwo0CgBlwyDoq4xH5rHnXM"
    print("Generating Clicksco synthetic demo data...")
    df = generate_dataset()
    print("\nUploading to Google Sheets...")
    upload_to_sheet(df, SHEET_ID)
    print("\nDone — sheet ready for Module 4 testing!")