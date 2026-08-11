from dotenv import load_dotenv
import os
import logging
import sys
from utils.scraper import scrape_producto, sesion_hsn
from utils.plotter import graficar_precios
from utils.mailer import enviar_email

# Configurar la salida estándar para UTF-8 en Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configurar logging para que vaya tanto a archivo como a consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("log_envio.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)  # También muestra en consola
    ]
)

logging.info("=== Inicio de ejecución del script ===")

try:
    # Cargar variables de entorno
    logging.info("Cargando variables de entorno...")
    load_dotenv()
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASS')
    
    if not EMAIL_USER or not EMAIL_PASS:
        raise ValueError("No se encontraron EMAIL_USER o EMAIL_PASS en el archivo .env")
    
    logging.info(f"Email configurado: {EMAIL_USER}")

    def cargar_emails(path="utils/emails.txt"):
        logging.info(f"Cargando emails desde {path}...")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No se encontró el archivo {path}")
        with open(path, "r", encoding="utf-8") as f:
            emails = [
                line.strip()
                for line in f
                if line.strip() and not line.lstrip().startswith("#")
            ]
        logging.info(f"Se cargaron {len(emails)} destinatarios")
        return emails

    productos = [
        {
            "nombre": "evowhey",
            "url":    "https://www.hsnstore.com/marcas/sport-series/evowhey-protein",
            "formato": "2Kg",
            "etiqueta": "Evowhey Protein (2Kg)",
        },
        {
            "nombre": "proteina_pack",
            "url":    "https://www.hsnstore.com/marcas/sport-series/evowhey-protein",
            "formato": "Pack (5x500g)",
            "etiqueta": "Evowhey Protein Pack (5x500g)",
        },
        {
            "nombre": "creatina",
            "url":    "https://www.hsnstore.com/marcas/raw-series/creatina-monohidrato-en-polvo-200-mesh",
            "formato": "1Kg",
            "etiqueta": "Creatina Monohidrato (200 Mesh) 1Kg",
        },
        {
            "nombre": "creatina_500",
            "url":    "https://www.hsnstore.com/marcas/raw-series/creatina-monohidrato-ultrafina-en-polvo-500-mesh",
            "formato": "500g",
            "etiqueta": "Creatina Monohidrato Ultrafina (500 Mesh) 500g",
        }
    ]

    logging.info("Cargando lista de emails...")
    destinatarios = cargar_emails()

    precios = {}
    grafs   = {}

    logging.info("Iniciando scraping de productos...")
    # Reutilizar el mismo Chrome para reducir bloqueos de Cloudflare.
    with sesion_hsn() as page:
        for p in productos:
            logging.info(f"Scrapeando {p['nombre']}...")
            try:
                resultado = scrape_producto(
                    nombre=p["nombre"],
                    url=p["url"],
                    formato_objetivo=p["formato"],
                    etiqueta=p.get("etiqueta"),
                    page=page
                )
                precios[p["nombre"]] = resultado
                logging.info(f"[OK] {p['nombre']}: {resultado['precio']}")

                logging.info(f"Generando grafica para {p['nombre']}...")
                grafs[p["nombre"]] = graficar_precios(p["nombre"])
                logging.info(f"[OK] Grafica generada: {grafs[p['nombre']]}")
            except Exception as e:
                logging.error(f"[ERROR] Error en {p['nombre']}: {str(e)}", exc_info=True)
                raise
    
    logging.info("Enviando correo...")
    enviar_email(
        remitente=EMAIL_USER,
        clave=EMAIL_PASS,
        destinatario=destinatarios,
        datos_productos=precios,
        imagenes=grafs
    )
    logging.info("Correo enviado correctamente [OK]")

except FileNotFoundError as e:
    logging.error(f"Archivo no encontrado: {e}", exc_info=True)
    print(f"\n[ERROR] {e}")
    sys.exit(1)
    
except ValueError as e:
    logging.error(f"Error de configuracion: {e}", exc_info=True)
    print(f"\n[ERROR] {e}")
    sys.exit(1)
    
except Exception as e:
    logging.error(f"Error general: {e}", exc_info=True)
    print(f"\n[ERROR INESPERADO] {e}")
    print("\nRevisa log_envio.txt para mas detalles")
    sys.exit(1)

finally:
    logging.info("=== Fin de ejecucion ===\n")
    
print("\n[OK] Script completado exitosamente")
