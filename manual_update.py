"""Actualización manual de precios HSN desde una página local."""

import datetime
import base64
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

from utils.mailer import enviar_email, generar_reporte_html
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
        "clave": "magnesio_bisglicinato_polvo",
        "etiqueta": "Bisglicinato de magnesio en polvo",
        "formato": "150g",
        "url": "https://www.hsnstore.com/marcas/raw-series/bisglicinato-de-magnesio-en-polvo",
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


class ErrorFormulario(ValueError):
    def __init__(self, errores):
        self.errores = errores
        super().__init__("Revisa los campos marcados en rojo.")


def _validar_valores(valores):
    """Valida todo el formulario antes de escribir ningún archivo."""
    errores = {}
    for producto in PRODUCTOS:
        clave = producto["clave"]
        if valores.get(f"agotado_{clave}") == "on":
            continue

        valor = valores.get(clave, "").strip()
        if not valor:
            errores[clave] = "Introduce un precio o marca Agotado."
            continue
        try:
            _precio_numerico(valor)
        except ValueError:
            errores[clave] = "Introduce un precio válido, por ejemplo 54,99."

    if errores:
        raise ErrorFormulario(errores)


def actualizar_y_enviar(valores):
    _validar_valores(valores)
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
        valor = valores[producto["clave"]].strip()
        datos[producto["clave"]] = _guardar_producto(producto, valor)
        imagenes[producto["clave"]] = graficar_precios(producto["clave"])

    enviar_email(remitente, clave, _destinatarios(), datos, imagenes)
    _marcador_hoy().touch()
    return datos, imagenes


def _imagenes_incorporadas(imagenes):
    """Convierte las gráficas en datos incrustados para verlas tras cerrar el servidor."""
    return {
        clave: "data:image/png;base64," + base64.b64encode(Path(ruta).read_bytes()).decode()
        for clave, ruta in imagenes.items()
    }


def _pagina(mensaje="", error="", valores=None, errores=None):
    valores = valores or {}
    errores = errores or {}
    filas = ""
    for p in PRODUCTOS:
        ultimo = _ultimo_precio(p["clave"])
        ultimo_numerico = _ultimo_precio_numerico(p["clave"])
        ultimo_atributo = "" if ultimo_numerico is None else str(ultimo_numerico)
        valor = html.escape(valores.get(p["clave"], ""), quote=True)
        agotado = valores.get(f'agotado_{p["clave"]}') == "on"
        error_campo = errores.get(p["clave"], "")
        clase_error = " campo-error" if error_campo else ""
        estado_agotado = " checked" if agotado else ""
        deshabilitado = " disabled" if agotado else ""
        aviso_campo = (
            f'<small class="error campo-mensaje">{html.escape(error_campo)}</small>'
            if error_campo
            else '<small class="error campo-mensaje" hidden></small>'
        )
        filas += f'''<section class="producto"><label for="precio_{p["clave"]}"><strong>{html.escape(p["etiqueta"])}</strong> · {html.escape(p["formato"])}</label>
        <a class="link" href="{html.escape(p["url"])}" target="_blank" rel="noopener">Abrir este producto en HSN ↗</a>
        <small>Último registrado: {html.escape(ultimo)} <span id="cambio_{p["clave"]}"></span></small>
        <input id="precio_{p["clave"]}" class="precio{clase_error}" name="{p["clave"]}" value="{valor}" inputmode="decimal" placeholder="Ej.: 54,99" data-ultimo="{ultimo_atributo}" data-minimo="{p["minimo_razonable"]}" data-maximo="{p["maximo_razonable"]}" aria-invalid="{'true' if error_campo else 'false'}"{deshabilitado}>
        {aviso_campo}
        <button class="usar" type="button" data-clave="{p["clave"]}" data-ultimo="{ultimo_atributo}"{deshabilitado}>Usar último precio</button>
        <label class="agotado"><input type="checkbox" name="agotado_{p["clave"]}"{estado_agotado}> Agotado / sin precio hoy</label></section>'''
    aviso = f'<p class="ok">{html.escape(mensaje)}</p>' if mensaje else ""
    aviso += f'<p class="error">{html.escape(error)}</p>' if error else ""
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Actualizar precios HSN</title>
    <style>body{{font:16px -apple-system,BlinkMacSystemFont,sans-serif;background:#f3f4f6;margin:0;color:#111827}}main{{max-width:580px;margin:45px auto;background:#fff;padding:30px;border-radius:14px;box-shadow:0 8px 28px #0001}}h1{{margin-top:0}}.producto{{margin:18px 0}}.producto>label:first-child{{display:block}}small{{display:block;color:#6b7280;margin:4px 0}}.link{{display:inline-block;margin:8px 0;color:#c2410c;font-size:14px;font-weight:700}}input{{box-sizing:border-box;width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px;font-size:17px}}input:disabled{{background:#f1f5f9;color:#94a3b8;cursor:not-allowed}}input.campo-error{{border:2px solid #dc2626;background:#fef2f2}}button{{background:#ea580c;color:white;border:0;border-radius:8px;padding:12px 16px;font-size:16px;font-weight:700;cursor:pointer;margin:8px 8px 0 0}}button:disabled{{cursor:not-allowed;opacity:.55}}button.usar{{background:#e2e8f0;color:#334155;font-size:13px;padding:7px 10px}}.agotado{{display:block;margin-top:8px;color:#475569;font-size:14px}}.agotado input{{width:auto;padding:0}}.ok{{color:#166534}}.error{{color:#b91c1c;font-weight:600}}.campo-mensaje{{margin-top:6px}}.cargando{{display:none;position:fixed;inset:0;background:#111827d9;z-index:10;align-items:center;justify-content:center;padding:24px;text-align:center;color:#fff}}.cargando.visible{{display:flex}}.cargando div{{max-width:380px}}.cargando span{{display:block;width:42px;height:42px;border:5px solid #ffffff55;border-top-color:#fff;border-radius:50%;margin:0 auto 18px;animation:girar .8s linear infinite}}.cargando p{{color:#cbd5e1;margin:10px 0 0}}@keyframes girar{{to{{transform:rotate(360deg)}}}}}}</style>
    <main><h1>Precios HSN de hoy</h1>{aviso}
    <form method="post" id="formulario">{filas}<button type="submit">Guardar y enviar correo</button></form></main>
    <div class="cargando" id="cargando" aria-live="polite"><div><span></span><strong>Guardando precios y enviando el correo…</strong><p>Generando el análisis y las gráficas. Puede tardar unos segundos.</p></div></div>
    <script>
    function numero(valor) {{ return Number(valor.replace(',', '.')); }}
    function actualizarCambio(input) {{
      const ultimo = Number(input.dataset.ultimo), salida = document.querySelector('#cambio_' + input.name), valor = numero(input.value);
      if (!ultimo || !input.value || Number.isNaN(valor)) {{ salida.textContent = ''; return; }}
      const porcentaje = ((valor - ultimo) / ultimo) * 100;
      salida.textContent = `· ${{porcentaje >= 0 ? '+' : ''}}${{porcentaje.toFixed(1).replace('.', ',')}}% vs último`;
    }}
    function marcarError(input, mensaje) {{
      input.classList.toggle('campo-error', Boolean(mensaje));
      input.setAttribute('aria-invalid', Boolean(mensaje));
      const salida = input.parentElement.querySelector('.campo-mensaje');
      salida.textContent = mensaje || '';
      salida.hidden = !mensaje;
    }}
    document.querySelectorAll('input[inputmode="decimal"]').forEach(input => {{
      actualizarCambio(input);
      input.addEventListener('input', () => {{ marcarError(input, ''); actualizarCambio(input); }});
    }});
    document.querySelectorAll('.usar').forEach(boton => boton.addEventListener('click', () => {{
      const input = document.querySelector('#precio_' + boton.dataset.clave);
      const ultimo = Number(boton.dataset.ultimo);
      if (!Number.isFinite(ultimo)) return;
      input.value = ultimo.toFixed(2).replace('.', ','); marcarError(input, ''); actualizarCambio(input); input.focus();
    }}));
    document.querySelectorAll('.agotado input').forEach(casilla => {{
      const clave = casilla.name.replace('agotado_', ''), input = document.querySelector('#precio_' + clave), boton = document.querySelector('.usar[data-clave="' + clave + '"]');
      const actualizarAgotado = () => {{ input.disabled = casilla.checked; boton.disabled = casilla.checked; if (casilla.checked) marcarError(input, ''); }};
      casilla.addEventListener('change', actualizarAgotado); actualizarAgotado();
    }});
    document.querySelector('#formulario').addEventListener('submit', evento => {{
      const avisos = [];
      document.querySelectorAll('input[inputmode="decimal"]').forEach(input => {{
        if (input.disabled) return;
        const valor = numero(input.value), ultimo = Number(input.dataset.ultimo);
        if (!input.value.trim()) {{ marcarError(input, 'Introduce un precio o marca Agotado.'); return; }}
        if (Number.isNaN(valor)) {{ marcarError(input, 'Introduce un precio válido, por ejemplo 54,99.'); return; }}
        marcarError(input, '');
        if (valor < Number(input.dataset.minimo) || valor > Number(input.dataset.maximo)) avisos.push(`${{input.name}}: ${{input.value}} € parece un precio fuera de rango.`);
        else if (ultimo && (valor < ultimo * 0.5 || valor > ultimo * 1.5)) avisos.push(`${{input.name}}: cambia más del 50% respecto al último precio.`);
      }});
      const primerError = document.querySelector('.campo-error');
      if (primerError) {{ evento.preventDefault(); primerError.focus(); return; }}
      if (avisos.length && !window.confirm(`Revisa estos precios:\\n\\n${{avisos.join('\\n')}}\\n\\n¿Enviar de todos modos?`)) {{ evento.preventDefault(); return; }}
      document.querySelector('#cargando').classList.add('visible');
      document.querySelector('#formulario button[type="submit"]').disabled = true;
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
            datos, imagenes = actualizar_y_enviar(valores)
            self._responder(
                generar_reporte_html(
                    datos,
                    _imagenes_incorporadas(imagenes),
                    "✓ Precios guardados y correo enviado correctamente.",
                )
            )
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        except ErrorFormulario as exc:
            self._responder(_pagina(error=str(exc), valores=valores, errores=exc.errores))
        except Exception as exc:
            self._responder(_pagina(error=str(exc), valores=valores))

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
