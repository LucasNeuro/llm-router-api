from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import requests
import os
import logging
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

MEGAAPI_TOKEN = os.getenv("MEGAAPI_TOKEN")
MEGAAPI_INSTANCE_KEY = os.getenv("MEGAAPI_INSTANCE_KEY")
MEGAAPI_BASE_URL = "https://apibusiness1.megaapi.com.br/api/v1"

async def send_whatsapp_message(phone: str, message: str):
    """Envia mensagem via MegaAPI"""
    url = f"{MEGAAPI_BASE_URL}/send-message"
    headers = {
        "Authorization": f"Bearer {MEGAAPI_TOKEN}",
        "Instance-Key": MEGAAPI_INSTANCE_KEY
    }
    payload = {
        "phone": phone,
        "message": message
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem WhatsApp: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao enviar mensagem")

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Recebe webhooks do WhatsApp via MegaAPI"""
    try:
        data = await request.json()
        logger.info(f"Webhook recebido: {data}")
        
        # Processa apenas mensagens recebidas
        if data.get("type") == "message" and not data.get("fromMe"):
            phone = data.get("from")
            message = data.get("body", "").strip()
            
            if message:
                # TODO: Integrar com o LLM Router para processar a mensagem
                # Por enquanto, apenas eco da mensagem
                await send_whatsapp_message(phone, f"Recebi sua mensagem: {message}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro no processamento do webhook") 