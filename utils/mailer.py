import smtplib
from email.message import EmailMessage
import os
import datetime
import pandas as pd
import re

def analizar_precio_historico(nombre_producto, precio_actual):
    """
    Analiza si el precio actual es el más alto o más bajo históricamente
    """
    archivo_excel = f"precios_{nombre_producto}.xlsx"
    
    if not os.path.exists(archivo_excel):
        return ""
    
    try:
        df = pd.read_excel(archivo_excel)
        if len(df) <= 1:  # Solo hay un registro (el actual)
            return ""
        
        # Convertir precios a números (remover € y comas)
        precios_numericos = []
        for precio in df['precio']:
            # Extraer número del precio (ej: "29,90 €" -> 29.90)
            precio_limpio = re.sub(r'[^\d,.]', '', str(precio))
            precio_limpio = precio_limpio.replace(',', '.')
            try:
                precios_numericos.append(float(precio_limpio))
            except:
                continue
        
        if not precios_numericos:
            return ""
        
        # Convertir precio actual a número
        precio_actual_limpio = re.sub(r'[^\d,.]', '', str(precio_actual))
        precio_actual_limpio = precio_actual_limpio.replace(',', '.')
        try:
            precio_actual_num = float(precio_actual_limpio)
        except:
            return ""
        
        min_precio = min(precios_numericos)
        max_precio = max(precios_numericos)
        
        if precio_actual_num == min_precio:
            return "🎉 ¡PRECIO MÁS BAJO HISTÓRICO! 🎉"
        elif precio_actual_num == max_precio:
            return "⚠️ PRECIO MÁS ALTO HISTÓRICO ⚠️"
        
        return ""
    
    except Exception as e:
        return ""

def enviar_email(remitente, clave, destinatario, pre_crea, pre_prot, img_crea, img_prot):
    # Analizar precios históricos
    mensaje_creatina = analizar_precio_historico("creatina", pre_crea)
    mensaje_proteina = analizar_precio_historico("evowhey", pre_prot)
    
    asunto = "Precios diarios: Creatina y Proteína"
    
    # Crear contenido en texto plano
    texto_plano = f"""Buenos días,

Precios de hoy ({datetime.date.today()}):
• Creatina: {pre_crea}"""
    
    if mensaje_creatina:
        texto_plano += f" {mensaje_creatina}"
    
    texto_plano += f"""
• Proteína: {pre_prot}"""
    
    if mensaje_proteina:
        texto_plano += f" {mensaje_proteina}"
    
    texto_plano += """

Adjunto las gráficas de evolución.

Saludos."""

    # Crear contenido en HTML para mejor compatibilidad
    html_content = f"""<html>
<body style="font-family: Arial, sans-serif; font-size: 14px;">
<p>Buenos días,</p>

<p><strong>Precios de hoy ({datetime.date.today()}):</strong></p>
<ul>
<li><strong>Creatina:</strong> {pre_crea}"""
    
    if mensaje_creatina:
        html_content += f" <span style='color: #e74c3c; font-weight: bold;'>{mensaje_creatina}</span>"
    
    html_content += f"""</li>
<li><strong>Proteína:</strong> {pre_prot}"""
    
    if mensaje_proteina:
        html_content += f" <span style='color: #e74c3c; font-weight: bold;'>{mensaje_proteina}</span>"
    
    html_content += """</li>
</ul>

<p>Adjunto las gráficas de evolución.</p>

<p>Saludos.</p>
</body>
</html>"""

    msg = EmailMessage()
    msg.set_content(texto_plano)
    msg.add_alternative(html_content, subtype='html')
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario

    for img in (img_crea, img_prot):
        with open(img, 'rb') as f:
            data = f.read()
            msg.add_attachment(data, maintype='image', subtype='png', filename=os.path.basename(img))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(remitente, clave)
        smtp.send_message(msg)
