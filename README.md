# 🚀 AntiGravity Crypto Hunter

**AntiGravity Crypto Hunter** es un bot avanzado de monitoreo, análisis de métricas y detección de oportunidades de arbitraje en el mercado de criptomonedas. Desarrollado en Python, cuenta con una arquitectura modular que no solo encuentra discrepancias de precios entre exchanges, sino que también integra análisis de sentimiento en redes sociales y un simulador de trading (Paper Trading).

> ⚠️ **Disclaimer Financiero:** Este bot tiene fines puramente educativos e informativos. El mercado local e internacional de criptomonedas es altamente volátil. ¡Se recomienda usar siempre primero el modo simulación y no arriesgar capital que no estés dispuesto a perder!

---

## 🚀 Despliegue en 1-Clic (Web App Pública)

¿Quieres compartir este bot o revisarlo desde tu celular sin dejar tu PC encendida? Haz clic en el siguiente botón para desplegar tu propio servidor web gratuito en Render. En 3 minutos **obtendrás un enlace (URL web) permanente** que abrirá directamente el Dashboard interactivo:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/nicco6482/Bot-de-Arbitraje-Cripto)

*Render detectará automáticamente que es una aplicación Python/Flask gracias al archivo `Procfile` y la iniciará sola en la nube.*

---

## 🌟 Características Principales

1. **Detección de Arbitraje Triangular:** Escanea múltiples exchanges (Binance, Coinbase, Kraken, KuCoin, Bybit) simultáneamente para detectar spreads de precios viables descontando comisiones pre-configuradas.
2. **Dashboard Web Interactivo (Cyberpunk UI):** Controla el bot a través de una interfaz gráfica moderna (`web_app.py`) desde tu navegador. Incluye tarjetas de criptos en vivo, barras de progreso de spread y terminal embebida.
3. **Eficiencia de API (Rate-Limit Safe):** Motor de peticiones altamente optimizado (`price_fetcher.py`). Usa un único llamado a la API (`/coins/{id}/tickers`) para traer todos los exchanges a la vez e incorpora un sistema *Exponential Backoff* para esquivar baneos por "Too Many Requests" (HTTP 429).
4. **Análisis de Sentimiento (Sentiment AI):** Capacidad de conectarse a la API de X (Twitter) para medir la temperatura emocional de los inversores.
5. **Trading Simulado (Paper Trading):** Rastrea las transacciones teóricas comprobando cómo hubieran resultado tras comisiones.

---

## 🏗️ Arquitectura y Archivos Claves

El proyecto está diseñado bajo principios de Clean Code, segmentando las responsabilidades lógicas en varios archivos:

| Archivo | Descripción |
|---------|-------------|
| 🌐 `web_app.py` | Servidor Flask que conecta la lógica del bot con el frontend y expone la API REST de control. |
| 🎨 `templates/`, `static/` | UI/UX interactiva y moderna con HTML, Javascript Vainilla y Tailwind. |
| ⚙️ `config.py` | Configuración global. Aquí se cambian claves API, exchanges objetivo, cryptos y umbrales de capital y comisiones. |
| 👁️ `monitor.py` | Entrada principal del motor del bot (`main`). Orquesta el bucle infinito que coordina todos los módulos. |
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

# Instala dependencias (incluyendo el servidor web Flask)
pip install -r requirements.txt
pip install flask
```

*(Si utilizas features extra de CCXT para operar:* `pip install ccxt`*)*

---

## 🚀 Cómo Empezar (Ejecución Local)

1. **Configuración de Variables:**  
   Abre el archivo `config.py`. En la clase `APIKeys` puedes agregar tus credenciales si deseas usar componentes reales (X, Telegram).

2. **Arrancar el Servidor Web (Recomendado):**  
   Ve a tu entorno virtual y ejecuta:

   ```bash
   python web_app.py
   ```
   Luego abre tu navegador en `http://127.0.0.1:5000` y haz clic en "START ENGINE". El dashboard Cyberpunk mostrará las tarjetas con los pares en vivo, progreso del arbitraje y logs gráficos.

3. **Ejecutar en Modo Terminal (Clásico):**
   Si prefieres no usar la web, ejecuta el script directo:
   ```bash
   python monitor.py
   ```

---

## � Próximas Actualizaciones y Mejoras
- Implementar los drivers de **CCXT** para enviar órdenes Reales en cuentas de prueba (Testnet) de Binance o ByBit.
- Alimentar el `ml_predictor.py` con una pipeline real de scikit-learn guardada en archivo `.csv` histórico.
- Conectar sockets *Websocket* directos a los exchanges para milisegundos de latencia en vez de Web REST.

---
**Desarrollado con ❤️ por la comunidad de Python y Crypto.**
