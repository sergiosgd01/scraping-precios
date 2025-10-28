import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def graficar_precios(nombre_archivo_csv):
    df = pd.read_csv(nombre_archivo_csv, parse_dates=['fecha'])
    df['precio_num'] = df['precio'].str.replace('€', '').str.replace(',', '.').astype(float)
    
    plt.figure(figsize=(12,6))
    sns.lineplot(data=df, x='fecha', y='precio_num', marker='o')
    plt.title(f'Evolución del precio ({nombre_archivo_csv})')
    plt.xlabel('Fecha')
    plt.ylabel('Precio (€)')
    plt.grid(True)
    
    nombre_png = nombre_archivo_csv.replace('.csv', '.png')
    plt.savefig(nombre_png)
    plt.close()

if __name__ == "__main__":
    graficar_precios('files/precios_evowhey.csv')
    graficar_precios('files/precios_creatina.csv')
