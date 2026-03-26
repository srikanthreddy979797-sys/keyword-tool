import requests
import time
from pytrends.request import TrendReq
from typing import List, Dict

def get_google_autocomplete(keyword: str, country: str = "in") -> List[str]:
    suggestions = []
    modifiers = ["", "a", "b", "c", "how", "best", "top", "buy", "cheap", "near me", "online", "vs", "for", "without", "with"]
    for mod in modifiers:
        query = f"{keyword} {mod}".strip()
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}&hl=en&gl={country}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 1:
                    suggestions.extend(data[1])
            time.sleep(0.1)
        except:
            continue
    seen = set()
    unique = []
    for s in suggestions:
        if s not in seen and keyword.lower() in s.lower():
            seen.add(s)
            unique.append(s)
    return unique[:50]

def get_pytrends_data(keywords: List[str], country: str = "IN") -> Dict:
    try:
        pt = TrendReq(hl='en-US', tz=330)
        batch = keywords[:5]
        pt.build_payload(batch, cat=0, timeframe='today 3-m', geo=country)
        interest = pt.interest_over_time()
        related = pt.related_queries()
        trend_scores = {}
        if not interest.empty:
            for kw in batch:
                if kw in interest.columns:
                    trend_scores[kw] = int(interest[kw].mean())
        rising_keywords = []
        for kw in batch:
            if kw in related and related[kw]['rising'] is not None:
                rising = related[kw]['rising']
                if not rising.empty:
                    rising_keywords.extend(rising['query'].tolist()[:5])
        return {
            "trend_scores": trend_scores,
            "rising_keywords": list(set(rising_keywords))[:10]
        }
    except Exception as e:
        return {"trend_scores": {}, "rising_keywords": []}

def classify_intent(keyword: str) -> str:
    kw = keyword.lower()
    if any(w in kw for w in ["buy", "price", "cost", "order", "purchase", "deal", "discount", "cheap", "affordable"]):
        return "BOFU"
    elif any(w in kw for w in ["best", "top", "vs", "compare", "review", "alternative"]):
        return "MOFU"
    elif any(w in kw for w in ["what", "how", "why", "when", "guide", "tutorial", "learn", "tips"]):
        return "TOFU"
    else:
        return "MOFU"

def estimate_cpc(keyword: str, competition: str) -> float:
    base = {"HIGH": 2.5, "MEDIUM": 1.2, "LOW": 0.4}
    cpc = base.get(competition, 1.0)
    if any(w in keyword.lower() for w in ["insurance", "loan", "finance", "software", "lawyer"]):
        cpc *= 4
    elif any(w in keyword.lower() for w in ["buy", "price", "cost", "hire"]):
        cpc *= 2
    return round(cpc, 2)

def estimate_volume(keyword: str, trend_score: int = 50) -> int:
    words = len(keyword.split())
    if words == 1:
        base = 10000
    elif words == 2:
        base = 5000
    elif words == 3:
        base = 2000
    else:
        base = 800
    return int(base * (trend_score / 50))

def get_competition(keyword: str) -> str:
    kw = keyword.lower()
    if any(w in kw for w in ["buy", "price", "insurance", "loan", "software"]):
        return "HIGH"
    elif any(w in kw for w in ["best", "top", "review", "compare"]):
        return "MEDIUM"
    else:
        return "LOW"

def build_keyword_dataset(keyword: str, country: str = "IN") -> List[Dict]:
    print(f"Fetching autocomplete suggestions for: {keyword}")
    suggestions = get_google_autocomplete(keyword, country.lower())
    if not suggestions:
        suggestions = [keyword]

    print(f"Got {len(suggestions)} suggestions. Fetching trends...")
    trends_data = get_pytrends_data(suggestions[:5], country)
    trend_scores = trends_data.get("trend_scores", {})
    rising = trends_data.get("rising_keywords", [])

    all_keywords = list(set(suggestions + rising))

    results = []
    for kw in all_keywords:
        trend_score = trend_scores.get(kw, 50)
        competition = get_competition(kw)
        results.append({
            "keyword": kw,
            "volume": estimate_volume(kw, trend_score),
            "cpc": estimate_cpc(kw, competition),
            "competition": competition,
            "intent": classify_intent(kw),
            "trend_score": trend_score,
            "is_rising": kw in rising
        })

    results.sort(key=lambda x: x["volume"], reverse=True)
    return results

def get_question_keywords(keyword: str, country: str = "in") -> List[str]:
    questions = []
    prefixes = ["how", "what", "why", "when", "which", "who", "where", "can", "is", "are", "do", "does"]
    for prefix in prefixes:
        query = f"{prefix} {keyword}"
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}&hl=en&gl={country}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 1:
                    for suggestion in data[1]:
                        if any(suggestion.lower().startswith(p) for p in prefixes):
                            questions.append(suggestion)
            time.sleep(0.1)
        except:
            continue
    seen = set()
    unique = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:30]

def calculate_opportunity_score(volume: int, cpc: float, competition_index: int,
                                 max_volume: int, max_cpc: float) -> int:
    if max_volume == 0:
        vol_score = 0
    else:
        vol_score = (volume / max_volume) * 40

    if max_cpc == 0:
        cpc_score = 30
    else:
        cpc_score = (1 - min(cpc / max_cpc, 1)) * 30

    comp_score = (1 - min(competition_index / 100, 1)) * 30

    return min(100, int(vol_score + cpc_score + comp_score))

def add_opportunity_scores(keywords_data: List[Dict]) -> List[Dict]:
    volumes = [k.get("volume", 0) for k in keywords_data]
    cpcs = [k.get("cpc", 0) for k in keywords_data]
    max_volume = max(volumes) if volumes else 1
    max_cpc = max(cpcs) if cpcs else 1

    for k in keywords_data:
        k["opportunity_score"] = calculate_opportunity_score(
            k.get("volume", 0),
            k.get("cpc", 0),
            k.get("competition_index", 50),
            max_volume,
            max_cpc
        )
    return keywords_data

def build_keyword_dataset(keyword: str, country: str = "IN") -> List[Dict]:
    print(f"Fetching autocomplete suggestions for: {keyword}")
    suggestions = get_google_autocomplete(keyword, country.lower())
    if not suggestions:
        suggestions = [keyword]

    print(f"Got {len(suggestions)} suggestions. Fetching trends...")
    trends_data = get_pytrends_data(suggestions[:5], country)
    trend_scores = trends_data.get("trend_scores", {})
    rising = trends_data.get("rising_keywords", [])

    print(f"Fetching question keywords...")
    questions = get_question_keywords(keyword, country.lower())

    all_keywords = list(set(suggestions + rising + questions))

    results = []
    for kw in all_keywords:
        trend_score = trend_scores.get(kw, 50)
        competition = get_competition(kw)
        competition_index = {"HIGH": 80, "MEDIUM": 50, "LOW": 20}.get(competition, 50)
        is_question = any(kw.lower().startswith(p) for p in
                         ["how", "what", "why", "when", "which", "who", "where", "can", "is", "are", "do", "does"])
        results.append({
            "keyword": kw,
            "volume": estimate_volume(kw, trend_score),
            "cpc": estimate_cpc(kw, competition),
            "competition": competition,
            "competition_index": competition_index,
            "intent": classify_intent(kw),
            "trend_score": trend_score,
            "is_rising": kw in rising,
            "is_question": is_question,
            "data_source": "Estimated"
        })

    results = add_opportunity_scores(results)
    results.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return results
