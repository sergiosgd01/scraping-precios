import smtplib
from email.message import EmailMessage
import os
import datetime

def enviar_email(remitente, clave, destinatario, pre_crea, pre_prot, img_crea, img_prot):
    asunto = "Precios diarios: Creatina y Proteína"
    cuerpo = (
        f"Buenos días,\n\n"
        f"Precios de hoy ({datetime.date.today()}):\n"
        f"- Creatina: {pre_crea}\n"
        f"- Proteína: {pre_prot}\n\n"
        f"Adjunto las gráficas de evolución.\n\n"
        f"Saludos."
    )

    msg = EmailMessage()
    msg.set_content(cuerpo)
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
