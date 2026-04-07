from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Callable


class EmailNotifier:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
        use_tls: bool = True,
        smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP,
        timeout: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls
        self.smtp_factory = smtp_factory
        self.timeout = timeout

    def send(self, title: str, body: str) -> bool:
        message = EmailMessage()
        message["Subject"] = title
        message["From"] = self.from_addr
        message["To"] = ", ".join(self.to_addrs)
        message.set_content(body)

        with self.smtp_factory(self.host, self.port, timeout=self.timeout) as smtp:
            if self.use_tls:
                smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.sendmail(self.from_addr, self.to_addrs, message.as_string())

        return True
