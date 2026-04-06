import requests
import json
import os
import re
from datetime import datetime
from tools.polymarket_api import get_markets, filter_markets
from tools.news_fetcher import build_context
from tools.kelly import kelly_criterion, calcular_stake
from tools.paper_trading import register_bet, show_summary

OLLAMA_URL = "http://localhost:11434/api/chat"
BANKROLL = 2000

def get_available_models():
    try:
        r = requests.get("http://localhost:11434/api/tags")
        return [m["name"] for m in r.json().get("models", [])]
    except:
        return []

def get_models():
    available = get_available_models()
    heavy = "qwen3.5:latest"
    light = "glm-4.7-flash:latest" if "glm-4.7-flash:latest" in available else "qwen3.5:latest"
    return heavy, light

def call_model(model, system_prompt, user_message, think=False):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2000}
    }
    if think:
        payload["think"] = True
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=300)
        r.raise_for_status()
        return r.json()["message"]["content"]
    except Exception as e:
        return f"ERROR: {str(e)}"

def load_agent(agent_name):
    path = os.path.join("agents", f"{agent_name}.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def save_state(cycle_dir, filename, content):
    os.makedirs(cycle_dir, exist_ok=True)
    path = os.path.join(cycle_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(content, (dict, list)):
            json.dump(content, f, indent=2, ensure_ascii=False)
        else:
            f.write(content)
    print(f"  [guardado] {path}")

def extract_probability(text, fallback=None):
    try:
        clean = re.sub(r'`json|`', '', text).strip()
        data = json.loads(clean)
        prob = data.get("probabilidad_final") or data.get("probabilidad_estimada")
        if prob is not None:
            return float(prob)
    except:
        pass
    matches = re.findall(r'"probabilidad_final"\s*:\s*([0-9.]+)', text)
    if matches:
        return float(matches[-1])
    matches = re.findall(r'"probabilidad_estimada"\s*:\s*([0-9.]+)', text)
    if matches:
        return float(matches[-1])
    return fallback

def extract_confidence(text, fallback="media"):
    matches = re.findall(r'"confianza"\s*:\s*"(\w+)"', text)
    if matches:
        val = matches[-1].lower()
        if val in ["alta", "media", "baja"]:
            return val
    return fallback

def build_market_info(market, context):
    noticias = json.dumps(context.get("noticias", []), indent=2, ensure_ascii=False)
    contexto_web = json.dumps(context.get("contexto_web", []), indent=2, ensure_ascii=False)
    return f"""
Mercado: {market['question']}
Probabilidad actual del mercado: {market['probability']}
Volumen: {market['volume']} USDC
Resuelve: {market['resolves_at']}

Noticias recientes:
{noticias}

Contexto web adicional:
{contexto_web}
"""

def run_debate(market, context, cycle_dir, heavy_model):
    analyst_prompt = load_agent("analyst")
    devil_prompt = load_agent("devil")
    market_info = build_market_info(market, context)
    debate_history = []
    last_analyst_response = ""

    for ronda in range(1, 4):
        print(f"\n  --- Ronda {ronda} ---")

        if ronda == 1:
            analyst_input = f"Analiza este mercado:\n{market_info}"
        else:
            analyst_input = f"""
Mercado original:
{market_info}

Debate hasta ahora:
{json.dumps(debate_history, indent=2, ensure_ascii=False)}

Responde a los argumentos del Devil's Advocate en ronda {ronda}.
"""

        print(f"  Analyst pensando...")
        analyst_response = call_model(heavy_model, analyst_prompt, analyst_input, think=True)
        last_analyst_response = analyst_response
        prob = extract_probability(analyst_response)
        print(f"  Analyst: prob_estimada={prob} | {analyst_response[:80]}...")

        devil_input = f"""
Mercado original:
{market_info}

Respuesta del Analyst en ronda {ronda}:
{analyst_response}

Debate previo:
{json.dumps(debate_history, indent=2, ensure_ascii=False)}
"""

        print(f"  Devil's Advocate pensando...")
        devil_response = call_model(heavy_model, devil_prompt, devil_input, think=True)
        print(f"  Devil: {devil_response[:80]}...")

        ronda_data = {
            "ronda": ronda,
            "analyst": analyst_response,
            "devil": devil_response,
            "prob_extraida": prob
        }
        debate_history.append(ronda_data)
        save_state(cycle_dir, f"debate_ronda_{ronda}.json", ronda_data)

    final_prob = extract_probability(last_analyst_response, fallback=market['probability'])
    final_conf = extract_confidence(last_analyst_response)
    print(f"\n  Probabilidad final extraida: {final_prob} | Confianza: {final_conf}")
    return debate_history, final_prob, final_conf

def run_risk_manager(market, debate_history, final_prob, final_conf, cycle_dir, light_model):
    risk_prompt = load_agent("risk_manager")
    risk_input = f"""
Mercado: {market['question']}
Probabilidad del mercado: {market['probability']}
Probabilidad estimada por el Analyst: {final_prob}
Confianza del Analyst: {final_conf}
Bankroll total: {BANKROLL} USDC

Debate completo:
{json.dumps(debate_history, indent=2, ensure_ascii=False)}

Calcula el Kelly Criterion usando la probabilidad estimada del Analyst ({final_prob}), no la del mercado.
"""

    print("\n  Risk Manager calculando...")
    risk_response = call_model(light_model, risk_prompt, risk_input)

    try:
        kelly = kelly_criterion(
            prob_estimated=final_prob,
            prob_market=market['probability']
        )
        stake = calcular_stake(kelly['kelly_fraccionado'], BANKROLL)
        kelly_data = {**kelly, **stake}
    except Exception as e:
        kelly_data = {"error": str(e)}

    result = {
        "prob_estimada": final_prob,
        "confianza": final_conf,
        "respuesta_modelo": risk_response,
        "kelly_calculado": kelly_data
    }
    save_state(cycle_dir, "risk_manager.json", result)
    return result

def run_arbitrator(market, debate_history, risk_data, cycle_dir, heavy_model):
    arbitrator_prompt = load_agent("arbitrator")
    kelly = risk_data.get("kelly_calculado", {})
    arb_input = f"""
Mercado: {market['question']}
Probabilidad del mercado: {market['probability']}
Probabilidad estimada por el Analyst: {risk_data.get('prob_estimada')}
Confianza del Analyst: {risk_data.get('confianza')}
Volumen: {market['volume']} USDC

Kelly fraccionado: {kelly.get('kelly_fraccionado', 0)}
Stake recomendado: {kelly.get('stake_final_usdc', 0)} USDC
Edge: {kelly.get('edge', 0)}

Debate completo (3 rondas):
{json.dumps(debate_history, indent=2, ensure_ascii=False)}

Toma la decision final: BET o NO BET.
"""

    print("\n  Arbitrator decidiendo...")
    decision = call_model(heavy_model, arbitrator_prompt, arb_input, think=True)
    print(f"\n  DECISION FINAL: {decision[:200]}")

    full_decision = {
        "decision": decision,
        "mercado": market,
        "prob_estimada": risk_data.get('prob_estimada'),
        "confianza": risk_data.get('confianza'),
        "kelly": kelly
    }
    save_state(cycle_dir, "decision_final.json", full_decision)
    return decision, full_decision

def main():
    print("=" * 60)
    print("POLYMARKET MULTI-AGENT TRADING SYSTEM")
    print("=" * 60)

    heavy_model, light_model = get_models()
    print(f"\nModelo pesado: {heavy_model}")
    print(f"Modelo ligero: {light_model}")

    cycle_id = datetime.utcnow().strftime("%Y%m%d_%H%M")
    cycle_dir = os.path.join("state", f"cycle_{cycle_id}")
    print(f"Ciclo: {cycle_id}")

    print("\n[1/5] SCOUT - Obteniendo mercados...")
    markets = get_markets(limit=100)
    filtered = filter_markets(markets)
    print(f"  Mercados encontrados: {len(filtered)}")
    save_state(cycle_dir, "markets.json", filtered)

    if not filtered:
        print("  No hay mercados que cumplan los criterios. Fin.")
        return

    top_markets = sorted(filtered, key=lambda x: x['score'], reverse=True)[:5]
    print(f"  Procesando top {len(top_markets)} mercados por volumen")

    for i, market in enumerate(top_markets):
        print(f"\n{'='*60}")
        print(f"MERCADO {i+1}/{len(top_markets)}: {market['question'][:60]}...")
        print(f"Probabilidad: {market['probability']} | Volumen: {market['volume']:,.0f} USDC")

        market_dir = os.path.join(cycle_dir, f"market_{i+1}")

        print("\n[2/5] DATA COLLECTOR - Buscando contexto...")
        context = build_context(market)
        print(f"  Fuentes totales: {context.get('total_fuentes', 0)}")
        save_state(market_dir, "context.json", context)

        print("\n[3/5] DEBATE - 3 rondas...")
        debate, final_prob, final_conf = run_debate(market, context, market_dir, heavy_model)

        print("\n[4/5] RISK MANAGER...")
        risk = run_risk_manager(market, debate, final_prob, final_conf, market_dir, light_model)

        print("\n[5/5] ARBITRATOR...")
        decision, full_decision = run_arbitrator(market, debate, risk, market_dir, heavy_model)

        kelly = risk.get("kelly_calculado", {})
        is_bet = "NO BET" not in decision.upper() and "BET" in decision.upper()
        if is_bet:
            register_bet(
                market=market,
                prob_estimada=final_prob,
                prob_mercado=market['probability'],
                kelly_data=kelly,
                decision="BET",
                cycle_id=cycle_id
            )
        else:
            print("  [paper] Decision NO BET — no se registra apuesta")

    print(f"\n{'='*60}")
    print(f"Ciclo completado. Estado guardado en: {cycle_dir}")
    show_summary()

if __name__ == "__main__":
    main()

