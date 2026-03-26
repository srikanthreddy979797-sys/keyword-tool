import requests
import os
import base64
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

def get_auth_header():
    credentials = f"{LOGIN}:{PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Content-Type": "application/json"}

def get_keyword_data(keywords: List[str], country: str = "IN", language: str = "en") -> List[Dict]:
    country_codes = {
        "IN": 2356, "US": 2840, "GB": 2826,
        "CA": 2124, "AU": 2036, "SG": 2702
    }
    language_codes = {
        "IN": "English", "US": "English", "GB": "English",
        "CA": "English", "AU": "English", "SG": "English"
    }

    location_code = country_codes.get(country, 2356)
    language_name = language_codes.get(country, "English")

    # Process in batches of 10
    all_results = []
    batches = [keywords[i:i+10] for i in range(0, len(keywords), 10)]

    for batch in batches:
        payload = [{
            "keywords": batch,
            "location_code": location_code,
            "language_name": language_name
        }]

        try:
            response = requests.post(
                "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                headers=get_auth_header(),
                json=payload,
                timeout=30
            )

            data = response.json()

            if data.get("status_code") == 20000:
                tasks = data.get("tasks", [])
                for task in tasks:
                    results = task.get("result", [])
                    if results:
                        for item in results:
                            competition_index = item.get("competition_index", 0)
                            competition_str = item.get("competition", "LOW")

                            all_results.append({
                                "keyword": item.get("keyword"),
                                "volume": item.get("search_volume", 0),
                                "cpc": round(item.get("cpc", 0), 2),
                                "low_bid": round(item.get("low_top_of_page_bid", 0), 2),
                                "high_bid": round(item.get("high_top_of_page_bid", 0), 2),
                                "competition_index": competition_index,
                                "competition": competition_str,
                                "monthly_searches": item.get("monthly_searches", [])
                            })
        except Exception as e:
            print(f"DataForSEO error: {e}")
            continue

    return all_results

def enrich_keywords_with_real_data(keywords_data: List[Dict], country: str = "IN") -> List[Dict]:
    keyword_list = [k["keyword"] for k in keywords_data]

    print(f"Fetching real data for {len(keyword_list)} keywords from DataForSEO...")
    real_data = get_keyword_data(keyword_list, country)

    real_data_map = {item["keyword"]: item for item in real_data}

    enriched = []
    for kw in keywords_data:
        real = real_data_map.get(kw["keyword"])
        if real:
            kw["volume"] = real["volume"] if real["volume"] > 0 else kw["volume"]
            kw["cpc"] = real["cpc"] if real["cpc"] > 0 else kw["cpc"]
            kw["competition_index"] = real.get("competition_index", 0)
            kw["competition"] = real.get("competition", "LOW")
            kw["low_bid"] = real.get("low_bid", 0)
            kw["high_bid"] = real.get("high_bid", 0)
            kw["data_source"] = "DataForSEO"
            kw["monthly_searches"] = real.get("monthly_searches", [])
        else:
            kw["data_source"] = "Estimated"
            kw["competition_index"] = 0
            kw["monthly_searches"] = []
        enriched.append(kw)

    return enriched
