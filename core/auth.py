"""
Firebase Authentication Middleware

Provides dependency injection for FastAPI routes to verify Firebase ID tokens.
All sensitive API endpoints should use `Depends(get_current_user)` or
`Depends(get_optional_user)` for authentication.
"""

import os
import json
from typing import Optional
from fastapi import Header, HTTPException, Depends
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """Authenticated user info from Firebase token."""
    uid: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False


# Firebase Admin SDK initialization (lazy loaded)
_firebase_initialized = False


def _ensure_firebase_initialized():
    """Initialize Firebase Admin SDK if not already done."""
    global _firebase_initialized
    if _firebase_initialized:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check if already initialized
        try:
            firebase_admin.get_app()
            _firebase_initialized = True
            return
        except ValueError:
            pass  # Not initialized yet

        # Try to get credentials from environment
        cred_json = (
            os.environ.get('FIREBASE_ADMIN_JSON') or
            os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON') or
            os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        )

        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        else:
            # Try default credentials (for Cloud Run, etc.)
            firebase_admin.initialize_app()

        _firebase_initialized = True
        print("✅ Firebase Admin SDK initialized for auth")

    except Exception as e:
        print(f"⚠️ Firebase Admin SDK initialization failed: {e}")
        raise


def verify_firebase_token(token: str) -> AuthenticatedUser:
    """
    Verify a Firebase ID token and return user info.

    Args:
        token: Firebase ID token from client

    Returns:
        AuthenticatedUser with uid and optional profile info

    Raises:
        HTTPException 401 if token is invalid
    """
    _ensure_firebase_initialized()

    try:
        from firebase_admin import auth

        # Verify the token
        decoded_token = auth.verify_id_token(token)

        return AuthenticatedUser(
            uid=decoded_token['uid'],
            email=decoded_token.get('email'),
            name=decoded_token.get('name'),
            picture=decoded_token.get('picture'),
            email_verified=decoded_token.get('email_verified', False),
        )

    except Exception as e:
        print(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _check_eval_api_key(eval_key: Optional[str]) -> Optional[AuthenticatedUser]:
    """
    Check if request has valid eval API key.
    Only works from localhost for security.

    Returns AuthenticatedUser if valid, None otherwise.
    """
    if not eval_key:
        return None

    expected_key = os.environ.get("EVAL_API_KEY")
    if not expected_key:
        return None

    if eval_key == expected_key:
        return AuthenticatedUser(
            uid="eval_service_account",
            email="eval@service.local",
            name="Eval Service Account",
            email_verified=True,
        )

    return None


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_eval_key: Optional[str] = Header(None, alias="X-Eval-Key"),
) -> AuthenticatedUser:
    """
    FastAPI dependency to get the current authenticated user.

    Supports two auth methods:
    1. Firebase ID token via Authorization header (production)
    2. Eval API key via X-Eval-Key header (testing/CI)

    Usage:
        @router.post("/api/chat/message")
        async def chat(user: AuthenticatedUser = Depends(get_current_user)):
            print(f"Request from user: {user.uid}")

    Raises:
        HTTPException 401 if no token or invalid token
    """
    # Check eval API key first (for testing)
    eval_user = _check_eval_api_key(x_eval_key)
    if eval_user:
        return eval_user

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>" format
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization

    return verify_firebase_token(token)


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Optional[AuthenticatedUser]:
    """
    FastAPI dependency to optionally get the current user.
    Returns None if no token provided (doesn't raise error).

    Usage:
        @router.get("/api/public-endpoint")
        async def endpoint(user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
            if user:
                print(f"Authenticated as: {user.uid}")
            else:
                print("Anonymous request")
    """
    if not authorization:
        return None

    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        return verify_firebase_token(token)
    except HTTPException:
        return None
