# 🚀 AntiGravity Crypto Hunter

**AntiGravity Crypto Hunter** es un bot avanzado de monitoreo, análisis de métricas y detección de oportunidades de arbitraje en el mercado de criptomonedas. Desarrollado en Python, cuenta con una arquitectura modular que no solo encuentra discrepancias de precios entre exchanges, sino que también integra análisis de sentimiento en redes sociales y un simulador de trading (Paper Trading).

> ⚠️ **Disclaimer Financiero:** Este bot tiene fines puramente educativos e informativos. El mercado local e internacional de criptomonedas es altamente volátil. ¡Se recomienda usar siempre primero el modo simulación y no arriesgar capital que no estés dispuesto a perder!

---

## 🚀 Probar Demo en Vivo (Desde el Navegador)

Puedes ejecutar este bot directamente en la nube sin instalar nada en tu computadora usando cualquiera de las siguientes opciones gratuitas:

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/nicco6482/Bot-de-Arbitraje-Cripto)

*Al abrir el entorno, simplemente escribe `python monitor.py` en la terminal que aparecerá en la parte inferior de la pantalla.*

---

## 🌟 Características Principales

1. **Detección de Arbitraje Triangular:** Escanea múltiples exchanges (Binance, Coinbase, Kraken, KuCoin, Bybit) simultáneamente para detectar spreads de precios viables descontando comisiones pre-configuradas.
2. **Eficiencia de API (Rate-Limit Safe):** Motor de peticiones altamente optimizado (`price_fetcher.py`). Usa un único llamado a la API (`/coins/{id}/tickers`) para traer todos los exchanges a la vez e incorpora un sistema *Exponential Backoff* para esquivar baneos por "Too Many Requests" (HTTP 429).
3. **Análisis de Sentimiento (Sentiment AI):** Capacidad de conectarse a la API de X (Twitter) para medir la temperatura emocional de los inversores (Bullish/Bearish) utilizando la librería TextBlob. (Se puede utilizar en modo simulado si no hay keys disponibles).
4. **Trading Simulado (Paper Trading):** Rastrea las transacciones teóricas comprobando cómo hubieran resultado tras comisiones (Gross Spread vs Net Spread) sin poner en riesgo fondos reales reales (`trade_simulator.py`).
5. **Preparado para Machine Learning:** Base sembrada para futura implementación predictiva con `ml_predictor.py`.
6. **Sistema de Notificaciones Automático:** Alertas visuales en consola con soporte en código para expandir a Email, Twilio (SMS), o Telegram Bots.

---

## 🏗️ Arquitectura y Archivos Claves

El proyecto está diseñado bajo principios de Clean Code, segmentando las responsabilidades lógicas en varios archivos:

| Archivo | Descripción |
|---------|-------------|
| ⚙️ `config.py` | Configuración global. Aquí se cambian claves API, exchanges objetivo, cryptos y umbrales de capital y comisiones. |
| 👁️ `monitor.py` | Entrada principal del bot (`main`). Orquesta el bucle infinito que coordina todos los módulos. |
| 💸 `price_fetcher.py` | Se conecta a CoinGecko. Filtra precios y normaliza a `USD`. Si hay límites HTTP, entra en retardo o activa un fallback de simulación. |
| 🎯 `arbitrage_detector.py` | Toma datos de precios paralelos, busca mínimos (compra) y máximos (venta) por cripto y diagnostica si el % es rentable. |
| 🤖 `sentiment_analyzer.py`| Recupera los últimos tuits y les aplica PNL (Procesamiento de Lenguaje Natural) para dar un Sentiment Score (-1 a 1). |
| 🧾 `trade_simulator.py` | Registra el trade validado, simula el descuento del coste real de transacción, y va guardando el PnL (Ganancias/Pérdidas). |
| � `notifier.py` | Manejo de alertas externas (Telegram/Email/Consola). |
| 🔮 `ml_predictor.py` | Preparación para algoritmos de Regresión Lineal/Random Forest en futuras versiones. |

---

## 🛠️ Requisitos de Instalación

- Python 3.9 o superior.
- Una cuenta gratuita (opcional) o Pro en [CoinGecko](https://www.coingecko.com/en/api).
- Credenciales opcionales (X API, Binance, Telegram, etc.) requeridas para modo *Live*.

### Instalación de Librerías
Clona el repositorio e instala las dependencias necesarias:

```bash
git clone https://github.com/nicco6482/Bot-de-Arbitraje-Cripto.git
cd Bot-de-Arbitraje-Cripto

# Instala dependencias (ejemplo con pip)
pip install requests textblob
```

*(Si utilizas features extra de CCXT para operar:* `pip install ccxt`*)*

---

## � Cómo Empezar

1. **Configuración de Variables:**  
   Abre el archivo `config.py`. En la clase `APIKeys` puedes agregar tus credenciales si deseas usar componentes reales (X, Telegram).  
   En `TradingConfig` puedes modificar la lista de exchanges ("binance", "kraken", "bybit", etc) o las cryptos.

2. **Ejecución de la Consola Principal:**  
   Ve a tu entorno virtual y ejecuta:

   ```bash
   python monitor.py
   ```

3. **Interperación de Resultados:**  
   El bot comenzará sus ciclos. Al inicio verás logs "obteniendo tickers..." y te mostrará el spread actual. Si la diferencia sobrepasa el **umbral estimado** de fees (ej: > 0.8%), saltará una alarma `🎯 OPORTUNIDAD DETECTADA` y el bot la enviará al `trade_simulator` automáticamente.

---

## � Próximas Actualizaciones y Mejoras
- Implementar los drivers de **CCXT** para enviar órdenes Reales en cuentas de prueba (Testnet) de Binance o ByBit.
- Alimentar el `ml_predictor.py` con una pipeline real de scikit-learn guardada en archivo `.csv` histórico.
- Conectar sockets *Websocket* directos a los exchanges para milisegundos de latencia en vez de Web REST.

---
**Desarrollado con ❤️ por la comunidad de Python y Crypto.**
