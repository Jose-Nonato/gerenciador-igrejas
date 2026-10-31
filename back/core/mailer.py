import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from core.config import settings

logger = logging.getLogger(__name__)


class Mailer(Protocol):
    def enviar(self, destinatario: str, assunto: str, corpo: str) -> None: ...


class ConsoleMailer:
    """Só registra no log. Uso restrito a desenvolvimento: o corpo contém links com token."""

    def enviar(self, destinatario: str, assunto: str, corpo: str) -> None:
        logger.warning("E-mail para %s | %s\n%s", destinatario, assunto, corpo)


class SmtpMailer:
    def enviar(self, destinatario: str, assunto: str, corpo: str) -> None:
        msg = EmailMessage()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.set_content(corpo)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)


def get_mailer() -> Mailer:
    return SmtpMailer() if settings.SMTP_HOST else ConsoleMailer()
