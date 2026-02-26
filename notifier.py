"""
╔══════════════════════════════════════════════════════╗
║      AntiGravity Crypto Hunter - notifier.py         ║
║  📣 Sistema de alertas: Email, SMS, Telegram         ║
╚══════════════════════════════════════════════════════╝
Canales de notificación disponibles:
  1. Email (Gmail SMTP) - Gratuito, requiere App Password
  2. SMS (Twilio) - De pago, ~$0.01/SMS
  3. Telegram Bot - Gratuito y recomendado para cryptos!

💡 TIP: Telegram es el canal preferido para trading bots.
   Muchos traders pro usan bots de Telegram para señales.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import API

logger = logging.getLogger("AntiGravity.Notifier")

# Dependencias opcionales
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class Notifier:
    """
    Hub de notificaciones multi-canal.
    Los canales se activan automáticamente si los tokens están configurados.
    """

    def __init__(self):
        self.channels_enabled = self._detect_channels()
        if not self.channels_enabled:
            logger.info("ℹ️ Sin canales de notificación configurados. Solo logging a consola.")

    def _detect_channels(self) -> list:
        """Detecta qué canales de notificación están configurados."""
        channels = []
        
        if API.EMAIL_PASSWORD and API.EMAIL_SENDER != "tu_email@gmail.com":
            channels.append("email")
        if TWILIO_AVAILABLE and API.TWILIO_SID:
            channels.append("sms")
        if REQUESTS_AVAILABLE and API.TELEGRAM_BOT_TOKEN:
            channels.append("telegram")
        
        logger.info(f"📡 Canales activos: {channels or ['console only']}")
        return channels

    def send_alert(self, subject: str, body: str, level: str = "INFO"):
        """
        Envía una alerta por todos los canales configurados.

        Args:
            subject: Asunto / título del mensaje
            body: Contenido completo del mensaje
            level: "INFO", "WARNING", "CRITICAL"
        """
        level_emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(level, "📢")
        full_message = f"{level_emoji} {subject}\n\n{body}"

        # Siempre loggeamos
        logger.info(f"ALERTA: {subject}")

        for channel in self.channels_enabled:
            try:
                if channel == "email":
                    self._send_email(subject, body)
                elif channel == "sms":
                    self._send_sms(full_message[:160])  # SMS máx 160 chars
                elif channel == "telegram":
                    self._send_telegram(full_message)
            except Exception as e:
                logger.error(f"Error enviando por {channel}: {e}")

    def _send_email(self, subject: str, body: str):
        """
        Envía email via Gmail SMTP.
        
        Setup: 
        1. Activa 2FA en tu cuenta de Google
        2. Genera un App Password en: accounts.google.com/AppPasswords
        3. Configura EMAIL_PASSWORD con ese App Password
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚀 AntiGravity Bot: {subject}"
        msg["From"] = API.EMAIL_SENDER
        msg["To"] = API.EMAIL_RECEIVER

        # Versión plaintext y HTML del email
        text_part = MIMEText(body, "plain")
        html_body = f"""
        <html><body style="font-family: monospace; background: #1a1a1a; color: #00ff88; padding: 20px;">
        <h2>🚀 AntiGravity Crypto Hunter</h2>
        <pre style="background: #0d0d0d; padding: 15px; border-radius: 8px;">{body}</pre>
        <hr style="border-color: #333"><small>Bot automático - No es consejo financiero</small>
        </body></html>
        """
        html_part = MIMEText(html_body, "html")
        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(API.EMAIL_SENDER, API.EMAIL_PASSWORD)
            server.sendmail(API.EMAIL_SENDER, API.EMAIL_RECEIVER, msg.as_string())
        
        logger.info("✅ Email enviado.")

    def _send_sms(self, message: str):
        """
        Envía SMS via Twilio.
        Plan gratuito: $15 crédito inicial para pruebas.
        """
        if not TWILIO_AVAILABLE:
            return
        
        client = TwilioClient(API.TWILIO_SID, API.TWILIO_TOKEN)
        client.messages.create(
            body=message,
            from_=API.TWILIO_FROM,
            to=API.TWILIO_TO
        )
        logger.info("✅ SMS enviado via Twilio.")

    def _send_telegram(self, message: str):
        """
        Envía mensaje a un canal/chat de Telegram.
        
        Setup:
        1. Habla con @BotFather en Telegram → /newbot
        2. Guarda el token como TELEGRAM_BOT_TOKEN
        3. Obtén tu Chat ID con @userinfobot o @get_id_bot
        4. Configura TELEGRAM_CHAT_ID con tu ID
        
        ¡Telegram es el mejor canal para bots crypto!
        """
        import requests
        url = f"https://api.telegram.org/bot{API.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": API.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",  # Permite negritas, monospace, etc.
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ Mensaje de Telegram enviado.")

    def send_arbitrage_alert(self, opportunity, sentiment, trade) -> None:
        """
        Alerta especializada para oportunidades de arbitraje.
        Formatea los datos de manera clara para toma de decisiones rápida.
        """
        body = (
            f"{'═'*40}\n"
            f"🎯 ARBITRAJE DETECTADO\n"
            f"{'═'*40}\n"
            f"Coin:      {opportunity.coin.upper()}\n"
            f"Comprar:   {opportunity.buy_exchange} @ ${opportunity.buy_price:,.2f}\n"
            f"Vender:    {opportunity.sell_exchange} @ ${opportunity.sell_price:,.2f}\n"
            f"Spread:    {opportunity.net_spread_pct:+.3f}% (neto)\n"
            f"Profit est: ${opportunity.estimated_profit_usd:.2f}\n"
            f"{'─'*40}\n"
            f"Sentimiento: {sentiment.label} ({sentiment.score:+.3f})\n"
            f"Tweets analizados: {sentiment.tweet_count}\n"
        )
        
        if trade:
            body += (
                f"{'─'*40}\n"
                f"💼 TRADE SIMULADO:\n"
                f"Capital: ${trade.capital_used:,.2f}\n"
                f"Profit neto: ${trade.net_profit_usd:+.2f}\n"
                f"Risk mult: x{trade.risk_multiplier:.2f}\n"
            )
        
        body += f"{'═'*40}\n⚠️ Simulación - No es consejo financiero"
        
        self.send_alert("Oportunidad de Arbitraje", body, "CRITICAL")
