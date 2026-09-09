import re
import email
from email.message import Message
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class ParsedInboundEmail:
    from_address: str
    to_address: str
    subject: str
    cleaned_body_text: str
    raw_body_text: str
    body_html: Optional[str] = None
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)

class EmailParser:
    QUOTE_PATTERNS = [
        r"(?i)\bOn\s+.*?\s+wrote:\s*",
        r"(?i)\bFrom:\s+.*?\nSent:\s+.*?\nTo:\s+.*?\nSubject:\s+.*?\n",
        r"(?i)---+\s*Original Message\s*---+",
        r"(?i)^>+.*$",
    ]

    @classmethod
    def strip_quote_history(cls, text: str) -> str:
        """
        Strips nested quote history, forwarded footers, and email client dividers.
        """
        lines = []
        for line in text.splitlines():
            # Stop if line is a standard quote marker
            if line.strip().startswith(">"):
                continue
            if re.match(r"(?i)^On\s+.+wrote:$", line.strip()):
                break
            if re.match(r"(?i)^---+\s*Original Message\s*---+$", line.strip()):
                break
            lines.append(line)

        cleaned = "\n".join(lines).strip()
        # Remove trailing quoted headers if present
        cleaned = re.split(r"(?i)\nFrom:\s+.*?\nSent:\s+", cleaned)[0].strip()
        return cleaned

    @classmethod
    def parse_raw_mime(cls, raw_mime: str | bytes) -> ParsedInboundEmail:
        if isinstance(raw_mime, str):
            msg: Message = email.message_from_string(raw_mime)
        else:
            msg = email.message_from_bytes(raw_mime)

        headers = {k.lower(): str(v) for k, v in msg.items()}

        from_addr = headers.get("from", "")
        # Extract clean email inside angle brackets if present
        m_from = re.search(r"<([^>]+)>", from_addr)
        if m_from:
            from_addr = m_from.group(1)

        to_addr = headers.get("to", "")
        m_to = re.search(r"<([^>]+)>", to_addr)
        if m_to:
            to_addr = m_to.group(1)

        subject = headers.get("subject", "")
        message_id = headers.get("message-id")
        in_reply_to = headers.get("in-reply-to")
        raw_refs = headers.get("references", "")
        references = [r.strip("<> ") for r in raw_refs.split() if r.strip("<> ")]

        # Extract text and HTML parts
        body_text = ""
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    continue

                payload = part.get_payload(decode=True)
                if not payload:
                    continue

                charset = part.get_content_charset() or "utf-8"
                decoded_text = payload.decode(charset, errors="replace")

                if content_type == "text/plain" and not body_text:
                    body_text = decoded_text
                elif content_type == "text/html" and not body_html:
                    body_html = decoded_text
        else:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            decoded_text = payload.decode(charset, errors="replace") if payload else ""
            if msg.get_content_type() == "text/html":
                body_html = decoded_text
            else:
                body_text = decoded_text

        cleaned_text = cls.strip_quote_history(body_text)

        return ParsedInboundEmail(
            from_address=from_addr.strip(),
            to_address=to_addr.strip(),
            subject=subject.strip(),
            cleaned_body_text=cleaned_text,
            raw_body_text=body_text,
            body_html=body_html,
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references,
            headers=headers
        )
