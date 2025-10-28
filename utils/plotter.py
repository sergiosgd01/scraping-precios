import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
import seaborn as sns
import numpy as np
import os


def graficar_precios(nombre):
    # Crear carpeta 'data' si no existe
    os.makedirs('data', exist_ok=True)
    
    # Rutas dentro de la carpeta 'data'
    archivo_csv = f"data/precios_{nombre}.csv"
    nombre_png = f"data/{nombre}.png"
    
    df = pd.read_csv(archivo_csv, parse_dates=['fecha'])
    df['precio_num'] = df['precio'].str.replace('€', '').str.replace(',', '.').astype(float)

    # Crear figura
    fig, ax = plt.subplots(figsize=(18, 10))

    # Estilo general
    sns.set_style("whitegrid")

    # Línea principal de precios
    ax.plot(df['fecha'], df['precio_num'], marker='o', linestyle='-', linewidth=2, color='#007acc', label='Precio Diario')

    # Relleno entre mínimos y la línea de precios
    ax.fill_between(df['fecha'], df['precio_num'].min(), df['precio_num'], color='#b3d9ff', alpha=0.3)

    # Anotaciones de los máximos y mínimos
    max_price = df.loc[df['precio_num'].idxmax()]
    min_price = df.loc[df['precio_num'].idxmin()]
    ax.annotate(f"Máximo: {max_price['precio_num']:.2f}€", xy=(max_price['fecha'], max_price['precio_num']),
                xytext=(0, 20), textcoords="offset points", arrowprops=dict(arrowstyle="->", lw=1.5),
                fontsize=11, ha='center', color='darkgreen')
    ax.annotate(f"Mínimo: {min_price['precio_num']:.2f}€", xy=(min_price['fecha'], min_price['precio_num']),
                xytext=(0, -30), textcoords="offset points", arrowprops=dict(arrowstyle="->", lw=1.5),
                fontsize=11, ha='center', color='darkred')

    # Títulos y ejes
    ax.set_title(f"Evolución del precio diario - {nombre.capitalize()}", fontsize=20, weight='bold')
    ax.set_xlabel("Fecha", fontsize=14)
    ax.set_ylabel("Precio (€)", fontsize=14)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f€'))

    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(fontsize=12)
    plt.tight_layout()

    plt.savefig(nombre_png, dpi=150)
    plt.close()
    return nombre_png