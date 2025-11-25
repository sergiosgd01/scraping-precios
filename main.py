# main.py
from dotenv import load_dotenv
import os
import datetime
import logging
from utils.scraper import scrape_producto
from utils.plotter import graficar_precios
from utils.mailer import enviar_email

# Configurar logging
LOG_PATH = "log_envio.txt"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logging.info("=== Inicio de ejecución del script ===")

# Cargar variables de entorno
load_dotenv()
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')

def cargar_emails(path="utils/emails.txt"):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

try:
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
        },
        {
            "nombre": "proteina_pack",
            "url":    "https://www.hsnstore.com/marcas/sport-series/evowhey-protein",
            "selector_peso":   "#input5520_16688",
            "selector_precio": "#product-price-16688",
        }
    ]

    logging.info("Cargando lista de emails...")
    destinatarios = cargar_emails()
    logging.info(f"Destinatarios cargados: {destinatarios}")

    precios = {}
    grafs   = {}

    logging.info("Iniciando scraping de productos...")
    for p in productos:
        logging.info(f"Scrapeando {p['nombre']}...")
        resultado = scrape_producto(
            nombre=p["nombre"],
            url=p["url"],
            selector_peso=p["selector_peso"],
            selector_precio=p["selector_precio"]
        )
        precios[p["nombre"]] = resultado
        grafs[p["nombre"]]   = graficar_precios(p["nombre"])
    logging.info(f"Precios obtenidos: {[(k, v['precio']) for k, v in precios.items()]}")

    logging.info("Enviando correo...")
    enviar_email(
        remitente=EMAIL_USER,
        clave=EMAIL_PASS,
        destinatario=destinatarios,
        datos_productos={
            'creatina': precios["creatina"],
            'evowhey': precios["evowhey"],
            'proteina_pack': precios["proteina_pack"]
        },
        imagenes={
            'creatina': grafs["creatina"],
            'evowhey': grafs["evowhey"],
            'proteina_pack': grafs["proteina_pack"]
        }
    )
    logging.info("Correo enviado correctamente ✅")

except Exception as e:
    logging.error(f"Error general: {e}", exc_info=True)

logging.info("=== Fin de ejecución ===\n")
