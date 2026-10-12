import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
import bcrypt
import jwt
from app.core.config import settings

class SecurityError(Exception):
    """Base exception for authentication and token errors."""
    pass

class TokenExpiredError(SecurityError):
    """Raised when a JWT has expired."""
    pass

class TokenInvalidError(SecurityError):
    """Raised when a JWT is malformed, invalid signature, or missing required claims."""
    pass

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with automatically generated salt.
    Never stores or logs the plaintext password.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Safe against timing attacks.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a signed JWT access token containing subject (user_id), expiration,
    issued-at timestamp, and a unique token ID (jti) for server-side revocation tracking.
    """
    if not settings.JWT_SECRET:
        raise SecurityError("JWT_SECRET is not configured")

    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "jti": jti,
    }

    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Validates expiration, required claims ('sub', 'exp', 'jti'), and signature algorithm.
    """
    if not settings.JWT_SECRET:
        raise SecurityError("JWT_SECRET is not configured")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "jti"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except (jwt.InvalidTokenError, jwt.PyJWTError) as exc:
        raise TokenInvalidError(f"Invalid token: {str(exc)}")
