import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyse_keywords_with_ai(keywords_data: list, seed_keyword: str) -> dict:
    try:
        kw_list = [f"{k['keyword']} (vol:{k['volume']}, intent:{k['intent']}, score:{k.get('opportunity_score', 0)})"
                   for k in keywords_data[:40]]

        prompt = f"""You are a Google Ads expert. Analyse these keywords for "{seed_keyword}" and return ONLY a JSON object.

Keywords:
{chr(10).join(kw_list)}

Return this exact JSON structure, nothing else, no markdown:
{{
    "clusters": [
        {{
            "name": "cluster name",
            "theme": "what this cluster targets",
            "keywords": ["kw1", "kw2", "kw3"],
            "intent": "BOFU or MOFU or TOFU",
            "recommended_match_type": "Exact or Phrase or Broad",
            "bid_strategy": "Target CPA or Maximize Conversions or Manual CPC"
        }}
    ],
    "ad_groups": [
        {{
            "name": "group name",
            "theme": "what this group targets",
            "keywords": ["kw1", "kw2", "kw3"],
            "match_types": {{
                "exact": ["kw1"],
                "phrase": ["kw2"],
                "broad": ["kw3"]
            }}
        }}
    ],
    "negative_keywords": ["neg1", "neg2", "neg3", "neg4", "neg5", "neg6", "neg7", "neg8", "neg9", "neg10"],
    "top_opportunity": "single best keyword to bid on and why in one sentence",
    "budget_recommendation": "suggested daily budget range and why",
    "ad_copy": {{
        "headline_1": "headline under 30 chars",
        "headline_2": "headline under 30 chars",
        "headline_3": "headline under 30 chars",
        "description_1": "description under 90 chars",
        "description_2": "description under 90 chars"
    }}
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )

        text = response.choices[0].message.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return json.loads(text)

    except Exception as e:
        return {
            "clusters": [],
            "ad_groups": [],
            "negative_keywords": [],
            "top_opportunity": f"AI analysis failed: {str(e)}",
            "budget_recommendation": "",
            "ad_copy": {}
        }