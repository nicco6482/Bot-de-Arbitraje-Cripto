"""
╔══════════════════════════════════════════════════════╗
║      AntiGravity Crypto Hunter - price_fetcher.py    ║
║   💰 Obtiene precios de cryptos desde CoinGecko API  ║
╚══════════════════════════════════════════════════════╝
CoinGecko ofrece datos de precios de +10,000 exchanges.
API Gratuita (sin key): ~30 calls/min.
API Pro (key de pago): hasta 500 calls/min.

FIX v2: Usa /coins/{id}/tickers (1 sola llamada por coin)
en vez de /exchanges/{id}/tickers (1 llamada por exchange).
Esto reduce el consumo de rate limit de 5x a 1x por ciclo.
"""

import time
import logging
import requests
from typing import Dict, Optional
from config import API, TRADING, LOG

logger = logging.getLogger("AntiGravity.PriceFetcher")

# ─────────────────────────────────────────────────────────────────────────────
# Mapa de IDs de exchanges en CoinGecko (actualizados 2026).
# Usados para filtrar los tickers que nos interesa del response masivo.
#   Formato: {ID_en_config: ID_real_en_CoinGecko}
# Si agregas exchanges a config.py, añade el mapeo aquí también.
# ─────────────────────────────────────────────────────────────────────────────
EXCHANGE_ID_MAP: Dict[str, str] = {
    "binance":          "binance",
    "coinbase":         "gdax",           # CoinGecko usa "gdax" para Coinbase Exchange
    "coinbase-exchange":"gdax",
    "kraken":           "kraken",
    "huobi":            "huobi",
    "htx":              "huobi",          # HTX es el nuevo nombre de Huobi
    "kucoin":           "kucoin",
    "bybit":            "bybit_spot",
    "okx":              "okex",
    "bitfinex":         "bitfinex",
    "gate":             "gate",
    "bitget":           "bitget",
    "mexc":             "mxc",
}


def _exponential_backoff(attempt: int, base_wait: int = 10) -> int:
    """Calcula el tiempo de espera con backoff exponencial. 10s, 20s, 40s, 80s..."""
    return base_wait * (2 ** attempt)


class PriceFetcher:
    """
    Clase para obtener precios de criptomonedas desde CoinGecko.
    Soporta múltiples exchanges para comparación de arbitraje.

    Estrategia eficiente (v2):
    - 1 llamada a /coins/{id}/tickers → devuelve precios en TODOS los exchanges
    - Filtramos los exchanges que nos interesan del response
    - Resultado: N exchanges con 1 sola llamada API (ahorro masivo de rate limit)
    """

    def __init__(self):
        self.base_url = API.COINGECKO_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "AntiGravity-Crypto-Hunter/2.0"
        })
        # Cache del último timestamp de respuesta exitosa (para throttling)
        self._last_call_time: float = 0.0
        self._min_call_interval: float = 2.0  # segundos mínimos entre llamadas

    def _safe_get(self, url: str, params: dict = None, max_retries: int = None) -> Optional[dict]:
        """
        Wrapper HTTP GET con rate-limit throttling y exponential backoff.
        Maneja 429 automáticamente y respeta el intervalo mínimo entre llamadas.

        Returns:
            JSON parseado como dict, o None si falló definitivamente.
        """
        if max_retries is None:
            max_retries = TRADING.max_retries

        # Throttle local: nunca llamamos más rápido que _min_call_interval
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_call_interval:
            time.sleep(self._min_call_interval - elapsed)

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=15)
                self._last_call_time = time.time()

                if response.status_code == 429:
                    wait = _exponential_backoff(attempt, base_wait=15)
                    logger.warning(
                        f"⏳ Rate limit (429) en intento {attempt+1}/{max_retries}. "
                        f"Esperando {wait}s antes de reintentar..."
                    )
                    time.sleep(wait)
                    continue  # Reintenta

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error {getattr(response, 'status_code', '?')}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(_exponential_backoff(attempt, base_wait=5))
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (intento {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(_exponential_backoff(attempt, base_wait=5))

        logger.error(f"❌ Fallo definitivo tras {max_retries} intentos: {url}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL: 1 llamada → precios en todos los exchanges
    # ─────────────────────────────────────────────────────────────────────────
    def get_all_exchange_prices(self, coin_id: str) -> Dict[str, float]:
        """
        ✅ ESTRATEGIA EFICIENTE (v2): Una sola llamada API para obtener precios
        del mismo coin en MÚLTIPLES exchanges simultáneamente.

        Endpoint: GET /coins/{id}/tickers
        → Retorna decenas de pares de trading en todos los exchanges que listan
          ese coin. Filtramos los exchanges de nuestra lista.

        Args:
            coin_id: ID CoinGecko del coin (e.g. "bitcoin")

        Returns:
            Dict {exchange_name: price_usd}
            Ejemplo: {"binance": 67800.0, "kraken": 67950.0, "gdax": 68100.0}
        """
        # Construir set de IDs reales de CoinGecko para los exchanges configurados
        target_ids = {
            EXCHANGE_ID_MAP.get(ex, ex)  # Si no está en el mapa, usa el nombre tal cual
            for ex in TRADING.exchanges
        }

        url = f"{self.base_url}/coins/{coin_id}/tickers"
        logger.info(f"📡 Obteniendo tickers de {coin_id} (1 llamada para {len(target_ids)} exchanges)...")

        prices: Dict[str, float] = {}
        page = 1

        # La API pagina los tickers. Normalmente la primera página (~100 tickers)
        # ya contiene Binance, Kraken, Coinbase y los demás grandes.
        while True:
            params = {
                "include_exchange_logo": "false",
                "order": "volume_desc",         # Los más líquidos primero
                "depth": "false",
                "page": page,
            }
            data = self._safe_get(url, params=params)

            if not data:
                break

            tickers = data.get("tickers", [])
            if not tickers:
                break  # No hay más páginas

            for ticker in tickers:
                exchange_id = ticker.get("market", {}).get("identifier", "")
                if exchange_id not in target_ids:
                    continue

                # Preferimos pares vs USD o USDT (más líquidos y comparables)
                target_currency = ticker.get("target", "")
                if target_currency not in ("USD", "USDT"):
                    continue

                # converted_last.usd siempre normaliza a USD (incluso desde USDT)
                price_usd = ticker.get("converted_last", {}).get("usd")
                if not price_usd or price_usd <= 0:
                    continue

                # Elegimos el exchange_id como clave (puede haber varios pares por exchange)
                # Guardamos solo el primer ticker válido por exchange (el más líquido)
                if exchange_id not in prices:
                    prices[exchange_id] = float(price_usd)
                    logger.debug(f"  ✓ {exchange_id}: ${price_usd:,.2f}")

            # Si ya tenemos todos los exchanges que buscamos, no necesitamos más páginas
            if target_ids.issubset(set(prices.keys())):
                break

            # Verificar si hay más páginas
            if not data.get("has_more", False) and len(tickers) < 100:
                break

            page += 1
            if page > 5:  # Máx 5 páginas para evitar loops con la API free
                break

        logger.info(f"  → Precios reales obtenidos: {len(prices)}/{len(target_ids)} exchanges")

        # Mapeo inverso: convierte IDs de CoinGecko de vuelta a nombres "amigables"
        # (ej. "gdax" → "coinbase" para que el display sea bonito)
        id_to_friendly = {v: k for k, v in EXCHANGE_ID_MAP.items() if k in TRADING.exchanges}
        prices_friendly: Dict[str, float] = {}
        for cg_id, price in prices.items():
            friendly = id_to_friendly.get(cg_id, cg_id)
            prices_friendly[friendly] = price

        if len(prices_friendly) < 2:
            logger.warning(
                f"⚠️ Solo {len(prices_friendly)} exchange(s) con datos reales para {coin_id}. "
                "Activando fallback a precios simulados..."
            )
            base_data = self.get_price_simple([coin_id])
            base_price = base_data.get(coin_id, {}).get("usd") if base_data else None
            return self._simulate_exchange_prices(coin_id, base_price=base_price)

        return prices_friendly

    # ─────────────────────────────────────────────────────────────────────────
    # Precio simple (varios coins de golpe)
    # ─────────────────────────────────────────────────────────────────────────
    def get_price_simple(self, coin_ids: list, vs_currency: str = "usd") -> Dict:
        """
        Obtiene precios simples de varios coins vs una moneda fiat.
        Endpoint: /simple/price — muy eficiente, 1 llamada para N coins.

        Args:
            coin_ids: lista de IDs de CoinGecko (e.g. ["bitcoin", "ethereum"])
            vs_currency: moneda de referencia (e.g. "usd", "eur")

        Returns:
            Dict con precios: {"bitcoin": {"usd": 67500.0}, ...}
        """
        url = f"{self.base_url}/simple/price"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": vs_currency,
            "include_24hr_change": "true",
            "include_market_cap": "true",
        }

        data = self._safe_get(url, params=params)
        if data:
            logger.debug(f"Precios simples obtenidos: {list(data.keys())}")
            return data

        logger.error("Fallo definitivo al obtener precios simples.")
        return {}

    # ─────────────────────────────────────────────────────────────────────────
    # DEPRECATED: Mantenido para compatibilidad pero ya NO se usa en el loop.
    # get_all_exchange_prices() lo reemplaza eficientemente.
    # ─────────────────────────────────────────────────────────────────────────
    def get_price_by_exchange(self, coin_id: str, exchange_id: str) -> Optional[float]:
        """
        ⚠️ DEPRECATED — Usa get_all_exchange_prices() en su lugar.
        Obtiene el precio de un coin en un exchange específico.
        Endpoint: /exchanges/{id}/tickers (1 llamada por exchange = ineficiente).

        Mantenido para debugging o uso puntual.
        """
        real_id = EXCHANGE_ID_MAP.get(exchange_id, exchange_id)
        url = f"{self.base_url}/exchanges/{real_id}/tickers"

        symbol_map = {
            "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
            "binancecoin": "BNB", "ripple": "XRP",
        }
        coin_symbol = symbol_map.get(coin_id, coin_id.upper()[:3])

        data = self._safe_get(url, params={"coin_ids": coin_id}, max_retries=2)
        if not data:
            return None

        for ticker in data.get("tickers", []):
            if (ticker.get("base") == coin_symbol and
                    ticker.get("target") in ["USD", "USDT"]):
                price = ticker.get("converted_last", {}).get("usd")
                if price:
                    return float(price)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback: precios simulados con spread realista
    # ─────────────────────────────────────────────────────────────────────────
    def _simulate_exchange_prices(self, coin_id: str, base_price: float = None) -> Dict[str, float]:
        """
        MODO SIMULACIÓN: Genera precios realistas con spread artificial
        basándose en el precio global de CoinGecko.

        Los spreads reales entre exchanges suelen ser 0.1%-2%.

        Args:
            coin_id: ID del coin
            base_price: Precio base ya conocido (evita un request extra)
        Returns:
            Dict con precios simulados por exchange
        """
        import random

        if base_price is None:
            base_data = self.get_price_simple([coin_id])
            if base_data and coin_id in base_data:
                base_price = base_data[coin_id].get("usd", 0)

        if not base_price:
            logger.warning(f"⚠️ Imposible obtener precio base de la API para {coin_id}. Usando precio de emergencia.")
            # Fallback de emergencia extremo si CoinGecko nos banea por completo
            fallback_prices = {
                "bitcoin": 68000.0,
                "ethereum": 2000.0,
                "solana": 85.0,
                "binancecoin": 620.0,
                "ripple": 1.40
            }
            base_price = fallback_prices.get(coin_id, 100.0)

        simulated = {}
        for exchange in TRADING.exchanges:
            # Spread aleatorio entre -1.5% y +1.5%
            spread_pct = random.uniform(-0.015, 0.015)
            simulated[exchange] = round(base_price * (1 + spread_pct), 2)

        logger.info(f"🎭 Precios SIMULADOS para {coin_id}: {simulated}")
        return simulated

    # ─────────────────────────────────────────────────────────────────────────
    # Market overview
    # ─────────────────────────────────────────────────────────────────────────
    def get_market_overview(self, limit: int = 10) -> list:
        """
        Obtiene overview del mercado: top cryptos por market cap.
        Útil para el dashboard y para decidir qué monitorear.

        Returns:
            Lista de coins con precio, cambio 24h, market cap
        """
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h,7d"
        }
        data = self._safe_get(url, params=params, max_retries=2)
        return data if data else []
