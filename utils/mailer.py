import csv
import datetime
import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


PRODUCTOS = {
    "creatina": {
        "nombre": "Creatina monohidrato",
        "detalle": "1Kg",
        "color": "#2563eb",
    },
    "evowhey": {
        "nombre": "Evowhey Protein",
        "detalle": "2Kg",
        "color": "#16a34a",
    },
    "proteina_pack": {
        "nombre": "Evowhey Protein Pack",
        "detalle": "Pack 5x500g",
        "color": "#9333ea",
    },
}


def _nombre_producto(clave):
    producto = PRODUCTOS.get(clave, {})
    nombre = producto.get("nombre", clave.replace("_", " ").title())
    detalle = producto.get("detalle", "")
    return f"{nombre} · {detalle}" if detalle else nombre


def _euros(valor):
    return f"{valor:.2f}€".replace(".", ",")


def _porcentaje(valor):
    return f"{valor:+.1f}%".replace(".", ",")


def _estado_precio(datos):
    analisis = datos["analisis"]
    precio_numerico = datos["precio_numerico"]
    promedio = analisis["precio_promedio"]

    if analisis["es_minimo_historico"]:
        return {
            "titulo": "Mínimo histórico",
            "texto": "Nunca se había registrado tan barato en tu histórico.",
            "color": "#15803d",
            "fondo": "#dcfce7",
            "borde": "#86efac",
        }
    if analisis["es_minimo_igualado"]:
        dias = analisis["veces_a_este_precio"]
        etiqueta = "día" if dias == 1 else "días"
        return {
            "titulo": "Mínimo igualado",
            "texto": f"Ya estuvo {dias} {etiqueta} a este precio.",
            "color": "#0369a1",
            "fondo": "#e0f2fe",
            "borde": "#7dd3fc",
        }
    if precio_numerico < promedio:
        ahorro = ((promedio - precio_numerico) / promedio) * 100 if promedio else 0
        return {
            "titulo": "Por debajo del promedio",
            "texto": f"{abs(ahorro):.1f}% más barato que su media histórica.".replace(".", ","),
            "color": "#0f766e",
            "fondo": "#ccfbf1",
            "borde": "#5eead4",
        }
    if precio_numerico > promedio:
        subida = ((precio_numerico - promedio) / promedio) * 100 if promedio else 0
        return {
            "titulo": "Por encima del promedio",
            "texto": f"{subida:.1f}% por encima de su media histórica.".replace(".", ","),
            "color": "#b45309",
            "fondo": "#fef3c7",
            "borde": "#fcd34d",
        }
    return {
        "titulo": "En el promedio",
        "texto": "El precio actual coincide con su media histórica.",
        "color": "#475569",
        "fondo": "#f1f5f9",
        "borde": "#cbd5e1",
    }


def _leer_historial_reciente(clave_producto, limite=6):
    ruta = f"data/precios_{clave_producto}.csv"
    if not os.path.exists(ruta):
        return []

    with open(ruta, newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))

    historial_por_dia = {}
    for fila in filas:
        fecha_raw = fila.get("fecha", "")
        if not fecha_raw:
            continue
        dia = fecha_raw.split(" ")[0]
        historial_por_dia[dia] = {
            "fecha": dia,
            "precio": fila.get("precio", "-"),
            "peso": fila.get("peso", ""),
        }

    return list(historial_por_dia.values())[-limite:]


def _generar_resumen_productos(datos_productos):
    filas = ""
    for clave, datos in datos_productos.items():
        analisis = datos["analisis"]
        estado = _estado_precio(datos)
        filas += f"""
        <tr>
            <td style="padding: 14px 12px; border-bottom: 1px solid #e5e7eb;">
                <div style="font-size: 14px; font-weight: 700; color: #111827;">{_nombre_producto(clave)}</div>
                <div style="font-size: 12px; color: #6b7280; margin-top: 3px;">{estado["titulo"]}</div>
            </td>
            <td style="padding: 14px 12px; border-bottom: 1px solid #e5e7eb; text-align: right; font-size: 20px; font-weight: 800; color: #111827;">{datos["precio"]}</td>
            <td style="padding: 14px 12px; border-bottom: 1px solid #e5e7eb; text-align: right; color: #374151;">{_euros(analisis["precio_minimo_historico"])}</td>
            <td style="padding: 14px 12px; border-bottom: 1px solid #e5e7eb; text-align: right; color: #374151;">{_euros(analisis["precio_promedio"])}</td>
            <td style="padding: 14px 12px; border-bottom: 1px solid #e5e7eb; text-align: right; color: {estado["color"]}; font-weight: 700;">{_porcentaje(analisis["diferencia_vs_promedio"] / analisis["precio_promedio"] * 100 if analisis["precio_promedio"] else 0)}</td>
        </tr>
        """

    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;">
        <tr style="background: #f8fafc;">
            <th align="left" style="padding: 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #64748b;">Producto</th>
            <th align="right" style="padding: 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #64748b;">Hoy</th>
            <th align="right" style="padding: 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #64748b;">Mínimo</th>
            <th align="right" style="padding: 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #64748b;">Media</th>
            <th align="right" style="padding: 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #64748b;">Vs media</th>
        </tr>
        {filas}
    </table>
    """


def generar_alerta_precio(nombre, datos):
    """Genera una tarjeta de producto con precio actual, estado e histórico."""
    analisis = datos["analisis"]
    estado = _estado_precio(datos)
    color_producto = PRODUCTOS.get(nombre, {}).get("color", "#2563eb")
    historial = _leer_historial_reciente(nombre)

    filas_historial = ""
    for item in historial:
        fecha = datetime.date.fromisoformat(item["fecha"]).strftime("%d/%m/%Y")
        filas_historial += f"""
        <tr>
            <td style="padding: 8px 0; color: #64748b; font-size: 13px;">{fecha}</td>
            <td style="padding: 8px 0; color: #111827; font-size: 13px; font-weight: 700; text-align: right;">{item["precio"]}</td>
        </tr>
        """

    if not filas_historial:
        filas_historial = """
        <tr>
            <td colspan="2" style="padding: 8px 0; color: #64748b; font-size: 13px;">Sin histórico disponible todavía.</td>
        </tr>
        """

    return f"""
    <div style="background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; margin: 18px 0; overflow: hidden;">
        <div style="height: 5px; background: {color_producto};"></div>
        <div style="padding: 22px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="vertical-align: top;">
                        <div style="font-size: 13px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;">{_nombre_producto(nombre)}</div>
                        <div style="font-size: 36px; line-height: 1.1; color: #111827; font-weight: 900; margin-top: 8px;">{datos["precio"]}</div>
                    </td>
                    <td align="right" style="vertical-align: top;">
                        <div style="display: inline-block; background: {estado["fondo"]}; border: 1px solid {estado["borde"]}; color: {estado["color"]}; padding: 8px 12px; border-radius: 999px; font-size: 13px; font-weight: 800;">{estado["titulo"]}</div>
                    </td>
                </tr>
            </table>

            <p style="margin: 14px 0 18px 0; color: #475569; font-size: 14px; line-height: 1.5;">{estado["texto"]}</p>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse;">
                <tr>
                    <td style="background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .04em;">Mínimo histórico</div>
                        <div style="font-size: 18px; color: #111827; font-weight: 800; margin-top: 5px;">{_euros(analisis["precio_minimo_historico"])}</div>
                    </td>
                    <td width="10"></td>
                    <td style="background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .04em;">Promedio</div>
                        <div style="font-size: 18px; color: #111827; font-weight: 800; margin-top: 5px;">{_euros(analisis["precio_promedio"])}</div>
                    </td>
                    <td width="10"></td>
                    <td style="background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .04em;">Máximo histórico</div>
                        <div style="font-size: 18px; color: #111827; font-weight: 800; margin-top: 5px;">{_euros(analisis["precio_maximo_historico"])}</div>
                    </td>
                </tr>
            </table>

            <div style="margin-top: 18px; padding-top: 16px; border-top: 1px solid #e5e7eb;">
                <div style="font-size: 13px; color: #111827; font-weight: 800; margin-bottom: 6px;">Histórico reciente</div>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse;">
                    {filas_historial}
                </table>
            </div>
        </div>
    </div>
    """


def enviar_email(remitente, clave, destinatario, datos_productos, imagenes):
    """
    Envía el correo con análisis de precios y gráficas embebidas.

    Args:
        remitente: Email del remitente
        clave: Contraseña o app password
        destinatario: Lista de destinatarios o string
        datos_productos: Dict con datos de cada producto (precio, analisis)
        imagenes: Dict con rutas de las imágenes
    """
    fecha = datetime.date.today()
    msg = MIMEMultipart("related")
    msg["Subject"] = f"Reporte HSN - {fecha.strftime('%d/%m/%Y')}"
    msg["From"] = remitente
    msg["To"] = ", ".join(destinatario) if isinstance(destinatario, list) else destinatario

    alertas_html = ""
    for nombre, datos in datos_productos.items():
        alertas_html += generar_alerta_precio(nombre, datos)

    secciones_graficas = ""
    for clave_producto in datos_productos:
        if clave_producto not in imagenes:
            continue
        secciones_graficas += f"""
        <div style="background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; margin: 18px 0; overflow: hidden;">
            <div style="padding: 18px 20px 8px 20px;">
                <div style="font-size: 16px; color: #111827; font-weight: 800;">{_nombre_producto(clave_producto)}</div>
            </div>
            <img src="cid:img_{clave_producto}" alt="Gráfica {_nombre_producto(clave_producto)}" style="display: block; width: 100%; max-width: 760px; height: auto; border: 0;">
        </div>
        """

    html = f"""
    <html>
    <body style="margin: 0; padding: 0; background: #eef2f7; font-family: Arial, Helvetica, sans-serif;">
        <div style="display: none; max-height: 0; overflow: hidden; color: transparent;">
            Resumen diario de precios HSN con estado actual, mínimos, medias e histórico reciente.
        </div>

        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background: #eef2f7;">
            <tr>
                <td align="center" style="padding: 28px 12px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 820px; border-collapse: collapse;">
                        <tr>
                            <td style="background: #111827; border-radius: 18px 18px 0 0; padding: 30px 28px;">
                                <div style="font-size: 13px; color: #93c5fd; text-transform: uppercase; letter-spacing: .08em; font-weight: 800;">Monitor de precios HSN</div>
                                <h1 style="margin: 8px 0 0 0; color: #ffffff; font-size: 30px; line-height: 1.2;">Reporte diario</h1>
                                <p style="margin: 10px 0 0 0; color: #cbd5e1; font-size: 15px;">{fecha.strftime('%d/%m/%Y')} · Seguimiento de precio actual, mínimos, medias y evolución.</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="background: #f8fafc; padding: 24px 28px;">
                                <h2 style="margin: 0 0 14px 0; color: #111827; font-size: 20px;">Resumen general</h2>
                                {_generar_resumen_productos(datos_productos)}

                                <h2 style="margin: 30px 0 6px 0; color: #111827; font-size: 20px;">Detalle por producto</h2>
                                <p style="margin: 0 0 12px 0; color: #64748b; font-size: 14px; line-height: 1.5;">Cada tarjeta compara el precio de hoy con tu histórico guardado y muestra los últimos registros por día.</p>
                                {alertas_html}

                                <h2 style="margin: 32px 0 6px 0; color: #111827; font-size: 20px;">Evolución histórica</h2>
                                <p style="margin: 0 0 12px 0; color: #64748b; font-size: 14px; line-height: 1.5;">Gráficas generadas automáticamente desde los CSV del proyecto.</p>
                                {secciones_graficas}
                            </td>
                        </tr>
                        <tr>
                            <td style="background: #ffffff; border-radius: 0 0 18px 18px; padding: 18px 28px; border-top: 1px solid #e5e7eb;">
                                <p style="margin: 0; color: #64748b; font-size: 12px; line-height: 1.5;">Correo automático generado por tu sistema de monitorización. Los datos salen del histórico local del proyecto y de la última ejecución del scraper.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    for cid, ruta in imagenes.items():
        with open(ruta, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<img_{cid}>")
            msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remitente, clave)
        server.send_message(msg)
