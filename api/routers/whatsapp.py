from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
from ..llm_router.router import LLMRouter
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import save_llm_data
import uuid
import json
from api.utils.logger import logger

router = APIRouter()
llm_router = LLMRouter()

# Configurações da MegaAPI
MEGAAPI_INSTANCE_ID = os.getenv("MEGAAPI_INSTANCE_ID")
MEGAAPI_API_KEY = os.getenv("MEGAAPI_API_KEY")
MEGAAPI_BASE_URL = os.getenv("MEGAAPI_BASE_URL", "https://apibusiness1.megaapi.com.br")

if not MEGAAPI_INSTANCE_ID or not MEGAAPI_API_KEY:
    raise ValueError("MEGAAPI_INSTANCE_ID e MEGAAPI_API_KEY precisam estar configurados")

class WhatsAppMessage(BaseModel):
    messageType: str
    text: Optional[str] = None
    phone: str
    instanceId: str
    messageId: str
    timestamp: int

async def send_whatsapp_message(phone: str, message: str):
    """
    Envia mensagem via MegaAPI
    """
    try:
        url = f"{MEGAAPI_BASE_URL}/instances/{MEGAAPI_INSTANCE_ID}/messages/text"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MEGAAPI_API_KEY}"
        }
        payload = {
            "phone": phone,
            "message": message,
            "quotedMessageId": None
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem WhatsApp: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar mensagem: {str(e)}")

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook para receber mensagens do WhatsApp
    """
    try:
        # Recebe o payload
        payload = await request.json()
        logger.info(f"Webhook recebido: {json.dumps(payload, indent=2)}")

        # Valida a mensagem
        if not payload.get("text"):
            return {"status": "ignored", "reason": "not_text_message"}

        # Extrai informações da mensagem
        message = WhatsAppMessage(
            messageType=payload.get("messageType", "text"),
            text=payload.get("text", {}).get("message", ""),
            phone=payload.get("phone", ""),
            instanceId=payload.get("instanceId", ""),
            messageId=payload.get("messageId", ""),
            timestamp=payload.get("timestamp", 0)
        )

        # Gera ID único para a requisição
        request_id = str(uuid.uuid4())

        # Processa a mensagem com o LLM Router
        result = await llm_router.route_prompt(message.text)
        
        # Analisa custos
        cost_analysis = analyze_cost(message.text, result["text"], result["model"])

        # Salva no Supabase
        await save_llm_data(
            prompt=message.text,
            response=result["text"],
            model=result["model"],
            success=result["success"],
            confidence=result.get("confidence"),
            scores=result.get("model_scores", {}),
            indicators=result.get("indicators", {}),
            cost_analysis=cost_analysis,
            request_id=request_id
        )

        # Envia resposta via WhatsApp
        await send_whatsapp_message(message.phone, result["text"])

        return {
            "status": "success",
            "request_id": request_id,
            "model_used": result["model"],
            "message_sent": True
        }

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/status")
async def whatsapp_status():
    """
    Verifica status da conexão com WhatsApp
    """
    try:
        url = f"{MEGAAPI_BASE_URL}/instances/{MEGAAPI_INSTANCE_ID}/status"
        headers = {"Authorization": f"Bearer {MEGAAPI_API_KEY}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            status = response.json()

        return {
            "status": "success",
            "instance_id": MEGAAPI_INSTANCE_ID,
            "whatsapp_status": status
        }

    except Exception as e:
        logger.error(f"Erro ao verificar status: {str(e)}")
        return {
            "status": "error",
            "instance_id": MEGAAPI_INSTANCE_ID,
            "error": str(e)
        }