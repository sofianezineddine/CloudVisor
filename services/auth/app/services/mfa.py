"""TOTP-based MFA service."""

import pyotp
import qrcode
import secrets
from io import BytesIO
from typing import Any


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
    """Generate QR code image for TOTP URI."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate single-use backup codes."""
    return [secrets.token_hex(4).upper() for _ in range(count)]


def verify_backup_code(code: str, hashed_codes: list[str]) -> bool:
    """Verify a backup code against hashed codes."""
    import hashlib

    code_hash = hashlib.sha256(code.encode()).hexdigest()
    return code_hash in hashed_codes
