from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

# Email templates live under app/templates/email; configure SMTP via the settings
# exposed in app/core/config.py (see .env.example for the available variables).
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "email"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_email_template(template_name: str, context: dict[str, Any]) -> str:
    """Render the given template with context data."""
    try:
        template = _jinja_env.get_template(template_name)
    except TemplateNotFound as exc:  # noqa: BLE001
        logger.error("Email template %s not found", template_name)
        raise exc
    return template.render(**context)


def send_email(*, to: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    """
    Send an email via SMTP; best effort logging to avoid breaking business flows.
    """

    if not settings.smtp_host or not settings.smtp_from_address:
        logger.info("SMTP is not configured; skipping email to %s", to)
        return False

    message = EmailMessage()
    from_display = (
        formataddr((settings.smtp_from_name, settings.smtp_from_address))
        if settings.smtp_from_name
        else settings.smtp_from_address
    )
    message["From"] = from_display
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body or "Please view this email in HTML.")
    message.add_alternative(html_body, subtype="html")

    try:
        if settings.smtp_use_ssl:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30)
        else:
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
        with smtp:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send email to %s", to)
        return False


def send_templated_email(
    *,
    template_name: str,
    to: str,
    subject: str,
    context: dict[str, Any],
    text_body: str | None = None,
) -> bool:
    """Render an HTML template and send it via SMTP."""
    html_body = render_email_template(template_name, context)
    return send_email(to=to, subject=subject, html_body=html_body, text_body=text_body)
