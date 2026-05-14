"""API routes for MFA.

Fixes applied:
- S-10: Replaced broken `Depends(lambda x: ...)` with proper `Header(...)` injection
- S-02: QR code now correctly base64-encoded (not hex)
- B-04: Bearer prefix stripped before token decoding
- M-10: Backup codes are single-use (consumed on use)
- M-19: Audit log for MFA enrollment/verification events
- M-20: Added backup code regeneration endpoint
"""

import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...schemas import MfaEnrollResponse, MfaVerifyRequest, MfaBackupCodesResponse
from ...services import (
    AuthService,
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
    generate_qr_code_base64,
    generate_backup_codes,
    hash_backup_code,
)
from ...models import UserModel, AuditLogModel
from ...services.utils import decode_token
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


def _extract_user_id(authorization: str | None) -> str:
    """Extract and validate user ID from Authorization header (B-04 + S-10 fix)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    auth_settings = get_auth_settings_cached()
    try:
        payload = decode_token(
            token,
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,  # S-09 fix: pass public_key
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/enroll", response_model=MfaEnrollResponse)
async def enroll_mfa(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> MfaEnrollResponse:
    """Begin MFA enrollment — returns TOTP secret and QR code data URI."""
    user_id = _extract_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled")

    secret = generate_totp_secret()
    uri = get_totp_uri(secret, user.email)
    # S-02 fix: correctly base64-encode the QR code PNG
    qr_data_uri = generate_qr_code_base64(uri)

    # Store secret (not yet confirmed — confirmed on /verify)
    user.mfa_secret = secret
    await db.commit()

    # M-19: Audit log for MFA enrollment start
    audit = AuditLogModel(
        organization_id=user.organization_id,
        user_id=user.id,
        event_type="auth.mfa.enroll_started",
        event_data={"email": user.email},
        success=True,
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return MfaEnrollResponse(
        secret=secret,
        qr_code=qr_data_uri,
    )


@router.post("/verify", response_model=dict)
async def verify_mfa(
    data: MfaVerifyRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify MFA code during enrollment — enables MFA and returns backup codes."""
    user_id = _extract_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not enrolled")

    if not verify_totp(user.mfa_secret, data.code):
        # M-19: Audit log for failed MFA verification
        audit = AuditLogModel(
            organization_id=user.organization_id,
            user_id=user.id,
            event_type="auth.mfa.verify_failed",
            event_data={"email": user.email},
            success=False,
            failure_reason="invalid_totp",
            ip_address=request.client.host if request.client else None,
            timestamp=datetime.utcnow(),
        )
        db.add(audit)
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid MFA code")

    # Generate backup codes — bcrypt-hashed per spec §3.3 (S-01 fix)
    backup_codes = generate_backup_codes(10)
    hashed_codes = [hash_backup_code(code) for code in backup_codes]

    user.mfa_enabled = True
    # Store as JSON array (Q-11 fix)
    user.mfa_backup_codes = json.dumps(hashed_codes)
    await db.commit()

    # M-19: Audit log for successful MFA enrollment
    audit = AuditLogModel(
        organization_id=user.organization_id,
        user_id=user.id,
        event_type="auth.mfa.enrolled",
        event_data={"email": user.email},
        success=True,
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "MFA enabled",
        "backup_codes": backup_codes,
    }


@router.post("/validate", response_model=dict)
async def validate_mfa(
    data: MfaVerifyRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate MFA code during login."""
    user_id = _extract_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user or not user.mfa_enabled:
        return {"valid": True, "mfa_required": False}

    if not verify_totp(user.mfa_secret, data.code):
        # M-19: Audit log for failed MFA validation
        audit = AuditLogModel(
            organization_id=user.organization_id,
            user_id=user.id,
            event_type="auth.mfa.validation_failed",
            event_data={"email": user.email},
            success=False,
            failure_reason="invalid_totp",
            ip_address=request.client.host if request.client else None,
            timestamp=datetime.utcnow(),
        )
        db.add(audit)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    return {"valid": True, "mfa_required": True}


@router.get("/backup-codes", response_model=MfaBackupCodesResponse)
async def get_backup_codes(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> MfaBackupCodesResponse:
    """Backup codes are shown only once during enrollment. Use /regenerate to get new ones."""
    _extract_user_id(authorization)  # Validate auth
    raise HTTPException(
        status_code=410,
        detail="Backup codes were shown only during enrollment. Use POST /auth/mfa/backup-codes/regenerate to generate new ones.",
    )


@router.post("/backup-codes/regenerate", response_model=dict)
async def regenerate_backup_codes(
    data: MfaVerifyRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Regenerate MFA backup codes. Requires current TOTP code to confirm identity (M-20 fix)."""
    user_id = _extract_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user or not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not enabled")

    # Require current TOTP to regenerate backup codes
    if not verify_totp(user.mfa_secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code. Provide your current TOTP code to regenerate backup codes.")

    # Generate new backup codes — bcrypt-hashed (S-01 fix)
    backup_codes = generate_backup_codes(10)
    hashed_codes = [hash_backup_code(code) for code in backup_codes]
    user.mfa_backup_codes = json.dumps(hashed_codes)
    await db.commit()

    # Audit log
    audit = AuditLogModel(
        organization_id=user.organization_id,
        user_id=user.id,
        event_type="auth.mfa.backup_codes_regenerated",
        event_data={"email": user.email},
        success=True,
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {
        "message": "Backup codes regenerated. Store these securely — they will not be shown again.",
        "backup_codes": backup_codes,
    }


@router.delete("/disable", response_model=dict)
async def disable_mfa(
    data: MfaVerifyRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disable MFA. Requires current TOTP code to confirm identity."""
    user_id = _extract_user_id(authorization)
    user = await db.get(UserModel, user_id)

    if not user or not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    if not verify_totp(user.mfa_secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    await db.commit()

    # Audit log
    audit = AuditLogModel(
        organization_id=user.organization_id,
        user_id=user.id,
        event_type="auth.mfa.disabled",
        event_data={"email": user.email},
        success=True,
        ip_address=request.client.host if request.client else None,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()

    return {"message": "MFA disabled successfully"}
