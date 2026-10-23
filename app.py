import os
import requests
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session

# 1. Aseguramos el nombre exacto de la aplicación para Gunicorn
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quantum_key_1h_predictive_v3_secure_final")

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
            precio_entrada REAL
        )
    ''')
    conn.commit()
    conn.close()

inicializar_db()

CONFIG_ACTIVOS_BASE = {'tp_pct': 0.025, 'sl_pct': 0.012}
CONFIG_ESPECIFICA = {
    'ETH': {'tp_pct': 0.025, 'sl_pct': 0.012},
    'XRP': {'tp_pct': 0.035, 'sl_pct': 0.017},
    'ADA': {'tp_pct': 0.035, 'sl_pct': 0.017},
    'ENA': {'tp_pct': 0.050, 'sl_pct': 0.022}
}

def registrar_señal_db(moneda, tipo_señal, precio):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT tipo_señal FROM señales WHERE moneda = ? ORDER BY id DESC LIMIT 1", (moneda,))
        ultimo = cursor.fetchone()
        if not ultimo or ultimo != tipo_señal:
            cursor.execute("INSERT INTO señales (fecha, moneda, tipo_señal, precio_entrada) VALUES (?, ?, ?, ?)",
                           (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), moneda, tipo_señal, precio))
            conn.commit()
    except Exception as e:
        print(f"Error DB: {e}")
    finally:
        conn.close()

def analizar_moneda_tiempo_real(moneda):
    ticker_binance = moneda if moneda.endswith('USDT') else f"{moneda}USDT"
    label = moneda.replace('USDT', '')
    cfg = CONFIG_ESPECIFICA.get(label, CONFIG_ACTIVOS_BASE)
    
    try:
        base_url = "https://binance.com"
        url = f"{base_url}/fapi/v1/klines?symbol={ticker_binance}&interval=1h&limit=30"
        raw_klines = requests.get(url, timeout=4).json()
        
        df = pd.DataFrame(raw_klines, columns=[
            'ts', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'q_volume', 'trades', 'taker_base', 'taker_quote', 'ignore'
        ]).astype(float)
        
        precio_actual = df['close'].iloc[-1]
        precio_str = f"{precio_actual:.2f}" if label in ['ETH', 'BTC'] else f"{precio_actual:.4f}"
        
        df['ma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['bb_sup'] = df['ma20'] + (1.8 * df['std20'])
        df['bb_inf'] = df['ma20'] - (1.8 * df['std20'])
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, 0.0001))))
        
        v_cerrada = df.iloc[-2]
        rsi_actual = df['rsi'].iloc[-1]
        bb_sup_actual = df['bb_sup'].iloc[-1]
        bb_inf_actual = df['bb_inf'].iloc[-1]
        
        estado_calculado = "⚪ ESPERANDO"
        if v_cerrada['close'] > v_cerrada['bb_sup'] and 55 < v_cerrada['rsi'] < 70:
            estado_calculado = "🟢 LONG"
            registrar_señal_db(label, "LONG", precio_actual)
        elif v_cerrada['close'] < v_cerrada['bb_inf'] and 30 < v_cerrada['rsi'] < 45:
            estado_calculado = "🔴 SHORT"
            registrar_señal_db(label, "SHORT", precio_actual)
            
        distancia_techo = ((bb_sup_actual - precio_actual) / precio_actual) * 100
        distancia_piso = ((precio_actual - bb_inf_actual) / precio_actual) * 100
        
        if estado_calculado == "⚪ ESPERANDO":
            if distancia_techo < 0.75 and rsi_actual > 50:
                estado_calculado = f"🟡 PRE-LONG ({distancia_techo:.2f}%)"
            elif distancia_piso < 0.75 and rsi_actual < 45:
                estado_calculado = f"🟡 PRE-SHORT ({distancia_piso:.2f}%)"
        
        if "SHORT" in estado_calculado:
            tp_calc = precio_actual * (1 - cfg['tp_pct'])
            sl_calc = precio_actual * (1 + cfg['sl_pct'])
        else:
            tp_calc = precio_actual * (1 + cfg['tp_pct'])
            sl_calc = precio_actual * (1 - cfg['sl_pct'])
            
        return {
            "estado": estado_calculado,
            "precio": precio_str,
            "tp": f"${tp_calc:.2f}" if label in ['ETH', 'BTC'] else f"${tp_calc:.4f}",
            "sl": f"${sl_calc:.2f}" if label in ['ETH', 'BTC'] else f"${sl_calc:.4f}",
            "fecha": datetime.now().strftime('%H:%M:%S')
        }
    except Exception:
        return {
            "estado": "RECONECTANDO", "precio": "Sincronizando...", 
            "tp": "Calculando...", "sl": "Calculando...", "fecha": datetime.now().strftime('%H:%M:%S')
        }

def obtener_historial_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, moneda, tipo_señal, precio_entrada FROM señales ORDER BY id DESC LIMIT 5")
        filas = cursor.fetchall()
        conn.close()
        return filas
    except Exception:
        return []

def obtener_plantilla_html():
    parte_head = "<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Panel Predictivo Pro</title><style>body{font-family:-apple-system,sans-serif;background-color:#0f172a;color:#f8fafc;margin:0;padding:15px;display:flex;flex-direction:column;align-items:center}h1{color:#38bdf8;font-size:22px;margin-bottom:5px;text-align:center}.update-time{color:#64748b;font-size:11px;margin-bottom:20px;text-align:center}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:15px;width:100%;max-width:1200px;margin-bottom:25px}.card{background-color:#1e293b;border-radius:12px;padding:15px;border:1px solid #334155}.coin-title{font-size:18px;font-weight:bold;border-bottom:1px solid #334155;padding-bottom:8px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}.status{font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;color:#fff;background:#334155}.metric{display:flex;justify-content:space-between;margin:8px 0;font-size:14px}.label{color:#94a3b8}.val-precio{color:#38bdf8;font-weight:bold;font-size:17px}.tp-color{color:#4ade80;font-weight:bold}.sl-color{color:#f87171;font-weight:bold}.btn-eliminar{background:none;border:none;color:#64748b;font-size:11px;cursor:pointer;padding:0;text-decoration:underline;margin-top:10px;display:block;text-align:right;width:100%}.panel-control-container{width:100%;max-width:1200px;display:flex;flex-direction:column;gap:20px}.form-container,.manual-container{background-color:#1e293b;border-radius:12px;border:1px solid #334155;padding:20px;box-sizing:border-box;width:100%}.manual-title{color:#38bdf8;font-size:16px;font-weight:bold;margin-top:0;margin-bottom:15px;border-bottom:1px solid #334155;padding-bottom:8px}.step-block{background:#0f172a;border-left:4px solid #38bdf8;padding:12px;border-radius:0 8px 8px 0;margin-bottom:12px;font-size:13.5px;line-height:1.5}.highlight{font-weight:bold;color:#fff}.form-group{display:flex;gap:10px;margin-top:15px}input[type='text']{background-color:#0f172a;border:1px solid #334155;color:#f8fafc;padding:10px;border-radius:6px;flex-grow:1;text-transform:uppercase;font-size:14px}.btn-agregar{background-color:#38bdf8;color:#0f172a;border:none;padding:10px 18px;border-radius:6px;font-weight:bold;cursor:pointer;font-size:14px}.historial-tabla{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}.historial-tabla th,.historial-tabla td{padding:8px;text-align:left;border-bottom:1px solid #334155}.historial-tabla th{color:#38bdf8}</style><meta http-equiv='refresh' content='10'></head><body>"
    parte_cards = "<h1>Monitor Cuantitativo Predictivo (1H + Alertas)</h1><div class='update-time'>Servidor Cloud Permanente Render | Análisis Proactivo de Ruptura y Base de Datos Activa</div><div class='grid'>{% for ticker, datos in info.items() %}<div class='card'><div class='coin-title'><span>{{ ticker }}</span><span class='status' style='background-color: {% if \"LONG\" in datos.estado %}#16a34a{% elif \"SHORT\" in datos.estado %}#dc2626{% elif \"PRE\" in datos.estado %}#ca8a04{% else %}#334155{% endif %};'>{{ datos.estado }}</span></div><div class='metric'><span class='label'>Precio en Vivo:</span><span class='val-precio'>${{ datos.precio }}</span></div><div class='metric'><span class='label'>Take Profit Intradía:</span><span class='val tp-color'>{{ datos.tp }}</span></div><div class='metric'><span class='label'>Stop Loss Corto:</span><span class='val sl-color'>{{ datos.sl }}</span></div><div class='metric'><span class='label'>Último Escaneo:</span><span style='color:#a78bfa;font-size:12px'>{{ datos.fecha }}</span></div><form action='{{ url_for(\"eliminar_moneda\") }}' method='POST'><input type='hidden' name='moneda_a_borrar' value='{{ ticker }}'><button type='submit' class='btn-eliminar'>❌ Eliminar activo</button></form></div>{% endfor %}</div>"
    parte_db = "<div class='panel-control-container'><div class='form-container'><div class='manual-title'>🗄️ HISTORIAL AUTOMÁTICO DE SEÑALES (ÚLTIMOS EXTRACTOS DB)</div>{% if historial %}<table class='historial-tabla'><thead><tr><th>Fecha</th><th>Moneda</th><th>Señal</th><th>Precio</th></tr></thead><tbody>{% for fila in historial %}<tr><td>{{ fila[0] }}</td><td>{{ fila[1] }}</td><td style='color:{% if fila[2]==\"LONG\" %}#4ade80{% else %}#f87171{% endif %}'>{{ fila[2] }}</td><td>${{ fila[3] }}</td></tr>{% endfor %}</tbody></table>{% else %}<p style='font-size:13px;color:#64748b;margin:0;'>Esperando la primera confirmación de señal horaria para registrar en la base de datos...</p>{% endif %}</div>"
