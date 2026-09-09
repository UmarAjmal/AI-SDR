import base64
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Any
import httpx
import logging

from packages.email.base import EmailProvider, OutboundEmail, SendResult, InboundEmail

logger = logging.getLogger("codenter.email.gmail")

class GmailProvider(EmailProvider):
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, mock_client: Optional[httpx.AsyncClient] = None):
        self.mock_client = mock_client

    @classmethod
    def build_raw_mime(cls, message: OutboundEmail) -> str:
        """
        Constructs an RFC 2822 compliant MIME message and encodes as base64url.
        """
        mime = MIMEMultipart("alternative")
        mime["From"] = message.from_address
        mime["To"] = message.to_address
        mime["Subject"] = message.subject
        mime["Date"] = email.utils.formatdate(localtime=False)
        
        # Message-ID
        msg_id = email.utils.make_msgid(domain=message.from_address.split("@")[-1])
        mime["Message-ID"] = msg_id

        # Threading Headers
        if message.in_reply_to:
            irt = message.in_reply_to if message.in_reply_to.startswith("<") else f"<{message.in_reply_to}>"
            mime["In-Reply-To"] = irt

        if message.references:
            formatted_refs = [
                r if r.startswith("<") else f"<{r}>" for r in message.references
            ]
            mime["References"] = " ".join(formatted_refs)
        elif message.in_reply_to:
            mime["References"] = mime["In-Reply-To"]

        # Custom Headers
        for k, v in message.custom_headers.items():
            mime[k] = v

        # Plain text & HTML parts
        part1 = MIMEText(message.body_text, "plain", "utf-8")
        mime.attach(part1)

        if message.body_html:
            part2 = MIMEText(message.body_html, "html", "utf-8")
            mime.attach(part2)

        raw_bytes = mime.as_bytes()
        return base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

    @classmethod
    def build_mime_message(cls, message: OutboundEmail) -> dict[str, str]:
        """
        Builds RFC 2822 MIME payload dict for Gmail send API.
        """
        return {"raw": cls.build_raw_mime(message)}

    async def send_message(self, credentials: dict[str, Any], message: OutboundEmail) -> SendResult:
        access_token = credentials.get("access_token", "")
        raw_b64 = self.build_raw_mime(message)

        payload = {"raw": raw_b64}
        if message.thread_id:
            payload["threadId"] = message.thread_id

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.post(
                f"{self.BASE_URL}/messages/send",
                headers=headers,
                json=payload
            )

            if resp.status_code == 401:
                return SendResult(
                    success=False,
                    status_code=401,
                    error="AUTHENTICATION_REVOKED",
                    raw_response={"status": 401, "detail": "Token expired or revoked"}
                )

            if resp.status_code in (200, 201):
                data = resp.json()
                return SendResult(
                    success=True,
                    provider_message_id=data.get("id"),
                    status_code=resp.status_code,
                    raw_response=data
                )

            return SendResult(
                success=False,
                status_code=resp.status_code,
                error=resp.text,
                raw_response={"body": resp.text}
            )
        except Exception as e:
            logger.error(f"Gmail send_message failed: {e}")
            return SendResult(
                success=False,
                status_code=500,
                error=str(e)
            )
        finally:
            if owns_client:
                await client.aclose()

    async def fetch_message(self, credentials: dict[str, Any], provider_msg_id: str) -> Optional[InboundEmail]:
        access_token = credentials.get("access_token", "")
        headers = {"Authorization": f"Bearer {access_token}"}

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.get(
                f"{self.BASE_URL}/messages/{provider_msg_id}?format=full",
                headers=headers
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

            headers_dict = {}
            payload = data.get("payload", {})
            for h in payload.get("headers", []):
                headers_dict[h["name"].lower()] = h["value"]

            snippet = data.get("snippet", "")
            return InboundEmail(
                provider_message_id=data["id"],
                from_address=headers_dict.get("from", ""),
                to_address=headers_dict.get("to", ""),
                subject=headers_dict.get("subject", ""),
                body_text=snippet,
                body_html=None,
                in_reply_to=headers_dict.get("in-reply-to"),
                references=[r.strip() for r in headers_dict.get("references", "").split() if r.strip()],
                headers=headers_dict
            )
        finally:
            if owns_client:
                await client.aclose()

    async def setup_webhook(self, credentials: dict[str, Any], callback_url: str) -> bool:
        return True
