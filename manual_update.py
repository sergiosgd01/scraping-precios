"""Actualización manual de precios HSN desde una página local."""

import datetime
import html
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib
import pandas as pd
from dotenv import load_dotenv

matplotlib.use("Agg")

from utils.mailer import enviar_email
from utils.plotter import graficar_precios
from utils.scraper import analizar_precio_historico


HOST = "127.0.0.1"
PRODUCTOS = [
    {
        "clave": "evowhey",
        "etiqueta": "Evowhey Protein",
        "formato": "2Kg",
        "url": "https://www.hsnstore.com/marcas/sport-series/evowhey-protein",
        "minimo_razonable": 20,
        "maximo_razonable": 150,
    },
    {
        "clave": "proteina_pack",
        "etiqueta": "Evowhey Protein Pack",
        "formato": "Pack (5x500g)",
        "url": "https://www.hsnstore.com/marcas/sport-series/evowhey-protein",
        "minimo_razonable": 40,
        "maximo_razonable": 250,
    },
    {
        "clave": "creatina",
        "etiqueta": "Creatina Monohidrato",
        "formato": "1Kg",
        "url": "https://www.hsnstore.com/marcas/raw-series/creatina-monohidrato-en-polvo-200-mesh",
        "minimo_razonable": 10,
        "maximo_razonable": 120,
    },
    {
        "clave": "creatina_500",
        "etiqueta": "Creatina Monohidrato Ultrafina",
        "formato": "500g",
        "url": "https://www.hsnstore.com/marcas/raw-series/creatina-monohidrato-ultrafina-en-polvo-500-mesh",
        "minimo_razonable": 8,
        "maximo_razonable": 80,
    },
    {
        "clave": "magnesio_bisglicinato",
        "etiqueta": "Bisglicinato de magnesio",
        "formato": "100mg de magnesio",
        "url": "https://www.hsnstore.com/marcas/essential-series/bisglicinato-de-magnesio-100mg-magnesio",
        "minimo_razonable": 4,
        "maximo_razonable": 30,
    },
]


def _precio_numerico(texto):
    match = re.search(r"\d+(?:[.,]\d{1,2})?", texto.replace(" ", ""))
    if not match:
        raise ValueError("Introduce un precio válido, por ejemplo 54,99")
    return float(match.group(0).replace(",", "."))


def _formato_precio(valor):
    return f"{valor:.2f} €".replace(".", ",")


def _ruta_excel(clave):
    return f"data/precios_{clave}.xlsx"


def _ruta_csv(clave):
    return f"data/precios_{clave}.csv"


def _historico(clave):
    ruta = _ruta_excel(clave)
    if os.path.exists(ruta):
        return pd.read_excel(ruta)
    return pd.DataFrame(columns=["fecha", "producto", "peso", "precio"])


def _ultimo_precio(clave):
    historico = _historico(clave)
    if historico.empty:
        return "Sin histórico"
    return str(historico.iloc[-1]["precio"])


def _ultimo_precio_numerico(clave):
    try:
        return _precio_numerico(_ultimo_precio(clave))
    except ValueError:
        return None


def _marcador_hoy():
    return Path("data") / f"actualizacion_manual_{datetime.date.today():%Y-%m-%d}.ok"


def _guardar_producto(producto, precio_texto):
    precio = _precio_numerico(precio_texto)
    historico = _historico(producto["clave"])
    hoy = datetime.date.today()

    if not historico.empty:
        historico["fecha"] = pd.to_datetime(historico["fecha"])
        historico_sin_hoy = historico[historico["fecha"].dt.date != hoy].copy()
    else:
        historico_sin_hoy = historico

    analisis = analizar_precio_historico(
        historico_sin_hoy.copy(), precio, producto["clave"]
    )
    nuevo = pd.DataFrame(
        {
            "fecha": [datetime.datetime.now()],
            "producto": [producto["etiqueta"]],
            "peso": [producto["formato"]],
            "precio": [_formato_precio(precio)],
        }
    )
    actualizado = pd.concat([historico_sin_hoy, nuevo], ignore_index=True)
    os.makedirs("data", exist_ok=True)
    actualizado.to_excel(_ruta_excel(producto["clave"]), index=False)
    actualizado.to_csv(_ruta_csv(producto["clave"]), index=False)

    return {
        "nombre_mostrar": f'{producto["etiqueta"]} ({producto["formato"]})',
        "peso": producto["formato"],
        "precio": _formato_precio(precio),
        "precio_numerico": precio,
        "analisis": analisis,
    }


def _marcar_agotado(producto):
    """Quita un posible precio de hoy: agotado no debe contar como precio."""
    historico = _historico(producto["clave"])
    if not historico.empty:
        historico["fecha"] = pd.to_datetime(historico["fecha"])
        historico = historico[historico["fecha"].dt.date != datetime.date.today()]
        historico.to_excel(_ruta_excel(producto["clave"]), index=False)
        historico.to_csv(_ruta_csv(producto["clave"]), index=False)

    return {
        "nombre_mostrar": f'{producto["etiqueta"]} ({producto["formato"]})',
        "peso": producto["formato"],
        "precio": "Agotado",
        "agotado": True,
    }


def _destinatarios():
    with open("utils/emails.txt", encoding="utf-8") as archivo:
        return [
            linea.strip()
            for linea in archivo
            if linea.strip() and not linea.lstrip().startswith("#")
        ]


def actualizar_y_enviar(valores):
    load_dotenv()
    remitente = os.getenv("EMAIL_USER")
    clave = os.getenv("EMAIL_PASS")
    if not remitente or not clave:
        raise ValueError("Faltan EMAIL_USER o EMAIL_PASS en el archivo .env")

    datos, imagenes = {}, {}
    for producto in PRODUCTOS:
        if valores.get(f'agotado_{producto["clave"]}') == "on":
            datos[producto["clave"]] = _marcar_agotado(producto)
            continue
        valor = valores.get(producto["clave"], "").strip()
        if not valor:
            raise ValueError(
                f'Falta el precio de {producto["etiqueta"]} o marca “Agotado”.'
            )
        datos[producto["clave"]] = _guardar_producto(producto, valor)
        imagenes[producto["clave"]] = graficar_precios(producto["clave"])

    enviar_email(remitente, clave, _destinatarios(), datos, imagenes)
    _marcador_hoy().touch()
    return datos


def _pagina(mensaje="", error=""):
    filas = ""
    for p in PRODUCTOS:
        ultimo = _ultimo_precio(p["clave"])
        ultimo_numerico = _ultimo_precio_numerico(p["clave"])
        ultimo_atributo = "" if ultimo_numerico is None else str(ultimo_numerico)
        filas += f'''<label><strong>{html.escape(p["etiqueta"])}</strong> · {html.escape(p["formato"])}
        <a class="link" href="{html.escape(p["url"])}" target="_blank" rel="noopener">Abrir este producto en HSN ↗</a>
        <small>Último registrado: {html.escape(ultimo)} <span id="cambio_{p["clave"]}"></span></small>
        <input id="precio_{p["clave"]}" name="{p["clave"]}" inputmode="decimal" placeholder="Ej.: 54,99" data-ultimo="{ultimo_atributo}" data-minimo="{p["minimo_razonable"]}" data-maximo="{p["maximo_razonable"]}">
        <button class="usar" type="button" data-clave="{p["clave"]}" data-ultimo="{ultimo_atributo}">Usar último precio</button>
        <span class="agotado"><input type="checkbox" name="agotado_{p["clave"]}"> Agotado / sin precio hoy</span></label>'''
    aviso = f'<p class="ok">{html.escape(mensaje)}</p>' if mensaje else ""
    aviso += f'<p class="error">{html.escape(error)}</p>' if error else ""
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Actualizar precios HSN</title>
    <style>body{{font:16px -apple-system,BlinkMacSystemFont,sans-serif;background:#f3f4f6;margin:0;color:#111827}}main{{max-width:580px;margin:45px auto;background:#fff;padding:30px;border-radius:14px;box-shadow:0 8px 28px #0001}}h1{{margin-top:0}}label{{display:block;margin:18px 0}}small{{display:block;color:#6b7280;margin:4px 0}}.link{{display:inline-block;margin:8px 0;color:#c2410c;font-size:14px;font-weight:700}}input{{box-sizing:border-box;width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px;font-size:17px}}button{{background:#ea580c;color:white;border:0;border-radius:8px;padding:12px 16px;font-size:16px;font-weight:700;cursor:pointer;margin:8px 8px 0 0}}button.usar{{background:#e2e8f0;color:#334155;font-size:13px;padding:7px 10px}}.agotado{{display:block;margin-top:8px;color:#475569;font-size:14px}}.agotado input{{width:auto;padding:0}}.ok{{color:#166534}}.error{{color:#b91c1c;font-weight:600}}</style>
    <main><h1>Precios HSN de hoy</h1><p>Cada precio tiene su enlace directo a HSN. No necesitas buscar ningún producto.</p>{aviso}
    <form method="post" id="formulario">{filas}<button type="submit">Guardar y enviar correo</button></form></main>
    <script>
    function numero(valor) {{ return Number(valor.replace(',', '.')); }}
    function actualizarCambio(input) {{
      const ultimo = Number(input.dataset.ultimo), salida = document.querySelector('#cambio_' + input.name), valor = numero(input.value);
      if (!ultimo || !input.value || Number.isNaN(valor)) {{ salida.textContent = ''; return; }}
      const porcentaje = ((valor - ultimo) / ultimo) * 100;
      salida.textContent = `· ${{porcentaje >= 0 ? '+' : ''}}${{porcentaje.toFixed(1).replace('.', ',')}}% vs último`;
    }}
    document.querySelectorAll('input[inputmode="decimal"]').forEach(input => input.addEventListener('input', () => actualizarCambio(input)));
    document.querySelectorAll('.usar').forEach(boton => boton.addEventListener('click', () => {{
      const input = document.querySelector('#precio_' + boton.dataset.clave); if (!boton.dataset.ultimo) return;
      input.value = Number(boton.dataset.ultimo).toFixed(2).replace('.', ','); actualizarCambio(input);
    }}));
    document.querySelector('#formulario').addEventListener('submit', evento => {{
      const avisos = [];
      document.querySelectorAll('input[inputmode="decimal"]').forEach(input => {{
        const valor = numero(input.value), ultimo = Number(input.dataset.ultimo);
        if (!input.value || Number.isNaN(valor)) return;
        if (valor < Number(input.dataset.minimo) || valor > Number(input.dataset.maximo)) avisos.push(`${{input.name}}: ${{input.value}} € parece un precio fuera de rango.`);
        else if (ultimo && (valor < ultimo * 0.5 || valor > ultimo * 1.5)) avisos.push(`${{input.name}}: cambia más del 50% respecto al último precio.`);
      }});
      if (avisos.length && !window.confirm(`Revisa estos precios:\n\n${{avisos.join('\n')}}\n\n¿Enviar de todos modos?`)) evento.preventDefault();
    }});
    </script></html>'''


class Aplicacion(BaseHTTPRequestHandler):
    def do_GET(self):
        self._responder(_pagina())

    def do_POST(self):
        longitud = int(self.headers.get("Content-Length", 0))
        valores = {
            clave: items[0]
            for clave, items in parse_qs(self.rfile.read(longitud).decode()).items()
        }
        try:
            actualizar_y_enviar(valores)
            self._responder(_pagina("Precios guardados y correo enviado correctamente."))
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        except Exception as exc:
            self._responder(_pagina(error=str(exc)))

    def _responder(self, contenido):
        datos = contenido.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, formato, *args):
        return


if __name__ == "__main__":
    servidor = ThreadingHTTPServer((HOST, 0), Aplicacion)
    puerto = servidor.server_address[1]
    url = f"http://{HOST}:{puerto}"
    print(f"Abriendo {url}. Pulsa Ctrl+C en esta terminal para cerrar.")
    subprocess.Popen(["open", "-a", "Google Chrome", url])
    servidor.serve_forever()
