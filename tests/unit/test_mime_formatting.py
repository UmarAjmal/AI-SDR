import base64
import email
from email import policy
import pytest
from packages.email.base import OutboundEmail
from packages.email.adapters.gmail_adapter import GmailProvider
from packages.email.adapters.graph_adapter import GraphProvider

def test_gmail_mime_formatting_and_threading():
    provider = GmailProvider()
    outbound = OutboundEmail(
        from_address="sales@company.com",
        to_address="prospect@acme.corp",
        subject="Streamlining outreach with AI",
        body_text="Hi Alex, Codenter AI helps teams scale outbound.",
        body_html="<p>Hi Alex, <b>Codenter AI</b> helps teams scale outbound.</p>",
        thread_id="thread-xyz-123",
        in_reply_to="<parent-msg-001@acme.corp>",
        references=["<root-msg-000@acme.corp>", "<parent-msg-001@acme.corp>"]
    )

    mime_payload = provider.build_mime_message(outbound)
    assert "raw" in mime_payload
    raw_b64 = mime_payload["raw"]
    
    # Decode base64url
    decoded_bytes = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
    msg = email.message_from_bytes(decoded_bytes, policy=policy.default)

    assert msg["From"] == "sales@company.com"
    assert msg["To"] == "prospect@acme.corp"
    assert msg["Subject"] == "Streamlining outreach with AI"
    assert msg["In-Reply-To"] == "<parent-msg-001@acme.corp>"
    assert "<root-msg-000@acme.corp>" in msg["References"]
    assert "<parent-msg-001@acme.corp>" in msg["References"]
    assert msg["Message-ID"] is not None
    assert msg["Message-ID"].startswith("<") and msg["Message-ID"].endswith(">")

def test_graph_message_formatting_and_headers():
    provider = GraphProvider()
    outbound = OutboundEmail(
        from_address="rep@contoso.com",
        to_address="lead@client.org",
        subject="Follow-up on product demo",
        body_text="Hi Sarah, following up on our call yesterday.",
        body_html="<p>Hi Sarah, following up on our call yesterday.</p>",
        thread_id="thread-graph-456",
        in_reply_to="<lead-inquiry-999@client.org>",
        references=["<lead-inquiry-999@client.org>"]
    )

    payload = provider.build_graph_payload(outbound)
    assert "message" in payload
    message = payload["message"]

    assert message["subject"] == "Follow-up on product demo"
    assert message["body"]["contentType"] == "HTML"
    assert "following up" in message["body"]["content"]
    assert message["toRecipients"][0]["emailAddress"]["address"] == "lead@client.org"
    
    # Check internet headers for threading
    headers = {h["name"].lower(): h["value"] for h in message["internetMessageHeaders"]}
    assert headers.get("in-reply-to") == "<lead-inquiry-999@client.org>"
    assert "<lead-inquiry-999@client.org>" in headers.get("references", "")
