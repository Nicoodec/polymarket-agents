import json
import os
from datetime import datetime

PORTFOLIO_FILE = "paper_portfolio.json"

def load_portfolio():
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)

def register_bet(market, prob_estimada, prob_mercado, kelly_data, decision, cycle_id):
    portfolio = load_portfolio()

    if decision.upper().strip().startswith("NO"):
        return None

    stake = kelly_data.get("stake_final_usdc", 0)
    if stake <= 0:
        return None

    apuesta = {
        "id": len(portfolio["apuestas"]) + 1,
        "cycle_id": cycle_id,
        "fecha": datetime.utcnow().isoformat(),
        "mercado": market["question"],
        "mercado_id": market.get("id", ""),
        "resuelve": market.get("resolves_at", ""),
        "prob_mercado": round(prob_mercado, 4),
        "prob_estimada": round(prob_estimada, 4),
        "edge": round(prob_estimada - prob_mercado, 4),
        "kelly_fraccionado": round(kelly_data.get("kelly_fraccionado", 0), 4),
        "stake_usdc": round(stake, 2),
        "estado": "pendiente",
        "resultado": None,
        "ganancia_usdc": None,
        "bankroll_antes": round(portfolio["bankroll_actual"], 2)
    }

    portfolio["apuestas"].append(apuesta)
    portfolio["total_apostado"] = round(portfolio["total_apostado"] + stake, 2)
    save_portfolio(portfolio)
    print(f"  [paper] Apuesta registrada: {market['question'][:50]}... | Stake: {stake} USDC")
    return apuesta

def resolve_bet(bet_id, resultado):
    portfolio = load_portfolio()
    for apuesta in portfolio["apuestas"]:
        if apuesta["id"] == bet_id and apuesta["estado"] == "pendiente":
            apuesta["estado"] = "resuelta"
            apuesta["resultado"] = resultado

            stake = apuesta["stake_usdc"]
            prob_mercado = apuesta["prob_mercado"]

            if resultado == "win":
                odds = (1 - prob_mercado) / prob_mercado
                ganancia = stake * odds
                apuesta["ganancia_usdc"] = round(ganancia, 2)
                portfolio["bankroll_actual"] = round(portfolio["bankroll_actual"] + ganancia, 2)
                portfolio["total_ganado"] = round(portfolio["total_ganado"] + ganancia, 2)
                print(f"  [paper] WIN — ganancia: +{ganancia:.2f} USDC")
            else:
                apuesta["ganancia_usdc"] = round(-stake, 2)
                portfolio["bankroll_actual"] = round(portfolio["bankroll_actual"] - stake, 2)
                portfolio["total_perdido"] = round(portfolio["total_perdido"] + stake, 2)
                print(f"  [paper] LOSS — perdida: -{stake:.2f} USDC")

            apuesta["bankroll_despues"] = round(portfolio["bankroll_actual"], 2)

            resueltas = [a for a in portfolio["apuestas"] if a["estado"] == "resuelta"]
            wins = [a for a in resueltas if a["resultado"] == "win"]
            portfolio["win_rate"] = round(len(wins) / len(resueltas), 4) if resueltas else 0

            invertido = portfolio["total_apostado"]
            ganado = portfolio["total_ganado"]
            perdido = portfolio["total_perdido"]
            portfolio["roi"] = round((ganado - perdido) / invertido, 4) if invertido > 0 else 0

            save_portfolio(portfolio)
            return apuesta

    print(f"  [paper] Apuesta {bet_id} no encontrada o ya resuelta")
    return None

def show_summary():
    portfolio = load_portfolio()
    print("\n" + "="*50)
    print("PAPER TRADING PORTFOLIO")
    print("="*50)
    print(f"Bankroll inicial:  {portfolio['bankroll_inicial']} USDC")
    print(f"Bankroll actual:   {portfolio['bankroll_actual']} USDC")
    print(f"Total apostado:    {portfolio['total_apostado']} USDC")
    print(f"Total ganado:      {portfolio['total_ganado']} USDC")
    print(f"Total perdido:     {portfolio['total_perdido']} USDC")
    print(f"Win rate:          {portfolio['win_rate']*100:.1f}%")
    print(f"ROI:               {portfolio['roi']*100:.1f}%")
    print(f"\nApuestas totales:  {len(portfolio['apuestas'])}")
    pendientes = [a for a in portfolio["apuestas"] if a["estado"] == "pendiente"]
    print(f"Pendientes:        {len(pendientes)}")
    print("="*50)

if __name__ == "__main__":
    show_summary()
