"""
╔══════════════════════════════════════════════════════╗
║      AntiGravity Crypto Hunter - ml_predictor.py     ║
║  🤖 Predicción de tendencias con Machine Learning    ║
╚══════════════════════════════════════════════════════╝
Modelo: Regresión Logística (simple pero efectivo para inicio)
Input features:
  - Precio actual vs media móvil 7 días
  - Cambio % en 24h
  - Volumen normalizado
  - Score de sentimiento de Twitter
  - Fear & Greed Index
Output: Probabilidad de subida (BUY signal) o bajada (SELL/WAIT)

⚠️ ML en crypto es muy difícil. Trátalo como un indicador
   más, NO como el oráculo. Combínalo con el análisis de
   arbitraje y el sentimiento para decisiones más robustas.
"""

import csv
import logging
import os
from datetime import datetime
from typing import Optional, Tuple
from config import LOG

logger = logging.getLogger("AntiGravity.MLPredictor")

# Dependencias opcionales
try:
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("scikit-learn/pandas/numpy no instalados. ML desactivado.")


class PriceDataRecorder:
    """
    Graba datos históricos de precios para entrenar el modelo.
    El modelo mejora con el tiempo a medida que se acumulan datos.
    
    Necesitas al menos 50-100 puntos de datos para resultados útiles.
    Con 1 ciclo/minuto → ~83 puntos en ~1.5 horas de ejecución.
    """

    def record(
        self,
        coin: str,
        price: float,
        change_24h: float,
        sentiment_score: float,
        fear_greed: int = 50,
    ):
        """
        Registra un punto de dato en el CSV histórico.
        
        También calcula el 'label' de la siguiente observación
        comparando si el precio subió o bajó respecto al registro anterior.
        """
        timestamp = datetime.now().isoformat()
        row = {
            "timestamp": timestamp,
            "coin": coin,
            "price": price,
            "change_24h_pct": change_24h,
            "sentiment_score": sentiment_score,
            "fear_greed_index": fear_greed,
        }

        file_exists = os.path.exists(LOG.ML_DATA_FILE)
        with open(LOG.ML_DATA_FILE, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        logger.debug(f"📊 Dato registrado: {coin} @ ${price:,.2f}")


class MLPredictor:
    """
    Modelo de ML para predicción de dirección de precio.
    Usa Regresión Logística como clasificador (sube/baja).
    """

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler() if ML_AVAILABLE else None
        self.is_trained = False
        self.accuracy = 0.0

    def train(self, min_samples: int = 60) -> bool:
        """
        Entrena el modelo con los datos históricos recopilados.
        
        Args:
            min_samples: Mínimo de registros para entrenar

        Returns:
            True si el entrenamiento fue exitoso
        """
        if not ML_AVAILABLE:
            logger.warning("ML no disponible (faltan librerías).")
            return False

        try:
            df = pd.read_csv(LOG.ML_DATA_FILE)
        except FileNotFoundError:
            logger.info("Sin datos históricos aún. Ejecuta el bot un rato primero.")
            return False

        if len(df) < min_samples:
            logger.info(
                f"Datos insuficientes: {len(df)}/{min_samples} muestras. "
                f"Sigue corriendo el bot para acumular más datos."
            )
            return False

        # Feature Engineering
        # El label es: ¿El precio SUBIÓ en la siguiente observación? (1=sí, 0=no)
        df["next_price"] = df.groupby("coin")["price"].shift(-1)
        df["label"] = (df["next_price"] > df["price"]).astype(int)
        df = df.dropna()

        # Feature: Moving average distance (% del precio respecto a MA7)
        df["ma_7"] = df.groupby("coin")["price"].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        df["dist_from_ma"] = (df["price"] - df["ma_7"]) / df["ma_7"] * 100

        features = [
            "change_24h_pct",
            "sentiment_score",
            "fear_greed_index",
            "dist_from_ma",
        ]
        X = df[features].fillna(0)
        y = df["label"]

        # Split: 80% train, 20% test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Normalizar features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Entrenar modelo
        self.model = LogisticRegression(max_iter=200, random_state=42)
        self.model.fit(X_train_scaled, y_train)

        # Evaluar
        y_pred = self.model.predict(X_test_scaled)
        self.accuracy = accuracy_score(y_test, y_pred)
        self.is_trained = True

        logger.info(
            f"🤖 Modelo entrenado! Accuracy: {self.accuracy:.1%} "
            f"(con {len(df)} muestras)"
        )
        return True

    def predict(
        self,
        change_24h: float,
        sentiment_score: float,
        fear_greed: int,
        dist_from_ma: float,
    ) -> Tuple[str, float]:
        """
        Predice si el precio subirá o bajará.
        
        Returns:
            ("BUY"/"SELL"/"UNCERTAIN", confidence_pct)
        """
        if not self.is_trained or self.model is None:
            return "UNCERTAIN", 0.0

        features = np.array([[change_24h, sentiment_score, fear_greed, dist_from_ma]])
        features_scaled = self.scaler.transform(features)

        proba = self.model.predict_proba(features_scaled)[0]
        prob_up = proba[1]
        prob_down = proba[0]

        confidence_threshold = 0.65  # Solo señal si >65% de confianza

        if prob_up >= confidence_threshold:
            signal = "BUY"
            confidence = prob_up
        elif prob_down >= confidence_threshold:
            signal = "SELL"
            confidence = prob_down
        else:
            signal = "UNCERTAIN"
            confidence = max(prob_up, prob_down)

        logger.info(
            f"🤖 ML Predicción: {signal} ({confidence:.1%} conf) | "
            f"Accuracy del modelo: {self.accuracy:.1%}"
        )
        return signal, round(confidence, 4)

    def get_feature_importance(self) -> Optional[dict]:
        """Retorna la importancia de cada feature del modelo."""
        if not self.is_trained or self.model is None:
            return None

        feature_names = ["change_24h_pct", "sentiment_score", "fear_greed", "dist_from_ma"]
        # En logistic regression, los coeficientes indican importancia
        importances = dict(zip(feature_names, abs(self.model.coef_[0])))
        return dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))
