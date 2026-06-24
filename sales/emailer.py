"""SMTP delivery — sends the license file to the customer.

Injectable: in tests we use the captured `FakeSMTP` to assert on
subject/body/attachment without actually opening a socket.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol

logger = logging.getLogger(__name__)


class Emailer(Protocol):
    def send_license(
        self,
        *,
        to_email: str,
        customer_name: str,
        tier: str,
        license_id: str,
        license_json: str,
        portal_url: str,
    ) -> None: ...


@dataclass
class SMTPEmailer:
    host: str
    port: int
    user: str
    password: str
    from_addr: str
    use_tls: bool = True

    def send_license(
        self,
        *,
        to_email: str,
        customer_name: str,
        tier: str,
        license_id: str,
        license_json: str,
        portal_url: str,
    ) -> None:
        msg = _build_message(
            to_email=to_email,
            customer_name=customer_name,
            tier=tier,
            license_id=license_id,
            license_json=license_json,
            portal_url=portal_url,
            from_addr=self.from_addr,
        )
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            if self.use_tls:
                smtp.starttls()
            smtp.login(self.user, self.password)
            smtp.send_message(msg)
        logger.info("license email sent: license_id=%s to=%s", license_id, to_email)


@dataclass
class FakeEmailer:
    """In-memory emailer for tests. Captures every message so the
    test can assert on subject / body / attachment without a network."""

    sent: list[EmailMessage]

    def __init__(self) -> None:
        self.sent = []

    def send_license(
        self,
        *,
        to_email: str,
        customer_name: str,
        tier: str,
        license_id: str,
        license_json: str,
        portal_url: str,
    ) -> None:
        msg = _build_message(
            to_email=to_email,
            customer_name=customer_name,
            tier=tier,
            license_id=license_id,
            license_json=license_json,
            portal_url=portal_url,
            from_addr="sales-test@kirkforge.invalid",
        )
        self.sent.append(msg)


def _build_message(
    *,
    to_email: str,
    customer_name: str,
    tier: str,
    license_id: str,
    license_json: str,
    portal_url: str,
    from_addr: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"Your Gargoyle Packy {tier} license is ready ({license_id})"
    msg["From"] = formataddr(("KirkForge Sales", from_addr))
    msg["To"] = formataddr((customer_name, to_email))
    body = (
        f"Hi {customer_name},\n\n"
        f"Thanks for buying Gargoyle Packy ({tier} tier).\n\n"
        f"Your license ID is: {license_id}\n\n"
        f"The signed license.json is attached. Drop it at:\n"
        f"    ~/.config/kirkforge/packy/license.json\n\n"
        f"You can re-download it any time from the customer portal:\n"
        f"    {portal_url}\n\n"
        f"— KirkForge\n"
    )
    msg.set_content(body)
    # attach the license.json
    msg.add_attachment(
        license_json.encode("utf-8"),
        maintype="application",
        subtype="json",
        filename=f"license-{license_id}.json",
    )
    return msg
