import requests
import json
from datetime import datetime, timedelta

GAMMA_API = "https://gamma-api.polymarket.com"

CATEGORY_KEYWORDS = {
    "politics": ["election", "ceasefire", "president", "senate", "president", "senate", "congress", "vote", "trump", "biden", "government", "ceasefire", "war", "ukraine", "russia"],
    "crypto": ["bitcoin", "eth", "crypto", "btc", "token", "blockchain", "defi", "airdrop", "megaeth", "solana"],
    "sports": ["nba", "nfl", "fifa", "championship", "world cup", "super bowl", "league", "team", "player", "match"],
    "economics": ["fed", "inflation", "gdp", "recession", "rate", "market", "stock", "gold", "oil", "dollar"],
    "science": ["nasa", "spacex", "ai", "gpt", "model", "launch", "mission", "discovery"],
    "entertainment": ["oscar", "grammy", "movie", "album", "song", "artist", "show", "gta", "game"]
}

CATEGORY_SCORES = {
    "politics": 1.3,
    "crypto": 1.2,
    "economics": 1.2,
    "sports": 1.1,
    "science": 1.0,
    "entertainment": 0.9,
    "unknown": 0.8
}

def infer_category(question):
    q = question.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in q for k in keywords):
            return category
    return "unknown"

def get_markets(limit=200, offset=0):
    url = f"{GAMMA_API}/markets"
    params = {
        "limit": limit,
        "offset": offset,
        "active": "true",
        "closed": "false"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def score_market(m, prob, volume, days_to_resolve):
    score = 0.0

    if volume >= 500000:
        score += 3.0
    elif volume >= 100000:
        score += 2.0
    elif volume >= 50000:
        score += 1.5
    elif volume >= 30000:
        score += 1.0

    if 0.20 <= prob <= 0.80:
        score += 2.0
    elif 0.15 <= prob <= 0.85:
        score += 1.0

    if 1 <= days_to_resolve <= 7:
        score += 2.0
    elif days_to_resolve <= 14:
        score += 1.5
    elif days_to_resolve <= 30:
        score += 1.0

    category = infer_category(m.get("question", ""))
    score *= CATEGORY_SCORES.get(category, 0.8)

    return round(score, 3)

def filter_markets(markets):
    filtered = []
    now = datetime.utcnow()
    deadline = now + timedelta(days=90)

    for m in markets:
        try:
            volume = float(m.get("volumeNum", 0) or m.get("volume", 0) or 0)
            if volume < 30000:
                continue

            end_date_str = m.get("endDateIso") or m.get("endDate", "")
            if not end_date_str:
                continue

            if "T" in end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", ""))
            else:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

            if end_date <= now:
                continue
            if end_date > deadline:
                continue

            days_to_resolve = (end_date - now).days

            prices = m.get("outcomePrices", "[]")
            if isinstance(prices, str):
                prices = json.loads(prices)
            if not prices:
                continue

            prob = float(prices[0])
            if prob < 0.08 or prob > 0.92:
                continue

            category = infer_category(m.get("question", ""))
            sc = score_market(m, prob, volume, days_to_resolve)

            filtered.append({
                "id": m.get("id"),
                "question": m.get("question"),
                "probability": prob,
                "volume": volume,
                "resolves_at": end_date_str,
                "category": category,
                "days_to_resolve": days_to_resolve,
                "score": sc
            })

        except Exception:
            continue

    filtered.sort(key=lambda x: x['score'], reverse=True)
    return filtered

if __name__ == "__main__":
    print("Obteniendo mercados de Polymarket...")
    markets = get_markets(limit=200)
    print(f"Total mercados obtenidos: {len(markets)}")
    filtered = filter_markets(markets)
    print(f"Mercados que pasan el filtro: {len(filtered)}")
    print("\nTop 10 por score:")
    for m in filtered[:10]:
        print(f"  [{m['score']}] {m['question'][:55]}... | prob: {m['probability']} | vol: {m['volume']:,.0f} | cat: {m['category']} | dias: {m['days_to_resolve']}")


