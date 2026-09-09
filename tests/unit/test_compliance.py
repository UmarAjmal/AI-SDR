import pytest
from packages.compliance.suppression import detect_explicit_opt_out

def test_deterministic_opt_out_recall():
    test_cases = [
        ("Please unsubscribe me from this list.", True),
        ("Unsubscribe", True),
        ("Please remove me immediately.", True),
        ("STOP", True),
        ("Stop emailing me.", True),
        ("Do not contact me again.", True),
        ("Please opt out my email address.", True),
        ("I would love to learn more, let's schedule a call.", False),
        ("What is the price of the enterprise tier?", False),
        ("Sounds interesting, tell me more.", False),
    ]

    for text, expected in test_cases:
        assert detect_explicit_opt_out(text) == expected, f"Failed on: '{text}'"
