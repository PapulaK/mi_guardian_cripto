# --- INTERFAZ PREMIUM DE BAJA LATENCIA PARA MÓVILES CON MANUAL INTEGRADO ---
async def http_html_dashboard(request):
    op_activa_html = "<p style='color:#ffbc00; font-weight:700; margin:0;'>⚠️ EN ESPERA DE ANOMALÍAS DE LIQUIDEZ</p>"
    if ENGINE_STATE["operacion_activa"]:
        op = ENGINE_STATE["operacion_activa"]
        op_activa_html = f"""
        <div style="background:#092115; padding:14px; border-radius:6px; border-left:4px solid #10b981;">
            <p style="margin:4px 0;"><strong>POSICIÓN:</strong> <span style="color:#10b981;">{op['tipo']}</span></p>
            <p style="margin:4px 0;"><strong>ENTRADA:</strong> {op['entrada']:.4f}</p>
            <p style="margin:4px 0; color:#10b981;"><strong>TAKE PROFIT:</strong> {op['tp']:.4f}</p>
            <p style="margin:4px 0; color:#ef4444;"><strong>STOP LOSS:</strong> {op['sl']:.4f}</p>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>MATRIX ULTRALOW V5</title>
        <style>
            body {{ background-color: #040406; color: #f4f4f5; font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 12px; }}
            .card {{ background: #0b0b0e; border: 1px solid #18181b; padding: 14px; border-radius: 10px; margin-bottom: 12px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #18181b; padding-bottom: 8px; }}
            .title {{ font-size: 15px; font-weight: 800; color: #10b981; letter-spacing: 0.5px; }}
            .metric {{ font-size: 28px; font-weight: 800; color: #ffffff; margin-top: 4px; }}
            .label {{ font-size: 11px; color: #71717a; text-transform: uppercase; font-weight: 600; }}
            select {{ width: 100%; padding: 12px; background: #121217; border: 1px solid #27272a; color: white; border-radius: 6px; font-size: 15px; font-weight: bold; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            .indicator-val {{ font-size: 18px; font-weight: 700; margin-top: 4px; }}
            .manual {{ font-size: 12px; color: #a1a1aa; line-height: 1.6; margin: 0; }}
            .manual strong {{ color: #ffffff; }}
        </style>
        <script>
            setInterval(() => {{ fetch('/api/state').then(r => r.json()).then(data => {{
                document.getElementById('price').innerText = data.precio_spot.toFixed(4);
                document.getElementById('vpin').innerText = (data.vpin_actual * 100).toFixed(1) + '%';
                document.getElementById('zscore').innerText = data.z_score_retornos.toFixed(2);
                document.getElementById('spread').innerText = data.orderbook_spread.toFixed(5);
                document.getElementById('clock').innerText = data.last_update;
                if(data.vpin_actual > 0.65) {{ document.getElementById('vpin').style.color = '#10b981'; }}
                else {{ document.getElementById('vpin').style.color = '#3b82f6'; }}
            }}); }}, 300);
            function cambiarAltcoin(sel) {{
                fetch('/api/switch?symbol=' + sel.value, {{ method: 'POST' }}).then(() => window.location.reload());
            }}
        </script>
    </head>
    <body>
        <div class="header">
            <div class="title">⚡ MATRIX PURE HFT V5</div>
            <div id="clock" style="font-size:11px; color:#52525b;">{ENGINE_STATE["last_update"]}</div>
        </div>
        <p></p>
        <div class="card">
            <span class="label">Inyección RAM de Altcoin Activa</span>
            <p></p>
            <select onchange="cambiarAltcoin(this)">
                <option value="SOLUSDT" {"selected" if ENGINE_STATE["activo_actual"]=="SOLUSDT" else ""}>SOL / USDT (Solana)</option>
                <option value="BTCUSDT" {"selected" if ENGINE_STATE["activo_actual"]=="BTCUSDT" else ""}>BTC / USDT (Bitcoin)</option>
                <option value="ETHUSDT" {"selected" if ENGINE_STATE["activo_actual"]=="ETHUSDT" else ""}>ETH / USDT (Ethereum)</option>
                <option value="XRPUSDT" {"selected" if ENGINE_STATE["activo_actual"]=="XRPUSDT" else ""}>XRP / USDT (Ripple)</option>
            </select>
        </div>
        <div class="card">
            <span class="label">Precio Spot</span>
            <div class="metric" id="price">{ENGINE_STATE["precio_spot"]:.4f}</div>
        </div>
        <div class="grid">
            <div class="card">
                <span class="label">Desequilibrio VPIN</span>
                <div class="indicator-val" id="vpin">{(ENGINE_STATE["vpin_actual"] * 100):.1f}%</div>
            </div>
            <div class="card">
                <span class="label">Z-Score Retornos</span>
                <div class="indicator-val" id="zscore">{ENGINE_STATE["z_score_retornos"]:.2f}</div>
            </div>
        </div>
        <div class="card">
            <span class="label">Spread de Orderbook Líquido</span>
            <div style="font-size:15px; font-weight:bold; margin-top:2px;" id="spread">{ENGINE_STATE["orderbook_spread"]:.5f}</div>
        </div>
        <div class="card">
            <span class="label">Matriz HFT - Flujo de Órdenes</span>
            <p></p>
            <div id="posicion-contenedor">{op_activa_html}</div>
        </div>
        <!-- MANUAL DE AYUDA INTEGRADO OPTIMIZADO PARA BAJA LATENCIA -->
        <div class="card">
            <span class="label" style="color: #10b981;">📖 Manual de Operación V5-HFT</span>
            <p></p>
            <p class="manual">
                <strong>Desequilibrio VPIN (>65%):</strong> Mide la toxicidad del flujo y la presión de órdenes en bloques cortos. Si sube de golpe, predice ráfagas institucionales inminentes.<br><br>
                <strong>Z-Score Retornos (>1.8 / <-1.8):</strong> Identifica anomalías estadísticas en el rendimiento logarítmico del precio. Valida volatilidad pura descartando movimientos lentos o laterales.<br><br>
                <strong>Estructura Transicional:</strong> Al cambiar de Altcoin en el menú, el motor limpia instantáneamente la RAM en microsegundos (`O(1)`) y reconecta el pipeline de streams de Binance sin dejar basura de datos en memoria.
            </p>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')
