"""
╔══════════════════════════════════════════════════════╗
║   AntiGravity Crypto Hunter - trade_simulator.py     ║
║   🎮 Simulador de trades ajustado por sentimiento    ║
╚══════════════════════════════════════════════════════╝
El simulador combina:
  - Oportunidad de arbitraje detectada
  - Sentimiento de Twitter como modificador de confianza
  - Capital virtual para calcular P&L (profit and loss)

Esto es SIMULACIÓN. No mueve dinero real.
Úsalo para validar tu estrategia antes de ir en vivo.
"""

import json
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from config import TRADING, LOG, BotMode
from arbitrage_detector import ArbitrageOpportunity
from sentiment_analyzer import SentimentResult

logger = logging.getLogger("AntiGravity.Simulator")


@dataclass
class SimulatedTrade:
    """Representa un trade simulado con todos sus detalles."""
    timestamp: str
    coin: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    capital_used: float           # Capital desplegado en el trade
    gross_profit_usd: float       # Ganancia antes de fees
    fees_paid_usd: float          # Fees estimados ambos lados
    net_profit_usd: float         # Ganancia neta real
    net_profit_pct: float         # % de retorno neto
    sentiment_score: float        # Score de sentimiento que influyó
    sentiment_label: str          # BULLISH/BEARISH/NEUTRAL
    risk_multiplier: float        # Cuánto ajustamos por sentimiento
    mode: str                     # simulation/paper/live

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        profit_emoji = "💰" if self.net_profit_usd > 0 else "📉"
        return (
            f"{profit_emoji} TRADE SIMULADO | {self.coin.upper()}\n"
            f"   Compra en {self.buy_exchange} @ ${self.buy_price:,.2f}\n"
            f"   Venta en  {self.sell_exchange} @ ${self.sell_price:,.2f}\n"
            f"   Capital: ${self.capital_used:,.2f} | "
            f"Profit neto: ${self.net_profit_usd:+.2f} ({self.net_profit_pct:+.3f}%)\n"
            f"   Sentimiento: {self.sentiment_label} ({self.sentiment_score:+.3f}) | "
            f"Risk mult: x{self.risk_multiplier:.2f}"
        )


class TradeSimulator:
    """
    Simula trades de arbitraje ajustados por análisis de sentimiento.
    
    Lógica de risk management basada en sentimiento:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    BULLISH fuerte  (+0.5 a +1.0) → risk_mult = 1.5 (50% más de capital)
    BULLISH moderado (+0.2 a +0.5) → risk_mult = 1.2
    NEUTRAL         (-0.2 a +0.2) → risk_mult = 1.0 (capital base)
    BEARISH moderado (-0.5 a -0.2) → risk_mult = 0.7 (reducir exposición)
    BEARISH fuerte  (-1.0 a -0.5) → risk_mult = 0.3 (capital mínimo)
    """

    def __init__(self, initial_capital: float = None):
        self.capital = initial_capital or TRADING.sim_capital_usd
        self.initial_capital = self.capital
        self.trade_history: List[SimulatedTrade] = []
        self._load_existing_trades()

    def execute_simulation(
        self,
        opportunity: ArbitrageOpportunity,
        sentiment: SentimentResult,
    ) -> Optional[SimulatedTrade]:
        """
        Simula la ejecución de un trade de arbitraje.

        Args:
            opportunity: La oportunidad de arbitraje detectada
            sentiment: El análisis de sentimiento para este coin

        Returns:
            SimulatedTrade con el resultado, o None si se rechaza
        """
        if not opportunity.is_viable:
            logger.debug(f"Trade rechazado: spread neto insuficiente")
            return None

        if self.capital <= 0:
            logger.warning("⚠️ Sin capital disponible para simular.")
            return None

        # Calcular multiplicador de riesgo basado en sentimiento
        risk_multiplier = self._sentiment_to_risk(sentiment)

        # Capital a desplegar en este trade
        # Nunca usamos más del 80% para mantener reserva
        max_capital = self.capital * 0.80
        capital_used = min(max_capital, self.capital * risk_multiplier * 0.5)
        capital_used = max(10.0, capital_used)  # mínimo $10 para ser relevante

        # Calcular P&L
        # Cuántas unidades podemos comprar
        units = capital_used / opportunity.buy_price

        # Ingreso de la venta
        gross_revenue = units * opportunity.sell_price
        gross_profit = gross_revenue - capital_used

        # Fees: fee en compra + fee en venta
        fee_buy = capital_used * (TRADING.estimated_fee_pct / 100)
        fee_sell = gross_revenue * (TRADING.estimated_fee_pct / 100)
        total_fees = fee_buy + fee_sell

        net_profit = gross_profit - total_fees
        net_profit_pct = (net_profit / capital_used) * 100

        # Actualizar capital virtual
        self.capital += net_profit

        trade = SimulatedTrade(
            timestamp=datetime.now().isoformat(),
            coin=opportunity.coin,
            buy_exchange=opportunity.buy_exchange,
            sell_exchange=opportunity.sell_exchange,
            buy_price=opportunity.buy_price,
            sell_price=opportunity.sell_price,
            capital_used=round(capital_used, 2),
            gross_profit_usd=round(gross_profit, 2),
            fees_paid_usd=round(total_fees, 2),
            net_profit_usd=round(net_profit, 2),
            net_profit_pct=round(net_profit_pct, 4),
            sentiment_score=sentiment.score,
            sentiment_label=sentiment.label,
            risk_multiplier=round(risk_multiplier, 3),
            mode=BotMode.CURRENT,
        )

        self.trade_history.append(trade)
        self._save_trade(trade)

        logger.info(str(trade))
        return trade

    def _sentiment_to_risk(self, sentiment: SentimentResult) -> float:
        """
        Convierte el score de sentimiento en un multiplicador de riesgo.
        
        El sentimiento modifica cuánto capital asignamos al trade.
        Nunca eliminamos el trade por sentimiento solo; 
        el spread de arbitraje es la señal primaria.
        """
        score = sentiment.score

        if score >= 0.5:
            multiplier = 1.5   # 🚀 Muy bullish → más agresivo
        elif score >= 0.2:
            multiplier = 1.2   # 🟢 Bullish → confiado
        elif score >= -0.2:
            multiplier = 1.0   # 😐 Neutral → base
        elif score >= -0.5:
            multiplier = 0.7   # 🟡 Bearish → precaución
        else:
            multiplier = 0.3   # 🔴 Muy bearish → mínima exposición

        # Si está trending (mucho hype subjetivo), añadir 10% extra
        if sentiment.trending:
            multiplier *= 1.1

        logger.debug(f"Risk multiplier para {sentiment.label} ({score:.3f}): x{multiplier:.2f}")
        return multiplier

    def get_performance_summary(self) -> dict:
        """Calcula métricas de performance del portafolio simulado."""
        if not self.trade_history:
            return {"message": "Sin trades registrados aún."}

        total_profit = sum(t.net_profit_usd for t in self.trade_history)
        win_trades = [t for t in self.trade_history if t.net_profit_usd > 0]
        loss_trades = [t for t in self.trade_history if t.net_profit_usd <= 0]
        
        win_rate = len(win_trades) / len(self.trade_history) * 100
        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        summary = {
            "total_trades": len(self.trade_history),
            "winning_trades": len(win_trades),
            "losing_trades": len(loss_trades),
            "win_rate_pct": round(win_rate, 1),
            "initial_capital": self.initial_capital,
            "current_capital": round(self.capital, 2),
            "total_profit_usd": round(total_profit, 2),
            "total_return_pct": round(total_return_pct, 2),
            "avg_profit_per_trade": round(total_profit / len(self.trade_history), 2),
            "best_trade": max(self.trade_history, key=lambda x: x.net_profit_usd).net_profit_usd,
            "worst_trade": min(self.trade_history, key=lambda x: x.net_profit_usd).net_profit_usd,
        }

        logger.info(
            f"\n{'═'*50}\n"
            f"  📈 PERFORMANCE SUMMARY\n"
            f"  Trades: {summary['total_trades']} | "
            f"Win Rate: {summary['win_rate_pct']}%\n"
            f"  Capital: ${summary['initial_capital']:,.2f} → "
            f"${summary['current_capital']:,.2f}\n"
            f"  P&L Total: ${summary['total_profit_usd']:+,.2f} "
            f"({summary['total_return_pct']:+.2f}%)\n"
            f"{'═'*50}"
        )
        return summary

    def _save_trade(self, trade: SimulatedTrade):
        """Guarda el trade en el archivo JSON de historial."""
        try:
            try:
                with open(LOG.TRADES_FILE, "r") as f:
                    trades_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                trades_data = []

            trades_data.append(trade.to_dict())

            with open(LOG.TRADES_FILE, "w") as f:
                json.dump(trades_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando trade: {e}")

    def _load_existing_trades(self):
        """Carga historial de trades previos al iniciar."""
        try:
            with open(LOG.TRADES_FILE, "r") as f:
                trades_data = json.load(f)
            # Reconstruir objetos SimulatedTrade
            for t in trades_data:
                self.trade_history.append(SimulatedTrade(**t))
            # Recalcular capital basado en historial
            if self.trade_history:
                cumulative_profit = sum(t.net_profit_usd for t in self.trade_history)
                self.capital = self.initial_capital + cumulative_profit
                logger.info(
                    f"📂 Cargados {len(self.trade_history)} trades previos. "
                    f"Capital actual: ${self.capital:,.2f}"
                )
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # Primer run, sin historial previo
