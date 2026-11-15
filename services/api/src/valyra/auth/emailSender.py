import os
import smtplib
import ssl

from pathlib import Path

from email.message import EmailMessage


class EmailDeliveryError(Exception):
    """Erro durante o envio de e-mail."""


class SMTPEmailService:

    def __init__(self):
        self.host = os.environ["SMTP_HOST"]
        self.port = int(os.environ.get("SMTP_PORT", "465"))
        self.username = os.environ["SMTP_USER"]
        self.password = os.environ["SMTP_PASSWORD"]
        self.sender = os.environ["SMTP_FROM"]

    def send_email(
        self,
        recipient: str,
        subject: str,
        html_content: str,
    ) -> None:

        message = EmailMessage()

        message["Subject"] = subject
        message["From"] = self.sender
        message["To"] = recipient

        message.set_content(
            "Para visualizar este e-mail, utilize um cliente "
            "compatível com HTML."
        )

        message.add_alternative(
            html_content,
            subtype="html",
        )

        try:
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(
                self.host,
                self.port,
                context=context,
                timeout=15,
            ) as smtp:

                smtp.login(
                    self.username,
                    self.password,
                )

                smtp.send_message(message)

        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError(
                "Não foi possível enviar o e-mail."
            ) from exc

    def send_password_reset(
        self,
        recipient: str,
        reset_url: str,
    ) -> None:

        template_path = (
            Path(__file__).parent
            / "templates"
            / "password_reset.html"
        )

        template = template_path.read_text(
            encoding="utf-8"
        )

        html_content = template.replace(
            "{{ reset_url }}",
            reset_url,
        )

        self.send_email(
            recipient=recipient,
            subject="Recuperação de senha - Valyra",
            html_content=html_content,
        )