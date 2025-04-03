from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
from ..llm_router.router import LLMRouter
import json
from api.utils.logger import logger

router = APIRouter()
llm_router = LLMRouter()

# Configuração do n8n webhook
N8N_WEBHOOK_URL = "https://neurolucas.app.n8n.cloud/webhook-test/02dbe3ee-757e-46e7-b9fa-5a2ba6267b6a"

class WhatsAppMessage(BaseModel):
    messageType: str
    text: Optional[str] = None
    phone: str
    instanceId: str
    messageId: str
    timestamp: int

async def send_to_n8n_webhook(phone: str, message: str, original_message: str):
    """
    Envia a resposta para o webhook do n8n usando método GET
    """
    try:
        # Formata o número do telefone
        if not phone.startswith("55"):
            phone = f"55{phone}"

        # Prepara os parâmetros para a query string
        params = {
            "phone": phone,  # número formatado
            "message": message,  # resposta do LLM
            "original_message": original_message,  # mensagem original recebida
            "instance_id": "megabusiness-MoYuzQehcPQ"  # ID da instância MegaAPI
        }

        logger.info(f"Enviando para n8n via GET: {json.dumps(params, indent=2)}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(N8N_WEBHOOK_URL, params=params)
            response.raise_for_status()
            logger.info(f"Resposta do n8n: {response.status_code}")
            return response

    except Exception as e:
        logger.error(f"Erro ao enviar para n8n: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            logger.error(f"Status code: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise e

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook para receber mensagens do WhatsApp
    """
    try:
        # Log do corpo da requisição bruto
        body = await request.body()
        logger.info(f"Corpo da requisição bruto: {body.decode()}")

        # Tenta fazer o parse do JSON
        try:
            payload = await request.json()
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {str(e)}")
            logger.error(f"Corpo da requisição que causou erro: {body.decode()}")
            return {"status": "error", "reason": "invalid_json"}

        logger.info(f"Webhook recebido: {json.dumps(payload, indent=2)}")

        # Verifica se é uma mensagem válida
        if not isinstance(payload, dict):
            logger.error(f"Payload inválido, não é um dicionário: {payload}")
            return {"status": "error", "reason": "invalid_payload"}

        # Verifica se é uma mensagem de texto e não é um ACK
        if payload.get("messageType") == "message.ack":
            logger.info("É uma mensagem de confirmação (ACK), ignorando")
            return {"status": "ignored", "reason": "ack_message"}

        # Verifica se tem a mensagem
        if not payload.get("message"):
            logger.info("Não é uma mensagem de texto, ignorando")
            return {"status": "ignored", "reason": "not_text_message"}

        # Extrai a mensagem do campo correto
        message_text = None
        message_data = payload.get("message", {})
        
        if isinstance(message_data, dict):
            if "extendedTextMessage" in message_data:
                message_text = message_data["extendedTextMessage"].get("text", "")
            elif "conversation" in message_data:
                message_text = message_data["conversation"]
            elif "text" in message_data:
                message_text = message_data["text"].get("message", "")

        # Se não houver mensagem de texto, ignora
        if not message_text:
            logger.info(f"Mensagem sem texto extraível: {json.dumps(message_data, indent=2)}")
            return {"status": "ignored", "reason": "no_text_content"}

        # Log da mensagem extraída
        logger.info(f"Mensagem extraída com sucesso: {message_text}")

        # Extrai informações da mensagem
        try:
            # Extrai o número do remetente do remoteJid
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
            
            # Log do número do remetente
            logger.info(f"Número do remetente: {phone}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair informações da mensagem: {str(e)}")
            return {"status": "error", "reason": "invalid_message_format"}

        # Processa a mensagem com o LLM Router
        try:
            logger.info(f"Iniciando processamento LLM Router para mensagem: {message.text}")
            
            # Força resposta em português do Brasil
            prompt_ptbr = f"""Por favor, responda em português do Brasil de forma natural e coloquial:

{message.text}

Lembre-se: Sua resposta DEVE ser em português do Brasil."""

            result = await llm_router.route_prompt(prompt_ptbr)
            logger.info(f"Resposta do LLM Router: {json.dumps(result, indent=2)}")

            # Envia para o n8n
            await send_to_n8n_webhook(message.phone, result["text"], message.text)
            logger.info("Mensagem enviada com sucesso para o n8n")

            return {
                "status": "success",
                "message": "Mensagem processada e enviada para o n8n"
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
        url = f"{MEGAAPI_BASE_URL}/rest/instance/status"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json"
        }
        params = {
            "instanceId": "megabusiness-MoYuzQehcPQ"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            status = response.json()

        return {
            "status": "success",
            "instance_id": "megabusiness-MoYuzQehcPQ",
            "whatsapp_status": status
        }

    except Exception as e:
        logger.error(f"Erro ao verificar status: {str(e)}")
        return {
            "status": "error",
            "instance_id": "megabusiness-MoYuzQehcPQ",
            "error": str(e)
        }