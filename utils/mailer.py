import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import datetime

def generar_alerta_precio(nombre, datos):
    """Genera HTML con alertas visuales según el estado del precio"""
    analisis = datos['analisis']
    precio = datos['precio']
    precio_numerico = datos['precio_numerico']
    
    # Estilos base
    alerta_html = ""
    
    if analisis['es_minimo_historico']:
        alerta_html = f"""
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                    padding: 20px; border-radius: 15px; margin: 15px 0; 
                    box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4); 
                    border: 3px solid #1e7e34;">
            <h2 style="color: white; margin: 0; font-size: 28px;">
                🎉 ¡MÍNIMO HISTÓRICO! 🎉
            </h2>
            <p style="color: white; font-size: 18px; margin: 10px 0 0 0; font-weight: bold;">
                {nombre.upper().replace('_', ' ')}: {precio}
            </p>
            <p style="color: #d4edda; font-size: 14px; margin: 5px 0 0 0;">
                ⭐ ¡Nunca ha estado tan barato! Es el mejor momento para comprar.
            </p>
        </div>
        """
    elif analisis['es_minimo_igualado']:
        dias_texto = "día" if analisis['veces_a_este_precio'] == 1 else "días"
        alerta_html = f"""
        <div style="background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); 
                    padding: 18px; border-radius: 12px; margin: 15px 0; 
                    box-shadow: 0 4px 15px rgba(23, 162, 184, 0.3); 
                    border: 2px solid #117a8b;">
            <h2 style="color: white; margin: 0; font-size: 24px;">
                ✅ ¡PRECIO MÍNIMO IGUALADO!
            </h2>
            <p style="color: white; font-size: 16px; margin: 8px 0 0 0;">
                {nombre.upper().replace('_', ' ')}: {precio}
            </p>
            <p style="color: #d1ecf1; font-size: 13px; margin: 5px 0 0 0;">
                Ha estado {analisis['veces_a_este_precio']} {dias_texto} a este precio. ¡Buen momento para comprar!
            </p>
        </div>
        """
    elif precio_numerico < analisis['precio_promedio']:
        diferencia = abs(analisis['diferencia_vs_promedio'])
        ahorro = (diferencia / analisis['precio_promedio']) * 100
        alerta_html = f"""
        <div style="background: linear-gradient(135deg, #20c997 0%, #17a2b8 100%); 
                    padding: 15px; border-radius: 10px; margin: 15px 0; 
                    box-shadow: 0 3px 10px rgba(32, 201, 151, 0.2); 
                    border: 2px solid #0d9488;">
            <h3 style="color: white; margin: 0; font-size: 20px;">
                💚 Precio por debajo del promedio
            </h3>
            <p style="color: white; font-size: 15px; margin: 8px 0 0 0;">
                {nombre.upper().replace('_', ' ')}: {precio}
            </p>
            <p style="color: #d4edda; font-size: 12px; margin: 5px 0 0 0;">
                {ahorro:.1f}% más barato que el promedio ({analisis['precio_promedio']:.2f}€)
            </p>
        </div>
        """
    else:
        diferencia = analisis['diferencia_vs_promedio']
        porcentaje = (diferencia / analisis['precio_promedio']) * 100
        alerta_html = f"""
        <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; 
                    margin: 15px 0; border-left: 4px solid #6c757d;">
            <h3 style="color: #495057; margin: 0; font-size: 18px;">
                ➡️ Precio actual
            </h3>
            <p style="color: #212529; font-size: 14px; margin: 8px 0 0 0;">
                {nombre.upper().replace('_', ' ')}: {precio}
            </p>
            <p style="color: #6c757d; font-size: 11px; margin: 5px 0 0 0;">
                {porcentaje:+.1f}% respecto al promedio ({analisis['precio_promedio']:.2f}€)
            </p>
        </div>
        """
    
    # Info adicional
    info_adicional = f"""
    <div style="background: #e9ecef; padding: 10px; border-radius: 6px; margin-top: 10px;">
        <p style="margin: 5px 0; font-size: 12px; color: #495057;">
            <strong>Rango histórico:</strong> {analisis['precio_minimo_historico']:.2f}€ - {analisis['precio_maximo_historico']:.2f}€
        </p>
        <p style="margin: 5px 0; font-size: 12px; color: #495057;">
            <strong>Diferencia vs mínimo:</strong> +{analisis['diferencia_vs_minimo']:.2f}€ 
            ({analisis['porcentaje_vs_minimo']:.1f}%)
        </p>
    </div>
    """
    
    return alerta_html + info_adicional

def enviar_email(remitente, clave, destinatario, datos_productos, imagenes):
    """
    Envía el correo con análisis de precios y gráficas embebidas
    
    Args:
        remitente: Email del remitente
        clave: Contraseña o app password
        destinatario: Lista de destinatarios o string
        datos_productos: Dict con datos de cada producto (precio, analisis)
        imagenes: Dict con rutas de las imágenes
    """
    msg = MIMEMultipart('related')
    msg['Subject'] = f'📊 Reporte de Precios - {datetime.date.today()}'
    msg['From'] = remitente
    msg['To'] = ', '.join(destinatario) if isinstance(destinatario, list) else destinatario

    # Generar alertas para cada producto
    alertas_html = ""
    for nombre, datos in datos_productos.items():
        alertas_html += generar_alerta_precio(nombre, datos)

    html = f"""
    <html>
    <head>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background-color: #f4f4f4; 
                margin: 0;
                padding: 0;
            }}
            .container {{ 
                max-width: 800px; 
                margin: 20px auto; 
                background: white; 
                padding: 30px; 
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            h1 {{ 
                color: #2c3e50; 
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 15px;
            }}
            .imagen {{ 
                width: 100%; 
                max-width: 700px; 
                border-radius: 10px; 
                margin: 20px 0; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                display: block;
            }}
            .producto-section {{
                margin-bottom: 30px;
            }}
            .fecha {{
                text-align: center;
                color: #7f8c8d;
                font-size: 14px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Reporte Diario de Precios</h1>
            <p class="fecha">Fecha: {datetime.date.today().strftime('%d/%m/%Y')}</p>
            
            <hr style="border: 2px solid #3498db; margin: 20px 0;">
            
            {alertas_html}
            
            <h2 style="color: #34495e; margin-top: 40px; text-align: center;">📈 Gráficas de Evolución</h2>
            
            <div class="producto-section">
                <h3 style="color: #2c3e50;">Evowhey Protein (2Kg)</h3>
                <img src="cid:img_evowhey" class="imagen" alt="Gráfica Evowhey"/>
            </div>
            
            <div class="producto-section">
                <h3 style="color: #2c3e50;">Creatina Monohidrato (1Kg)</h3>
                <img src="cid:img_creatina" class="imagen" alt="Gráfica Creatina"/>
            </div>
            
            <div class="producto-section">
                <h3 style="color: #2c3e50;">Proteína Pack (5x500g)</h3>
                <img src="cid:img_proteina_pack" class="imagen" alt="Gráfica Pack"/>
            </div>
            
            <hr style="border: 1px solid #ecf0f1; margin: 30px 0;">
            <p style="text-align: center; color: #95a5a6; font-size: 12px;">
                Reporte automático generado por el sistema de monitoreo de precios HSN
            </p>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, 'html'))

    # Adjuntar imágenes
    for cid, ruta in imagenes.items():
        with open(ruta, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<img_{cid}>')
            msg.attach(img)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(remitente, clave)
        server.send_message(msg)