import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# Configuración visual de la página web (se adapta a Celular y PC)
st.set_page_config(page_title="Guardián Cripto 5%", layout="centered")

st.title("🤖 Guardián Cripto Cuantitativo Pro")
st.subheader("📊 Panel de Alta Precisión - Rango 5% (Velas de 4 Horas)")

# 📖 MANUAL DE OPERACIÓN INTEGRADO EN UN DESPLEGABLE
with st.expander("📖 HACER CLIC AQUÍ PARA VER EL MANUAL DE OPERACIÓN"):
    st.markdown("""
    ### 📋 Cómo operar las señales en tu Exchange (Binance, Bybit, etc.):
    * **🟢 ENTRADA (COMPRAR):** La altcoin cayó a un suelo extremo inusual en el gráfico de 4 horas y entraron manos fuertes. Compra en tu Exchange y coloca una orden de venta un 5% más arriba (Take Profit) y un seguro un 5% más abajo (Stop Loss).
    * **🔵 MANTENER POSICIÓN:** La matemática indica que la señal de compra sigue activa. Ten paciencia y espera a que el precio toque tus extremos del 5%.
    * **🔴 SALIDA (VENDER GANANCIA):** El rebote se cumplió con éxito y tocó el objetivo del +5%. Vende y asegura tus ganancias en dólares.
    * **🚨 SALIDA (CORTAR PÉRDIDA):** El soporte falló y el precio cayó un -5%. El bot activó el candado de protección. Vende para limitar tu pérdida.
    * **🔒 NEUTRAL:** El precio está en zonas normales o aburridas. Mantente al margen en liquidez (dólares).
    """)

tickers = {
    "Bitcoin (BTC)": "BTC-USD",
    "Ethereum (ETH)": "ETH-USD",
    "Ethena (ENA)": "ENA-USD",
    "Cardano (ADA)": "ADA-USD",
    "Ripple (XRP)": "XRP-USD"
}

# Botón interactivo web
if st.button("🚀 ESCANEAR MERCADO EN TIEMPO REAL"):
    st.info("⚡ Conectándose a los servidores globales y procesando velas de 4 horas...")
    
    filas_tabla = []
    
    for nombre, ticker in tickers.items():
        try:
            # 🚀 AJUSTE DE PRECISIÓN: Descarga datos en intervalo de 4 HORAS ('4h')
            # Las APIs oficiales exigen descargar máximo los últimos 730 días para temporalidad de 4h
            data = yf.download(ticker, period="730d", interval="4h", progress=False)
            if data.empty: continue
            df = data.copy()
            df.columns = df.columns.get_level_values(0)
            
            # Fórmulas Cuantitativas
            df['Media'] = df['Close'].rolling(window=20).mean()
            df['Desviacion'] = df['Close'].rolling(window=20).std()
            df['Z_Score'] = (df['Close'] - df['Media']) / df['Desviacion']
            df['Vol_Inst'] = df['Volume'].rolling(window=20).quantile(0.80)
            
            # Simulación con candados del 5%
            en_posicion, precio_entrada = False, 0.0
            for i in range(len(df) - 1):
                if not en_posicion and df['Z_Score'].iloc[i] < -2.5 and df['Volume'].iloc[i] > df['Vol_Inst'].iloc[i]:
                    en_posicion, precio_entrada = True, df['Close'].iloc[i]
                elif en_posicion and (df['Close'].iloc[i] >= (precio_entrada * 1.05) or df['Close'].iloc[i] <= (precio_entrada * 0.95)):
                    en_posicion = False
            
            z_hoy = df['Z_Score'].iloc[-1]
            precio_hoy = df['Close'].iloc[-1]
            
            if not en_posicion and z_hoy < -2.5 and df['Volume'].iloc[-1] > df['Vol_Inst'].iloc[-1]:
                accion = "🟢 ENTRADA (COMPRAR)"
                guia = f"Suelo. TP: ${precio_hoy*1.05:,.2f} | SL: ${precio_hoy*0.95:,.2f}"
            elif en_posicion:
                if precio_hoy >= (precio_entrada * 1.05):
                    accion = "🔴 SALIDA (VENDER)"
                    guia = f"¡Objetivo +5% alcanzado! Cobrar ${precio_hoy:,.2f}"
                elif precio_hoy <= (precio_entrada * 0.95):
                    accion = "🚨 SALIDA (PÉRDIDA)"
                    guia = "Candado -5% activado. Proteger capital."
                else:
                    accion = "🔵 MANTENER POSICIÓN"
                    guia = f"Simulado a ${precio_entrada:,.2f} | Esperando objetivo."
            else:
                accion = "🔒 NEUTRAL"
                guia = "Buscando suelo estructural en 4h. No operar hoy."
                
            filas_tabla.append({
                "Criptomoneda": nombre,
                "Precio Actual": f"${precio_hoy:,.4f}",
                "Desviación (Z)": f"{z_hoy:.2f}",
                "Acción Recomendada": accion,
                "Guía Operativa y Objetivos": guia
            })
        except Exception as e:
            st.error(f"Error procesando {nombre}: {e}")
            
    # Renderizar la tabla de forma nativa y elegante en la web
    df_visual = pd.DataFrame(filas_tabla)
    st.table(df_visual)
    st.success(f"✅ Escaneo completado con éxito a las {datetime.datetime.now().strftime('%H:%M:%S')}")
