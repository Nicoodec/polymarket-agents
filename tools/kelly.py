def kelly_criterion(prob_estimated, prob_market):
    """
    Calcula Kelly Criterion para una apuesta en Polymarket.
    
    prob_estimated: probabilidad que estima nuestro Analyst (0 a 1)
    prob_market: probabilidad implicita del mercado (0 a 1) = precio actual
    
    En Polymarket las odds son:
    - Si apuestas YES a precio p, ganas (1-p) por cada p apostado
    - b = (1 - p) / p
    """
    p = prob_estimated
    q = 1 - p
    b = (1 - prob_market) / prob_market

    kelly = (b * p - q) / b
    kelly_fraction = kelly / 4  # 1/4 Kelly para seguridad

    return {
        "kelly_completo": round(kelly, 4),
        "kelly_fraccionado": round(kelly_fraction, 4),
        "apostar": kelly_fraction > 0.01,
        "edge": round(p - prob_market, 4)
    }

def calcular_stake(kelly_fraction, bankroll, max_pct=0.02):
    """
    Calcula el stake final aplicando limite de bankroll.
    
    kelly_fraction: fraccion de Kelly (0 a 1)
    bankroll: capital total en USDC
    max_pct: maximo porcentaje del bankroll por apuesta (default 2%)
    """
    stake_kelly = kelly_fraction * bankroll
    stake_max = max_pct * bankroll
    stake_final = min(stake_kelly, stake_max)

    return {
        "stake_kelly_usdc": round(stake_kelly, 2),
        "stake_max_usdc": round(stake_max, 2),
        "stake_final_usdc": round(stake_final, 2),
        "limitado_por_max": stake_kelly > stake_max
    }

if __name__ == "__main__":
    # Test con ejemplo real
    print("Test Kelly Criterion")
    print("=" * 40)
    
    # Ejemplo: mercado en 32% pero creemos que es 45%
    resultado = kelly_criterion(
        prob_estimated=0.45,
        prob_market=0.319
    )
    print(f"Probabilidad estimada: 45%")
    print(f"Probabilidad mercado:  31.9%")
    print(f"Edge: {resultado['edge']}")
    print(f"Kelly completo: {resultado['kelly_completo']}")
    print(f"Kelly fraccionado: {resultado['kelly_fraccionado']}")
    print(f"Apostar: {resultado['apostar']}")
    print()
    
    stake = calcular_stake(resultado['kelly_fraccionado'], bankroll=1000)
    print(f"Stake recomendado (bankroll 1000 USDC): {stake['stake_final_usdc']} USDC")
