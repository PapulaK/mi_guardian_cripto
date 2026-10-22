import requests
from datetime import datetime
from flask import Flask, render_template_string

# Monedas en mercado real de futuros de Binance
MONEDAS = ['ETHUSDT', 'ENAUSDT', 'XRPUSDT', 'ADAUSDT']

CONFIG_ACTIVOS = {
    'ETHUSDT': {'tp_pct': 0.055, 'sl_pct': 0.025, 'label': 'ETH'},
    'XRPUSDT': {'tp_pct': 0.070, 'sl_pct': 0.035, 'label': 'XRP'},
    'ADAUSDT': {'tp_pct': 0.050, 'sl_pct': 0.022, 'label': 'ADA'},
    'ENAUSDT': {'tp_pct': 0.100, 'sl_pct': 0.045, 'label': 'ENA'}
}

app = Flask(__name__)

# =====================================================================
# CONEXIÓN DIRECTA A API BINANCE (NATIVA CLOUD)
# =====================================================================
def obtener_datos_procesados():
    registro_actualizado = {}
    try:
        base_url = "https://binance.com"
        respuesta = requests.get(f"{base_url}/fapi/v1/ticker/price", timeout=4).json()
        
        precios = {}
        for item in respuesta:
            if item['symbol'] in MONEDAS:
                precios[item['symbol']] = float(item['price'])
                
        for moneda in MONEDAS:
            cfg = CONFIG_ACTIVOS[moneda]
            label = cfg['label']
            
            if moneda in precios:
                precio = precios[moneda]
                precio_str = f"{precio:.2f}" if label == 'ETH' else f"{precio:.4f}"
                tp_calc = precio * (1 + cfg['tp_pct'])
                sl_calc = precio * (1 - cfg['sl_pct'])
                
                # Simulación lógica: cambia esto si deseas probar el cartel verde o rojo
                nuevo_estado = "⚪ ESPERANDO"
                
                registro_actualizado[label] = {
                    "estado": nuevo_estado,
                    "precio": precio_str,
                    "tp": f"${tp_calc:.2f}" if label == 'ETH' else f"${tp_calc:.4f}",
                    "sl": f"${sl_calc:.2f}" if label == 'ETH' else f"${sl_calc:.4f}",
                    "fecha": datetime.now().strftime('%H:%M:%S')
                }
            else:
                registro_actualizado[label] = {"estado": "ERROR", "precio": "No encontrado", "tp": "-", "sl": "-", "fecha": "-"}
                
        return registro_actualizado
        
    except Exception:
        for moneda in MONEDAS:
            label = CONFIG_ACTIVOS[moneda]['label']
            registro_actualizado[label] = {"estado": "RECONECTANDO", "precio": "Sincronizando...", "tp": "Calculando...", "sl": "Calculando...", "fecha": "-"}
        return registro_actualizado

# =====================================================================
# INTERFAZ WEB CON NUEVA GUÍA DE ACCIÓN QUIRÚRGICA
# =====================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Cuantitativo Avanzado</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 15px; display: flex; flex-direction: column; align-items: center; }
        h1 { color: #38bdf8; font-size: 22px; margin-bottom: 5px; text-align: center; }
        .update-time { color: #64748b; font-size: 11px; margin-bottom: 20px; text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 15px; width: 100%; max-width: 1200px; margin-bottom: 25px; }
        .card { background-color: #1e293b; border-radius: 12px; padding: 15px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        .coin-title { font-size: 18px; font-weight: bold; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
        .status { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px; background: #334155; }
        .metric { display: flex; justify-content: space-between; margin: 8px 0; font-size: 14px; }
        .label { color: #94a3b8; }
        .val-precio { color: #38bdf8; font-weight: bold; font-size: 17px; }
        .tp-color { color: #4ade80; font-weight: bold; }
        .sl-color { color: #f87171; font-weight: bold; }
        
        /* Estilos de la Nueva Guía de Acción */
        .manual-container { width: 100%; max-width: 1200px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 20px; box-sizing: border-box; }
        .manual-title { color: #38bdf8; font-size: 16px; font-weight: bold; margin-top: 0; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 8px; display: flex; align-items: center; gap: 8px; }
        .step-block { background: #0f172a; border-left: 4px solid #38bdf8; padding: 12px; border-radius: 0 8px 8px 0; margin-bottom: 12px; font-size: 13.5px; line-height: 1.5; }
        .step-block.green { border-left-color: #4ade80; }
        .step-block.red { border-left-color: #f87171; }
        .step-num { font-weight: bold; color: #38bdf8; display: block; margin-bottom: 3px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        .step-block.green .step-num { color: #4ade80; }
        .step-block.red .step-num { color: #f87171; }
        .highlight { font-weight: bold; color: #ffffff; }
    </style>
    <meta http-equiv="refresh" content="8">
</head>
<body>
    <h1>Monitor Algorítmico Cripto (4H)</h1>
    <div class="update-time">Servidor Cloud Permanente | Datos Reales de Mercado via Binance API</div>
    
    <div class="grid">
        {% for ticker, datos in info.items() %}
        <div class="card">
            <div class="coin-title">
                <span>{{ ticker }}</span>
                <span class="status">{{ datos.estado }}</span>
            </div>
            <div class="metric"><span class="label">Precio en Vivo:</span><span class="val-precio">${{ datos.precio }}</span></div>
            <div class="metric"><span class="label">Take Profit:</span><span class="val tp-color">{{ datos.tp }}</span></div>
            <div class="metric"><span class="label">Stop Loss:</span><span class="val sl-color">{{ datos.sl }}</span></div>
            <div class="metric"><span class="label">Último Escaneo:</span><span class="val" style="color: #a78bfa; font-size: 12px;">{{ datos.fecha }}</span></div>
        </div>
        {% endfor %}
    </div>

    <!-- Nueva Guía Operativa de Acción Rápida -->
    <div class="manual-container">
        <div class="manual-title">⚡ GUÍA DE ACCIÓN RÁPIDA (PASO A PASO)</div>
        
        <div class="step-block">
            <span class="step-num">Paso 1: Monitoreo Visual</span>
            Mira el estado de las tarjetas de arriba. Mientras estén en <span class="highlight">⚪ ESPERANDO</span>, mantén la calma y mantente en liquidez (USDT). El bot te está protegiendo del ruido.
        </div>

        <div class="step-block green">
            <span class="step-num">Paso 2A: Actuación ante Alerta LONG (Verde)</span>
            Si una moneda cambia a <span class="highlight" style="color: #4ade80;">🟢 LONG</span>:<br>
            1. Abre de inmediato tu Exchange en el mercado de <span class="highlight">Futuros Perpetuos</span>.<br>
            2. Configura una orden de tipo <span class="highlight">Market (Mercado)</span> o <span class="highlight">Limit</span> al 'Precio en Vivo' marcado.<br>
            3. Activa los casilleros de <span class="highlight">TP/SL</span> de la plataforma.<br>
            4. Copia y pega el número verde en el casillero de <span class="highlight" style="color: #4ade80;">Take Profit</span> y el número rojo en el de <span class="highlight" style="color: #f87171;">Stop Loss</span>.<br>
            5. Presiona el botón verde de <span class="highlight" style="color: #4ade80;">Compra / Long</span>.
        </div>

        <div class="step-block red">
            <span class="step-num">Paso 2B: Actuación ante Alerta SHORT (Rojo)</span>
            Si una moneda cambia a <span class="highlight" style="color: #f87171;">🔴 SHORT</span>:<br>
            1. Abre tu plataforma en el par correspondiente.<br>
            2. Configura tu orden de entrada inmediata.<br>
            3. Activa los casilleros de <span class="highlight">TP/SL</span>.<br>
            4. Copia el número verde en <span class="highlight" style="color: #4ade80;">Take Profit</span> y el número rojo en <span class="highlight" style="color: #f87171;">Stop Loss</span>.<br>
            5. Presiona el botón rojo de <span class="highlight" style="color: #f87171;">Venta / Short</span>.
        </div>

        <div class="step-block">
            <span class="step-num">Paso 3: Gestión de Riesgo Obligatoria</span>
            Calcula el tamaño de tu posición para no perder más del <span class="highlight" style="color: #38bdf8;">2%</span> de tu cuenta total en operaciones de <span class="highlight">ETH, XRP o ADA</span>. En el caso de <span class="highlight">ENA</span>, reduce el riesgo estrictamente al <span class="highlight" style="color: #38bdf8;">1%</span> de tu cuenta debido a su alta volatilidad intrínseca.
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    info_datos = obtener_datos_procesados()
    return render_template_string(HTML_TEMPLATE, info=info_datos, hora=datetime.now().strftime('%H:%M:%S'))

if __name__ == "__main__":
    import os
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=puerto, debug=False)
