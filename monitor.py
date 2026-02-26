"""
╔══════════════════════════════════════════════════════╗
║       AntiGravity Crypto Hunter - monitor.py         ║
║   🚀 MAIN LOOP — El corazón del bot en tiempo real   ║
╚══════════════════════════════════════════════════════╝
Este es el script principal. Ejecuta:
    python monitor.py

Flujo de cada ciclo:
  1. 📡 Obtener precios de múltiples exchanges
  2. 🧠 Analizar sentimiento en Twitter/X
  3. 🎯 Detectar oportunidades de arbitraje
  4. 🎮 Simular trade (ajustado por sentimiento)
  5. 📣 Enviar alertas si hay oportunidad viable
  6. 🤖 Registrar datos para ML
  7. 💤 Esperar intervalo de tiempo
  8. 🔄 Repetir...

⚠️  DISCLAIMER: Este bot es educativo y para simulación.
    El trading crypto real conlleva riesgo de pérdida total.
    Nunca inviertas más de lo que puedas permitirte perder.
"""

import time
import signal
import logging
import sys
from datetime import datetime

# ─── Setup de Logging ───────────────────────────────────
from config import TRADING, LOG, BotMode

logging.basicConfig(
    level=getattr(logging, LOG.LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG.LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger("AntiGravity.Monitor")

# ─── Importar módulos del bot ────────────────────────────
from price_fetcher import PriceFetcher
from sentiment_analyzer import SentimentAnalyzer
from arbitrage_detector import ArbitrageDetector
from trade_simulator import TradeSimulator
from notifier import Notifier
from ml_predictor import MLPredictor, PriceDataRecorder


# ─────────────────────────────────────────────────────────
# Banner de bienvenida
# ─────────────────────────────────────────────────────────
BANNER = r"""
    _          _   _  _____                 _ _         
   / \   _ __ | |_(_)/ ___|_ __ __ ___   _(_) |_ _   _ 
  / _ \ | '_ \| __| | |  _| '__/ _` \ \ / / | __| | | |
 / ___ \| | | | |_| | |_| | | | (_| |\ V /| | |_| |_| |
/_/   \_\_| |_|\__|_|\____|_|  \__,_| \_/ |_|\__|\__, |
   🚀 C R Y P T O   H U N T E R               |___/ 
   ══════════════════════════════════════════════════
   Arbitrage Bot + Sentiment AI | Modo: {mode}
   ══════════════════════════════════════════════════
"""


class AntiGravityBot:
    """
    Clase principal del bot AntiGravity Crypto Hunter.
    Orquesta todos los módulos en un bucle de monitoreo en tiempo real.
    """

    def __init__(self):
        self.running = False
        self.cycle_count = 0
        self.start_time = datetime.now()

        logger.info("Inicializando módulos...")

        # Instanciar todos los módulos
        self.price_fetcher     = PriceFetcher()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.arb_detector      = ArbitrageDetector()
        self.simulator         = TradeSimulator()
        self.notifier          = Notifier()
        self.ml_predictor      = MLPredictor()
        self.data_recorder     = PriceDataRecorder()

        # Intentar cargar modelo ML previo (si hay datos acumulados)
        self.ml_predictor.train()

        # Manejar Ctrl+C suavemente
        signal.signal(signal.SIGINT, self._graceful_shutdown)

        logger.info("✅ Bot inicializado. Listo para cazar arbitraje.")

    def run(self):
        """Bucle principal de monitoreo en tiempo real."""
        print(BANNER.format(mode=BotMode.CURRENT.upper()))
        self.running = True

        while self.running:
            self.cycle_count += 1
            cycle_start = time.time()

            logger.info(f"\n{'─'*55}")
            logger.info(f"🔄 CICLO #{self.cycle_count} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'─'*55}")

            try:
                self._run_cycle()
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Error en ciclo {self.cycle_count}: {e}", exc_info=True)
                # Continuar al próximo ciclo aunque haya error

            # Cada 10 ciclos, mostrar performance summary
            if self.cycle_count % 10 == 0:
                self.simulator.get_performance_summary()

                # Reentrenar ML con datos acumulados
                logger.info("🤖 Re-entrenando modelo ML con nuevos datos...")
                self.ml_predictor.train()

            # Esperar hasta completar el intervalo configurado
            elapsed = time.time() - cycle_start
            sleep_time = max(0, TRADING.loop_interval_seconds - elapsed)
            logger.info(
                f"⏱️ Ciclo completado en {elapsed:.1f}s. "
                f"Próximo en {sleep_time:.0f}s..."
            )
            time.sleep(sleep_time)

        # Al finalizar, mostrar resumen final
        self._final_report()

    def _run_cycle(self):
        """
        Ejecuta un ciclo completo de análisis para todos los coins.
        """
        # 🔮 Fear & Greed Index (una sola vez por ciclo, es global)
        fg = self.sentiment_analyzer.get_fear_and_greed()
        fear_greed_value = fg["value"] if fg else 50

        # 🗺️ Market Overview rápido
        if self.cycle_count == 1:
            logger.info("📊 Market Overview (Top 5 coins por market cap):")
            overview = self.price_fetcher.get_market_overview(limit=5)
            for coin_data in overview:
                change = coin_data.get("price_change_percentage_24h", 0) or 0
                emoji = "🟢" if change >= 0 else "🔴"
                logger.info(
                    f"   {emoji} {coin_data['symbol'].upper():6s} | "
                    f"${coin_data['current_price']:>12,.2f} | "
                    f"{change:+.2f}% 24h"
                )

        all_prices = {}      # {coin: {exchange: price}}
        all_sentiments = {}  # {coin: SentimentResult}

        # ─────────────────────────────────────────
        # Paso 1: Obtener precios de todos los coins
        # ─────────────────────────────────────────
        # Primero obtenemos precios simples para todos (eficiente, 1 request)
        simple_prices = self.price_fetcher.get_price_simple(TRADING.coins)

        for coin in TRADING.coins:
            logger.info(f"\n🔍 Analizando {coin.upper()}...")

            if coin not in simple_prices:
                logger.warning(f"  Sin datos para {coin}")
                continue

            # Precio global y cambio 24h
            coin_data = simple_prices[coin]
            global_price = coin_data.get("usd", 0)
            change_24h = coin_data.get("usd_24h_change", 0) or 0

            logger.info(f"  💰 Precio global: ${global_price:,.2f} ({change_24h:+.2f}% 24h)")

            # Precios por exchange (para detectar spreads)
            exchange_prices = self.price_fetcher.get_all_exchange_prices(coin)
            all_prices[coin] = exchange_prices

            # Resumen de precios por exchange
            price_summary = self.arb_detector.get_price_summary(coin, exchange_prices)
            logger.info(price_summary)

            # ─────────────────────────────────────
            # Paso 2: Análisis de sentimiento
            # ─────────────────────────────────────
            sentiment = self.sentiment_analyzer.analyze(coin)
            all_sentiments[coin] = sentiment
            logger.info(f"  {sentiment}")

            # ─────────────────────────────────────
            # Paso 3: Detección de arbitraje
            # ─────────────────────────────────────
            opportunity = self.arb_detector.find_opportunity(coin, exchange_prices)

            # ─────────────────────────────────────
            # Paso 4: Simulación de trade
            # ─────────────────────────────────────
            simulated_trade = None
            if opportunity and opportunity.is_viable:
                logger.info(f"\n  {opportunity}")
                simulated_trade = self.simulator.execute_simulation(opportunity, sentiment)

            # ─────────────────────────────────────
            # Paso 5: Predicción ML (si entrenado)
            # ─────────────────────────────────────
            if self.ml_predictor.is_trained:
                # Calcular dist_from_ma approximado usando precio global
                dist_from_ma = change_24h / 5  # Simplificación para demo
                ml_signal, ml_conf = self.ml_predictor.predict(
                    change_24h=change_24h,
                    sentiment_score=sentiment.score,
                    fear_greed=fear_greed_value,
                    dist_from_ma=dist_from_ma,
                )
                logger.info(
                    f"  🤖 ML Signal: {ml_signal} "
                    f"({ml_conf:.1%} confianza)"
                )

            # ─────────────────────────────────────
            # Paso 6: Notificación si hay oportunidad
            # ─────────────────────────────────────
            if opportunity and opportunity.is_viable:
                self.notifier.send_arbitrage_alert(
                    opportunity, sentiment, simulated_trade
                )

            # ─────────────────────────────────────
            # Paso 7: Registrar datos para ML
            # ─────────────────────────────────────
            self.data_recorder.record(
                coin=coin,
                price=global_price,
                change_24h=change_24h,
                sentiment_score=sentiment.score,
                fear_greed=fear_greed_value,
            )

            # Rate limiting: pausa entre análisis de coins
            time.sleep(1.5)

    def _graceful_shutdown(self, signum, frame):
        """Maneja Ctrl+C de forma elegante."""
        logger.info("\n⚠️ Señal de interrupción recibida. Cerrando bot...")
        self.running = False

    def _final_report(self):
        """Muestra el reporte final al cerrar el bot."""
        runtime = (datetime.now() - self.start_time).total_seconds() / 60
        logger.info(f"\n{'═'*55}")
        logger.info(f"  🛬 BOT DETENIDO")
        logger.info(f"  ⏱️  Runtime: {runtime:.1f} minutos")
        logger.info(f"  🔄 Ciclos completados: {self.cycle_count}")
        self.simulator.get_performance_summary()
        logger.info(f"{'═'*55}")


# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot = AntiGravityBot()
    bot.run()
