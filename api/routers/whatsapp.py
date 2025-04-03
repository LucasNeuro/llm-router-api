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

        # Extrai a mensagem do campo correto
        message_text = None
        if payload.get("message", {}).get("conversation"):
            message_text = payload["message"]["conversation"]
        elif payload.get("message", {}).get("text"):
            message_text = payload["message"]["text"].get("message", "")

        # Se não houver mensagem de texto, ignora
        if not message_text:
            return {"status": "ignored", "reason": "not_text_message"}

        # Extrai informações da mensagem
        message = WhatsAppMessage(
            messageType=payload.get("messageType", "text"),
            text=message_text,
            phone=payload.get("key", {}).get("remoteJid", "").split("@")[0],
            instanceId=payload.get("instance_key", ""),
            messageId=payload.get("key", {}).get("id", ""),
            timestamp=payload.get("messageTimestamp", 0)
        )

        # Gera ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Log da requisição recebida
        logger.info(f"Processando mensagem - ID: {request_id}")
        logger.info(f"Texto: {message.text}")

        # Processa a mensagem com o LLM Router (mesmo padrão do chat)
        result = await llm_router.route_prompt(message.text)
        
        # Analisa custos
        cost_analysis = analyze_cost(result["model"], message.text, result["text"])
        
        # Prepara resposta no mesmo formato do chat
        response_data = {
            "text": result["text"],
            "model": result["model"],
            "success": result["success"],
            "confidence": result.get("confidence"),
            "model_scores": result.get("model_scores"),
            "indicators": result.get("indicators"),
            "cost_analysis": cost_analysis
        }

        # Salva no Supabase
        await save_llm_data(
            prompt=message.text,
            response=response_data["text"],
            model=response_data["model"],
            success=response_data["success"],
            confidence=response_data["confidence"],
            scores=response_data["model_scores"] or {},
            indicators=response_data["indicators"] or {},
            cost_analysis=cost_analysis,
            request_id=request_id
        )

        # Envia resposta via WhatsApp
        await send_whatsapp_message(message.phone, response_data["text"])

        return {
            "status": "success",
            "request_id": request_id,
            "model_used": response_data["model"],
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