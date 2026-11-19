"""Envía el informe en PDF por Gmail.

Uso: python enviar.py informe.pdf "Asunto" destinatario1 [destinatario2 ...]
Credenciales: variables de entorno GMAIL_USUARIO y GMAIL_APP_PASSWORD,
o un archivo credenciales.txt (CLAVE=valor) en la carpeta del proyecto.
"""
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path


def cargar_credenciales():
    archivo = Path(__file__).resolve().parent.parent / "credenciales.txt"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())
    usuario = os.environ.get("GMAIL_USUARIO")
    clave = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    if not usuario or not clave:
        sys.exit("Faltan GMAIL_USUARIO o GMAIL_APP_PASSWORD")
    return usuario, clave


def enviar(pdf, asunto, destinatarios, cuerpo=None):
    usuario, clave = cargar_credenciales()
    msg = EmailMessage()
    msg["From"] = f"Informe YECA <{usuario}>"
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = asunto
    msg.set_content(cuerpo or (
        "Hola,\n\nTe adjuntamos el informe semanal de Instagram de YECA (@dameyeca).\n\n"
        "Este mail se envía automáticamente todos los domingos."))
    pdf = Path(pdf)
    msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(usuario, clave)
        s.send_message(msg)
    print(f"Enviado a: {', '.join(destinatarios)}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    enviar(sys.argv[1], sys.argv[2], sys.argv[3:])
