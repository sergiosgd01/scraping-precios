from playwright.sync_api import sync_playwright
import pandas as pd
import datetime
import os
import re
import time
from pathlib import Path
from contextlib import contextmanager


INTERVALO_MINIMO_ENTRE_PAGINAS_MS = 8_000
TIEMPO_MAXIMO_VALIDACION_CLOUDFLARE_MS = 120_000
_ultima_navegacion_hsn = 0.0
_ultima_url_hsn = None

def _normalizar_texto(texto):
    return " ".join(texto.replace("\xa0", " ").split()).strip()


def _extraer_precio_numerico(texto_precio):
    texto_limpio = texto_precio.replace("\xa0", " ")
    match = re.search(r"(\d+[\.,]\d+)", texto_limpio)
    if not match:
        raise ValueError(f"No se pudo extraer el precio de: {texto_precio}")
    return float(match.group(1).replace(',', '.'))


def _seleccionar_formato(page, formato_objetivo):
    # HSN ya no usa el contenedor #sticky-add-to-cart. Los formatos siguen
    # siendo etiquetas que contienen un input radio dentro de la ficha.
    locator = page.locator('label').filter(has_text=formato_objetivo)
    if locator.count() > 0:
        label = locator.first
        try:
            # El input está visualmente oculto por HSN; el clic normal puede
            # terminar en el contenedor sin activar la variante.
            label.click(timeout=5000, force=True)
        except Exception:
            try:
                label.evaluate("element => element.click()")
            except Exception:
                raise ValueError(f"No se pudo seleccionar el formato '{formato_objetivo}'")

        page.wait_for_timeout(1500)
        formato_seleccionado = _obtener_formato_seleccionado(page, formato_objetivo)
        if _normalizar_texto(formato_seleccionado) != _normalizar_texto(formato_objetivo):
            raise ValueError(
                f"HSN no aplicó el formato '{formato_objetivo}'. "
                f"Formato activo: '{formato_seleccionado}'"
            )
        return

    raise ValueError(f"No se encontró el formato '{formato_objetivo}'")


def _obtener_formato_seleccionado(page, formato_objetivo):
    seleccionado = page.locator('input[type="radio"]:checked')
    if seleccionado.count() > 0:
        texto = seleccionado.first.evaluate(
            "element => element.closest('label')?.innerText || ''"
        )
        if texto:
            return _normalizar_texto(texto)
    return formato_objetivo


def _obtener_precio_actual(page):
    # El precio final de la variante activa se renderiza aquí en la ficha actual de HSN.
    precio_actual = page.locator('[id^="product-price-"] .primary-price').first
    if precio_actual.count() > 0:
        return _normalizar_texto(precio_actual.inner_text())

    # Fallback por si HSN elimina el identificador del contenedor del precio.
    fallback = page.locator('.primary-price[x-html*="getFormattedFinalPrice"]').first
    if fallback.count() > 0:
        return _normalizar_texto(fallback.inner_text())

    raise ValueError("No se pudo localizar el precio actual en el panel de compra")


def _es_bloqueo_cloudflare(page, respuesta=None):
    return (
        (respuesta and respuesta.status == 403)
        or 'Attention Required' in page.title()
    )


def _esperar_validacion_cloudflare(page):
    """Mantiene Chrome abierto para que el usuario complete Cloudflare."""
    print(
        "\n[ACCIÓN NECESARIA] HSN ha pedido una verificación de Cloudflare. "
        "Complétala en la ventana de Chrome; el proceso continuará solo.\n",
        flush=True,
    )
    page.bring_to_front()
    inicio = time.monotonic()

    while (time.monotonic() - inicio) * 1000 < TIEMPO_MAXIMO_VALIDACION_CLOUDFLARE_MS:
        try:
            page.locator('[id^="product-price-"] .primary-price').first.wait_for(
                state='visible', timeout=1000
            )
            if not _es_bloqueo_cloudflare(page):
                print("[OK] Verificación completada. Se reanuda la consulta.\n", flush=True)
                return
        except Exception:
            pass

    raise RuntimeError(
        "La verificación de Cloudflare no se completó en dos minutos. "
        "Vuelve a ejecutar el proceso cuando HSN esté accesible."
    )


@contextmanager
def sesion_hsn():
    """Abre una única sesión visible y persistente de Chrome para HSN."""
    perfil_chrome = Path(
        os.getenv('HSN_CHROME_PROFILE', Path.home() / '.hsn-price-scraper-chrome')
    )

    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            str(perfil_chrome),
            channel='chrome',
            headless=False,
            viewport={'width': 1440, 'height': 1000}
        )
        try:
            yield contexto.pages[0] if contexto.pages else contexto.new_page()
        finally:
            contexto.close()


def scrape_producto(nombre, url, formato_objetivo, etiqueta=None, page=None):
    global _ultima_navegacion_hsn, _ultima_url_hsn
    # Crear carpeta 'data' si no existe
    os.makedirs('data', exist_ok=True)
    
    # Rutas dentro de la carpeta 'data'
    archivo_excel = f"data/precios_{nombre}.xlsx"
    archivo_csv   = f"data/precios_{nombre}.csv"

    if page is None:
        # Mantiene compatibilidad para ejecutar un único producto directamente.
        with sesion_hsn() as pagina:
            return scrape_producto(nombre, url, formato_objetivo, etiqueta, pagina)

    # Chromium headless es bloqueado por Cloudflare. Chrome con un perfil
    # persistente conserva la sesión y carga la misma ficha que un usuario.
    espera_restante = INTERVALO_MINIMO_ENTRE_PAGINAS_MS - int(
        (time.monotonic() - _ultima_navegacion_hsn) * 1000
    )
    if espera_restante > 0:
        page.wait_for_timeout(espera_restante)

    # Algunos productos son formatos de la misma ficha. Reutilizarla evita una
    # recarga innecesaria que puede activar Cloudflare; después se selecciona
    # el formato objetivo en la página ya cargada.
    respuesta = None
    if _ultima_url_hsn != url:
        respuesta = page.goto(url, wait_until='domcontentloaded', timeout=30000)
        _ultima_navegacion_hsn = time.monotonic()
        _ultima_url_hsn = url

    if _es_bloqueo_cloudflare(page, respuesta):
        _esperar_validacion_cloudflare(page)

    boton_cookies = page.locator('#cookiebar-accept-button')
    if boton_cookies.count() > 0:
        boton_cookies.first.click(timeout=2000)

    page.wait_for_selector('[id^="product-price-"] .primary-price', timeout=20000)
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
