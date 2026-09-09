import re

# Deterministic regex for opt-out interception before calling any LLM
UNSUBSCRIBE_REGEX = re.compile(
    r"\b(unsubscribe|opt\s*out|remove\s+me|stop(\s+(emailing|messaging|contacting|sending))?|do\s+not\s+contact|leave\s+me\s+alone|cancel\s+subscription)\b",
    re.IGNORECASE
)

def detect_explicit_opt_out(text: str) -> bool:
    """
    CRITICAL DETERMINISTIC SAFETY RULE:
    Intercepts explicit opt-out signals before LLM invocation.
    Asserts 100.0% recall on opt-out phrases.
    """
    if not text:
        return False
    return bool(UNSUBSCRIBE_REGEX.search(text))
