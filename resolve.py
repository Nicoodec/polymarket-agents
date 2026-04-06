import requests
import json
import os
from datetime import datetime
from tools.paper_trading import resolve_bet, load_portfolio, show_summary

GAMMA_API = "https://gamma-api.polymarket.com"

def get_market_result(market_id):
    try:
        url = f"{GAMMA_API}/markets/{market_id}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        m = r.json()

        if not m.get("closed", False):
            return None, "pendiente"

        prices = m.get("outcomePrices", "[]")
        if isinstance(prices, str):
            prices = json.loads(prices)

        if not prices:
            return None, "sin_datos"

        prob_yes = float(prices[0])

        if prob_yes >= 0.99:
            return "win", "resuelto_yes"
        elif prob_yes <= 0.01:
            return "loss", "resuelto_no"
        else:
            return None, "sin_resolver"

    except Exception as e:
        print(f"  Error consultando mercado {market_id}: {e}")
        return None, "error"

def check_and_resolve():
    portfolio = load_portfolio()
    pendientes = [a for a in portfolio["apuestas"] if a["estado"] == "pendiente"]

    if not pendientes:
        print("No hay apuestas pendientes de resolver.")
        return

    print(f"Comprobando {len(pendientes)} apuestas pendientes...")
    print("=" * 60)

    resueltas = 0
    for apuesta in pendientes:
        market_id = apuesta.get("mercado_id", "")
        question = apuesta.get("mercado", "")[:55]
        print(f"\nApuesta #{apuesta['id']}: {question}...")
        print(f"  Mercado ID: {market_id}")
        print(f"  Stake: {apuesta['stake_usdc']} USDC")
        print(f"  Fecha: {apuesta['fecha'][:10]}")
        print(f"  Resuelve: {apuesta.get('resuelve', 'N/A')[:10]}")

        resultado, estado = get_market_result(market_id)

        if resultado:
            resolve_bet(apuesta["id"], resultado)
            resueltas += 1
            print(f"  Estado: {estado.upper()} -> {resultado.upper()}")
        else:
            print(f"  Estado: {estado} — sin resolver todavia")

    print(f"\n{'='*60}")
    print(f"Resueltas: {resueltas}/{len(pendientes)}")
    show_summary()

def resolve_manual(bet_id, resultado):
    if resultado not in ["win", "loss"]:
        print("resultado debe ser 'win' o 'loss'")
        return
    resolve_bet(bet_id, resultado)
    show_summary()

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        bid = int(sys.argv[1])
        res = sys.argv[2]
        print(f"Resolviendo apuesta #{bid} como {res}...")
        resolve_manual(bid, res)
    else:
        check_and_resolve()
