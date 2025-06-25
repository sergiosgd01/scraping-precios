from playwright.sync_api import sync_playwright
import pandas as pd
import datetime
import os

def scrape_producto(nombre, url, selector_peso, selector_precio):
    archivo_excel = f"precios_{nombre}.xlsx"
    archivo_csv   = f"precios_{nombre}.csv"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page    = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector('#cookiebar-accept-button', timeout=5000)
            page.click('#cookiebar-accept-button')
        except:
            pass

        page.click(selector_peso)
        page.wait_for_timeout(1000)

        name   = page.locator('h1[itemprop="name"]').inner_text()
        peso   = page.locator(f'{selector_peso} p').inner_text()
        precio = page.locator(selector_precio).inner_text()

        ahora = datetime.datetime.now()
        datos = {
            'fecha':   [ahora],
            'producto':[name],
            'peso':    [peso],
            'precio':  [precio]
        }

        if os.path.exists(archivo_excel):
            df_old      = pd.read_excel(archivo_excel)
            df_new      = pd.DataFrame(datos)
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_combined = pd.DataFrame(datos)

        df_combined.to_excel(archivo_excel, index=False)
        df_combined.to_csv(archivo_csv, index=False)

        browser.close()
        return precio
