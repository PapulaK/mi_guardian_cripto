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
# CONEXIÓN DIRECTA A API BINANCE (COMPATIBLE CON ARRANQUE CLOUD)
# =====================================================================
def obtener_datos_procesados():
    """Consulta los precios reales directamente a Binance en cada recarga de pantalla."""
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
                
                registro_actualizado[label] = {
                    "estado": "⚪ ESPERANDO",
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
# INTERFAZ WEB DINÁMICA CON MANUAL INTEGRADO
# =====================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Cuantitativo</title>
    <style>
        body { font-family: -apple-system, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        h1 { color: #38bdf8; font-size: 24px; margin-bottom: 5px; }
        .update-time { color: #64748b; font-size: 12px; margin-bottom: 25px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; width: 100%; max-width: 1200px; margin-bottom: 40px; }
        .card { background-color: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
        .coin-title { font-size: 20px; font-weight: bold; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        .status { font-size: 13px; font-weight: 600; padding: 4px 10px; border-radius: 6px; background: #334155; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; font-size: 15px; }
        .label { color: #94a3b8; }
        .val-precio { color: #38bdf8; font-weight: bold; font-size: 18px; }
        .tp-color { color: #4ade80; font-weight: bold; }
        .sl-color { color: #f87171; font-weight: bold; }
        .manual-container { width: 100%; max-width: 1200px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 25px; box-sizing: border-box; }
        .manual-title { color: #38bdf8; font-size: 18px; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        ul { margin: 5px 0; padding-left: 20px; color: #94a3b8; font-size: 14px; }
        li { margin-bottom: 4px; }
        .highlight { font-weight: 600; color: #f8fafc; }
    </style>
    <meta http-equiv="refresh" content="10">
</head>
<body>
    <h1>Monitor Algorítmico Cripto (4H)</h1>
    <div class="update-time">Servidor Cloud Permanente | Datos Reales de Mercado vía Binance API</div>
    
    <div class="grid">
        {% for ticker, datos in info.items() %}
        <div class="card">
            <div class="coin-title"><span>{{ ticker }}</span><span class="status">{{ datos.estado }}</span></div>
            <div class="metric"><span class="label">Precio en Vivo:</span><span class="val-precio">${{ datos.precio }}</span></div>
            <div class="metric"><span class="label">Take Profit:</span><span class="val tp-color">{{ datos.tp }}</span></div>
            <div class="metric"><span class="label">Stop Loss:</span><span class="val sl-color">{{ datos.sl }}</span></div>
            <div class="metric"><span class="label">Último Escaneo:</span><span style="color: #a78bfa; font-size: 13px;">{{ datos.fecha }}</span></div>
        </div>
        {% endfor %}
    </div>

    <div class="manual-container">
        <div class="manual-title">📖 Manual Operativo del Sistema</div>
        <ul>
            <li><span class="highlight">Precios 100% Reales:</span> Sincronizados directamente con las terminales de futuros de Binance en cada recarga automática del navegador.</li>
            <li><span class="highlight">Gestión de Riesgo:</span> Arriesgar máximo el 2% en ETH, XRP, ADA y el 1% en ENA de tu saldo global por operación.</li>
        </ul>
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
    # Render asigna el puerto dinámicamente mediante variables de entorno
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=puerto, debug=False)
