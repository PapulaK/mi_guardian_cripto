import os
import time
import hmac
import hashlib
import sqlite3
import requests
import threading
import numpy as np
from flask import Flask, jsonify, request, render_template_string
from urllib.parse import urlencode

app = Flask(__name__)

# =====================================================================
# ⚙️ CONFIGURACIÓN DE ENTORNO Y CONTEXTO DEL SISTEMA
# =====================================================================
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")
TRADING_MODE = os.environ.get("TRADING_MODE", "PAPER")
ACTIVO_PRINCIPAL = os.environ.get("ACTIVO_PRINCIPAL", "SOLUSDT").upper()

BINANCE_FUTURES_URL = "https://binance.com"
DB_PATH = "/tmp/estadisticas_trading.db"

def init_db():
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

try:
    init_db()
except Exception as e:
    print(f"Error inicializando DB: {e}")

# =====================================================================
# 🔑 MÓDULO DE FIRMA CRIPTO-SEGURA (API BINANCE)
# =====================================================================
def firmar_peticion(params):
    query_string = urlencode(params)
    return hmac.new(
        BINANCE_SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def enviar_orden_binance(symbol, side, quantity):
    if TRADING_MODE != "REAL":
        return {"status": "SUCCESS_PAPER", "orderId": f"mock_{int(time.time())}"}
        
    endpoint = f"{BINANCE_FUTURES_URL}/fapi/v1/order"
    params = {
        "symbol": symbol.upper(),
        "side": side.upper(),
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": int(time.time() * 1000),
        "recvWindow": 6000
    }
    params["signature"] = firmar_peticion(params)
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    
    try:
        response = requests.post(endpoint, data=params, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}

# =====================================================================
# 🧮 MOTOR CUANTITATIVO 9.2 EN TIEMPO REAL (EXTRACCIÓN QUIRÚRGICA)
# =====================================================================
def procesar_logica_cuantitativa():
    try:
        url = f"{BINANCE_FUTURES_URL}/fapi/v1/klines"
        params = {"symbol": ACTIVO_PRINCIPAL, "interval": "15m", "limit": 100}
        res = requests.get(url, params=params, timeout=8)
        if res.status_code != 200: return
        
        klines = res.json()
        
        # Corrección: Extraer el índice correspondiente de la sublista de Binance
        precios_cierre = np.array([float(k[4]) for k in klines])
        volumenes = np.array([float(k[5]) for k in klines])
        highs = np.array([float(k[2]) for k in klines])
        lows = np.array([float(k[3]) for k in klines])
        
        close_actual = precios_cierre[-1]
        vol_actual = volumenes[-1]
        
        params_btc = {"symbol": "BTCUSDT", "interval": "1h", "limit": 21}
        res_btc = requests.get(url, params=params_btc, timeout=8)
        btc_alcista = True
        if res_btc.status_code == 200:
            klines_btc = res_btc.json()
            cierres_btc = np.array([float(k[4]) for k in klines_btc])
            btc_alcista = cierres_btc[-1] > np.mean(cierres_btc[:-1])

        ma20 = np.mean(precios_cierre[-21:-1])
        std20 = np.std(precios_cierre[-21:-1])
        banda_sup = ma20 + (2.0 * std20)
        banda_inf = ma20 - (2.0 * std20)
        
        ma_vol = np.mean(volumenes[-21:-1])
        std_vol = np.std(volumenes[-21:-1])
        z_score_vol = (vol_actual - ma_vol) / std_vol if std_vol > 0 else 0
        
        atr_14 = np.mean(highs[-15:-1] - lows[-15:-1])

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo_posicion, precio_entrada, tp_precio, sl_precio FROM operaciones WHERE estado='ABIERTA' AND symbol=?", (ACTIVO_PRINCIPAL,))
        posicion_activa = cursor.fetchone()
        
        if not posicion_activa:
            if close_actual >= banda_sup and z_score_vol > 1.5 and btc_alcista:
                tp = close_actual + (3.0 * atr_14)
                sl = close_actual - (1.5 * atr_14)
                enviar_orden_binance(ACTIVO_PRINCIPAL, "BUY", 1.0)
                cursor.execute("INSERT INTO operaciones (symbol, tipo_posicion, precio_entrada, tp_precio, sl_precio, estado, timestamp) VALUES (?, 'LONG', ?, ?, ?, 'ABIERTA', ?)",
                               (ACTIVO_PRINCIPAL, close_actual, tp, sl, int(time.time())))
                
            elif close_actual <= banda_inf and z_score_vol > 1.5 and not btc_alcista:
                tp = close_actual - (3.0 * atr_14)
                sl = close_actual + (1.5 * atr_14)
                enviar_orden_binance(ACTIVO_PRINCIPAL, "SELL", 1.0)
                cursor.execute("INSERT INTO operaciones (symbol, tipo_posicion, precio_entrada, tp_precio, sl_precio, estado, timestamp) VALUES (?, 'SHORT', ?, ?, ?, 'ABIERTA', ?)",
                               (ACTIVO_PRINCIPAL, close_actual, tp, sl, int(time.time())))
        else:
            id_op, tipo, entrada, tp, sl = posicion_activa
            if tipo == "LONG":
                if close_actual >= tp:
                    enviar_orden_binance(ACTIVO_PRINCIPAL, "SELL", 1.0)
                    cursor.execute("UPDATE operaciones SET estado='GANADA' WHERE id=?", (id_op,))
                elif close_actual <= sl:
                    enviar_orden_binance(ACTIVO_PRINCIPAL, "SELL", 1.0)
                    cursor.execute("UPDATE operaciones SET estado='PERDIDA' WHERE id=?", (id_op,))
            elif tipo == "SHORT":
                if close_actual <= tp:
                    enviar_orden_binance(ACTIVO_PRINCIPAL, "BUY", 1.0)
                    cursor.execute("UPDATE operaciones SET estado='GANADA' WHERE id=?", (id_op,))
                elif close_actual >= sl:
                    enviar_orden_binance(ACTIVO_PRINCIPAL, "BUY", 1.0)
                    cursor.execute("UPDATE operaciones SET estado='PERDIDA' WHERE id=?", (id_op,))
                    
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error en bucle cuantitativo: {e}")

# =====================================================================
# 🔁 DEMONIO ASÍNCRONO DE FONDO CON ARRANQUE SEGURO
# =====================================================================
def background_loop_perpetuo():
    print("🤖 Esperando estabilización de red de Flask (Safe Boot)...")
    time.sleep(5)
    print("🤖 Servomotor Cuantitativo de Fondo Activado.")
    while True:
        procesar_logica_cuantitativa()
        time.sleep(10)

t = threading.Thread(target=background_loop_perpetuo, daemon=True)
t.start()

# =====================================================================
# 🧮 MOTOR DE BACKTESTING HISTÓRICO INTEGRADO
# =====================================================================
@app.route('/api/backtest', methods=['POST'])
def ejecutar_backtest():
    data = request.get_json() or {}
    symbol = data.get("symbol", ACTIVO_PRINCIPAL).upper()
    capital_inicial = float(data.get("capital", 1000.0))
    
    url = f"{BINANCE_FUTURES_URL}/fapi/v1/klines"
    res = requests.get(url, params={"symbol": symbol, "interval": "15m", "limit": 1000}, timeout=10)
    if res.status_code != 200: 
        return jsonify({"error": "Error de descarga"}), 400
        
    klines = res.json()
    precios = np.array([float(k[4]) for k in klines])
    vols = np.array([float(k[5]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    
    ganadas, perdidas = 0, 0
    en_posicion = False
    tipo, entrada, tp, sl = "", 0.0, 0.0, 0.0
    
    for i in range(20, len(precios) - 1):
        close = precios[i]
        if not en_posicion:
            ma = np.mean(precios[i-20:i])
            std = np.std(precios[i-20:i])
            z = (vols[i] - np.mean(vols[i-20:i])) / (np.std(vols[i-20:i]) or 1)
            atr = np.mean(highs[i-14:i] - lows[i-14:i])
            
            if close >= (ma + 2*std) and z > 1.5:
                en_posicion, tipo, entrada, tp, sl = True, "LONG", close, close + 3*atr, close - 1.5*atr
            elif close <= (ma - 2*std) and z > 1.5:
                en_posicion, tipo, entrada, tp, sl = True, "SHORT", close, close - 3*atr, close + 3*atr
        else:
            if tipo == "LONG":
                if highs[i] >= tp: 
                    ganadas += 1
                    en_posicion = False
                elif lows[i] <= sl: 
                    perdidas += 1
                    en_posicion = False
            elif tipo == "SHORT":
                if lows[i] <= tp: 
                    ganadas += 1
                    en_posicion = False
                elif highs[i] >= sl: 
                    perdidas += 1
                    en_posicion = False

    total = ganadas + perdidas
    wr = (ganadas / total * 100) if total > 0 else 0
    return jsonify({"status": "SUCCESS", "activo": symbol, "operaciones": total, "win_rate": f"{round(wr, 2)}%"})

# =====================================================================
# 📱 PANEL DE INSTRUMENTACIÓN PREMIUM (WEB)
# =====================================================================
@app.route('/')
def dashboard():
    rows = []
    ganadas, perdidas, activas = 0, 0, 0
    win_rate, profit_factor = 0.0, 0.0
    
    try:
