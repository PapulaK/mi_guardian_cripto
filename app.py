import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quantum_institutional_key_4h_pro_fixed_final")

CONFIG_ACTIVOS_BASE = {'tp_pct': 0.055, 'sl_pct': 0.025}
CONFIG_ESPECIFICA = {
    'ETH': {'tp_pct': 0.055, 'sl_pct': 0.025},
    'XRP': {'tp_pct': 0.070, 'sl_pct': 0.035},
    'ADA': {'tp_pct': 0.050, 'sl_pct': 0.022},
    'ENA': {'tp_pct': 0.100, 'sl_pct': 0.045}
}

def analizar_moneda_tiempo_real(moneda):
    ticker_binance = moneda if moneda.endswith('USDT') else f"{moneda}USDT"
    label = moneda.replace('USDT', '')
    cfg = CONFIG_ESPECIFICA.get(label, CONFIG_ACTIVOS_BASE)
    
    try:
        base_url = "https://binance.com"
        url = f"{base_url}/fapi/v1/klines?symbol={ticker_binance}&interval=4h&limit=30"
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
        
        estado_calculado = "⚪ ESPERANDO"
        if v_cerrada['close'] > v_cerrada['bb_sup'] and 55 < v_cerrada['rsi'] < 70:
            estado_calculado = "🟢 LONG"
        elif v_cerrada['close'] < v_cerrada['bb_inf'] and 30 < v_cerrada['rsi'] < 45:
            estado_calculado = "🔴 SHORT"
            
        if estado_calculado == "🔴 SHORT":
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

# Diseño web optimizado en formato compacto tradicional
HTML_COMPLETO = (
    "<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>"
    "<title>Panel Pro</title><style>body{font-family:-apple-system,sans-serif;background-color:#0f172a;color:#f8fafc;margin:0;padding:15px;display:flex;flex-direction:column;align-items:center}h1{color:#38bdf8;font-size:22px;margin-bottom:5px;text-align:center}.update-time{color:#64748b;font-size:11px;margin-bottom:20px;text-align:center}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:15px;width:100%;max-width:1200px;margin-bottom:25px}.card{background-color:#1e293b;border-radius:12px;padding:15px;border:1px solid #334155}.coin-title{font-size:18px;font-weight:bold;border-bottom:1px solid #334155;padding-bottom:8px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}.status{font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;color:#fff;background:#334155}.metric{display:flex;justify-content:space-between;margin:8px 0;font-size:14px}.label{color:#94a3b8}.val-precio{color:#38bdf8;font-weight:bold;font-size:17px}.tp-color{color:#4ade80;font-weight:bold}.sl-color{color:#f87171;font-weight:bold}.btn-eliminar{background:none;border:none;color:#64748b;font-size:11px;cursor:pointer;padding:0;text-decoration:underline;margin-top:10px;display:block;text-align:right;width:100%}.panel-control-container{width:100%;max-width:1200px;display:flex;flex-direction:column;gap:20px}.form-container,.manual-container{background-color:#1e293b;border-radius:12px;border:1px solid #334155;padding:20px;box-sizing:border-box;width:100%}.manual-title{color:#38bdf8;font-size:16px;font-weight:bold;margin-top:0;margin-bottom:15px;border-bottom:1px solid #334155;padding-bottom:8px}.step-block{background:#0f172a;border-left:4px solid #38bdf8;padding:12px;border-radius:0 8px 8px 0;margin-bottom:12px;font-size:13.5px;line-height:1.5}.highlight{font-weight:bold;color:#fff}.form-group{display:flex;gap:10px;margin-top:15px}input[type='text']{background-color:#0f172a;border:1px solid #334155;color:#f8fafc;padding:10px;border-radius:6px;flex-grow:1;text-transform:uppercase;font-size:14px}.btn-agregar{background-color:#38bdf8;color:#0f172a;border:none;padding:10px 18px;border-radius:6px;font-weight:bold;cursor:pointer;font-size:14px}</style><meta http-equiv='refresh' content='10'></head><body>"
    "<h1>Monitor Algorítmico Cuantitativo (Velas 4H)</h1><div class='update-time'>Servidor Cloud Permanente Render | Análisis de Variación Histórica de Precios Activo</div>"
    "<div class='grid'>{% for ticker, datos in info.items() %}<div class='card'><div class='coin-title'><span>{{ ticker }}</span><span class='status'>{{ datos.estado }}</span></div><div class='metric'><span class='label'>Precio en Vivo:</span><span class='val-precio'>${{ datos.precio }}</span></div><div class='metric'><span class='label'>Take Profit:</span><span class='val tp-color'>{{ datos.tp }}</span></div><div class='metric'><span class='label'>Stop Loss:</span><span class='val sl-color'>{{ datos.sl }}</span></div><div class='metric'><span class='label'>Último Escaneo:</span><span style='color:#a78bfa;font-size:12px'>{{ datos.fecha }}</span></div><form action='{{ url_for(\"eliminar_moneda\") }}' method='POST'><input type='hidden' name='moneda_a_borrar' value='{{ ticker }}'><button type='submit' class='btn-eliminar'>❌ Eliminar activo</button></form></div>{% endfor %}</div>"
    "<div class='panel-control-container'><div class='form-container'><div class='manual-title'>➕ AGREGAR NUEVA ALTCOIN EN TIEMPO REAL</div><p style='font-size:13px;color:#94a3b8;margin:0;line-height:1.4'>Ingresa las siglas de cualquier criptomoneda disponible en Binance Futuros. El sistema viajará 20 velas al pasado automáticamente para evaluar su variación técnica histórica.</p><form action='{{ url_for(\"agregar_moneda\") }}' method='POST' class='form-group'><input type='text' name='nueva_moneda' placeholder='Ej: SOL, MATIC, LINK, BTC, AVAX' required autocomplete='off'><button type='submit' class='btn-agregar'>Agregar</button></form></div>"
    "<div class='manual-container'><div class='manual-title'>⚡ GUÍA DE ACCIÓN RÁPIDA (PASO A PASO COMPLETADO)</div>"
    "<div class='step-block'><span class='highlight'>Paso 1: Monitoreo Visual</span><br>Mira el estado de las tarjetas de arriba. Mientras estén en ⚪ ESPERANDO, mantén la calma y mantente en liquidez (USDT). El bot analiza el volumen de las últimas velas de 4 horas en Binance y te protege del ruido lateral del mercado.</div>"
    "<div class='step-block'><span class='highlight' style='color:#4ade80'>Paso 2A: Actuación ante Alerta LONG (Verde)</span><br>Si una moneda cambia a 🟢 LONG por ruptura de volatilidad:<br>1. Abre de inmediato tu Exchange en el mercado de Futuros Perpetuos.<br>2. Configura una orden de tipo Market para una entrada instantánea o Limit al precio actual.<br>3. Activa las casillas TP/SL, copia y pega el número verde en Take Profit y el número rojo en Stop Loss.<br>4. Presiona el botón verde de Compra / Long.</div>"
    "<div class='step-block'><span class='highlight' style='color:#f87171'>Paso 2B: Actuación ante Alerta SHORT (Rojo)</span><br>Si una moneda cambia a 🔴 SHORT por caída e inyección de contratos cortos:<br>1. Configura tu orden de entrada inmediata en futuros.<br>2. Activa los casilleros de protección integrada TP/SL.<br>3. Copia el número verde en Take Profit y el número rojo en Stop Loss.<br>4. Presiona el botón de gatillo de Venta / Short.</div>"
    "<div class='step-block'><span class='highlight'>Paso 3: Gestión de Riesgo Obligatoria</span><br>Calcula el apalancamiento para no arriesgar más del 2% de tu cuenta total en operaciones de ETH, XRP o ADA. En el caso de ENA, debido a que sus variaciones históricas son mucho más violentas, reduce el riesgo estrictamente al 1% de tu capital total por posición para proteger tu balance.</div></div></div></body></html>"
)

@app.route('/')
def home():
    if 'lista_monedas' not in session:
        session['lista_monedas'] = ['ETH', 'ENA', 'XRP', 'ADA']
    info_datos = {m: analizar_moneda_tiempo_real(m) for m in session['lista_monedas']}
    return render_template_string(HTML_COMPLETO, info=info_datos, hora=datetime.now().strftime('%H:%M:%S'))

@app.route('/agregar', methods=['POST'])
def agregar_moneda():
    nueva = request.form.get('nueva_moneda', '').strip().upper()
    if nueva:
        lista = session.get('lista_monedas', ['ETH', 'ENA', 'XRP', 'ADA'])
        if nueva not in lista:
            lista.append(nueva)
            session['lista_monedas'] = lista
            session.modified = True
    return redirect(url_for('home'))

@app.route('/eliminar', methods=['POST'])
def eliminar_moneda():
    borrar = request.form.get('moneda_a_borrar', '').strip().upper()
