"""Single-use HMAC token bound to the exact action (name + args)."""
import hmac, hashlib, json, os, secrets
KEY = os.environ.get("AEGIS_HMAC_KEY", "dev-only-change-me").encode()
_used: set[str] = set()

def action_hash(name: str, args: dict) -> str:
    return hashlib.sha256(json.dumps({"n": name, "a": args}, sort_keys=True).encode()).hexdigest()

def mint(name: str, args: dict) -> str:
    nonce = secrets.token_hex(8)
    sig = hmac.new(KEY, f"{nonce}:{action_hash(name, args)}".encode(), hashlib.sha256).hexdigest()
    return f"{nonce}.{sig}"

def consume(token: str, name: str, args: dict) -> bool:
    if not token or token in _used:
        return False
    nonce, sig = token.split(".", 1)
    good = hmac.new(KEY, f"{nonce}:{action_hash(name, args)}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, good):
        return False
    _used.add(token)
    return True
