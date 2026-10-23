import os
import requests
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quantum_institutional_ultra_v9_trend_aligned")

DB_FILE = "estadisticas_trading.db"

def inicializar_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS señales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            moneda TEXT,
            tipo_señal TEXT,
            precio_entrada REAL,
            tp_objetivo REAL,
            sl_objetivo REAL,
            estado_operacion TEXT
        )
    ''')
    conn.commit()
    conn.close()

inicializar_db()

CONFIG_BASE = {'atr_multiplicador_tp': 3.0, 'atr_multiplicador_sl': 1.5}

def obtener_tendencia_macro_btc():
    """Analiza la tendencia estructural de Bitcoin en 1H para alinear las probabilidades"""
    try:
        base_url = "https://binance.com"
        url = f"{base_url}/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=25"
        raw_klines = requests.get(url, timeout=3).json()
        df = pd.DataFrame(raw_klines, columns=['ts', 'open', 'high', 'low', 'close', 'v', 'ct', 'qv', 't', 'tb', 'tq', 'i']).astype(float)
        
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        precio_btc = df['close'].iloc[-1]
        
        if precio_btc > ma20:
            return "ALCISTA"
        elif precio_btc < ma20:
            return "BAJISTA"
        return "NEUTRAL"
    except Exception:
        return "NEUTRAL"

def obtener_metricas_globales():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM señales WHERE estado_operacion = 'GANADA'")
        ganadas = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM señales WHERE estado_operacion = 'PERDIDA'")
        perdidas = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM señales WHERE estado_operacion = 'ABIERTA'")
        abiertas = cursor.fetchone()[0] or 0
        
        total_cerradas = ganadas + perdidas
        win_rate = (ganadas / total_cerradas * 100) if total_cerradas > 0 else 0.0
        profit_factor = (ganadas * 2.0) / (perdidas if perdidas > 0 else 1.0) if total_cerradas > 0 else 0.0
        
        return {
            "ganadas": ganadas, "perdidas": perdidas, "abiertas": abiertas,
            "win_rate": f"{win_rate:.1f}%", "profit_factor": f"{profit_factor:.2f}" if perdidas > 0 else "N/A"
        }
    except Exception as e:
        print(f"Error Métricas: {e}")
        return {"ganadas": 0, "perdidas": 0, "abiertas": 0, "win_rate": "0.0%", "profit_factor": "0.00"}
    finally:
        conn.close()

def gestionar_ordenes_virtuales(moneda, precio_actual):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tipo_señal, precio_entrada, tp_objetivo, sl_objetivo 
            FROM señales WHERE moneda = ? AND estado_operacion = 'ABIERTA'
        """, (moneda,))
        posiciones = cursor.fetchall()
        
        for pos in posiciones:
            id_op, tipo, entrada, tp, sl = pos
            if tipo == "LONG":
                if precio_actual >= tp:
                    cursor.execute("UPDATE señales SET estado_operacion = 'GANADA' WHERE id = ?", (id_op,))
                elif precio_actual <= sl:
                    cursor.execute("UPDATE señales SET estado_operacion = 'PERDIDA' WHERE id = ?", (id_op,))
            elif tipo == "SHORT":
                if precio_actual <= tp:
                    cursor.execute("UPDATE señales SET estado_operacion = 'GANADA' WHERE id = ?", (id_op,))
                elif precio_actual >= sl:
                    cursor.execute("UPDATE señales SET estado_operacion = 'PERDIDA' WHERE id = ?", (id_op,))
        conn.commit()
    except Exception as e:
        print(f"Error Broker Virtual: {e}")
    finally:
        conn.close()

def registrar_señal_db(moneda, tipo_señal, precio, tp, sl):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM señales 
            WHERE moneda = ? AND tipo_señal = ? AND estado_operacion = 'ABIERTA'
        """, (moneda, tipo_señal))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO señales (fecha, moneda, tipo_señal, precio_entrada, tp_objetivo, sl_objetivo, estado_operacion) 
                VALUES (?, ?, ?, ?, ?, ?, 'ABIERTA')
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), moneda, tipo_señal, precio, tp, sl))
            conn.commit()
    except Exception as e:
        print(f"Error DB Matrix: {e}")
    finally:
        conn.close()

def analizar_moneda_tiempo_real(moneda, macro_btc):
    ticker_binance = moneda if moneda.endswith('USDT') else f"{moneda}USDT"
    label = moneda.replace('USDT', '')
    
    try:
        base_url = "https://binance.com"
        url = f"{base_url}/fapi/v1/klines?symbol={ticker_binance}&interval=15m&limit=50"
        raw_klines = requests.get(url, timeout=4).json()
        
        df = pd.DataFrame(raw_klines, columns=[
            'ts', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'q_volume', 'trades', 'taker_base', 'taker_quote', 'ignore'
        ]).astype(float)
        
        precio_actual = df['close'].iloc[-1]
        precio_str = f"{precio_actual:.2f}" if label in ['ETH', 'BTC'] else f"{precio_actual:.4f}"
        
        gestionar_ordenes_virtuales(label, precio_actual)
        
        df['ma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['bb_sup'] = df['ma20'] + (2.0 * df['std20'])
        df['bb_inf'] = df['ma20'] - (2.0 * df['std20'])
        
        df['vol_med'] = df['volume'].rolling(20).mean()
        df['vol_std'] = df['volume'].rolling(20).std()
        df['vol_zscore'] = (df['volume'] - df['vol_med']) / df['vol_std'].replace(0, 0.0001)
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, 0.0001))))
        
        v_cerrada = df.iloc[-2]
        rsi_actual = df['rsi'].iloc[-1]
        bb_sup_actual = df['bb_sup'].iloc[-1]
        bb_inf_actual = df['bb_inf'].iloc[-1]
        atr_actual = df['atr'].iloc[-1]
        zscore_actual = df['vol_zscore'].iloc[-1]
        
        tp_long = precio_actual + (atr_actual * CONFIG_BASE['atr_multiplicador_tp'])
        sl_long = precio_actual - (atr_actual * CONFIG_BASE['atr_multiplicador_sl'])
        tp_short = precio_actual - (atr_actual * CONFIG_BASE['atr_multiplicador_tp'])
        sl_short = precio_actual + (atr_actual * CONFIG_BASE['atr_multiplicador_sl'])
        
        estado_calculado = "⚪ ESCANEANDO"
        tp_final, sl_final = tp_long, sl_long
        
        # 🔥 Validación Cruzada con Tendencia de Bitcoin
        if v_cerrada['close'] > v_cerrada['bb_sup'] and 55 < v_cerrada['rsi'] < 75:
            if zscore_actual > 1.5:
                if macro_btc == "ALCISTA" or label == "BTC":
                    estado_calculado = "🔥 ALGO_LONG (MOMENTUM)"
                    tp_final, sl_final = tp_long, sl_long
                    registrar_señal_db(label, "LONG", precio_actual, tp_final, sl_final)
                else:
                    estado_calculado = "⏳ BLOQUEADO (BTC BAJISTA)"
            else:
                estado_calculado = "⚠️ RUPTURA FALSA (SIN VOL)"
                
        elif v_cerrada['close'] < v_cerrada['bb_inf'] and 25 < v_cerrada['rsi'] < 45:
            if zscore_actual > 1.5:
                if macro_btc == "BAJISTA" or label == "BTC":
                    estado_calculado = "💥 ALGO_SHORT (MOMENTUM)"
                    tp_final, sl_final = tp_short, sl_short
                    registrar_señal_db(label, "SHORT", precio_actual, tp_final, sl_final)
                else:
                    estado_calculado = "⏳ BLOQUEADO (BTC ALCISTA)"
            else:
                estado_calculado = "⚠️ RUPTURA FALSA (SIN VOL)"
        
        distancia_techo = ((bb_sup_actual - precio_actual) / precio_actual) * 100
        distancia_piso = ((precio_actual - bb_inf_actual) / precio_actual) * 100
        
        if estado_calculado == "⚪ ESCANEANDO":
            if distancia_techo < 0.75 and rsi_actual > 52:
                estado_calculado = f"🟡 PRE-RANG ALTO ({distancia_techo:.2f}%)"
            elif distancia_piso < 0.75 and rsi_actual < 43:
                estado_calculado = f"🟡 PRE-RANG BAJO ({distancia_piso:.2f}%)"
        
        return {
            "estado": estado_calculado,
            "precio": precio_str,
            "tp": f"${tp_final:.2f}" if label in ['ETH', 'BTC'] else f"${tp_final:.4f}",
            "sl": f"${sl_final:.2f}" if label in ['ETH', 'BTC'] else f"${sl_final:.4f}",
            "fecha": datetime.now().strftime('%H:%M:%S'),
            "zscore": f"{zscore_actual:+.2f} SD",
            "vol_critico": "ALTO RIESGO" if zscore_actual > 1.5 else "NORMAL"
        }
    except Exception as ex:
        print(f"Error Engine: {ex}")
        return {
            "estado": "RECONECTANDO", "precio": "Sincronizando...", 
            "tp": "Calculando...", "sl": "Calculando...", "fecha": datetime.now().strftime('%H:%M:%S'),
            "zscore": "0.00", "vol_critico": "ESTABLE"
