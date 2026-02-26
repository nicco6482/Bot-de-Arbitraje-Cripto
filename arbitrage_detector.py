"""
╔══════════════════════════════════════════════════════╗
║  AntiGravity Crypto Hunter - arbitrage_detector.py   ║
║  🎯 Detecta oportunidades de arbitraje entre exchanges║
╚══════════════════════════════════════════════════════╝
El arbitraje crypto funciona así:
  1. BTC cotiza en $67,800 en Binance
  2. BTC cotiza en $68,200 en Coinbase
  3. Diferencia = $400 = 0.59% → con fees netos: ~0.19%
  4. Compras en Binance, vendes en Coinbase = PROFIT

Riesgos reales:
  - Velocidad de ejecución (slippage, latencia)
  - Fees de withdrawal entre exchanges
  - Volatilidad puede cerrar el spread antes de ejecutar
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from config import TRADING

logger = logging.getLogger("AntiGravity.Arbitrage")


@dataclass
class ArbitrageOpportunity:
    """Representa una oportunidad de arbitraje detectada."""
    coin: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    gross_spread_pct: float       # % diferencia bruta
    net_spread_pct: float         # % diferencia después de fees
    estimated_profit_usd: float   # En USD basado en capital de simulación
    is_viable: bool               # ¿Supera el umbral mínimo?

    def __str__(self):
        viable_str = "✅ VIABLE" if self.is_viable else "❌ No viable"
        return (
            f"\n{'='*55}\n"
            f"  💎 ARBITRAJE: {self.coin.upper()}\n"
            f"  🟢 COMPRAR en {self.buy_exchange:10s}: ${self.buy_price:,.2f}\n"
            f"  🔴 VENDER en  {self.sell_exchange:10s}: ${self.sell_price:,.2f}\n"
            f"  📊 Spread bruto:  {self.gross_spread_pct:+.3f}%\n"
            f"  💵 Spread neto:   {self.net_spread_pct:+.3f}% "
            f"(después de ~{TRADING.estimated_fee_pct*2:.1f}% en fees)\n"
            f"  💰 Profit estimado: ${self.estimated_profit_usd:.2f} "
            f"(sobre ${TRADING.sim_capital_usd:.0f})\n"
            f"  {viable_str}\n"
            f"{'='*55}"
        )


class ArbitrageDetector:
    """
    Detecta spreads de precio entre exchanges.
    
    Estrategia: Triangular Arbitrage Simplificado
    Buscamos el exchange más barato para comprar y el más caro
    para vender, calculando si el spread neto cubre los fees.
    """

    def find_opportunity(
        self,
        coin_id: str,
        exchange_prices: Dict[str, float]
    ) -> Optional[ArbitrageOpportunity]:
        """
        Encuentra la mejor oportunidad de arbitraje dado un mapa de precios.

        Args:
            coin_id: ID del coin (e.g. "bitcoin")
            exchange_prices: {exchange: price} (e.g. {"binance": 67800, "coinbase": 68200})

        Returns:
            ArbitrageOpportunity si existe oportunidad, None si no
        """
        if len(exchange_prices) < 2:
            logger.warning(f"Necesitamos al menos 2 exchanges para arbitraje. Got: {len(exchange_prices)}")
            return None

        # Encontrar el exchange con precio mínimo (compra aquí)
        buy_exchange = min(exchange_prices, key=exchange_prices.get)
        buy_price = exchange_prices[buy_exchange]

        # Encontrar el exchange con precio máximo (vende aquí)
        sell_exchange = max(exchange_prices, key=exchange_prices.get)
        sell_price = exchange_prices[sell_exchange]

        if buy_exchange == sell_exchange:
            # No hay spread útil
            return None

        # Calcular spread
        gross_spread_pct = ((sell_price - buy_price) / buy_price) * 100

        # Restamos fees de ambos lados del trade
        # fee_pct representa el fee total estimado (compra + venta)
        total_fee_pct = TRADING.estimated_fee_pct * 2
        net_spread_pct = gross_spread_pct - total_fee_pct

        # Profit en USD basado en capital de simulación
        estimated_profit_usd = (net_spread_pct / 100) * TRADING.sim_capital_usd

        is_viable = net_spread_pct >= TRADING.arbitrage_threshold_pct

        opportunity = ArbitrageOpportunity(
            coin=coin_id,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            gross_spread_pct=round(gross_spread_pct, 4),
            net_spread_pct=round(net_spread_pct, 4),
            estimated_profit_usd=round(estimated_profit_usd, 2),
            is_viable=is_viable,
        )

        if is_viable:
            logger.info(f"🎯 OPORTUNIDAD DETECTADA: {opportunity}")
        else:
            logger.debug(
                f"Spread {gross_spread_pct:.3f}% < umbral {TRADING.arbitrage_threshold_pct}% + fees"
            )

        return opportunity

    def scan_all_coins(
        self,
        all_prices: Dict[str, Dict[str, float]]
    ) -> List[ArbitrageOpportunity]:
        """
        Escanea TODOS los coins monitoreados en busca de arbitraje.

        Args:
            all_prices: {coin_id: {exchange: price}}

        Returns:
            Lista de oportunidades viables, ordenadas por rentabilidad
        """
        opportunities = []

        for coin_id, exchange_prices in all_prices.items():
            opp = self.find_opportunity(coin_id, exchange_prices)
            if opp and opp.is_viable:
                opportunities.append(opp)

        # Ordenar por mayor profit neto primero
        opportunities.sort(key=lambda x: x.net_spread_pct, reverse=True)

        if opportunities:
            logger.info(
                f"🚀 {len(opportunities)} oportunidades viables encontradas!"
            )
        else:
            logger.info("😴 Sin oportunidades viables en este ciclo.")

        return opportunities

    def calculate_price_matrix(
        self,
        exchange_prices: Dict[str, float]
    ) -> Dict[Tuple[str, str], float]:
        """
        Calcula la matriz de spreads entre todos los pares de exchanges.
        Útil para análisis y para el módulo de ML.

        Returns:
            {(buy_ex, sell_ex): spread_pct}
        """
        matrix = {}
        exchanges = list(exchange_prices.keys())

        for i, buy_ex in enumerate(exchanges):
            for sell_ex in exchanges[i+1:]:
                buy_p = exchange_prices[buy_ex]
                sell_p = exchange_prices[sell_ex]
                spread = ((sell_p - buy_p) / buy_p) * 100
                matrix[(buy_ex, sell_ex)] = round(spread, 4)

        return matrix

    def get_price_summary(self, coin_id: str, prices: Dict[str, float]) -> str:
        """Genera un resumen de precios formateado para logging/alertas."""
        if not prices:
            return f"Sin datos de precios para {coin_id}"

        lines = [f"\n💰 Precios de {coin_id.upper()}:"]
        for exchange, price in sorted(prices.items(), key=lambda x: x[1]):
            lines.append(f"   {exchange:12s}: ${price:>12,.2f}")

        min_p = min(prices.values())
        max_p = max(prices.values())
        spread = ((max_p - min_p) / min_p) * 100
        lines.append(f"   → Spread total: {spread:.3f}%")
        return "\n".join(lines)
