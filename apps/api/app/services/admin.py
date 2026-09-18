import base64, hashlib, hmac, secrets
from datetime import UTC, datetime, timedelta

ITERATIONS = 210_000

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt, digest = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds))
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(digest))
    except (ValueError, TypeError):
        return False

def make_session(username: str, secret: str) -> str:
    payload = f"{username}.{int((datetime.now(UTC) + timedelta(hours=12)).timestamp())}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"

def verify_session(value: str | None, secret: str) -> bool:
    try:
        username, expires, signature = (value or "").split(".")
        payload = f"{username}.{expires}"
        return int(expires) > int(datetime.now(UTC).timestamp()) and hmac.compare_digest(signature, hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest())
    except (ValueError, TypeError):
        return False
