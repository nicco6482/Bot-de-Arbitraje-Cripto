"""
╔══════════════════════════════════════════════════════╗
║   AntiGravity Crypto Hunter - sentiment_analyzer.py  ║
║   🧠 Análisis de sentimiento en X (Twitter) en RT    ║
╚══════════════════════════════════════════════════════╝
Usa Twitter API v2 (Tweepy) + TextBlob para NLP.
El sentimiento ajusta el tamaño de los trades simulados:
  - Positivo fuerte → más confianza → trade más grande
  - Negativo         → modo precaución → trade más pequeño

⚠️ Requiere Twitter Developer Account (nivel Free o Basic).
   Regístrate en: https://developer.twitter.com/
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional
from config import API, TRADING

logger = logging.getLogger("AntiGravity.Sentiment")

# Intentamos importar las dependencias opcionales
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    logger.warning("tweepy no instalado. Usando sentimiento simulado.")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("textblob no instalado. Usando sentimiento simulado.")


@dataclass
class SentimentResult:
    """Resultado del análisis de sentimiento para un coin."""
    coin: str
    score: float          # -1.0 (muy negativo) a +1.0 (muy positivo)
    subjectivity: float   # 0.0 (objetivo) a 1.0 (subjetivo)
    tweet_count: int      # Tweets analizados
    label: str            # "BULLISH", "BEARISH", or "NEUTRAL"
    trending: bool        # ¿Está en tendencia?

    @property
    def emoji(self) -> str:
        if self.label == "BULLISH":
            return "🚀🟢"
        elif self.label == "BEARISH":
            return "💀🔴"
        return "😐🟡"

    def __str__(self):
        return (
            f"{self.emoji} {self.coin.upper()} | Score: {self.score:+.3f} | "
            f"Tweets: {self.tweet_count} | {self.label}"
        )


class SentimentAnalyzer:
    """
    Analiza el sentimiento del mercado cripto usando tweets.
    
    El sentimiento de redes sociales tiene una correlación
    documentada con movimientos de precio a corto plazo,
    especialmente en altcoins con comunidades activas.
    """

    # Mapa de coin_id → hashtags/keywords de búsqueda
    COIN_QUERIES = {
        "bitcoin":      "#Bitcoin OR $BTC OR Bitcoin price",
        "ethereum":     "#Ethereum OR $ETH OR Ethereum price",
        "solana":       "#Solana OR $SOL OR Solana price",
        "binancecoin":  "#BNB OR $BNB OR Binance Coin",
        "ripple":       "#XRP OR $XRP OR Ripple price",
    }

    def __init__(self):
        self.client = None
        self._setup_client()

    def _setup_client(self):
        """Inicializa el cliente de Twitter API v2."""
        if not TWEEPY_AVAILABLE:
            logger.info("Tweepy no disponible. Modo sentimiento simulado activado.")
            return

        bearer = API.TWITTER_BEARER_TOKEN
        if not bearer or bearer == "TU_BEARER_TOKEN_AQUI":
            logger.warning("⚠️ No hay Bearer Token de Twitter. Modo simulado.")
            return

        try:
            self.client = tweepy.Client(
                bearer_token=bearer,
                wait_on_rate_limit=True   # Tweepy maneja el rate limit automáticamente
            )
            logger.info("✅ Cliente de Twitter API v2 conectado.")
        except Exception as e:
            logger.error(f"Error conectando Twitter API: {e}")

    def analyze(self, coin_id: str) -> SentimentResult:
        """
        Analiza el sentimiento de un coin en X (Twitter).
        
        Si la API de Twitter no está disponible, usa modo simulado
        con datos aleatorios realistas para desarrollo/testing.

        Args:
            coin_id: ID del coin (e.g. "bitcoin")

        Returns:
            SentimentResult con score, label y metadata
        """
        if self.client and TWEEPY_AVAILABLE and TEXTBLOB_AVAILABLE:
            return self._analyze_real(coin_id)
        else:
            return self._analyze_simulated(coin_id)

    def _analyze_real(self, coin_id: str) -> SentimentResult:
        """
        Análisis real usando Twitter API v2 + TextBlob NLP.
        
        TextBlob calcula la polaridad de cada tweet:
          +1.0 = muy positivo ("Bitcoin goes to the moon!")
          -1.0 = muy negativo ("Crypto is crashing hard")
           0.0 = neutral    ("Bitcoin trading at $68k")
        """
        query_str = self.COIN_QUERIES.get(
            coin_id,
            f"#{coin_id} OR ${coin_id[:3].upper()}"
        )
        # Excluimos retweets y contenido adulto para mejor calidad
        query_str += " -is:retweet lang:en"

        polarity_scores = []
        subjectivity_scores = []
        tweet_count = 0

        try:
            # Buscamos tweets recientes (últimos 7 días para plan Free)
            response = self.client.search_recent_tweets(
                query=query_str,
                max_results=min(TRADING.max_tweets, 100),  # máx 100 por request
                tweet_fields=["created_at", "public_metrics"],
            )

            if not response.data:
                logger.warning(f"No se encontraron tweets para {coin_id}")
                return self._analyze_simulated(coin_id)

            for tweet in response.data:
                try:
                    blob = TextBlob(tweet.text)
                    polarity_scores.append(blob.sentiment.polarity)
                    subjectivity_scores.append(blob.sentiment.subjectivity)
                    tweet_count += 1
                except Exception:
                    continue

        except tweepy.errors.TweepyException as e:
            logger.error(f"Error Twitter API: {e}")
            return self._analyze_simulated(coin_id)

        if not polarity_scores:
            return self._analyze_simulated(coin_id)

        avg_score = sum(polarity_scores) / len(polarity_scores)
        avg_subjectivity = sum(subjectivity_scores) / len(subjectivity_scores)

        label = self._score_to_label(avg_score)
        # "Trending" si tenemos muchos tweets subjetivos (hype real)
        trending = avg_subjectivity > 0.5 and tweet_count >= 20

        result = SentimentResult(
            coin=coin_id,
            score=round(avg_score, 4),
            subjectivity=round(avg_subjectivity, 4),
            tweet_count=tweet_count,
            label=label,
            trending=trending,
        )
        logger.info(f"Sentimiento real → {result}")
        return result

    def _analyze_simulated(self, coin_id: str) -> SentimentResult:
        """
        MODO SIMULACIÓN: Genera sentimiento realista con distribución
        normal centrada en 0 (mercados suelen ser mixed).
        
        Útil para: testing, demos, cuando no tienes API de Twitter.
        """
        import random
        # Distribución normal: mayormente neutral con picos ocasionales
        score = max(-1.0, min(1.0, random.gauss(0.05, 0.35)))
        subjectivity = random.uniform(0.2, 0.8)
        tweet_count = random.randint(15, 150)
        label = self._score_to_label(score)
        trending = subjectivity > 0.55 and tweet_count > 80

        result = SentimentResult(
            coin=coin_id,
            score=round(score, 4),
            subjectivity=round(subjectivity, 4),
            tweet_count=tweet_count,
            label=label,
            trending=trending,
        )
        logger.info(f"Sentimiento SIMULADO → {result}")
        return result

    @staticmethod
    def _score_to_label(score: float) -> str:
        if score >= TRADING.sentiment_bullish_threshold:
            return "BULLISH"
        elif score <= TRADING.sentiment_bearish_threshold:
            return "BEARISH"
        return "NEUTRAL"

    def get_fear_and_greed(self) -> Optional[dict]:
        """
        Bonus: Obtiene el índice Fear & Greed de Alternative.me.
        Es un indicador de sentimiento global del mercado crypto.
        0 = Miedo extremo (potencial compra)  
        100 = Codicia extrema (potencial venta)
        """
        import requests
        try:
            response = requests.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=5
            )
            data = response.json()
            entry = data["data"][0]
            logger.info(
                f"🔮 Fear & Greed Index: {entry['value']} ({entry['value_classification']})"
            )
            return {
                "value": int(entry["value"]),
                "label": entry["value_classification"],
                "timestamp": entry["timestamp"]
            }
        except Exception as e:
            logger.warning(f"No se pudo obtener Fear & Greed: {e}")
            return None
