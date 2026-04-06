import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
API_KEY = os.getenv("KALSHI_API_KEY")

CATEGORY_KEYWORDS = {
    "politics": ["election", "president", "senate", "congress", "vote", "trump", "biden", "government", "ceasefire", "war", "ukraine", "russia", "fed", "policy"],
    "crypto": ["bitcoin", "eth", "crypto", "btc", "token", "blockchain", "defi", "solana", "coinbase"],
    "sports": ["nba", "nfl", "nhl", "fifa", "championship", "world cup", "super bowl", "league", "team", "player", "match", "game", "score", "win", "loss", "mlb"],
    "economics": ["inflation", "gdp", "recession", "rate", "market", "stock", "gold", "oil", "dollar", "cpi", "jobs", "unemployment"],
    "science": ["nasa", "spacex", "ai", "gpt", "model", "launch", "mission"],
    "entertainment": ["oscar", "grammy", "movie", "album", "song", "artist", "show"]
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

def get_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

def infer_category(title):
    t = title.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in t for k in keywords):
            return category
    return "unknown"

def get_kalshi_markets(limit=200):
    url = f"{KALSHI_API}/markets"
    params = {"limit": limit, "status": "open"}
    try:
        r = requests.get(url, headers=get_headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("markets", [])
    except Exception as e:
        print(f"  [kalshi] Error: {e}")
        return []

def score_kalshi_market(m, prob, liquidity, days_to_resolve):
    score = 0.0

    if liquidity >= 50000:
        score += 3.0
    elif liquidity >= 10000:
        score += 2.0
    elif liquidity >= 1000:
        score += 1.0

    if 0.20 <= prob <= 0.80:
        score += 2.0
    elif 0.15 <= prob <= 0.85:
        score += 1.0

    if days_to_resolve <= 1:
        score += 3.0
    elif days_to_resolve <= 3:
        score += 2.5
    elif days_to_resolve <= 7:
        score += 2.0
    elif days_to_resolve <= 14:
        score += 1.5
    elif days_to_resolve <= 30:
        score += 1.0

    title = m.get("title", "")
    category = infer_category(title)
    score *= CATEGORY_SCORES.get(category, 0.8)

    return round(score, 3)

def filter_kalshi_markets(markets, max_days=30):
    filtered = []
    now = datetime.utcnow()
    deadline = now + timedelta(days=max_days)

    for m in markets:
        try:
            close_time_str = m.get("close_time") or m.get("expiration_time", "")
            if not close_time_str:
                continue

            close_time = datetime.fromisoformat(close_time_str.replace("Z", ""))
            if close_time <= now:
                continue
            if close_time > deadline:
                continue

            days_to_resolve = max(0, (close_time - now).days)

            price = float(m.get("last_price_dollars", 0) or 0)
            if price <= 0 or price >= 1:
                continue
            if price < 0.08 or price > 0.92:
                continue

            liquidity = float(m.get("liquidity_dollars", 0) or 0)
            if liquidity < 500:
                continue

            title = m.get("title", "")
            if not title:
                continue

            category = infer_category(title)
            sc = score_kalshi_market(m, price, liquidity, days_to_resolve)

            filtered.append({
                "id": m.get("ticker", ""),
                "question": title,
                "probability": round(price, 4),
                "volume": liquidity,
                "resolves_at": close_time_str,
                "category": category,
                "days_to_resolve": days_to_resolve,
                "score": sc,
                "source": "kalshi"
            })

        except Exception:
            continue

    filtered.sort(key=lambda x: x['score'], reverse=True)
    return filtered

if __name__ == "__main__":
    print("Obteniendo mercados de Kalshi...")
    markets = get_kalshi_markets(limit=200)
    print(f"Total mercados obtenidos: {len(markets)}")
    filtered = filter_kalshi_markets(markets)
    print(f"Mercados que pasan el filtro: {len(filtered)}")
    print("\nTop 10 por score:")
    for m in filtered[:10]:
        print(f"  [{m['score']}] {m['question'][:55]} | prob: {m['probability']} | liq: {m['volume']:,.0f} | dias: {m['days_to_resolve']}")
