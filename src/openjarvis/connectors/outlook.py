"""Outlook / Microsoft 365 connector — reads email via IMAP with app password.

Thin subclass of GmailIMAPConnector that defaults to the Outlook IMAP host
and relabels documents with source='outlook'.

Setup: enable 2FA on your Microsoft account, then generate an app password
at https://account.microsoft.com/security
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterator, Optional

from openjarvis.connectors._stubs import Document
from openjarvis.connectors.gmail_imap import GmailIMAPConnector
from openjarvis.core.config import DEFAULT_CONFIG_DIR
from openjarvis.core.registry import ConnectorRegistry

_DEFAULT_CREDENTIALS_PATH = str(DEFAULT_CONFIG_DIR / "connectors" / "outlook.json")


@ConnectorRegistry.register("outlook")
class OutlookConnector(GmailIMAPConnector):
    """Outlook connector using IMAP + app password."""

    connector_id = "outlook"
    display_name = "Outlook / Microsoft 365"
    _default_imap_host = "outlook.office365.com"

    def __init__(
        self,
        email_address: str = "",
        app_password: str = "",
        credentials_path: str = "",
        *,
        max_messages: int = 500,
    ) -> None:
        super().__init__(
            email_address,
            app_password,
            credentials_path or _DEFAULT_CREDENTIALS_PATH,
            max_messages=max_messages,
        )

    def auth_url(self) -> str:
        return "https://account.microsoft.com/security"

    def sync(
        self,
        *,
        since: Optional[datetime] = None,
        cursor: Optional[str] = None,
    ) -> Iterator[Document]:
        # Propagate close() to the inner generator: a bare `for ... yield`
        # wrapper abandons the inner generator on GeneratorExit, so its
        # finally (IMAP logout) would never run until GC. Closing it
        # explicitly here logs out promptly on consumer close().
        inner = super().sync(since=since, cursor=cursor)
        try:
            for doc in inner:
                doc.source = "outlook"
                doc.doc_id = doc.doc_id.replace("gmail:", "outlook:", 1)
                yield doc
        finally:
            inner.close()
