"""
App web para controlar y visualizar el bot AntiGravity Crypto Hunter.
Expone una API REST para el Frontend.
"""
import os
import threading
import json
from flask import Flask, render_template, jsonify, request
from monitor import AntiGravityBot
from config import TRADING

app = Flask(__name__)

# Instancia global del bot (pero no corriendo aún)
bot_instance = AntiGravityBot()
bot_thread = None

def run_bot_in_background():
    """Ejecuta el bot en un hilo separado para no bloquear Flask."""
    global bot_instance
    try:
        # Esto iniciará el bucle infinito del bot
        bot_instance.run()
    except Exception as e:
        print(f"Error en el hilo del bot: {e}")

@app.route("/")
def index():
    """Sirve la interfaz web principal."""
    return render_template("index.html")

@app.route("/api/bot/start", methods=["POST"])
def start_bot():
    """Inicia el bot si no está corriendo."""
    global bot_thread, bot_instance
    
    if bot_instance.running:
        return jsonify({"status": "error", "message": "El bot ya está corriendo."}), 400

    # Resetear instancia por si se detuvo antes
    # (El init ya no debe auto-entrenar bloqueando todo, pero lo hace rápido)
    if not bot_instance:
        bot_instance = AntiGravityBot()
        
    bot_thread = threading.Thread(target=run_bot_in_background, daemon=True)
    bot_thread.start()
    
    return jsonify({"status": "success", "message": "Bot iniciado correctamente."})

@app.route("/api/bot/stop", methods=["POST"])
def stop_bot():
    """Detiene el bucle del bot de forma segura."""
    global bot_instance
    
    if not bot_instance.running:
        return jsonify({"status": "error", "message": "El bot no estaba corriendo."}), 400
        
    # Cambiar el flag hará que el bucle while termine limpiamente
    bot_instance.running = False
    return jsonify({"status": "success", "message": "Señal de detención enviada."})

@app.route("/api/bot/status", methods=["GET"])
def get_bot_status():
    """Retorna los datos dinámicos actuales para actualizar la UI."""
    global bot_instance
    
    # 1. Estado de ejecución
    is_running = bot_instance.running if bot_instance else False
    cycle = bot_instance.cycle_count if bot_instance else 0
    
    # 2. Últimos trades simulados (leer del JSON)
    trades = []
    if os.path.exists("simulated_trades.json"):
        try:
            with open("simulated_trades.json", "r", encoding="utf-8") as f:
                trades = json.load(f)
                # Tomar los últimos 10 trades
                trades = trades[-10:] if len(trades) > 10 else trades
                trades.reverse()  # Más recientes primero
        except Exception:
            pass

    # 3. Leer los datos más recientes de Precios desde el logger
    # Vamos a extraer los spreads de precios reportados en el log
    # para armar unas "Tarjetas" visuales en el frontend.
    market_data = {}
    logs = []
    if os.path.exists("antigravity_bot.log"):
        try:
            with open("antigravity_bot.log", "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Extraer log de terminal (últimas 40)
                logs = [line.strip() for line in lines[-40:]]
                
                # Parsear los precios más recientes para pasarlos estructurados a la UI
                # Buscamos bloques de "💰 Precios de COIN:" y Extraemos el spread
                current_coin = None
                for line in reversed(lines[-200:]): # Buscar hacia atrás en los últimos 200 logs
                    if "Precios de " in line:
                        current_coin = line.split("Precios de ")[1].replace(":", "").strip().lower()
                        if current_coin not in market_data:
                            market_data[current_coin] = {"exchanges": {}, "spread": 0}
                    elif current_coin and "→ Spread total:" in line:
                        if market_data[current_coin]["spread"] == 0:
                            spread_str = line.split(":")[-1].replace("%", "").strip()
                            try:
                                market_data[current_coin]["spread"] = float(spread_str)
                            except: pass
                    elif current_coin and ":" in line and "$" in line and "Spread" not in line:
                        # '   binance     : $   67,897.00'
                        parts = line.split(":")
                        if len(parts) >= 3:  # Tiene timestamp, modulo, etc
                            ex_data = parts[-1].split("$")
                            if len(ex_data) == 2:
                                exchange = parts[-2].split()[-1].strip()
                                price_str = ex_data[1].replace(",", "").strip()
                                try:
                                    if exchange not in market_data[current_coin]["exchanges"]:
                                        market_data[current_coin]["exchanges"][exchange] = float(price_str)
                                except: pass
        except Exception as e:
            print("Error parsing logs:", e)

    # 4. Configuración activa
    active_config = {
        "coins": TRADING.coins,
        "exchanges": TRADING.exchanges,
        "threshold": TRADING.arbitrage_threshold_pct
    }

    return jsonify({
        "status": "running" if is_running else "stopped",
        "cycle": cycle,
        "config": active_config,
        "recent_trades": trades,
        "market_data": market_data,
        "logs": logs
    })

if __name__ == "__main__":
    # Ejecutar en el puerto 5000, debug desactivado para no crear hilos duplicados
    app.run(host="127.0.0.1", port=5000, debug=False)
