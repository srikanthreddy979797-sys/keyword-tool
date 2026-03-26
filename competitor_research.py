import requests
from bs4 import BeautifulSoup
import time
import os
from typing import List, Dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

def get_serp_competitors(keyword: str, country: str = "IN") -> Dict:
    try:
        country_params = {
            "IN": {"gl": "in", "hl": "en"},
            "US": {"gl": "us", "hl": "en"},
            "GB": {"gl": "gb", "hl": "en"},
            "AU": {"gl": "au", "hl": "en"},
        }
        params = country_params.get(country, {"gl": "in", "hl": "en"})
        query = keyword.replace(" ", "+")
        url = f"https://www.google.com/search?q={query}&gl={params['gl']}&hl={params['hl']}&num=10"

        session = requests.Session()
        session.headers.update(HEADERS)
        r = session.get(url, timeout=15)

        soup = BeautifulSoup(r.text, "lxml")

        organic = []
        paid = []

        # Organic results — multiple selectors for robustness
        for result in soup.select("div.g, div[data-sokoban-container], div.Gx5Zad"):
            link = result.select_one("a[href^='http']")
            title = result.select_one("h3")
            snippet = result.select_one("div.VwiC3b, div.s3v9rd, span.st")
            if link and title:
                href = link.get("href", "")
                if href.startswith("http") and "google" not in href:
                    domain = href.split("/")[2].replace("www.", "")
                    if domain not in [o["domain"] for o in organic]:
                        organic.append({
                            "domain": domain,
                            "title": title.text[:60],
                            "snippet": snippet.text[:120] if snippet else "",
                            "url": href
                        })
            if len(organic) >= 5:
                break

        # Paid ads
        for ad in soup.select("div.uEierd, div[data-text-ad='1'], .pla-unit"):
            link = ad.select_one("a")
            title = ad.select_one("div.CCgQ5, div[role='heading'], h3")
            if link and title:
                href = link.get("href", "")
                if href.startswith("http"):
                    domain = href.split("/")[2].replace("www.", "")
                    if domain and "google" not in domain:
                        paid.append({
                            "domain": domain,
                            "title": title.text[:60],
                            "url": href
                        })
            if len(paid) >= 5:
                break

        # If no organic found — Google blocked us, use DuckDuckGo as fallback
        if not organic:
            organic = get_duckduckgo_results(keyword)

        time.sleep(1)

        return {
            "keyword": keyword,
            "organic_competitors": organic[:5],
            "paid_competitors": paid[:5],
            "total_organic": len(organic),
            "total_paid": len(paid)
        }

    except Exception as e:
        return {
            "keyword": keyword,
            "organic_competitors": [],
            "paid_competitors": [],
            "error": str(e)
        }

def get_duckduckgo_results(keyword: str) -> List[Dict]:
    try:
        url = f"https://html.duckduckgo.com/html/?q={keyword.replace(' ', '+')}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        results = []
        for result in soup.select("div.result__body"):
            link = result.select_one("a.result__url")
            title = result.select_one("a.result__a")
            snippet = result.select_one("a.result__snippet")
            if link and title:
                domain = link.text.strip().split("/")[0].replace("www.", "")
                results.append({
                    "domain": domain,
                    "title": title.text[:60],
                    "snippet": snippet.text[:120] if snippet else "",
                    "url": "https://" + domain
                })
            if len(results) >= 5:
                break
        return results
    except:
        return []

def analyse_competitor_domains(serp_results: List[Dict]) -> Dict:
    domain_organic = {}
    domain_paid = {}

    for result in serp_results:
        for org in result.get("organic_competitors", []):
            d = org["domain"]
            domain_organic[d] = domain_organic.get(d, 0) + 1
        for paid in result.get("paid_competitors", []):
            d = paid["domain"]
            domain_paid[d] = domain_paid.get(d, 0) + 1

    top_organic = sorted(domain_organic.items(), key=lambda x: x[1], reverse=True)[:10]
    top_paid = sorted(domain_paid.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "top_organic_domains": [{"domain": d, "appearances": c} for d, c in top_organic],
        "top_paid_domains": [{"domain": d, "appearances": c} for d, c in top_paid]
    }
