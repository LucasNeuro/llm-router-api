import hmac
import hashlib
import os
import time
from typing import Dict, Any
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from loguru import logger
from api.llm_router.router import LLMRouter


router = APIRouter()

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")


def verify_slack_signature(signature: str, timestamp: str, body: bytes) -> bool:
    try:
        if not SLACK_SIGNING_SECRET:
            # Se não configurado, permitir (ambiente de dev)
            return True
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
        basestring = f"v0:{timestamp}:{body.decode()}".encode()
        digest = hmac.new(SLACK_SIGNING_SECRET.encode(), basestring, hashlib.sha256).hexdigest()
        expected = f"v0={digest}"
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


@router.post("/slack/events")
async def slack_events(
    request: Request,
    x_slack_signature: str = Header(default=""),
    x_slack_request_timestamp: str = Header(default="")
):
    try:
        raw_body = await request.body()

        # URL verification challenge
        try:
            payload = await request.json()
            if payload.get("type") == "url_verification":
                return {"challenge": payload.get("challenge")}
        except Exception:
            pass

        if not verify_slack_signature(x_slack_signature, x_slack_request_timestamp, raw_body):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")

        event = (await request.json()).get("event", {})
        if event.get("type") != "message" or event.get("bot_id"):
            return {"ok": True}

        text = event.get("text", "").strip()
        user = event.get("user")

        router_llm = LLMRouter()
        result = await router_llm.route_prompt(prompt=text, sender_phone=user)

        reply_text = result.get("text", "")
        return {"ok": True, "response": reply_text}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro nos eventos do Slack: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

