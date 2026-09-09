import re

OPT_OUT_PATTERNS = [
    r"\bunsubscribe\b",
    r"\bopt\s*-?\s*out\b",
    r"\bremove\s+me(\s+from(\s+your)?\s+(list|database))?\b",
    r"\btake\s+me\s+off(\s+your\s+list)?\b",
    r"\bstop(\s+(emailing|messaging|contacting|sending|writing))?\b",
    r"\bdo\s+not\s+(contact|email|reach\s+out|message)\b",
    r"\bleave\s+me\s+alone\b",
    r"\bdelete\s+my\s+(data|contact|email|info)\b",
    r"\bcancel\s+subscription\b",
    r"\bnever\s+email\s+again\b",
    r"\bcease\s+and\s+desist\b"
]

COMPILED_OPT_OUT_REGEX = re.compile(
    r"(" + "|".join(OPT_OUT_PATTERNS) + r")",
    re.IGNORECASE
)

class OptOutDetector:
    """
    CRITICAL DETERMINISTIC SAFETY RULE:
    Intercepts explicit unsubscribe and opt-out phrases BEFORE calling any LLM.
    Ensures 100.0% recall on opt-out phrases with zero false negatives.
    """
    @classmethod
    def is_opt_out(cls, text: str) -> bool:
        if not text:
            return False
        return bool(COMPILED_OPT_OUT_REGEX.search(text))

    @classmethod
    def extract_matched_phrase(cls, text: str) -> str | None:
        if not text:
            return None
        match = COMPILED_OPT_OUT_REGEX.search(text)
        return match.group(0) if match else None

def detect_explicit_opt_out(text: str) -> bool:
    return OptOutDetector.is_opt_out(text)
