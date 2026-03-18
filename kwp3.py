import requests
import os
from dotenv import load_dotenv

load_dotenv()

# 🔐 ENV VARIABLES
ACCESS_TOKEN = None  # will pass dynamically
DEVELOPER_TOKEN = os.getenv("DEVELOPER_TOKEN")
CUSTOMER_ID = os.getenv("CUSTOMER_ID")  # Ads account ID
MCC_ID = os.getenv("MCC_ID")  # optional

BASE_URL = "https://googleads.googleapis.com/v16"


def fetch_keyword_ideas(access_token, keyword, geo_target, language):
    url = f"{BASE_URL}/customers/{CUSTOMER_ID}:generateKeywordIdeas"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": DEVELOPER_TOKEN,
        "Content-Type": "application/json"
    }

    # Only include if using MCC
    if MCC_ID:
        headers["login-customer-id"] = MCC_ID

    body = {
        "keyword_seed": {
            "keywords": [keyword]
        },
        "geo_target_constants": [geo_target],
        "language": language,
        "keyword_plan_network": "GOOGLE_SEARCH"
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        print("\n❌ API Error Status:", response.status_code)
        print(response.text)
        print("\n⚠️ Note: If using TEST MODE, Keyword Planner is blocked.")
        return {"results": []}

    return response.json()


def main():
    # 👇 TEMP test values (later connect step 1 + 2)
    access_token = input("Paste access token: ").strip()

    keyword = "garlic press"
    geo_target = "geoTargetConstants/356"
    language = "languageConstants/1000"

    data = fetch_keyword_ideas(access_token, keyword, geo_target, 
language)

    print("\n✅ Raw API Response:")
    print(data)


if __name__ == "__main__":
    main()
