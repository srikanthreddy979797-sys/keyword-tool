def micros_to_currency(micros):
    if micros:
        return round(micros / 1_000_000, 2)
    return 0


def classify_intent(keyword):
    keyword = keyword.lower()

    if any(word in keyword for word in ["buy", "price", "order"]):
        return "High"
    elif any(word in keyword for word in ["best", "review", "top"]):
        return "Research"
    elif "vs" in keyword:
        return "Comparison"
    else:
        return "Low"


def process_keywords(api_response):
    results = api_response.get("results", [])

    processed_data = []

    for item in results:
        keyword = item.get("text")

        metrics = item.get("keyword_idea_metrics", {})

        volume = metrics.get("avg_monthly_searches", 0)
        competition = metrics.get("competition", "UNKNOWN")

        cpc_micros = metrics.get("low_top_of_page_bid_micros", 0)
        cpc = micros_to_currency(cpc_micros)

        intent = classify_intent(keyword)

        processed_data.append({
            "keyword": keyword,
            "volume": volume,
            "cpc": cpc,
            "competition": competition,
            "intent": intent
        })

    return processed_data


def main():
    # 🔥 TEMP TEST DATA (simulate API response)
    sample_response = {
        "results": [
            {
                "text": "buy garlic press",
                "keyword_idea_metrics": {
                    "avg_monthly_searches": 5400,
                    "competition": "HIGH",
                    "low_top_of_page_bid_micros": 20000000
                }
            },
            {
                "text": "best garlic press",
                "keyword_idea_metrics": {
                    "avg_monthly_searches": 8100,
                    "competition": "MEDIUM",
                    "low_top_of_page_bid_micros": 15000000
                }
            }
        ]
    }

    processed = process_keywords(sample_response)

    print("\n✅ Processed Keyword Data:\n")
    for row in processed:
        print(row)


if __name__ == "__main__":
    main()
