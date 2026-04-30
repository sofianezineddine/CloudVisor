"""API routes for MFA."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...schemas import MfaEnrollResponse, MfaVerifyRequest, MfaBackupCodesResponse
from ...services import (
    AuthService,
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
    generate_qr_code,
    generate_backup_codes,
)
from ...models import UserModel
from ...services.utils import decode_token


router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


def get_current_user_id(authorization: str) -> str:
    """Extract user ID from authorization token."""
    auth_settings = get_auth_settings_cached()
    payload = decode_token(authorization, auth_settings.secret_key)
    return payload.get("sub")


@router.post("/enroll", response_model=MfaEnrollResponse)
async def enroll_mfa(
    authorization: str = Depends(lambda x: x.headers.get("Authorization", "")),
    db: AsyncSession = Depends(get_db),
) -> MfaEnrollResponse:
    """Begin MFA enrollment."""
    user_id = get_current_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled")

    secret = generate_totp_secret()
    uri = get_totp_uri(secret, user.email)
    qr_code = generate_qr_code(uri)

    user.mfa_secret = secret
    await db.commit()

    return MfaEnrollResponse(
        secret=secret,
        qr_code=f"data:image/png;base64,{qr_code.hex()}",
    )


@router.post("/verify", response_model=dict)
async def verify_mfa(
    data: MfaVerifyRequest,
    authorization: str = Depends(lambda x: x.headers.get("Authorization", "")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify MFA code during enrollment."""
    user_id = get_current_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not enrolled")

    if not verify_totp(user.mfa_secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")

    backup_codes = generate_backup_codes()
    import hashlib

    hashed_codes = [hashlib.sha256(code.encode()).hexdigest() for code in backup_codes]

    user.mfa_enabled = True
    user.mfa_backup_codes = ",".join(hashed_codes)
    await db.commit()

    return {
        "status": "MFA enabled",
        "backup_codes": backup_codes,
    }


@router.post("/validate", response_model=dict)
async def validate_mfa(
    data: MfaVerifyRequest,
    authorization: str = Depends(lambda x: x.headers.get("Authorization", "")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate MFA code during login."""
    from ...services.utils import decode_token

    auth_settings = get_auth_settings_cached()
    payload = decode_token(authorization.replace("Bearer ", ""), auth_settings.secret_key)
    user_id = payload.get("sub")

    user = await db.get(UserModel, user_id)
    if not user or not user.mfa_enabled:
        return {"valid": True, "mfa_required": False}

    if not verify_totp(user.mfa_secret, data.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    return {"valid": True, "mfa_required": True}


@router.get("/backup-codes", response_model=MfaBackupCodesResponse)
async def get_backup_codes(
    authorization: str = Depends(lambda x: x.headers.get("Authorization", "")),
    db: AsyncSession = Depends(get_db),
) -> MfaBackupCodesResponse:
    """Get MFA backup codes (only shown once on enrollment)."""
    user_id = get_current_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user or not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not enabled")

    raise HTTPException(
        status_code=410,
        detail="Backup codes were shown only during enrollment. Generate new ones.",
    )
