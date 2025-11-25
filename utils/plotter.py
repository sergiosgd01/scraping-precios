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

    # Crear figura con fondo blanco
    fig, ax = plt.subplots(figsize=(16, 9), facecolor='white')
    ax.set_facecolor('#f8f9fa')

    # Calcular estadísticas
    precio_min = df['precio_num'].min()
    precio_max = df['precio_num'].max()
    precio_promedio = df['precio_num'].mean()
    precio_actual = df['precio_num'].iloc[-1]

    # Línea de precio promedio (discontinua)
    ax.axhline(y=precio_promedio, color='#6c757d', linestyle='--', linewidth=2, 
               label=f'Precio Promedio: {precio_promedio:.2f}€', alpha=0.7)

    # Línea principal de precios con gradiente
    line = ax.plot(df['fecha'], df['precio_num'], marker='o', markersize=8, 
                   linestyle='-', linewidth=3, color='#0066cc', 
                   label='Evolución de Precio', zorder=3)

    # Relleno dinámico: verde si está por debajo del promedio, rojo si está por encima
    ax.fill_between(df['fecha'], precio_promedio, df['precio_num'], 
                     where=(df['precio_num'] <= precio_promedio), 
                     color='#28a745', alpha=0.2, label='Por debajo del promedio')
    ax.fill_between(df['fecha'], precio_promedio, df['precio_num'], 
                     where=(df['precio_num'] > precio_promedio), 
                     color='#dc3545', alpha=0.2, label='Por encima del promedio')

    # Destacar el punto más bajo (MÍNIMO HISTÓRICO)
    min_idx = df['precio_num'].idxmin()
    ax.scatter(df.loc[min_idx, 'fecha'], precio_min, color='#28a745', 
               s=300, zorder=5, marker='*', edgecolors='darkgreen', linewidths=2)
    ax.annotate(f'MINIMO HISTORICO\n{precio_min:.2f}€', 
                xy=(df.loc[min_idx, 'fecha'], precio_min),
                xytext=(20, -40), textcoords="offset points", 
                bbox=dict(boxstyle="round,pad=0.8", facecolor='#28a745', alpha=0.9, edgecolor='darkgreen', linewidth=2),
                arrowprops=dict(arrowstyle="->, head_width=0.4, head_length=0.8", 
                               connectionstyle="arc3,rad=.2", color='darkgreen', lw=2.5),
                fontsize=13, weight='bold', color='white', ha='left')

    # Destacar el punto más alto (MÁXIMO HISTÓRICO)
    max_idx = df['precio_num'].idxmax()
    ax.scatter(df.loc[max_idx, 'fecha'], precio_max, color='#dc3545', 
               s=300, zorder=5, marker='v', edgecolors='darkred', linewidths=2)
    ax.annotate(f'MAXIMO\n{precio_max:.2f}€', 
                xy=(df.loc[max_idx, 'fecha'], precio_max),
                xytext=(20, 40), textcoords="offset points", 
                bbox=dict(boxstyle="round,pad=0.6", facecolor='#dc3545', alpha=0.8, edgecolor='darkred', linewidth=1.5),
                arrowprops=dict(arrowstyle="->, head_width=0.3, head_length=0.6", 
                               connectionstyle="arc3,rad=-.2", color='darkred', lw=2),
                fontsize=11, weight='bold', color='white', ha='left')

    # Destacar el precio actual
    ax.scatter(df['fecha'].iloc[-1], precio_actual, color='#ffc107', 
               s=250, zorder=5, marker='D', edgecolors='#ff8800', linewidths=2)
    
    # Determinar estado del precio actual
    if precio_actual == precio_min:
        estado = "AL MINIMO HISTORICO!"
        color_estado = '#28a745'
    elif precio_actual < precio_promedio:
        estado = "Por debajo del promedio"
        color_estado = '#17a2b8'
    elif precio_actual > precio_promedio:
        diferencia = ((precio_actual - precio_promedio) / precio_promedio) * 100
        estado = f"{diferencia:.1f}% sobre promedio"
        color_estado = '#fd7e14'
    else:
        estado = "En el promedio"
        color_estado = '#6c757d'
    
    ax.annotate(f'PRECIO ACTUAL: {precio_actual:.2f}€\n{estado}', 
                xy=(df['fecha'].iloc[-1], precio_actual),
                xytext=(-120, 30), textcoords="offset points", 
                bbox=dict(boxstyle="round,pad=0.8", facecolor=color_estado, alpha=0.95, edgecolor='black', linewidth=2),
                arrowprops=dict(arrowstyle="->, head_width=0.4, head_length=0.8", 
                               connectionstyle="arc3,rad=.3", color='black', lw=2.5),
                fontsize=12, weight='bold', color='white', ha='center')

    # Configuración de ejes y título
    ax.set_title(f"Evolución de Precio - {nombre.upper().replace('_', ' ')}", 
                 fontsize=22, weight='bold', pad=20, color='#212529')
    ax.set_xlabel("Fecha", fontsize=15, weight='bold', color='#495057')
    ax.set_ylabel("Precio (€)", fontsize=15, weight='bold', color='#495057')

    # Formato de fechas
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(df) // 15)))
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f€'))

    # Grid mejorado
    ax.grid(True, linestyle='--', alpha=0.4, color='#adb5bd', linewidth=0.8)
    ax.set_axisbelow(True)

    # Rotación de etiquetas
    plt.xticks(rotation=45, ha='right', fontsize=11)
    plt.yticks(fontsize=11)

    # Leyenda mejorada
    ax.legend(fontsize=11, loc='upper left', framealpha=0.95, 
              shadow=True, fancybox=True, borderpad=1)

    # Ajustar layout
    plt.tight_layout()

    # Guardar con alta calidad
    plt.savefig(nombre_png, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return nombre_png