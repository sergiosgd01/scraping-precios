from playwright.sync_api import sync_playwright
import pandas as pd
import datetime
import os

def scrape_producto(url, selector_peso, selector_precio, archivo_excel, archivo_csv):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        # Aceptar cookies
        page.wait_for_selector('#cookiebar-accept-button')
        page.click('#cookiebar-accept-button')

        # Seleccionar el peso deseado
        page.click(selector_peso)

        # Esperar actualización
        page.wait_for_timeout(1000)

        # Extraer datos
        product_name = page.locator('h1[itemprop="name"]').inner_text()
        product_weight = page.locator(f'{selector_peso} p').inner_text()
        product_price = page.locator(selector_precio).inner_text()

        print(f"Producto: {product_name}, Peso: {product_weight}, Precio: {product_price}")

        # Preparar datos para guardar
        fecha_hora = datetime.datetime.now()
        datos = {
            'fecha': [fecha_hora],
            'producto': [product_name],
            'peso': [product_weight],
            'precio': [product_price]
        }

        # Leer archivo existente o crear nuevo DataFrame
        if os.path.exists(archivo_excel):
            df_existente = pd.read_excel(archivo_excel)
            df_nuevo = pd.DataFrame(datos)
            df_combinado = pd.concat([df_existente, df_nuevo], ignore_index=True)
        else:
            df_combinado = pd.DataFrame(datos)

        # Guardar Excel y CSV
        df_combinado.to_excel(archivo_excel, index=False)
        df_combinado.to_csv(archivo_csv, index=False)

        browser.close()

# Scrapeamos el primer producto
scrape_producto(
    url="https://www.hsnstore.com/marcas/sport-series/evowhey-protein",
    selector_peso="#input3486_16688",
    selector_precio="#product-price-16688",
    archivo_excel="precios_evowhey.xlsx",
    archivo_csv="precios_evowhey.csv"
)

# Scrapeamos el segundo producto
scrape_producto(
    url="https://www.hsnstore.com/marcas/raw-series/creatina-monohidrato-en-polvo",
    selector_peso="#input3485_10120",
    selector_precio="#product-price-10120",
    archivo_excel="precios_creatina.xlsx",
    archivo_csv="precios_creatina.csv"
)
