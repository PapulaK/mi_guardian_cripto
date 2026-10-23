import os
import time
import hmac
import hashlib
import sqlite3
import requests
import numpy as np
from flask import Flask, jsonify, request, render_template_string
from urllib.parse import urlencode

app = Flask(__name__)

# =====================================================================
# ⚙️ CONFIGURACIÓN DE ENTORNO Y BASE DE DATOS (RENDER COMPATIBLE)
# =====================================================================
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
TRADING_MODE = os.environ.get("TRADING_MODE", "PAPER")  # 'PAPER' o 'REAL'
BINANCE_FUTURES_URL = "https://binance.com"

# Ruta temporal compartida para bypass de solo lectura en Render Free Tier
DB_PATH = "/tmp/estadisticas_trading.db"

def init_db():
    """Inicializa la base de datos local en el directorio /tmp."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            tipo_posicion TEXT,
            precio_entrada REAL,
            tp_precio REAL,
            sl_precio REAL,
            estado TEXT,
            timestamp INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# =====================================================================
# 🔑 MÓDULO DE EJECUCIÓN REAL (CRIPTO-FIRMADO)
# =====================================================================
def firmar_peticion(params):
    """Genera la firma HMAC-SHA256 obligatoria para la API de Binance."""
    query_string = urlencode(params)
    signature = hmac.new(
        BINANCE_SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def enviar_orden_binance(symbol, side, quantity):
    """Envía una orden de mercado real a Binance Futuros."""
    if TRADING_MODE != "REAL":
        return {"status": "SUCCESS_PAPER", "msg": "Modo Paper Trading Activo"}
        
    endpoint = f"{BINANCE_FUTURES_URL}/fapi/v1/order"
    timestamp = int(time.time() * 1000)
    
    params = {
        "symbol": symbol.upper(),
        "side": side.upper(),       # 'BUY' (Long) o 'SELL' (Short)
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": timestamp,
        "recvWindow": 6000          # Tolerancia para latencia de Render
    }
    
    params["signature"] = firmar_peticion(params)
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    
    try:
        response = requests.post(endpoint, data=params, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}

# =====================================================================
# 🧮 MOTOR DE BACKTESTING HISTÓRICO INTEGRADO (LÓGICA NIVEL 9.2)
# =====================================================================
@app.route('/api/backtest', methods=['POST'])
def ejecutar_backtest():
    """
    Ejecuta un backtesting histórico usando la estrategia cuantitativa 9.2.
    JSON esperado: { "symbol": "SOLUSDT", "capital": 1000 }
    """
    data = request.get_json() or {}
    symbol = data.get("symbol", "SOLUSDT").upper()
    capital_inicial = float(data.get("capital", 1000.0))
    
    # Descarga de datos históricos (15m para el activo desde la API pública)
    url = f"{BINANCE_FUTURES_URL}/fapi/v1/klines"
    params = {"symbol": symbol, "interval": "15m", "limit": 1500}
    
    res = requests.get(url, params=params, timeout=10)
    if res.status_code != 200:
        return jsonify({"error": "No se pudieron obtener datos históricos de Binance"}), 400
        
    klines = res.json()
    
    # Mapeo de vectores para cálculos estadísticos con NumPy
    precios_cierre = np.array([float(k[4]) for k in klines])
    volumenes = np.array([float(k[5]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    
    trades_ganados = 0
    trades_perdidos = 0
    beneficio_total = 0.0
    posicion_abierta = False
    precio_entrada = 0.0
    tp_precio = 0.0
    sl_precio = 0.0
    tipo_posicion = ""
    
    # Bucle cuantitativo iterativo (Ventana mínima de 20 periodos)
    for i in range(20, len(precios_cierre) - 1):
        close_actual = precios_cierre[i]
        vol_actual = volumenes[i]
        
        # Filtro Bollinger 20, 2.0
        ventana_close = precios_cierre[i-20:i]
        ma20 = np.mean(ventana_close)
        std20 = np.std(ventana_close)
        banda_sup = ma20 + (2.0 * std20)
        banda_inf = ma20 - (2.0 * std20)
        
        # Filtro de Liquidez (Z-Score de Volumen)
        ventana_vol = volumenes[i-20:i]
        ma_vol = np.mean(ventana_vol)
        std_vol = np.std(ventana_vol)
        z_score_vol = (vol_actual - ma_vol) / std_vol if std_vol > 0 else 0
        
        # Filtro de Riesgo (ATR 14 simplificado)
        atr_14 = np.mean(highs[i-14:i] - lows[i-14:i]) 
        
        if not posicion_abierta:
            # Entrada por ruptura confirmada con volumen (Z-Score > 1.5)
            if close_actual >= banda_sup and z_score_vol > 1.5:
                posicion_abierta = True
                precio_entrada = close_actual
                tp_precio = precio_entrada + (3.0 * atr_14)
                sl_precio = precio_entrada - (1.5 * atr_14)
                tipo_posicion = "LONG"
                
            elif close_actual <= banda_inf and z_score_vol > 1.5:
                posicion_abierta = True
                precio_entrada = close_actual
                tp_precio = precio_entrada - (3.0 * atr_14)
                sl_precio = precio_entrada + (1.5 * atr_14)
                tipo_posicion = "SHORT"
                
        else:
            # Auditoría de salida (TP 3.0x ATR vs SL 1.5x ATR)
            high_actual = highs[i]
            low_actual = lows[i]
            
            if tipo_posicion == "LONG":
                if high_actual >= tp_precio:
                    trades_ganados += 1
                    beneficio_total += (tp_precio - precio_entrada)
                    posicion_abierta = False
                elif low_actual <= sl_precio:
                    trades_perdidos += 1
                    beneficio_total += (sl_precio - precio_entrada)
                    posicion_abierta = False
                    
            elif tipo_posicion == "SHORT":
                if low_actual <= tp_precio:
                    trades_ganados += 1
                    beneficio_total += (precio_entrada - tp_precio)
                    posicion_abierta = False
                elif high_actual >= sl_precio:
                    trades_perdidos += 1
                    beneficio_total += (precio_entrada - sl_precio)
                    posicion_abierta = False

    total_trades = trades_ganados + trades_perdidos
    win_rate = (trades_ganados / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (trades_ganados * 3.0) / (trades_perdidos * 1.5) if trades_perdidos > 0 else trades_ganados
    
    return jsonify({
        "status": "BACKTEST_COMPLETED",
        "activo": symbol,
        "trading_mode_actual": TRADING_MODE,
        "total_operaciones": total_trades,
        "ganadas": trades_ganados,
        "perdidas": trades_perdidos,
        "win_rate_porcentaje": round(win_rate, 2),
        "profit_factor_teorico": round(profit_factor, 2),
        "balance_final_estimado": round(capital_inicial + (beneficio_total * (capital_inicial * 0.01)), 2)
    })

# =====================================================================
# 📊 INTERFAZ DE AUDITORÍA Y PANEL WEB PREMIUM (CELULAR)
# =====================================================================
@app.route('/')
def dashboard():
    """Panel de control optimizado para navegadores móviles con KPIs en vivo."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, tipo_posicion, precio_entrada, tp_precio, sl_precio, estado FROM operaciones ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    # Cálculo dinámico de métricas para la barra superior
    ganadas = sum(1 for r in rows if r[5] == "GANADA")
    perdidas = sum(1 for r in rows if r[5] == "PERDIDA")
    activas = sum(1 for r in rows if r[5] == "ABIERTA")
    total = ganadas + perdidas
    win_rate = round((ganadas / total * 100), 1) if total > 0 else 0.0
    profit_factor = round((ganadas * 3.0) / (perdidas * 1.5), 2) if perdidas > 0 else ganadas

    # HTML Puro inyectado dinámicamente para evitar problemas de renderizado de strings
    html_template = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="10">
        <title>GurdianCripto Quantum Pro</title>
        <style>
            body { font-family: -apple-system, sans-serif; background: #0b0e11; color: #eaecef; margin: 0; padding: 10px; }
            .kpi-container { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 15px; }
            .kpi-card { background: #1e2329; padding: 12px; border-radius: 8px; text-align: center; border-left: 4px solid #f0b90b; }
            .kpi-value { font-size: 20px; font-weight: bold; color: #fff; margin-top: 4px; }
            .mode-badge { background: {{ 'red' if mode == 'REAL' else 'green' }}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block; margin-bottom: 10px; }
            .trade-card { background: #1e2329; margin-bottom: 10px; padding: 12px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.5); }
            .status-ABIERTA { color: #f0b90b; font-weight: bold; }
            .status-GANADA { color: #0ecb81; font-weight: bold; }
            .status-PERDIDA { color: #f6465d; font-weight: bold; }
