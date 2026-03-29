"""
Setup Routes

BYOK onboarding: user provides their API key and picks a provider.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from core.config import load_config, save_config

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupRequest(BaseModel):
    provider: str  # "gemini", "openai", "anthropic"
    api_key: str
    model: Optional[str] = None


PROVIDER_DEFAULTS = {
    "gemini": "gemini/gemini-2.5-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
}


@router.post("")
async def setup(request: SetupRequest):
    """Save user's API key and provider choice."""
    config = load_config()
    config["llm"] = {
        "provider": request.provider,
        "api_key": request.api_key,
        "model": request.model or PROVIDER_DEFAULTS.get(request.provider, "gpt-4o"),
    }
    save_config(config)

    return JSONResponse({
        "success": True,
        "provider": request.provider,
        "model": config["llm"]["model"],
    })


@router.get("/status")
async def setup_status():
    """Check if OpenPriors is configured."""
    config = load_config()
    has_key = bool(config.get("llm", {}).get("api_key"))

    return JSONResponse({
        "configured": has_key,
        "provider": config.get("llm", {}).get("provider"),
        "model": config.get("llm", {}).get("model"),
    })
