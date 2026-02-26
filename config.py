"""
╔══════════════════════════════════════════════════════╗
║         AntiGravity Crypto Hunter - config.py        ║
║   🚀 Configuration, API Keys & Trading Parameters    ║
╚══════════════════════════════════════════════════════╝
⚠️  ADVERTENCIA: Esto NO es consejo financiero.
    Úsalo en modo simulación primero. El crypto es volátil.
"""

import os
from dataclasses import dataclass, field
from typing import List


# ─────────────────────────────────────────────
# 🔑 API KEYS (carga desde variables de entorno
#    para máxima seguridad — nunca hardcodear!)
# ─────────────────────────────────────────────
class APIKeys:
    # CoinGecko (gratis, sin auth requerida para uso básico)
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

    # Twitter/X Developer API v2
    # Obtén tu key en: https://developer.twitter.com/
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "TU_BEARER_TOKEN_AQUI")

    # Notificaciones por Email (Gmail SMTP)
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "tu_email@gmail.com")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "tu_app_password")  # App Password de Google
    EMAIL_RECEIVER: str = os.getenv("EMAIL_RECEIVER", "destino@gmail.com")

    # Twilio SMS (opcional)
    TWILIO_SID: str = os.getenv("TWILIO_SID", "")
    TWILIO_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM: str = os.getenv("TWILIO_PHONE_FROM", "+1234567890")
    TWILIO_TO: str = os.getenv("TWILIO_PHONE_TO", "+0987654321")

    # Telegram Bot (opcional)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # CCXT para trading real (usa testnet primero!)
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET: str = os.getenv("BINANCE_SECRET", "")


# ─────────────────────────────────────────────
# 📊 Cryptos y Exchanges a Monitorear
# ─────────────────────────────────────────────
@dataclass
class TradingConfig:
    # IDs de CoinGecko (ver: https://api.coingecko.com/api/v3/coins/list)
    coins: List[str] = field(default_factory=lambda: [
        "bitcoin",
        "ethereum",
        "solana",
        "binancecoin",
        "ripple",
    ])

    # Exchanges soportados por CoinGecko (IDs del EXCHANGE_ID_MAP en price_fetcher.py)
    # ✅ IDs verificados 2026: binance, coinbase (→gdax), kraken, kucoin, bybit
    # ⚠️ huobi/htx puede estar no disponible en la API free — reemplazado por bybit
    exchanges: List[str] = field(default_factory=lambda: [
        "binance",
        "coinbase",   # Se mapea automáticamente a 'gdax' en price_fetcher.py
        "kraken",
        "kucoin",
        "bybit",      # Reemplaza huobi/htx (más activo y disponible en API free)
    ])

    # Umbral mínimo de diferencia de precio para detectar arbitraje (%)
    # Por debajo de esto, los fees lo hacen no rentable
    arbitrage_threshold_pct: float = 0.8

    # Umbral de sentimiento para arriesgar más en un trade simulado
    # Rango: -1.0 (negativo) a +1.0 (positivo)
    sentiment_bullish_threshold: float = 0.2
    sentiment_bearish_threshold: float = -0.2

    # Capital inicial de simulación (en USD)
    sim_capital_usd: float = 1000.0

    # Fee estimado por trade en exchanges (%)
    # Binance cobra ~0.1%, Coinbase ~0.5%
    estimated_fee_pct: float = 0.2

    # Número de tweets a analizar por búsqueda
    max_tweets: int = 50

    # Intervalo entre ciclos de monitoreo (segundos)
    # ✅ 120s = seguro con API gratuita (~30 calls/min). Sube a 60 solo con API Pro.
    loop_interval_seconds: int = 120

    # Máximos intentos de reintentos ante error de API
    max_retries: int = 3


# ─────────────────────────────────────────────
# 🎛️ Modo de Operación
# ─────────────────────────────────────────────
class BotMode:
    SIMULATION = "simulation"   # 🟢 Modo seguro: solo simula, no ejecuta trades reales
    PAPER     = "paper"         # 🟡 Paper trading con exchange testnet
    LIVE      = "live"          # 🔴 Trading real (¡CUIDADO! Solo si sabes lo que haces)

    CURRENT = SIMULATION        # ← Cambia esto cuando estés listo


# ─────────────────────────────────────────────
# 📁 Logging y Output
# ─────────────────────────────────────────────
class LogConfig:
    LOG_FILE = "antigravity_bot.log"
    TRADES_FILE = "simulated_trades.json"
    ML_DATA_FILE = "price_history.csv"
    LOG_LEVEL = "INFO"


# ─────────────────────────────────────────────
# Instancias globales (importa desde aquí)
# ─────────────────────────────────────────────
API = APIKeys()
TRADING = TradingConfig()
LOG = LogConfig()
