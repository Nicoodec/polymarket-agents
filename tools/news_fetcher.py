from ddgs import DDGS
from datetime import datetime

def search_news(query, max_results=5):
    """
    Busca noticias relevantes usando ddgs.
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "titulo": r.get("title", ""),
                    "resumen": r.get("body", ""),
                    "fuente": r.get("source", ""),
                    "url": r.get("url", ""),
                    "fecha": r.get("date", "")
                })
        return results

    except Exception as e:
        return [{"error": str(e)}]

def search_web(query, max_results=3):
    """
    Busca informacion general en la web (no solo noticias).
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "titulo": r.get("title", ""),
                    "resumen": r.get("body", ""),
                    "url": r.get("href", "")
                })
        return results

    except Exception as e:
        return [{"error": str(e)}]

def build_context(market):
    """
    Construye contexto completo para un mercado dado.
    Combina noticias recientes y busqueda web general.
    """
    question = market.get("question", "")

    # Busqueda de noticias recientes
    news = search_news(question, max_results=5)

    # Busqueda web general para base rates y contexto historico
    web = search_web(question + " history base rate statistics", max_results=3)

    # Filtrar resultados con error
    news_clean = [n for n in news if "error" not in n]
    web_clean = [w for w in web if "error" not in w]

    context = {
        "mercado": market,
        "noticias": news_clean,
        "contexto_web": web_clean,
        "total_fuentes": len(news_clean) + len(web_clean),
        "timestamp": datetime.utcnow().isoformat()
    }

    return context

if __name__ == "__main__":
    mercados_test = [
        {
            "id": "test1",
            "question": "Will Harvey Weinstein be sentenced to no prison time?",
            "probability": 0.319,
            "volume": 307323
        },
        {
            "id": "test2",
            "question": "Will MegaETH perform an airdrop by June 30?",
            "probability": 0.433,
            "volume": 1018920
        }
    ]

    for market in mercados_test:
        print(f"\nBuscando contexto para: {market['question']}")
        print("=" * 60)
        context = build_context(market)

        print(f"Noticias encontradas: {len(context['noticias'])}")
        for n in context['noticias']:
            print(f"  [{n['fecha']}] {n['titulo']}")
            print(f"  {n['resumen'][:120]}...")

        print(f"\nContexto web encontrado: {len(context['contexto_web'])}")
        for w in context['contexto_web']:
            print(f"  {w['titulo']}")
            print(f"  {w['resumen'][:120]}...")
