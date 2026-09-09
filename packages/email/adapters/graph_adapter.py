from typing import Optional, Any
import httpx
import logging

from packages.email.base import EmailProvider, OutboundEmail, SendResult, InboundEmail

logger = logging.getLogger("codenter.email.graph")

class GraphProvider(EmailProvider):
    BASE_URL = "https://graph.microsoft.com/v1.0/me"

    def __init__(self, mock_client: Optional[httpx.AsyncClient] = None):
        self.mock_client = mock_client

    @classmethod
    def build_graph_payload(cls, message: OutboundEmail) -> dict[str, Any]:
        """
        Formats Microsoft Graph /sendMail payload with threading headers.
        """
        email_dict: dict[str, Any] = {
            "subject": message.subject,
            "body": {
                "contentType": "HTML" if message.body_html else "Text",
                "content": message.body_html if message.body_html else message.body_text
            },
            "toRecipients": [
                {"emailAddress": {"address": message.to_address}}
            ]
        }

        # Internet Message Headers for threading
        custom_headers = []
        if message.in_reply_to:
            irt = message.in_reply_to if message.in_reply_to.startswith("<") else f"<{message.in_reply_to}>"
            custom_headers.append({"name": "In-Reply-To", "value": irt})

        if message.references:
            refs = " ".join([r if r.startswith("<") else f"<{r}>" for r in message.references])
            custom_headers.append({"name": "References", "value": refs})

        for k, v in message.custom_headers.items():
            custom_headers.append({"name": k, "value": v})

        if custom_headers:
            email_dict["internetMessageHeaders"] = custom_headers

        return {"message": email_dict, "saveToSentItems": "true"}

    async def send_message(self, credentials: dict[str, Any], message: OutboundEmail) -> SendResult:
        access_token = credentials.get("access_token", "")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = self.build_graph_payload(message)

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.post(f"{self.BASE_URL}/sendMail", headers=headers, json=payload)
            if resp.status_code == 401:
                return SendResult(
                    success=False,
                    status_code=401,
                    error="AUTHENTICATION_REVOKED",
                    raw_response={"status": 401}
                )

            if resp.status_code in (200, 202):
                msg_id = resp.headers.get("client-request-id", "graph-msg-ok")
                return SendResult(
                    success=True,
                    provider_message_id=msg_id,
                    status_code=resp.status_code
                )

            return SendResult(
                success=False,
                status_code=resp.status_code,
                error=resp.text
            )
        except Exception as e:
            logger.error(f"Graph send_message failed: {e}")
            return SendResult(success=False, status_code=500, error=str(e))
        finally:
            if owns_client:
                await client.aclose()

    async def fetch_message(self, credentials: dict[str, Any], provider_msg_id: str) -> Optional[InboundEmail]:
        access_token = credentials.get("access_token", "")
        headers = {"Authorization": f"Bearer {access_token}"}

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.get(f"{self.BASE_URL}/messages/{provider_msg_id}", headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

            from_addr = data.get("from", {}).get("emailAddress", {}).get("address", "")
            to_recips = data.get("toRecipients", [])
            to_addr = to_recips[0].get("emailAddress", {}).get("address", "") if to_recips else ""

            return InboundEmail(
                provider_message_id=data["id"],
                from_address=from_addr,
                to_address=to_addr,
                subject=data.get("subject", ""),
                body_text=data.get("bodyPreview", ""),
                body_html=data.get("body", {}).get("content"),
                in_reply_to=None,
                references=[],
                headers={}
            )
        finally:
            if owns_client:
                await client.aclose()

    async def setup_webhook(self, credentials: dict[str, Any], callback_url: str) -> bool:
        return True
