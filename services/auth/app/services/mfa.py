"""TOTP-based MFA service.

Spec §3.3:
- TOTP-based MFA (RFC 6238) compatible with Google Authenticator, Authy, 1Password
- MFA enrollment: generate QR code + backup codes (10 single-use codes, bcrypt hashed)
- Backup codes are bcrypt-hashed (not SHA-256) per spec
"""

import base64
import secrets
from io import BytesIO

import bcrypt
import pyotp
import qrcode


def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "CloudVisor") -> str:
    """Get TOTP provisioning URI for QR code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code."""
    if not secret or not code:
        return False

    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_qr_code(uri: str) -> bytes:
    """Generate QR code image for TOTP URI. Returns raw PNG bytes."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qr_code_base64(uri: str) -> str:
    """Generate QR code as a base64-encoded data URI (safe for embedding in JSON/HTML)."""
    png_bytes = generate_qr_code(uri)
    return f"data:image/png;base64,{base64.b64encode(png_bytes).decode('utf-8')}"


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate single-use backup codes with sufficient entropy.

    Each code is 16 URL-safe random bytes (128 bits of entropy).
    Spec §3.3: 10 single-use codes, bcrypt hashed.
    """
    return [secrets.token_urlsafe(16) for _ in range(count)]


def hash_backup_code(code: str) -> str:
    """Hash a backup code using bcrypt (spec §3.3 requirement)."""
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_backup_code(code: str, hashed_codes: list[str]) -> tuple[bool, str | None]:
    """Verify a backup code against bcrypt-hashed codes.

    Returns (matched, matched_hash) so the caller can remove the used code.
    Backup codes are single-use — the matched hash must be deleted after use.
    """
    for hashed in hashed_codes:
        try:
            if bcrypt.checkpw(code.encode("utf-8"), hashed.encode("utf-8")):
                return True, hashed
        except Exception:
            continue
    return False, None
