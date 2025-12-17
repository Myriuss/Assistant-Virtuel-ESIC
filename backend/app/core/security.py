import hashlib

def hash_user(user_id: str) -> str:
    # Pas de PII en clair en base -> hash
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:40]

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "jailbreak",
    "do anything now",
    "reveal",
    "bypass",
    "override",
]

def looks_like_prompt_injection(text: str) -> bool:
    t = (text or "").lower()
    return any(p in t for p in INJECTION_PATTERNS)
