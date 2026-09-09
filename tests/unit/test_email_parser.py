import pytest
from packages.email.parser import EmailParser

def test_quote_history_stripping_on_wrote_pattern():
    raw_reply = """Thanks for reaching out! We are interested in seeing a demo on Thursday.

On Mon, Sep 7, 2026 at 2:30 PM John Rep <john@codenter.com> wrote:
> Hi Alex,
> Wanted to see if you have 15 minutes to talk about our AI SDR platform.
> Best,
> John
"""
    clean_body = EmailParser.strip_quote_history(raw_reply)
    assert "Thanks for reaching out! We are interested in seeing a demo on Thursday." in clean_body
    assert "On Mon, Sep 7" not in clean_body
    assert "> Wanted to see" not in clean_body

def test_quote_history_stripping_on_outlook_original_message():
    outlook_reply = """Let's connect next week.

-----Original Message-----
From: John Rep [mailto:john@codenter.com]
Sent: Monday, September 7, 2026 10:00 AM
To: Alex Prospect
Subject: Introduction
"""
    clean_body = EmailParser.strip_quote_history(outlook_reply)
    assert clean_body.strip() == "Let's connect next week."
    assert "Original Message" not in clean_body

def test_quote_history_stripping_on_greater_than_quotes():
    quoted_text = """> Previous message line 1
> Previous message line 2

I am unsubscribing from this list. Please remove me.
"""
    clean_body = EmailParser.strip_quote_history(quoted_text)
    assert "I am unsubscribing from this list. Please remove me." in clean_body
    assert "Previous message line 1" not in clean_body

def test_inbound_mime_parsing():
    raw_email_str = """From: "Jane Prospect" <jane@prospectcorp.com>
To: "Sales Rep" <sales@codenter.com>
Subject: Re: AI SDR Platform
Date: Mon, 7 Sep 2026 14:00:00 +0000
Message-ID: <msg-reply-12345@prospectcorp.com>
In-Reply-To: <orig-msg-67890@codenter.com>
References: <orig-msg-67890@codenter.com>
Content-Type: text/plain; charset="utf-8"

We would love to learn more about the pricing plans.

On Mon, Sep 7, 2026 at 10:00 AM Sales Rep wrote:
> Hi Jane, are you open to a quick call?
"""
    parsed = EmailParser.parse_raw_mime(raw_email_str)

    assert parsed.from_address == "jane@prospectcorp.com"
    assert parsed.to_address == "sales@codenter.com"
    assert parsed.subject == "Re: AI SDR Platform"
    assert parsed.message_id == "<msg-reply-12345@prospectcorp.com>"
    assert parsed.in_reply_to == "<orig-msg-67890@codenter.com>"
    assert "orig-msg-67890@codenter.com" in parsed.references
    assert "We would love to learn more about the pricing plans." in parsed.cleaned_body_text
    assert "On Mon, Sep 7" not in parsed.cleaned_body_text
