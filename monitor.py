"""
Monitor de oportunidades cripto (Reddit + CoinGecko) com alerta via ntfy.sh

Como funciona (sem IA, 100% heurístico -> zero custo de token):
1. Busca as top ~250 moedas por market cap na CoinGecko (preço, volume, variação 24h)
2. Busca moedas em "trending" na CoinGecko
3. Lê posts recentes de subreddits de cripto (JSON público, sem precisar de API key)
4. Conta menções de cada moeda nos posts e compara com a execução anterior (spike)
5. Calcula um score combinando: variação de preço + liquidez + trending + spike de menções
6. Se o score passar do limiar (THRESHOLD) e a moeda não foi alertada recentemente,
   envia um push notification pro celular via ntfy.sh

Rode isso a cada 15-30 min via GitHub Actions (arquivo .github/workflows/monitor.yml incluso).

AVISO: isso é uma ferramenta de triagem, não uma recomendação de investimento.
Mercado cripto é extremamente volátil e moedas "em alta" podem ser pump-and-dump.
Sempre faça sua própria pesquisa (DYOR) antes de qualquer decisão financeira.
"""

import json
import re
import time
from pathlib import Path

import requests

# ============================== CONFIGURAÇÃO ==============================

NTFY_TOPIC = "SEU-TOPICO-UNICO-AQUI-troque-isso"  # crie um nome único e secreto
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

SUBREDDITS = [
    "CryptoCurrency",
    "CryptoMoonShots",
    "SatoshiStreetBets",
    "altcoin",
]
POSTS_PER_SUBREDDIT = 40  # posts "new" analisados por subreddit a cada rodada

COINGECKO_MARKETS_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&order=market_cap_desc&per_page=250&page=1"
    "&price_change_percentage=1h,24h&sparkline=false"
)
COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

MIN_VOLUME_USD = 2_000_000       # ignora moedas com pouca liquidez (maior risco de manipulação)
MIN_MARKET_CAP_USD = 10_000_000  # ignora micro-caps extremos

SCORE_THRESHOLD = 6.0            # score mínimo para disparar alerta
ALERT_COOLDOWN_SECONDS = 6 * 3600  # não alerta a mesma moeda de novo em menos de 6h

STATE_FILE = Path(__file__).parent / "state.json"

HEADERS = {"User-Agent": "crypto-opportunity-monitor/1.0 (personal use)"}

# ============================================================================


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_mentions": {}, "alerted_at": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_market_data() -> list[dict]:
    r = requests.get(COINGECKO_MARKETS_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_trending_symbols() -> set[str]:
    r = requests.get(COINGECKO_TRENDING_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return {item["item"]["symbol"].upper() for item in data.get("coins", [])}


def fetch_reddit_texts() -> str:
    """Concatena título+corpo dos posts recentes dos subreddits monitorados."""
    texts = []
    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit={POSTS_PER_SUBREDDIT}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            posts = r.json()["data"]["children"]
            for p in posts:
                d = p["data"]
                texts.append(d.get("title", ""))
                texts.append(d.get("selftext", ""))
        except Exception as e:
            print(f"[aviso] falha ao ler r/{sub}: {e}")
        time.sleep(1)  # gentil com o rate-limit do reddit
    return "\n".join(texts)


def build_symbol_pattern(symbol: str) -> re.Pattern:
    # Aceita "$BTC" ou "BTC" isolado (word boundary), case-sensitive p/ evitar
    # falso-positivo tipo "one" = moeda ONE.
    escaped = re.escape(symbol)
    return re.compile(rf"(?<![A-Za-z]){escaped}(?![A-Za-z])")


def count_mentions(text: str, coins: list[dict]) -> dict[str, int]:
    counts = {}
    for c in coins:
        symbol = c["symbol"].upper()
        if len(symbol) < 3:
            continue  # símbolos de 1-2 letras geram ruído demais
        pattern = build_symbol_pattern(symbol)
        n = len(pattern.findall(text))
        if n > 0:
            counts[symbol] = n
    return counts


def compute_score(coin: dict, mentions_now: int, mentions_before: int, trending: set[str]) -> float:
    symbol = coin["symbol"].upper()
    price_change_24h = coin.get("price_change_percentage_24h") or 0
    volume = coin.get("total_volume") or 0
    market_cap = coin.get("market_cap") or 1

    liquidity_ratio = volume / market_cap  # quanto maior, mais "girando" agora
    mention_spike = mentions_now - mentions_before

    score = 0.0
    score += max(price_change_24h, 0) * 0.08        # sobe com a valorização (só lado positivo)
    score += min(liquidity_ratio * 10, 4)           # capado em 4 pontos
    score += min(mention_spike * 0.5, 4)            # capado em 4 pontos
    if symbol in trending:
        score += 2.0
    return round(score, 2)


def send_alert(coin: dict, score: float, mentions_now: int) -> None:
    symbol = coin["symbol"].upper()
    name = coin["name"]
    price = coin.get("current_price")
    change_24h = coin.get("price_change_percentage_24h") or 0

    title = f"Oportunidade: {name} ({symbol})"
    message = (
        f"Score: {score} | Preço: ${price} | 24h: {change_24h:.1f}%\n"
        f"Menções recentes no Reddit: {mentions_now}\n"
        f"Volume 24h: ${coin.get('total_volume', 0):,.0f}\n"
        f"⚠️ Sinal heurístico, não é recomendação. DYOR."
    )
    try:
        requests.post(
            NTFY_URL,
            data=message.encode("utf-8"),
            headers={**HEADERS, "Title": title, "Priority": "high", "Tags": "chart_with_upwards_trend"},
            timeout=10,
        )
        print(f"[alerta enviado] {symbol} score={score}")
    except Exception as e:
        print(f"[erro] falha ao enviar alerta de {symbol}: {e}")


def main() -> None:
    state = load_state()
    now = time.time()

    coins = fetch_market_data()
    trending = fetch_trending_symbols()
    reddit_text = fetch_reddit_texts()
    mentions_now = count_mentions(reddit_text, coins)

    for coin in coins:
        symbol = coin["symbol"].upper()
        volume = coin.get("total_volume") or 0
        market_cap = coin.get("market_cap") or 0

        if volume < MIN_VOLUME_USD or market_cap < MIN_MARKET_CAP_USD:
            continue

        m_now = mentions_now.get(symbol, 0)
        m_before = state["last_mentions"].get(symbol, 0)

        score = compute_score(coin, m_now, m_before, trending)

        last_alert = state["alerted_at"].get(symbol, 0)
        cooldown_ok = (now - last_alert) > ALERT_COOLDOWN_SECONDS

        if score >= SCORE_THRESHOLD and cooldown_ok:
            send_alert(coin, score, m_now)
            state["alerted_at"][symbol] = now

    state["last_mentions"] = mentions_now
    save_state(state)


if __name__ == "__main__":
    main()
