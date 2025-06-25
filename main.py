# main.py
from dotenv import load_dotenv
import os
from utils.scraper import scrape_producto
from utils.plotter import graficar_precios
from utils.mailer import enviar_email
import datetime

# Cargar variables de entorno
load_dotenv()
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')

if __name__ == "__main__":
    productos = [
        {
            "nombre": "evowhey",
            "url":    "https://www.hsnstore.com/marcas/sport-series/evowhey-protein",
            "selector_peso":   "#input3486_16688",
            "selector_precio": "#product-price-16688",
        },
        {
            "nombre": "creatina",
            "url":    "https://www.hsnstore.com/marcas/raw-series/creatina-monohidrato-en-polvo",
            "selector_peso":   "#input3485_10120",
            "selector_precio": "#product-price-10120",
        }
    ]

    precios = {}
    grafs   = {}
    for p in productos:
        pre = scrape_producto(
            nombre=p["nombre"],
            url=p["url"],
            selector_peso=p["selector_peso"],
            selector_precio=p["selector_precio"]
        )
        precios[p["nombre"]] = pre
        grafs[p["nombre"]]   = graficar_precios(p["nombre"])

    enviar_email(
        remitente=EMAIL_USER,
        clave=EMAIL_PASS,
        destinatario=[
            "sergiosgd2001@gmail.com",
            "fjmr.10messi@gmail.com"
        ],
        pre_crea = precios["creatina"],
        pre_prot = precios["evowhey"],
        img_crea = grafs["creatina"],
        img_prot = grafs["evowhey"]
    )
