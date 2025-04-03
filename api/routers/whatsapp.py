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
        url = f"{MEGAAPI_BASE_URL}/message/text"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MEGAAPI_API_KEY}"
        }
        payload = {
            "id": MEGAAPI_INSTANCE_ID,
            "to": phone,
            "text": message
        }

        logger.info(f"Enviando mensagem para {phone}: {message}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Resposta do envio: {response.json()}")
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
        # Log do corpo da requisição bruto
        body = await request.body()
        logger.info(f"Corpo da requisição bruto: {body}")

        # Tenta fazer o parse do JSON
        try:
            payload = await request.json()
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {str(e)}")
            logger.error(f"Corpo da requisição que causou erro: {body}")
            return {"status": "error", "reason": "invalid_json"}

        logger.info(f"Webhook recebido: {json.dumps(payload, indent=2)}")

        # Verifica se é uma mensagem válida
        if not isinstance(payload, dict):
            logger.error(f"Payload inválido, não é um dicionário: {payload}")
            return {"status": "error", "reason": "invalid_payload"}

        # Verifica se é uma mensagem de texto
        if not payload.get("message"):
            logger.info("Não é uma mensagem de texto, ignorando")
            return {"status": "ignored", "reason": "not_text_message"}

        # Extrai a mensagem do campo correto
        message_text = None
        message_data = payload.get("message", {})
        
        if isinstance(message_data, dict):
            if "conversation" in message_data:
                message_text = message_data["conversation"]
            elif "text" in message_data:
                message_text = message_data["text"].get("message", "")

        # Se não houver mensagem de texto, ignora
        if not message_text:
            logger.info("Mensagem sem texto, ignorando")
            return {"status": "ignored", "reason": "no_text_content"}

        # Log da mensagem extraída
        logger.info(f"Mensagem extraída: {message_text}")

        # Extrai informações da mensagem
        try:
            phone = payload.get("key", {}).get("remoteJid", "").split("@")[0]
            # Remove o prefixo "55" se existir
            if phone.startswith("55"):
                phone = phone[2:]
                
            message = WhatsAppMessage(
                messageType=payload.get("messageType", "text"),
                text=message_text,
                phone=phone,
                instanceId=payload.get("instance_key", ""),
                messageId=payload.get("key", {}).get("id", ""),
                timestamp=payload.get("messageTimestamp", 0)
            )
        except Exception as e:
            logger.error(f"Erro ao extrair informações da mensagem: {str(e)}")
            return {"status": "error", "reason": "invalid_message_format"}

        # Gera ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Log da requisição recebida
        logger.info(f"Processando mensagem - ID: {request_id}")
        logger.info(f"Texto: {message.text}")

        try:
            # Processa a mensagem com o LLM Router
            result = await llm_router.route_prompt(message.text)
            logger.info(f"Resposta do LLM Router: {result}")
            
            # Analisa custos
            cost_analysis = analyze_cost(result["model"], message.text, result["text"])
            
            # Prepara resposta
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
            logger.error(f"Erro no processamento da mensagem: {str(e)}")
            return {"status": "error", "reason": str(e)}

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return {"status": "error", "reason": str(e)}

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