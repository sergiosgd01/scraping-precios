from playwright.sync_api import sync_playwright
import pandas as pd
import datetime
import os
import re

def _normalizar_texto(texto):
    return " ".join(texto.replace("\xa0", " ").split()).strip()


def _extraer_precio_numerico(texto_precio):
    texto_limpio = texto_precio.replace("\xa0", " ")
    match = re.search(r"(\d+[\.,]\d+)", texto_limpio)
    if not match:
        raise ValueError(f"No se pudo extraer el precio de: {texto_precio}")
    return float(match.group(1).replace(',', '.'))


def _seleccionar_formato(page, formato_objetivo):
    contenedor = page.locator('#sticky-add-to-cart')
    if contenedor.count() == 0:
        raise ValueError("No se encontró el panel principal de compra")

    candidatos = [
        contenedor.locator('label').filter(has_text=formato_objetivo),
        page.locator('label').filter(has_text=formato_objetivo),
    ]

    for locator in candidatos:
        if locator.count() > 0:
            label = locator.first
            try:
                label.click(timeout=5000)
            except Exception:
                try:
                    label.click(timeout=5000, force=True)
                except Exception:
                    label.evaluate("element => element.click()")

            page.wait_for_timeout(1500)
            return

    raise ValueError(f"No se encontró el formato '{formato_objetivo}'")


def _obtener_formato_seleccionado(page, formato_objetivo):
    seleccionado = page.locator(
        '#sticky-add-to-cart label.border-hsn-blue, #sticky-add-to-cart label.text-hsn-blue'
    )
    if seleccionado.count() > 0:
        return _normalizar_texto(seleccionado.first.inner_text())
    return formato_objetivo


def _obtener_precio_actual(page):
    # En la nueva HSN el precio vigente aparece como '.primary-price' dentro del panel de compra.
    precio_actual = page.locator('#sticky-add-to-cart .primary-price').first
    if precio_actual.count() > 0:
        return _normalizar_texto(precio_actual.inner_text())

    # Fallback si cambia la clase del precio principal.
    fallback = page.locator('#sticky-add-to-cart [id^="product-price-"]').nth(1)
    if fallback.count() > 0:
        return _normalizar_texto(fallback.inner_text())

    raise ValueError("No se pudo localizar el precio actual en el panel de compra")


def scrape_producto(nombre, url, formato_objetivo, etiqueta=None):
    # Crear carpeta 'data' si no existe
    os.makedirs('data', exist_ok=True)
    
    # Rutas dentro de la carpeta 'data'
    archivo_excel = f"data/precios_{nombre}.xlsx"
    archivo_csv   = f"data/precios_{nombre}.csv"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page    = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector('#cookiebar-accept-button', timeout=5000)
            page.click('#cookiebar-accept-button')
        except:
            pass

        page.wait_for_selector('#sticky-add-to-cart', timeout=20000)
        page.wait_for_timeout(1000)
        _seleccionar_formato(page, formato_objetivo)

        name   = _normalizar_texto(page.locator('h1').first.inner_text())
        peso   = _obtener_formato_seleccionado(page, formato_objetivo)
        precio = _obtener_precio_actual(page)

        # Analizar el precio ANTES de añadirlo al histórico
        precio_actual = _extraer_precio_numerico(precio)
        
        # Cargar histórico existente
        if os.path.exists(archivo_excel):
            df_historico = pd.read_excel(archivo_excel)
        else:
            df_historico = pd.DataFrame(columns=['fecha', 'producto', 'peso', 'precio'])
        
        # Analizar con el histórico SIN el precio actual
        analisis = analizar_precio_historico(df_historico, precio_actual, nombre)
        
        # AHORA SÍ agregamos el precio actual
        ahora = datetime.datetime.now()
        datos = {
            'fecha':   [ahora],
            'producto':[name],
            'peso':    [peso],
            'precio':  [precio]
        }
        
        df_new = pd.DataFrame(datos)
        df_combined = pd.concat([df_historico, df_new], ignore_index=True)

        df_combined.to_excel(archivo_excel, index=False)
        df_combined.to_csv(archivo_csv, index=False)

        browser.close()
        
        return {
            'nombre_mostrar': etiqueta or name,
            'peso': peso,
            'precio': precio,
            'precio_numerico': precio_actual,
            'analisis': analisis
        }

def analizar_precio_historico(df, precio_actual, nombre_producto=""):
    """
    Analiza si el precio actual es mínimo histórico, máximo, etc.
    """
    # Si no hay histórico, es el primer registro
    if len(df) == 0:
        return {
            'precio_minimo_historico': precio_actual,
            'precio_maximo_historico': precio_actual,
            'precio_promedio': precio_actual,
            'veces_a_este_precio': 0,
            'es_minimo_historico': True,
            'es_minimo_igualado': False,
            'es_maximo_historico': True,
            'es_maximo_igualado': False,
            'diferencia_vs_minimo': 0.0,
            'diferencia_vs_promedio': 0.0,
            'porcentaje_vs_minimo': 0.0
        }
    
    # Convertir precios a numérico
    df['precio_num'] = df['precio'].str.replace('€', '').str.replace(',', '.').str.strip().astype(float)
    
    # Convertir fecha a solo fecha (sin hora) para agrupar por día
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['fecha_dia'] = df['fecha'].dt.date
    
    # Agrupar por día y tomar el último precio de cada día
    df_por_dia = df.groupby('fecha_dia').agg({
        'precio_num': 'last'
    }).reset_index()
    
    precio_min = df_por_dia['precio_num'].min()
    precio_max = df_por_dia['precio_num'].max()
    precio_promedio = df_por_dia['precio_num'].mean()
    
    # Contar cuántos DÍAS diferentes ha estado a este precio
    veces_a_este_precio = (df_por_dia['precio_num'] == precio_actual).sum()
    
    analisis = {
        'precio_minimo_historico': precio_min,
        'precio_maximo_historico': precio_max,
        'precio_promedio': precio_promedio,
        'veces_a_este_precio': veces_a_este_precio,
        'es_minimo_historico': False,
        'es_minimo_igualado': False,
        'es_maximo_historico': False,
        'es_maximo_igualado': False,
        'diferencia_vs_minimo': precio_actual - precio_min,
        'diferencia_vs_promedio': precio_actual - precio_promedio,
        'porcentaje_vs_minimo': ((precio_actual - precio_min) / precio_min) * 100 if precio_min > 0 else 0
    }
    
    # Determinar el estado del precio
    if precio_actual < precio_min:
        analisis['es_minimo_historico'] = True
    elif precio_actual == precio_min:
        if veces_a_este_precio == 0:
            analisis['es_minimo_historico'] = True
        else:
            analisis['es_minimo_igualado'] = True
    
    if precio_actual > precio_max:
        analisis['es_maximo_historico'] = True
    elif precio_actual == precio_max:
        if veces_a_este_precio == 0:
            analisis['es_maximo_historico'] = True
        else:
            analisis['es_maximo_igualado'] = True
    
    return analisis
