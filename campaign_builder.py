import os
import json
from groq import Groq
from dotenv import load_dotenv
import pandas as pd
from typing import List, Dict

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def build_campaign_structure(keywords_data: List[Dict], seed_keyword: str,
                              campaign_goal: str = "conversions",
                              daily_budget: float = 500.0,
                              target_country: str = "IN") -> Dict:
    try:
        kw_list = [
            f"{k['keyword']} (vol:{k['volume']}, cpc:{k['cpc']}, intent:{k['intent']}, score:{k.get('opportunity_score', 0)})"
            for k in keywords_data[:50]
        ]

        prompt = f"""You are a senior Google Ads strategist. Build a complete campaign structure for "{seed_keyword}".

Campaign Goal: {campaign_goal}
Daily Budget: ${daily_budget}
Country: {target_country}

Keywords available:
{chr(10).join(kw_list)}

Return ONLY this JSON structure, nothing else, no markdown:
{{
    "campaign": {{
        "name": "campaign name",
        "type": "Search",
        "goal": "{campaign_goal}",
        "daily_budget": {daily_budget},
        "bid_strategy": "Target CPA or Maximize Conversions or Manual CPC",
        "target_cpa": 0,
        "networks": ["Search", "Search Partners"],
        "languages": ["English"],
        "locations": ["{target_country}"],
        "ad_schedule": "recommended schedule",
        "device_bid_adjustments": {{
            "mobile": 0,
            "tablet": -20,
            "desktop": 0
        }}
    }},
    "ad_groups": [
        {{
            "name": "ad group name",
            "intent": "BOFU or MOFU or TOFU",
            "theme": "what this targets",
            "max_cpc": 0.0,
            "keywords": [
                {{"keyword": "kw1", "match_type": "Exact"}},
                {{"keyword": "kw2", "match_type": "Phrase"}},
                {{"keyword": "kw3", "match_type": "Broad"}}
            ],
            "negative_keywords": ["neg1", "neg2"],
            "ads": [
                {{
                    "headline_1": "under 30 chars",
                    "headline_2": "under 30 chars",
                    "headline_3": "under 30 chars",
                    "description_1": "under 90 chars",
                    "description_2": "under 90 chars",
                    "final_url": "https://example.com/landing-page",
                    "display_url_path1": "path1",
                    "display_url_path2": "path2"
                }}
            ]
        }}
    ],
    "campaign_negative_keywords": ["neg1", "neg2", "neg3", "neg4", "neg5"],
    "budget_allocation": {{
        "BOFU": 60,
        "MOFU": 30,
        "TOFU": 10
    }},
    "recommendations": [
        "recommendation 1",
        "recommendation 2",
        "recommendation 3"
    ]
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )

        text = response.choices[0].message.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return json.loads(text)

    except Exception as e:
        return {"error": str(e)}


def campaign_to_ads_editor_format(campaign_structure: Dict) -> Dict[str, pd.DataFrame]:
    campaign = campaign_structure.get("campaign", {})
    ad_groups = campaign_structure.get("ad_groups", [])
    campaign_negs = campaign_structure.get("campaign_negative_keywords", [])
    campaign_name = campaign.get("name", "Campaign 1")

    keywords_rows = []
    ads_rows = []
    negatives_rows = []

    for ag in ad_groups:
        ag_name = ag.get("name", "Ad Group")
        max_cpc = ag.get("max_cpc", 1.0)

        # Keywords
        for kw in ag.get("keywords", []):
            keywords_rows.append({
                "Campaign": campaign_name,
                "Ad Group": ag_name,
                "Keyword": kw.get("keyword", ""),
                "Match Type": kw.get("match_type", "Phrase"),
                "Max CPC": max_cpc,
                "Status": "Enabled",
                "Intent": ag.get("intent", ""),
                "Theme": ag.get("theme", "")
            })

        # Ads
        for ad in ag.get("ads", []):
            ads_rows.append({
                "Campaign": campaign_name,
                "Ad Group": ag_name,
                "Headline 1": ad.get("headline_1", ""),
                "Headline 2": ad.get("headline_2", ""),
                "Headline 3": ad.get("headline_3", ""),
                "Description 1": ad.get("description_1", ""),
                "Description 2": ad.get("description_2", ""),
                "Final URL": ad.get("final_url", ""),
                "Path 1": ad.get("display_url_path1", ""),
                "Path 2": ad.get("display_url_path2", ""),
                "Status": "Enabled"
            })

        # Ad group negatives
        for neg in ag.get("negative_keywords", []):
            negatives_rows.append({
                "Campaign": campaign_name,
                "Ad Group": ag_name,
                "Keyword": neg,
                "Match Type": "Negative Exact",
                "Level": "Ad Group"
            })

    # Campaign level negatives
    for neg in campaign_negs:
        negatives_rows.append({
            "Campaign": campaign_name,
            "Ad Group": "",
            "Keyword": neg,
            "Match Type": "Negative Exact",
            "Level": "Campaign"
        })

    return {
        "keywords": pd.DataFrame(keywords_rows),
        "ads": pd.DataFrame(ads_rows),
        "negatives": pd.DataFrame(negatives_rows)
    }


def export_campaign_to_sheets(campaign_structure: Dict,
                               sheets_client, sheet_id: str) -> str:
    try:
        from datetime import datetime
        import gspread

        dfs = campaign_to_ads_editor_format(campaign_structure)
        campaign_name = campaign_structure.get("campaign", {}).get("name", "Campaign")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        spreadsheet = sheets_client.open_by_key(sheet_id)

        tab_configs = [
            ("keywords", f"Keywords - {timestamp}",
             {"red": 0.07, "green": 0.47, "blue": 0.93}),
            ("ads", f"Ads - {timestamp}",
             {"red": 0.13, "green": 0.55, "blue": 0.13}),
            ("negatives", f"Negatives - {timestamp}",
             {"red": 0.8, "green": 0.1, "blue": 0.1})
        ]

        for key, tab_name, color in tab_configs:
            df = dfs[key]
            if df.empty:
                continue
            try:
                ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)
            except Exception:
                ws = spreadsheet.get_worksheet(0)
                ws.clear()

            ws.update([df.columns.tolist()] + df.fillna("").values.tolist())
            ws.format("A1:Z1", {
                "backgroundColor": color,
                "textFormat": {
                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    "bold": True
                },
                "horizontalAlignment": "CENTER"
            })

        return f"https://docs.google.com/spreadsheets/d/{sheet_id}"

    except Exception as e:
        return f"Error: {str(e)}"
